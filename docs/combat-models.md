# Combat model audit and smoothing prototype

Status: offline export and one-step smoothing study, 2026-09-11. No model
replacement is installed in the game. Original assets and generated previews
remain local under ignored `output/model-audit/`.

## What the live models contain

The copied slot-10 battle has the partner named Patamon fighting Kunemon.
The partner's active **model is Digitamamon**, not the Patamon rookie model:
its action record's resource ID is `0x38`, matching the Digitamamon entry in
the owned executable's form-profile table. Patamon's rookie resource is `0x1f`.
Older motion traces use the partner name; they must not be read as measurements
of the Patamon rookie mesh.

| Active model | Mesh parts | Stored vertices across parts | Triangles | Smoothing prototype |
| --- | ---: | ---: | ---: | ---: |
| Digitamamon | 9 | 260 | 484 | 1,936 triangles |
| Kunemon | 13 | 343 | 598 | 2,392 triangles |

Counts include all decoded mesh polygons, not just front-facing visible ones.
Original streams have 318 and 400 polygons respectively, mixing triangles and
quads. Quads use PSX strip order: triangles 0/1/2 and 1/3/2.

This is a custom compact format, not an ordinary OBJ/FBX or an assumed standard
TMD. The combatant controller (`0x80083e0c`) has a transform hierarchy with
`0x84`-byte records. Child slot one is a transform-only root; drawable parts
start at child slot two and use callback `0x8008606c`. A separate child-zero
controller can supply effects. Each mesh part has:

| Child offset | Observed contents |
| --- | --- |
| `+0x5c` | Resource section table |
| `+0x60` | Vertex table: signed 16-bit count, 6-byte header, then signed XYZ triples |
| `+0x64` | Normal table with the same compact triple layout |
| `+0x68` | Polygon/material command stream ending in `0xff` |
| `+0x70/+0x74` | Texture placement in VRAM |
| `+0x78/+0x7c/+0x80` | Runtime projected-coordinate/depth/lighting buffers |
| `+0x84/+0x98` | Current part matrix and translation |

The stream selects triangle/quad shape, texture use, per-corner normal indices
and other rendering flags. Indices into the vertex and normal tables are
**one byte**. Each part can therefore address 256 entries in the current path;
the whole creature can contain more because parts have separate tables.
UV coordinates are also bytes. The captured model textures use **4-bit indexed
pixels**, with 16-color palettes chosen by material commands. Different
polygons can use different palette/page settings, so this is not a 16-color
limit for the entire character.

The animation timeline and per-part transforms are separate from these vertex
buffers. That suggests a replacement renderer could retain the native part
matrices and animation timing while drawing denser host-side meshes. The export
captures one posed frame and does **not** recover a complete editable skeleton,
all clips, expression sprites or effect controllers.

## What the prototype changes

`tools/battle_models.py` decodes the owned RAM snapshot, rejects unsupported
layouts/indices, exports each part and creates an optional curved subdivision
variant. Each triangle becomes four. Original corners stay fixed. A midpoint
curves using the original normals only when both adjacent triangles agree on
those normals; boundaries, nonmanifold edges and hard-normal seams stay straight.
Both faces share the same edge midpoint. Corner UVs interpolate per face, and
normal transformation uses the inverse transpose for scaled part matrices.

The result rounds Digitamamon's shell and gives Kunemon a subtler head/body
improvement. It does not invent anatomy, repair topology, redraw markings, or
make the textures more detailed. The local comparison uses the same offline
renderer and original texture pixels on both sides. It is a static mesh study,
not proof of in-game animation or effect alignment. Transparent/effect surfaces
are not a complete reproduction of the PSX blend pipeline.

To reproduce exports from owned captures:

```powershell
python tools/battle_models.py output/battle-events/fraction-basic-before.bin `
  --vram output/model-audit/vram.bin --output output/model-audit/my-export
```

Use a new output directory. The JSON retains part, material and source-hash
metadata. OBJ files preserve part groups, normals and UVs; the optional VRAM
input supplies PNG texture pages and an MTL file. Keep the MTL and PNGs beside
the OBJs. Exported OBJ corners are intentionally separate to preserve seams;
OBJ vertex-line counts are not the original indexed-vertex counts above.
No textures, mesh exports, owned captures or generated game code belong upstream.

## Paths toward an in-game upgrade

- **Sharper rendering:** the existing OpenGL backend supports higher internal
  resolution through supersampling. This increases rendered pixel density but
  does not change the model topology or texture artwork.
- **Sharper textures:** extract and repaint selected faces/markings while
  retaining their placement and palette semantics. Truly larger texture pages
  need a host texture-replacement path; simply enlarging an image cannot fit
  through the existing byte UVs and fixed VRAM layout unchanged.
- **Denser shapes:** retain part boundaries and native transforms, then add a
  guarded host mesh draw path. The current byte-indexed packet stream is not a
  drop-in destination for an unrestricted subdivided mesh. Splitting oversized
  parts would also affect allocations, draw buffers and transform ownership.

The next concrete integration target is one optional replacement model with
original-model fallback, tested through idle, attacks, reactions, victory and
form changes. No runtime performance gain is claimed: more geometry costs work;
a host draw path may avoid some PSX-side processing but requires measurement.

## Validation

Eight synthetic tests cover stream termination/index validation, signed vectors,
owned-graph decoding/parent validation, quad order, planar subdivision, original-corner retention, consistent curved
shared edges, hard seams, scaled normal transforms, OBJ counts/UV offsets and
4-bit palette decoding. Real snapshot decoding and textured OBJ export completed
for both actors, and both before/after images were visually inspected. Runtime
and saved preferences were left unchanged; the diagnostic game instance was
closed after capture.
