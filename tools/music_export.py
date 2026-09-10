"""Export owned MP/MV music packs to MIDI, sample WAVs and instrument metadata.

Read-only, offline tooling. MIDI program numbers refer to the accompanying VAB
bank, not General MIDI. Sample WAVs use a 44100 Hz reference rate. Tone tuning
and envelope metadata are retained; tuning, envelopes and reverb are not rendered.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unpack_pack(data):
    require(len(data) >= 4, 'Truncated pack')
    first = struct.unpack_from('<I', data)[0]
    require(4 <= first <= len(data) and first % 4 == 0, 'Invalid pack directory')
    offsets = list(struct.unpack_from(f'<{first // 4}I', data)) + [len(data)]
    require(all(a < b for a, b in zip(offsets, offsets[1:])), 'Overlapping pack entries')
    return [data[a:b] for a, b in zip(offsets, offsets[1:])]


def vlq(data, position):
    value = 0
    for _ in range(4):
        require(position < len(data), 'Truncated MIDI delta/length')
        byte = data[position]; position += 1
        value = (value << 7) | (byte & 127)
        if byte < 128:
            return value, position
    raise ValueError('MIDI variable-length value exceeds four bytes')


def midi_events(data, psx=False):
    """Parse events and resolve running status into an explicit event timeline."""
    position = tick = running = 0
    result = []
    while position < len(data):
        delta, position = vlq(data, position); tick += delta
        require(position < len(data), 'Missing MIDI event')
        status = data[position]
        if status >= 128:
            position += 1
            running = status if status < 240 else 0
        else:
            require(running != 0, 'MIDI data without running status')
            status = running
        if status == 255:
            require(position < len(data), 'Truncated MIDI meta event')
            kind = data[position]; position += 1
            if psx and kind == 0x51:
                size = 3  # Sony omits SMF's tempo payload-length byte.
            else:
                size, position = vlq(data, position)
            require(position + size <= len(data), 'Truncated MIDI meta payload')
            payload = data[position:position + size]; position += size
            require(kind != 0x51 or size == 3, 'Invalid tempo event')
            result.append(dict(tick=tick, status=status, meta=kind, data=list(payload)))
            if kind == 0x2f:
                require(size == 0 and position == len(data), 'Invalid end-of-track boundary')
                return result
        elif status in (0xf0, 0xf7):
            size, position = vlq(data, position)
            require(position + size <= len(data), 'Truncated MIDI SysEx')
            result.append(dict(tick=tick, status=status, data=list(data[position:position + size])))
            position += size
        else:
            require(0x80 <= status < 0xf0, 'Unsupported MIDI system event')
            size = 1 if status & 0xf0 in (0xc0, 0xd0) else 2
            payload = data[position:position + size]; position += size
            require(len(payload) == size and all(x < 128 for x in payload), 'Invalid MIDI channel payload')
            result.append(dict(tick=tick, status=status, data=list(payload)))
    raise ValueError('Missing MIDI end-of-track')


def encode_vlq(value):
    require(0 <= value <= 0x0fffffff, 'MIDI delta outside VLQ range')
    out = [value & 127]
    while value >> 7:
        value >>= 7; out.insert(0, (value & 127) | 128)
    return bytes(out)


def encode_events(events):
    out = bytearray(); last = 0
    for event in events:
        out.extend(encode_vlq(event['tick'] - last)); last = event['tick']
        out.append(event['status'])
        if event['status'] == 255:
            out.append(event['meta']); out.extend(encode_vlq(len(event['data'])))
        elif event['status'] in (0xf0, 0xf7):
            out.extend(encode_vlq(len(event['data'])))
        out.extend(event['data'])
    return bytes(out)


def sequences(data):
    require(data[:6] == b'pQES\0\0', 'Expected SEP version 0')
    position = 6
    result = []
    while position < len(data):
        if len(data) - position <= 3 and not any(data[position:]):
            break
        require(position + 13 <= len(data), 'Truncated SEP sequence header')
        header = data[position:position + 13]
        identity, resolution = struct.unpack_from('>2H', header)
        tempo = int.from_bytes(header[4:7], 'big')
        numerator, denominator = header[7:9]
        size = int.from_bytes(header[9:13], 'big'); position += 13
        require(0 < resolution < 0x8000 and tempo > 0 and numerator > 0 and denominator <= 7,
                'Invalid sequence timing')
        require(position + size <= len(data), 'Sequence extends beyond pack')
        body = data[position:position + size]; position += size
        events = midi_events(body, psx=True)
        track = b'\0\xff\x51\x03' + header[4:7]
        track += b'\0\xff\x58\x04' + bytes((numerator, denominator, 24, 8)) + encode_events(events)
        midi = b'MThd' + struct.pack('>I3H', 6, 0, 1, resolution)
        midi += b'MTrk' + struct.pack('>I', len(track)) + track
        seconds = 0.0; last = 0; current_tempo = tempo
        programs = [0] * 16; usage = {}; controls = []
        for event in events:
            seconds += (event['tick'] - last) * current_tempo / (resolution * 1000000)
            last = event['tick']; status = event['status']; payload = event['data']
            if status == 255 and event['meta'] == 0x51:
                current_tempo = int.from_bytes(bytes(payload), 'big')
                require(current_tempo > 0, 'Zero MIDI tempo')
            elif status & 0xf0 == 0xc0:
                programs[status & 15] = payload[0]
            elif status & 0xf0 == 0x90 and payload[1]:
                key = (status & 15, programs[status & 15])
                row = usage.setdefault(key, dict(channel=key[0], program=key[1], notes=0,
                                                lowest=127, highest=0))
                row['notes'] += 1; row['lowest'] = min(row['lowest'], payload[0])
                row['highest'] = max(row['highest'], payload[0])
            elif status & 0xf0 == 0xb0:
                controls.append(dict(tick=last, channel=status & 15, controller=payload[0], value=payload[1]))
        result.append((dict(id=identity, ticks_per_quarter=resolution, initial_tempo_us=tempo,
                            time_signature=[numerator, 2 ** denominator], ticks=last,
                            seconds_one_pass=seconds, event_count=len(events),
                            program_usage=list(usage.values()), controllers=controls), midi))
    require(result and len({row[0]['id'] for row in result}) == len(result), 'Empty or duplicate SEP sequence IDs')
    return result


def decode_adpcm(data):
    require(data and len(data) % 16 == 0, 'Incomplete SPU ADPCM blocks')
    coefficients = ((0, 0), (60, 0), (115, -52), (98, -55), (122, -60))
    pcm = []; previous = older = 0; loop_start = None
    for offset in range(0, len(data), 16):
        shift, predictor = data[offset] & 15, data[offset] >> 4
        flags = data[offset + 1]
        require(shift <= 12 and predictor < 5 and flags < 8, 'Unsupported SPU ADPCM block')
        if flags & 4:
            loop_start = len(pcm)
        a, b = coefficients[predictor]
        for byte in data[offset + 2:offset + 16]:
            for nibble in (byte & 15, byte >> 4):
                signed = nibble if nibble < 8 else nibble - 16
                value = (signed << 12) >> shift
                value += (previous * a + older * b + 32) >> 6
                value = max(-32768, min(32767, value))
                older, previous = previous, value; pcm.append(value)
        if flags & 1:
            loop = [loop_start, len(pcm)] if flags & 2 and loop_start is not None else None
            return pcm, loop, offset + 16
    raise ValueError('Sample has no end block')


def wav_bytes(pcm, loop=None):
    def chunk(tag, payload):
        return tag + struct.pack('<I', len(payload)) + payload + (b'\0' if len(payload) % 2 else b'')
    body = b'WAVE' + chunk(b'fmt ', struct.pack('<HHIIHH', 1, 1, 44100, 88200, 2, 16))
    body += chunk(b'data', struct.pack(f'<{len(pcm)}h', *pcm))
    if loop:
        # WAV smpl end is inclusive; manifest end is exclusive.
        body += chunk(b'smpl', struct.pack('<9I', 0, 0, round(1e9 / 44100), 60, 0, 0, 0, 1, 0)
                      + struct.pack('<6I', 0, 0, loop[0], loop[1] - 1, 0, 0))
    return b'RIFF' + struct.pack('<I', len(body)) + body


def bank(header, body):
    require(len(header) >= 0x820 and header[:4] == b'pBAV', 'Missing VAB header')
    version, identity, total = struct.unpack_from('<3I', header, 4)
    programs, tones, samples = struct.unpack_from('<3H', header, 18)
    require(version == 7 and 0 < programs <= 128 and samples <= 254, 'Unsupported VAB version/counts')
    size_table = 0x820 + programs * 512
    require(len(header) == size_table + 512 and total == len(header) + len(body), 'VAB extent mismatch')
    sizes = struct.unpack_from('<256H', header, size_table)
    require(sizes[0] == 0 and not any(sizes[samples + 1:]) and sum(sizes) * 8 == len(body), 'VAB sample sizes mismatch')
    metadata = []; waves = []; position = 0
    for number, size in enumerate(sizes[1:samples + 1], 1):
        length = size * 8
        pcm, loop, consumed = decode_adpcm(body[position:position + length])
        metadata.append(dict(id=number, body_offset=position, adpcm_bytes=length,
                             consumed_adpcm_bytes=consumed, frames=len(pcm), loop_frames=loop,
                             wav=f'sample-{number:03}.wav'))
        waves.append(wav_bytes(pcm, loop)); position += length
    instruments = []; tone_slot = 0
    for program in range(128):
        p = header[32 + program * 16:48 + program * 16]
        if not p[0]:
            continue
        require(p[0] <= 16 and tone_slot < programs, 'Invalid program tone count')
        rows = []
        for i in range(p[0]):
            t = header[0x820 + tone_slot * 512 + i * 32:0x840 + tone_slot * 512 + i * 32]
            adsr1, adsr2, owner, sample = struct.unpack_from('<4H', t, 16)
            require(owner == program and 1 <= sample <= samples and t[6] <= t[7], 'Invalid tone mapping')
            rows.append(dict(sample=sample, volume=t[2], pan=t[3], root_key=t[4],
                             fine_tuning=t[5], key_min=t[6], key_max=t[7], mode=t[1],
                             pitch_bend_down=t[12], pitch_bend_up=t[13], adsr1=adsr1, adsr2=adsr2,
                             vibrato=list(t[8:10]), portamento=list(t[10:12])))
        instruments.append(dict(program=program, volume=p[1], pan=p[4], tones=rows)); tone_slot += 1
    require(tone_slot == programs and sum(len(p['tones']) for p in instruments) == tones, 'VAB program/voice count mismatch')
    return dict(version=version, id=identity, master_volume=header[24], master_pan=header[25],
                sample_bytes=len(body), programs=instruments, samples=metadata), waves


def export(mp, mv, output):
    mp_data, mv_data = mp.read_bytes(), mv.read_bytes()
    parts, bodies = unpack_pack(mp_data), unpack_pack(mv_data)
    headers = [p for p in parts if p.startswith(b'pBAV')]
    scores = [p for p in parts if p.startswith(b'pQES')]
    require(len(headers) == 1 and len(scores) == 1 and len(parts) == 2 and len(bodies) == 1,
            'Expected one VAB header, one SEP and one sample body')
    instrument_bank, waves = bank(headers[0], bodies[0])
    songs = sequences(scores[0])
    available_programs = {p['program'] for p in instrument_bank['programs']}
    for meta, _ in songs:
        meta['unmapped_programs'] = sorted({p['program'] for p in meta['program_usage']}
                                           - available_programs)
    report = dict(inputs={mp.name: hashlib.sha256(mp_data).hexdigest(), mv.name: hashlib.sha256(mv_data).hexdigest()},
                  bank=instrument_bank, sequences=[s[0] for s in songs],
                  notes=['Program numbers are bank-specific, not General MIDI.',
                         'MIDI controllers are preserved verbatim; sequence loops are not expanded.',
                         'WAVs are untuned 44100 Hz samples, without tone ADSR or reverb.'])
    require(not output.exists(), 'Choose a new output directory')
    require(mp.name != mv.name, 'Input basenames must differ')
    output.mkdir(parents=True)
    for meta, midi in songs:
        (output / f'sequence-{meta["id"]:03}.mid').write_bytes(midi)
    for meta, wav in zip(instrument_bank['samples'], waves):
        (output / meta['wav']).write_bytes(wav)
    (output / 'music.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mp', type=Path)
    parser.add_argument('mv', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = export(args.mp, args.mv, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Exported {len(report['sequences'])} sequences and {len(report['bank']['samples'])} samples to {args.output}")


if __name__ == '__main__':
    main()
