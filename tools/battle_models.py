"""Export local combatant meshes from a copied European battle RAM snapshot.

Outputs contain owned game assets: keep them under ignored output/. This is an
offline posed-mesh experiment, not a replacement asset loader or animation rig.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

from analyze_battle_motion import discover, offset


def vectors(ram, pointer):
    start = offset(pointer, 6)
    count = struct.unpack_from('<h', ram, start)[0]
    if not 0 < count <= 256 or start + 6 + count * 6 > len(ram):
        raise ValueError('Unsupported vector count or truncated vector table')
    return [list(struct.unpack_from('<3h', ram, start + 6 + i * 6)) for i in range(count)]


def polygons(ram, pointer, vertex_count, normal_count):
    start = offset(pointer)
    cursor, flags, faces, material = start, {}, [], None

    def take(count):
        nonlocal cursor
        if cursor + count > min(len(ram), start + 65536):
            raise ValueError('Unterminated or truncated polygon stream')
        result = list(ram[cursor:cursor + count])
        cursor += count
        return result

    while True:
        command = take(1)[0]
        if command == 255:
            return faces, cursor - start
        if 0x80 <= command <= 0xef:
            flags[command >> 4] = command & 15
        elif command == 1:
            material = take(6)
        elif 2 <= command <= 5:
            raise ValueError('Untextured constant-color commands need a separate export path')
        elif command == 0:
            if any(flags.get(key) not in (0, 1) for key in (8, 9, 12)):
                raise ValueError('Unsupported polygon layout flags')
            count = 3 + flags[8]
            indices = take(count)
            normals = take(count) if flags[12] else []
            uv_bytes = take(count * 2) if flags[9] else []
            if max(indices) >= vertex_count or (normals and max(normals) >= normal_count):
                raise ValueError('Polygon index outside its vector table')
            if not material or not uv_bytes:
                raise ValueError('Only textured polygons are supported by this exporter')
            faces.append(dict(v=indices, n=normals, uv=list(zip(uv_bytes[::2], uv_bytes[1::2])),
                              material=material[:], flags=dict(flags)))
        else:
            raise ValueError(f'Unsupported polygon command {command:#x}')


def decode(ram):
    if len(ram) != 0x200000:
        raise ValueError('Expected a complete 2 MiB RAM snapshot')

    def word(p):
        return struct.unpack_from('<I', ram, offset(p))[0]

    actors, _ = discover(ram)
    result = []
    for model, actor in actors.items():
        count, table = word(model + 0x20), word(model + 0x24)
        if not 3 <= count <= 65 or word(model + 0x50) != count - 1:
            raise ValueError('Unsupported model hierarchy')
        parts = []
        hierarchy = word(model + 0x54)
        offset(hierarchy, (count-1)*0x84)
        for slot in range(2, count):  # child zero = effects; child one = transform-only root
            child = word(table + slot * 4)
            if word(child + 0x48) != 0x8008606c:
                raise ValueError('Unsupported mesh child callback')
            parent = word(hierarchy + (slot-1)*0x84)
            if parent >= slot-1:
                raise ValueError('Unsupported parent ordering in model hierarchy')
            vertices = vectors(ram, word(child + 0x60))
            normals = vectors(ram, word(child + 0x64))
            faces, size = polygons(ram, word(child + 0x68), len(vertices), len(normals))
            matrix = list(struct.unpack_from('<9h', ram, offset(child + 0x84, 18)))
            translation = list(struct.unpack_from('<3i', ram, offset(child + 0x98, 12)))
            parts.append(dict(slot=slot, transform_index=slot-1, parent_transform=parent, child=hex(child), vertices=vertices, normals=normals,
                              faces=faces, matrix=matrix, translation=translation,
                              texture_origin=[word(child + 0x70), word(child + 0x74)],
                              stream_bytes=size))
        result.append(dict(**actor, model_resource_id=word(int(actor["control"], 0) + 0x14),
                           parts=parts, counts=dict(
            parts=len(parts), vertices=sum(len(p['vertices']) for p in parts),
            polygons=sum(len(p['faces']) for p in parts),
            triangles=sum(len(f['v']) - 2 for p in parts for f in p['faces']))))
    return dict(schema=1, ram_sha256=hashlib.sha256(ram).hexdigest(), actors=result)


def normalize(v):
    length = math.sqrt(sum(x*x for x in v))
    if length < 1e-8:
        raise ValueError('Zero-length normal')
    return [x / length for x in v]


def triangles(part):
    """Triangulate PSX strip-ordered quads, retaining corner UVs/normals."""
    result = []
    for face in part['faces']:
        if not face['n']:
            raise ValueError('Smoothing requires explicit corner normals')
        for corners in ([(0, 1, 2)] if len(face['v']) == 3 else [(0, 1, 2), (1, 3, 2)]):
            result.append(dict(
                ids=[face['v'][i] for i in corners],
                points=[part['vertices'][face['v'][i]][:] for i in corners],
                normals=[normalize(part['normals'][face['n'][i]]) for i in corners],
                uv=[face['uv'][i] for i in corners], material=face['material'][:]))
    return result


def subdivide(mesh):
    """One normal-guided subdivision, locking boundaries and normal seams.

    Original corners stay fixed. Shared smooth edges use a common curved
    midpoint; open, nonmanifold or hard-normal edges stay straight. This adds
    shape samples, not authored anatomical detail. UVs interpolate per face.
    """
    edges = defaultdict(list)
    for triangle in mesh:
        for i, j in ((0, 1), (1, 2), (2, 0)):
            ids = triangle['ids']
            if ids[i] > ids[j]:
                i, j = j, i
            edges[ids[i], ids[j]].append((triangle, i, j))
    midpoints = {}
    for key, uses in edges.items():
        triangle, i, j = uses[0]
        a, b = triangle['points'][i], triangle['points'][j]
        midpoint = [(x+y)/2 for x, y in zip(a, b)]
        if len(uses) == 2:
            other, k, m = uses[1]
            na, nb = triangle['normals'][i], triangle['normals'][j]
            agree = all(abs(x-y) < 1e-5 for x, y in zip(na+nb, other['normals'][k]+other['normals'][m]))
            if agree:
                da = sum((y-x)*n for x, y, n in zip(a, b, na))
                db = sum((x-y)*n for x, y, n in zip(a, b, nb))
                midpoint = [p - (da*x + db*y)/8 for p, x, y in zip(midpoint, na, nb)]
        midpoints[key] = midpoint
    result = []
    for triangle in mesh:
        points, normals, uv = [list(triangle[k]) for k in ('points', 'normals', 'uv')]
        for i, j in ((0, 1), (1, 2), (2, 0)):
            points.append(midpoints[tuple(sorted((triangle['ids'][i], triangle['ids'][j])))])
            normals.append(normalize([x+y for x, y in zip(normals[i], normals[j])]))
            uv.append([(x+y)/2 for x, y in zip(uv[i], uv[j])])
        for indices in ((0, 3, 5), (3, 1, 4), (5, 4, 2), (3, 4, 5)):
            result.append(dict(points=[points[i] for i in indices], normals=[normals[i] for i in indices],
                               uv=[uv[i] for i in indices], material=triangle['material'][:]))
    return result


def transform(part, point, normal=False):
    matrix = part['matrix']
    if normal:
        a, b, c, d, e, f, g, h, i = matrix
        cofactor = [e*i-f*h, f*g-d*i, d*h-e*g,
                    c*h-b*i, a*i-c*g, b*g-a*h,
                    b*f-c*e, c*d-a*f, a*e-b*d]
        determinant = a*cofactor[0] + b*cofactor[1] + c*cofactor[2]
        if not determinant:
            raise ValueError('Singular part transform')
        return normalize([sum(cofactor[row*3+k]*point[k] for k in range(3)) / determinant
                          for row in range(3)])
    result = [sum(matrix[row*3+k] * point[k] for k in range(3)) / 4096 for row in range(3)]
    return [a+b for a, b in zip(result, part['translation'])]


def texture_key(part, material):
    x, y = part['texture_origin']
    if material[5] != 0:
        raise ValueError('Texture export currently supports the observed 4-bit pages only')
    return ((x + material[1]*64) & 1023, y & 256,
            ((x + material[3]) // 16 * 16) & 1023, (y + material[4]) & 511)


def texture_name(key):
    return 'page_' + '_'.join(map(str, key))


def texture_png(vram, key):
    if len(vram) != 1024*512*2:
        raise ValueError('Expected a complete 1024x512 16-bit VRAM image')
    x, y, cx, cy = key

    def word(px, py):
        return struct.unpack_from('<H', vram, ((py & 511)*1024 + (px & 1023))*2)[0]

    rows = bytearray()
    for v in range(256):
        rows.append(0)  # PNG scanline: no filter
        for u in range(256):
            index = (word(x + u//4, y + v) >> ((u % 4)*4)) & 15
            color = word(cx + index, cy)
            rows.extend(((color & 31)*255//31, ((color >> 5) & 31)*255//31,
                         ((color >> 10) & 31)*255//31, 255 if color else 0))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data))

    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', 256, 256, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def export_obj(actor, smooth=False, textured=False):
    lines = ['# Local posed combatant export; no animation rig.']
    if textured:
        lines.append('mtllib materials.mtl')
    index = 1
    for part in actor['parts']:
        mesh = triangles(part)
        if smooth:
            mesh = subdivide(mesh)
        lines.append(f"g part_{part['slot']}")
        for triangle in mesh:
            if textured:
                lines.append('usemtl ' + texture_name(texture_key(part, triangle['material'])))
            for v, n, uv in zip(triangle['points'], triangle['normals'], triangle['uv']):
                lines.append('v ' + ' '.join(f'{x:.6f}' for x in transform(part, v)))
                lines.append('vn ' + ' '.join(f'{x:.6f}' for x in transform(part, n, True)))
                u = (uv[0] + triangle['material'][0]) % 256
                v = (uv[1] + triangle['material'][2]) % 256
                lines.append(f'vt {(u+.5)/256:.6f} {1-(v+.5)/256:.6f}')
            lines.append('f ' + ' '.join(f'{i}/{i}/{i}' for i in range(index, index+3)))
            index += 3
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ram', type=Path)
    parser.add_argument('--vram', type=Path, help='Optional same-scene raw GPU VRAM capture')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = decode(args.ram.read_bytes())
    vram = args.vram.read_bytes() if args.vram else None
    textures = {}
    if vram is not None:
        for actor in report['actors']:
            for part in actor['parts']:
                for face in part['faces']:
                    key = texture_key(part, face['material'])
                    textures.setdefault(key, None)
        textures = {key: texture_png(vram, key) for key in textures}
        report['vram_sha256'] = hashlib.sha256(vram).hexdigest()
    args.output.mkdir(parents=True, exist_ok=False)
    if textures:
        material_lines = []
        for key, png in textures.items():
            name = texture_name(key)
            (args.output/(name+'.png')).write_bytes(png)
            material_lines.extend([f'newmtl {name}', 'Kd 1 1 1', f'map_Kd {name}.png', ''])
        (args.output/'materials.mtl').write_text('\n'.join(material_lines), encoding='utf-8')
    (args.output/'models.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    for actor in report['actors']:
        name = actor['address'].lower()
        for smooth in (False, True):
            (args.output/f'{name}-{"smooth" if smooth else "original"}.obj').write_text(
                export_obj(actor, smooth, vram is not None), encoding='utf-8')
        print(actor['address'], actor['counts'])
    print('Local asset outputs only; no runtime or save data changed.')


if __name__ == '__main__':
    main()
