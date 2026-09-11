import math
from pathlib import Path
import struct
import sys
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from battle_models import decode, export_obj, polygons, subdivide, texture_png, transform, triangles, vectors


def fixture():
    return dict(slot=2, vertices=[[0, 0, 0], [2, 0, 0], [0, 2, 0], [2, 2, 0]],
                normals=[[0, 0, 4096]], matrix=[4096, 0, 0, 0, 4096, 0, 0, 0, 4096],
                translation=[10, 20, 30], texture_origin=[0, 0],
                faces=[dict(v=[0, 1, 2, 3], n=[0]*4, uv=[[0, 0], [2, 0], [0, 2], [2, 2]],
                            material=[16, 0, 32, 0, 1, 0])])


class BattleModelTests(unittest.TestCase):
    def test_compact_polygon_layout_and_bounds(self):
        stream = bytes([0x81, 0x91, 0xc1, 1, 16, 0, 32, 0, 1, 0, 0,
                        0, 1, 2, 3, 0, 0, 0, 0, 0, 0, 2, 0, 0, 2, 2, 2, 255])
        faces, size = polygons(stream, 0, 4, 1)
        self.assertEqual(size, len(stream))
        self.assertEqual(faces[0]['v'], [0, 1, 2, 3])
        self.assertEqual(faces[0]['uv'], [(0, 0), (2, 0), (0, 2), (2, 2)])
        for data, count in [(stream[:-1], 4), (stream, 3), (b'\x07', 4), (b'\x80\x00', 4)]:
            with self.subTest(data=data, count=count), self.assertRaises(ValueError):
                polygons(data, 0, count, 1)

    def test_owned_graph_decode_and_parent_rejection(self):
        from inspect_runtime_objects import MODE_ADDRESS, OWNER_ADDRESS, SIGNATURE
        ram = bytearray(0x200000)

        def word(address, value):
            struct.pack_into('<I', ram, address, value)

        def obj(address, callback, children):
            ram[address+0x28:address+0x48] = SIGNATURE
            word(address+0x48, callback)
            word(address+0x20, len(children))
            word(address+0x24, 0x80000000+address+0x300)
            for i, child in enumerate(children):
                word(address+0x300+i*4, child)

        word(MODE_ADDRESS, 0x600)
        word(OWNER_ADDRESS, 0x80090000)
        obj(0x90000, 0x800a6c44, [0x80091000])
        obj(0x91000, 0x80087bb0, [0x800a0000])
        obj(0xa0000, 0x80083e0c, [0, 0, 0x800a1000])
        obj(0xa1000, 0x8008606c, [])
        word(0xa0050, 2)
        word(0xa0054, 0x800c1000)
        word(0xa0064, 0x800b0000)
        word(0xb0014, 0x38)
        word(0xa1060, 0x800c0000)
        word(0xa1064, 0x800c0100)
        word(0xa1068, 0x800c0200)
        struct.pack_into('<12h', ram, 0xc0000, 3, 0, 0, 0, 0, 0, 2, 0, 0, 0, 2, 0)
        struct.pack_into('<6h', ram, 0xc0100, 1, 0, 0, 0, 0, 4096)
        stream = bytes([0x80, 0x91, 0xc1, 1, 0, 0, 0, 0, 0, 0, 0,
                        0, 1, 2, 0, 0, 0, 0, 0, 2, 0, 0, 2, 255])
        ram[0xc0200:0xc0200+len(stream)] = stream
        report = decode(ram)['actors'][0]
        self.assertEqual(report['counts'], dict(parts=1, vertices=3, polygons=1, triangles=1))
        self.assertEqual(report['model_resource_id'], 0x38)
        self.assertEqual(report['parts'][0]['parent_transform'], 0)
        word(0xc1084, 1)  # self-parent is unsupported
        with self.assertRaises(ValueError):
            decode(ram)

    def test_vectors_and_snapshot_rejection(self):
        self.assertEqual(vectors(struct.pack('<6h', 1, 0, 0, -25, 40, 80), 0), [[-25, 40, 80]])
        for count in (0, 257, -1):
            with self.assertRaises(ValueError):
                vectors(struct.pack('<3h', count, 0, 0), 0)
        with self.assertRaises(ValueError):
            decode(b'partial')
        with self.assertRaises(ValueError):
            decode(bytes(0x200000))

    def test_quad_order_and_flat_subdivision(self):
        part = fixture()
        mesh = triangles(part)
        self.assertEqual([t['ids'] for t in mesh], [[0, 1, 2], [1, 3, 2]])
        smooth = subdivide(mesh)
        self.assertEqual(len(smooth), 8)
        self.assertTrue(all(p[2] == 0 for t in smooth for p in t['points']))
        for point in part['vertices']:
            self.assertTrue(any(point in t['points'] for t in smooth))
        # Shared diagonal uses exactly the same midpoint on both faces.
        self.assertIn([1, 1, 0], smooth[0]['points'] + smooth[1]['points'])
        self.assertIn([1, 1, 0], smooth[4]['points'] + smooth[5]['points'] + smooth[6]['points'])

    def test_curved_edge_and_hard_seam(self):
        mesh = triangles(fixture())
        for triangle in mesh:
            triangle['normals'] = [[0, 1/math.sqrt(2), 1/math.sqrt(2)] if i == 1
                                   else [0, 0, 1] for i in triangle['ids']]
        smooth = subdivide(mesh)
        # Only the shared edge curves; open boundaries remain in their plane.
        moved = [p for t in smooth for p in t['points'] if p[2] != 0]
        self.assertTrue(moved)
        self.assertTrue(all(p == moved[0] for p in moved))
        mesh[1]['normals'] = [[0, 0, 1]]*3
        self.assertTrue(all(p[2] == 0 for t in subdivide(mesh) for p in t['points']))

    def test_normal_uses_inverse_transpose(self):
        part = fixture()
        part['matrix'][0] = 8192
        self.assertEqual(transform(part, [1, 2, 3]), [12, 22, 33])
        actual = transform(part, [1, 1, 0], True)
        self.assertAlmostEqual(actual[1] / actual[0], 2)
        part['matrix'] = [0]*9
        with self.assertRaises(ValueError):
            transform(part, [1, 0, 0], True)

    def test_obj_counts_and_texture_offset(self):
        actor = dict(parts=[fixture()])
        original = export_obj(actor, textured=True)
        smooth = export_obj(actor, True)
        self.assertEqual(sum(line.startswith('f ') for line in original.splitlines()), 2)
        self.assertEqual(sum(line.startswith('f ') for line in smooth.splitlines()), 8)
        self.assertIn('mtllib materials.mtl', original)
        self.assertIn('vt 0.064453 0.873047', original)
        self.assertIn('v 10.000000 20.000000 30.000000', original)

    def test_palette_texture_decode(self):
        vram = bytearray(1024*512*2)
        struct.pack_into('<H', vram, 0, 0x0011)
        struct.pack_into('<H', vram, (1024+1)*2, 0x001f)
        png = texture_png(vram, (0, 0, 0, 1))
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        pos = 8
        compressed = b''
        while pos < len(png):
            size = struct.unpack_from('>I', png, pos)[0]
            if png[pos+4:pos+8] == b'IDAT':
                compressed += png[pos+8:pos+8+size]
            pos += size+12
        raw = zlib.decompress(compressed)
        self.assertEqual(raw[1:13], bytes([255, 0, 0, 255]*2 + [0, 0, 0, 0]))
        with self.assertRaises(ValueError):
            texture_png(b'', (0, 0, 0, 0))
