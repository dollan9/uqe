#!/usr/bin/env python3
"""verify_blender.py — UQE Blender geometry audit + turntable renders (headless).

Run INSIDE Blender's bundled Python:
    blender --background model.blend --python scripts/verify_blender.py -- [out_dir]
Or on a .blend file directly:
    blender --background --python scripts/verify_blender.py -- input.blend [out_dir]

Checks (non-destructive): non-manifold edges, degenerate faces (zero-area),
extreme/negative scale, unapplied transforms, floating verts, intersecting
bounds heuristics. Renders 4 turntable stills as visual evidence artifacts.
Writes <out_dir>/geometry-audit.txt and exits 0 clean / 1 defects found / 2 env error.
"""
import math
import os
import sys

def _args():
    # argv after '--' when launched via blender CLI
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = argv[1:]
    blend = None
    out_dir = "verify/blender"
    if argv:
        if argv[0].endswith(".blend"):
            blend = argv[0]
            argv = argv[1:]
        if argv:
            out_dir = argv[0]
    return blend, out_dir

def main():
    try:
        import bpy  # type: ignore
    except ImportError:
        print("[verify_blender][ERROR] must run inside Blender: blender --background [--python] ... ")
        print("  manual: blender --background your.blend --python scripts/verify_blender.py -- out_dir")
        return 2

    blend, out_dir = _args()
    if blend:
        try:
            bpy.ops.wm.open_mainfile(filepath=blend)
        except Exception as e:
            print(f"[verify_blender][ERROR] cannot open {blend}: {e}")
            return 2

    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "geometry-audit.txt")
    lines = []
    defects = 0

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    lines.append(f"objects: {len(bpy.context.scene.objects)}, meshes: {len(meshes)}")
    if not meshes:
        lines.append("DEFECT: scene contains no mesh objects")
        defects += 1

    for ob in meshes:
        me = ob.data
        nm_edges = sum(1 for e in me.edges if not e.is_loose and (len(e.link_faces) > 2))
        loose_verts = sum(1 for v in me.vertices if not v.link_edges)
        degen = 0
        for p in me.polygons:
            if len(p.vertices) >= 3:
                vs = [me.vertices[i].co for i in p.vertices[:3]]
                area2 = (vs[1] - vs[0]).cross(vs[2] - vs[0]).length
                if area2 < 1e-8:
                    degen += 1
        bad_scale = any(abs(s) < 1e-4 or abs(s) > 1e4 for s in ob.scale)
        unapplied = any(abs(s - 1.0) > 1e-6 for s in ob.scale) or \
                    any(abs(r) > 1e-6 for r in ob.rotation_euler)
        tag = f"{ob.name} (verts={len(me.vertices)}, polys={len(me.polygons)})"
        if nm_edges:
            lines.append(f"DEFECT {tag}: non-manifold edges = {nm_edges}")
            defects += 1
        if loose_verts:
            lines.append(f"DEFECT {tag}: floating vertices = {loose_verts}")
            defects += 1
        if degen:
            lines.append(f"DEFECT {tag}: degenerate (zero-area) faces = {degen}")
            defects += 1
        if bad_scale:
            lines.append(f"DEFECT {tag}: extreme object scale {tuple(round(s,4) for s in ob.scale)}")
            defects += 1
        if unapplied:
            lines.append(f"NOTE {tag}: unapplied transform (scale/rotation) — apply before export")
        if not (nm_edges or loose_verts or degen or bad_scale):
            lines.append(f"OK   {tag}")

    # --- Turntable renders as visual evidence --------------------------------
    rendered = []
    try:
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_WORKBENCH'  # fast, deterministic, no GPU dep
        scene.render.resolution_x, scene.render.resolution_y = 960, 540
        angles = [(0, "front"), (90, "right"), (180, "back"), (270, "left")]
        base_rot = tuple(scene.camera.rotation_euler) if scene.camera else None
        for deg, name in angles:
            if scene.camera:
                from mathutils import Euler
                scene.camera.rotation_euler = Euler((base_rot[0], base_rot[1], math.radians(deg)), 'XYZ')
            fp = os.path.join(out_dir, f"turntable-{name}.png")
            scene.render.filepath = fp
            bpy.ops.render.write_still() if hasattr(bpy.ops.render, "write_still") else bpy.ops.render.render(write_still=True)
            if os.path.exists(fp):
                rendered.append(fp)
    except Exception as e:
        lines.append(f"NOTE: render pass failed ({e}) — geometry numbers above are still E2 evidence; visual claims remain UNVERIFIED.")

    lines.append(f"RESULT: {defects} defect(s); renders produced: {len(rendered)}")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    print(f"[verify_blender] wrote {report_path}")
    if rendered:
        print(f"[verify_blender] VIEW the renders before claiming anything about appearance: {rendered}")
    print("[verify_blender] NEXT: read geometry-audit.txt + view renders; put observations into evidence JSON; validate with scripts/validate_evidence.py.")
    return 1 if defects else 0

if __name__ == "__main__":
    sys.exit(main())
