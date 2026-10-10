# Module: Blender (3D)

**Load when:** 3D modeling, sculpting, materials, lighting, or rendering with Blender.
**Skip loading for:** T0 file ops or answering conceptual questions without touching a scene.

## Evidence ladder
1. **T1 small adjustment:** headless audit of the changed property via
   `blender --background file.blend --python-expr "..."` and read the printed values.
2. **T2 asset/model:** geometry audit script (non-manifold edges, degenerate faces, poly count,
   object scale vs world units, unapplied transforms, UV presence/overlaps) — print counts, then
   actually read them; plus one preview render you look at.
3. **T3 full scene:** audits above + renders from ≥3 angles (Cycles or Eevee), material/lighting
   inspection per render, check for z-fighting, visible UV seams, missing textures.

Example audit expression (adapt as needed):
```
blender --background scene.blend --python-expr "
import bpy, bmesh
for o in bpy.context.scene.objects:
    if o.type=='MESH':
        bm=bmesh.new(); bm.from_mesh(o.data)
        nm=[e for e in bm.edges if not e.is_manifold]
        print(o.name,'verts',len(bm.verts),'nonmanifold',len(nm),'scale',tuple(o.scale))
        bm.free()"
```

## Tools
Host 3D tools first; otherwise Blender CLI (`which blender && blender --version`). If Blender is
missing: deliver the exact `.py` script + command line the user can run locally, mark geometry and
visual claims UNVERIFIED, never invent audit numbers.

## Common failure modes
- Non-manifold edges/degenerate faces breaking 3D-print or boolean workflows.
- Unapplied scale distorting modifiers and physics; wrong real-world scale.
- Missing or default material shipped as "done"; UV overlaps causing texture stretch.
- Z-fighting on coincident faces; lighting artifacts mistaken for model defects.
- Renders inspected only from one flattering angle.

## Cannot verify here
A script audit proves topology facts, never artistic quality. Without actual renders viewed, all
statements about how it looks are UNVERIFIED by definition.

## Stopping conditions
One critique pass at T2; ≤3 cycles at T3. Re-render only after changes that affect pixels.

**Good verification:** "Audit output shows 0 non-manifold edges, scale (1,1,1), 14.2k tris; viewed
`render_front.png`, `render_side.png`: no stretched UVs on the strap, material slots resolve."
**Bad verification:** "Modeled the mesh in Python, so it should be watertight."
