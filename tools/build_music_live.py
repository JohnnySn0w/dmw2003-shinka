"""Build local music-only replacement sample tables from owned exported banks.

This is an instrument palette, not offline song playback: the game's SPU drives
the resulting samples. CC0 SoundFonts are build inputs only. No game data belongs
in Git. Default voice choices outside Asuka are provisional and recorded for review.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import wave

import numpy as np
from music_export import require, unpack_pack
from music_fetch_banks import CATALOG, checked
from music_chip import blep
from music_routing import ROUTING, bank_overrides

RATE = 44100
ROOT = Path(__file__).resolve().parents[1]
MIX = dict(revision=3, melodic_rms_ceiling=.50, percussion_rms_ceiling=.22,
           minimum_rms=.025, peak_ceiling=.80, presence_db=3., presence_hz=2200,
           ds_cutoff_hz=12000, ds_percussion_cutoff_hz=8000)


def reference_pitch(root, instrument):
    # Avoid rendering a high VAB root and then slowing it down again in the
    # SPU: that discards harmonics and lowers every sample-domain filter cutoff.
    # Unpitched drums retain their existing key-map compensation.
    reference = 48. if instrument == 'bass' else 60.
    reference = max(reference, root - 48.) # bound unusually high automatic bass routes
    ratio = round(65536 * 2 ** ((root - reference) / 12))
    require(2048 <= ratio <= 2097152, 'Replacement pitch ratio outside supported range')
    return reference, ratio


def rms(pcm):
    return float(np.sqrt(np.mean(np.asarray(pcm, dtype=np.float64)**2)))


def lowpass(pcm, cutoff):
    taps = np.sinc(2*cutoff/RATE*(np.arange(31)-15))*np.hamming(31)
    taps /= taps.sum()
    return np.convolve(pcm, taps, mode='same')


def presence(pcm, instrument):
    # Sample-domain presence shelf, before the native SPU pitch/envelope. Keep
    # drums and bass unboosted so snare brightness cannot bury the melody again.
    if instrument in ('drums', 'bass'):
        return pcm
    high = pcm-lowpass(pcm, MIX['presence_hz'])
    return pcm+(10**(MIX['presence_db']/20)-1)*high


def level_target(original, instrument):
    # The old universal .22 RMS ceiling disproportionately attenuated strong
    # melodic source samples. Preserve their source level up to a safer ceiling;
    # drums retain their previous target and every wave retains peak headroom.
    ceiling = MIX['percussion_rms_ceiling' if instrument=='drums' else 'melodic_rms_ceiling']
    return min(ceiling, max(MIX['minimum_rms'], rms(original)))


def loop_wave(pcm, root, looping):
    pcm = np.asarray(pcm, dtype=np.float64)
    if not looping:
        pcm[-441:] *= np.linspace(1, 0, 441)
        return pcm, 0xffffffff
    # Use an integer number of nominal periods and an overlap crossfade. The
    # latter handles sample-bank modulation as well as non-periodic textures.
    period = RATE / (440 * 2 ** ((root - 69) / 12))
    end = len(pcm)
    span = max(4096, round(round((end // 2) / period) * period))
    span = min(span, end - 2048)
    start = end - span
    fade = min(2048, start, span // 2)
    blend = np.linspace(0, 1, fade, endpoint=False)
    pcm[end-fade:end] = pcm[end-fade:end] * (1-blend) + pcm[start-fade:start] * blend
    return pcm, start


def normalized(pcm, target):
    peak = float(np.max(np.abs(pcm)))
    rms = float(np.sqrt(np.mean(pcm * pcm)))
    require(peak > 1e-7 and rms > 1e-8, 'Silent live instrument')
    pcm = pcm * min(target / rms, MIX['peak_ceiling'] / peak)
    return np.rint(np.clip(pcm, -1, 1) * 32767).astype('<i2')


class Instruments:
    def __init__(self, directory):
        from importlib.metadata import version
        require(version('tinysoundfont') == '0.3.7', 'Install pinned tinysoundfont 0.3.7')
        from tinysoundfont import Synth
        self.synth = Synth(gain=-12, samplerate=RATE)
        self.channels = {}
        for channel, (name, bank) in enumerate(json.loads(CATALOG.read_text())['banks'].items()):
            data = checked((directory / f'{name}.sf2').read_bytes(), bank['sha256'])
            sfid = self.synth.sfload(data)
            self.synth.program_select(channel, sfid, 0, 0, is_drums=False)
            self.channels[name] = channel
        self.cache = {}

    def sampled(self, name, root, drum_key=None):
        cache_key = name, root, drum_key
        if cache_key in self.cache:
            return self.cache[cache_key].copy()
        ch = self.channels[name]
        self.synth.sounds_off()
        # Pick an actual populated key, then tune to the original VAB root.
        key = drum_key if name == 'drums' else 35 if name == 'bass' else 60
        self.synth.set_tuning(ch, root - key)
        self.synth.noteon(ch, key, 100)
        pcm = np.frombuffer(self.synth.generate_simple(RATE), dtype=np.float32).reshape(-1, 2).mean(axis=1)
        require(np.max(np.abs(pcm)) > 1e-7, f'Silent sampled route {name} {key}')
        self.cache[cache_key] = pcm
        return pcm.copy()


def chip(root, kind, seed):
    t = np.arange(RATE) / RATE
    freq = 440 * 2 ** ((root - 69) / 12)
    step = min(.45, freq / RATE)
    phase = np.arange(RATE) * step % 1
    if kind in ('pulse', 'square'):
        duty = .25 if kind == 'pulse' else .5
        return (np.where(phase < duty, 1., -1.) + blep(phase, step)
                - blep((phase-duty) % 1, step) - (2*duty-1))
    if kind == 'triangle':
        return 1 - 4 * np.abs(phase-.5)
    if kind == 'noise':
        return np.random.default_rng(seed).uniform(-1, 1, RATE) * np.exp(-t*16)
    if kind in ('kick', 'tom'):
        return np.sin(2*np.pi*(freq*t + 60*.025*(1-np.exp(-t/.025)))) * np.exp(-t*16)
    table_phase = np.floor(phase*32) / 32 * 2*np.pi
    return np.round(((np.sin(table_phase)+.28*np.sin(3*table_phase))/1.28)*31)/31


def build(exports, inputs, bank_dir, output):
    require(not output.exists(), 'Choose a new output directory')
    profiles = json.loads((ROOT/'assets/music/bgm001-audition.json').read_text())['programs']
    routing_data = ROUTING.read_bytes()
    routing_profile = json.loads(routing_data)
    synth = Instruments(bank_dir)
    blobs = []
    report = []
    for folder in sorted(exports.iterdir()):
        if not (folder/'music.json').exists():
            continue
        meta = json.loads((folder/'music.json').read_text())
        name = folder.name
        mp = [p/f'MP{name}.BIN' for p in inputs if (p/f'MP{name}.BIN').exists()]
        mv = [p/f'MV{name}.BIN' for p in inputs if (p/f'MV{name}.BIN').exists()]
        require(len(mp)==len(mv)==1, f'Need unique owned MP/MV inputs for {name}')
        require(hashlib.sha256(mp[0].read_bytes()).hexdigest()==meta['inputs'][mp[0].name], 'MP export mismatch')
        require(hashlib.sha256(mv[0].read_bytes()).hexdigest()==meta['inputs'][mv[0].name], 'MV export mismatch')
        overrides = bank_overrides(name, meta, routing_profile)
        body, = unpack_pack(mv[0].read_bytes())
        samples = []
        routes = []
        for sample in meta['bank']['samples']:
            owners = [(p['program'], t) for p in meta['bank']['programs'] for t in p['tones'] if t['sample']==sample['id']]
            if not owners:
                continue
            program, tone = owners[0]
            root = tone['root_key'] + tone['fine_tuning']/128
            percussion = tone['key_min']==tone['key_max']
            original_route = profiles.get(str(program)) if name=='BGM001' else None
            override = overrides.get(str(sample['id']))
            if override:
                instrument, oscillator = override['soundfont'], override['chip']
            elif original_route:
                instrument, oscillator = original_route['soundfont'], original_route['chip']
            elif percussion:
                instrument, oscillator = 'drums', 'drums'
            else:
                instrument = ('bass' if program==1 else 'strings' if program==2 else 'clarinet' if program%3==0 else 'piano')
                oscillator = 'triangle' if instrument=='bass' else 'pulse' if instrument=='clarinet' else 'wave'
            drum_key = None
            render_root = root
            playback_ratio = 65536
            if instrument=='drums':
                note = tone['key_min']
                gm = int(original_route.get('key_map', {}).get(str(note), note)) if original_route else note
                drum_key = {35:48,36:48,38:50,42:54,46:54,49:55,52:55,45:57,47:59,50:61}.get(gm,50)
                # Drum preset keys are samples, not a chromatic scale. Cancel
                # the VAB note-to-root offset so the triggered drum stays tuned.
                render_root = drum_key + root - note
                oscillator = 'kick' if gm in (35,36) else 'tom' if gm in (41,43,45,47,48,50) else 'noise'
            else:
                render_root, playback_ratio = reference_pitch(root, instrument)
            sampled = synth.sampled(instrument, render_root, drum_key)
            chip_root = ((root if not percussion else (33 if oscillator=='kick' else 48) + root-tone['key_min'])
                         if instrument == 'drums' else render_root)
            generated = chip(chip_root, oscillator, sample['id'])
            looping = sample['loop_frames'] is not None
            sampled, loop = loop_wave(presence(sampled, instrument), root if instrument == 'drums' else render_root, looping)
            generated, chip_loop = loop_wave(presence(generated, instrument), chip_root, looping)
            with wave.open(str(folder/sample['wav'])) as f:
                original = np.frombuffer(f.readframes(f.getnframes()), dtype='<i2').astype(np.float64)/32768
            target = level_target(original, instrument)
            sampled = normalized(sampled, target)
            generated = normalized(generated, target)
            # Compact hybrid with an audible synthetic component. Unlike the
            # offline Asuka profile, this runs per sample, not per MIDI part.
            ds = (.7*sampled.astype(np.float64) + .3*generated.astype(np.float64))/32767
            # Finite low-pass, preserving the shared loop and source pitch.
            ds = lowpass(ds, MIX['ds_percussion_cutoff_hz'] if instrument == 'drums' else MIX['ds_cutoff_hz'])
            # Filtering and phase cancellation previously made DS quieter than
            # its component palettes. Restore the intended level after the blend.
            ds = (np.rint(np.clip(ds, -1, 1)*32767).astype('<i2')
                  if instrument=='drums' else normalized(ds, target))
            role = 2 if instrument == 'drums' else 1 if instrument == 'bass' else 0
            row = struct.pack('<III', sample['body_offset'], role, playback_ratio)
            for pcm, start in ((ds,loop),(sampled,loop),(generated,chip_loop)):
                row += struct.pack('<II',len(pcm),start)+pcm.tobytes()
            samples.append(row)
            routes.append(dict(sample=sample['id'], program=program, root=root, render_root=render_root,
                               playback_ratio_q16=playback_ratio, soundfont=instrument,
                               chip=oscillator, source_loop=looping, shared_tone_count=len(owners),
                               original_rms=rms(original), target_rms=target,
                               palette_rms={key:rms(pcm.astype(np.float64)/32767)
                                            for key,pcm in [('ds',ds),('sampled',sampled),('chip',generated)]},
                               routing='guarded sample override' if override else 'Asuka profile by sample' if original_route else 'provisional automatic'))
            if override:
                routes[-1]['routing_reason'] = override['reason']
        blobs.append(struct.pack('<II',len(body),len(samples))+body+b''.join(samples))
        report.append(dict(bank=name, source_sha256=meta['inputs'], samples=routes))
        print(f'{name}: {len(samples)} live instruments',flush=True)
    require(blobs, 'No exported banks found')
    output.mkdir(parents=True)
    data = b'SHKMUS03'+struct.pack('<II',RATE,len(blobs))+b''.join(blobs)
    (output/'music-live.bin').write_bytes(data)
    (output/'music-live.json').write_text(json.dumps(dict(schema=1,sha256=hashlib.sha256(data).hexdigest(),
        sample_rate=RATE,pack_format='SHKMUS03',mix=MIX,banks=report,cc0_banks=json.loads(CATALOG.read_text()),
        live_routing_sha256=hashlib.sha256(routing_data).hexdigest(),
        limitations=['Provisional sample-level routing; not the same arrangement as offline previews.',
                     'Shared samples use their first tone route; original SPU timing/envelopes/pan remain.',
                     'Unknown banks, ambience and streamed audio retain original instruments.']),indent=2)+'\n')
    print(f'Wrote {len(data)} bytes to {output}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exports',type=Path,required=True)
    parser.add_argument('--inputs',type=Path,action='append',required=True)
    parser.add_argument('--banks',type=Path,default=Path('output/music-banks'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.exports,args.inputs,args.banks,args.output)
