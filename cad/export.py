"""Exports: print-ready STL (PETG / TPU split), 3MF plates, STEP, viewer GLB + states JSON."""
import json
import os
import shutil
import sys
import zipfile
from xml.sax.saxutils import escape

import numpy as np
import trimesh
import cadquery as cq

from params import *
import assembly as A

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "out"))
PRINT = os.path.join(OUT, "print")
STEP = os.path.join(OUT, "step")
VIEW = os.path.join(OUT, "viewer")

# print orientation (part frame -> bed frame, bed at z = 0)
PRINT_ORIENT = {
    "base": np.eye(4),
    "table": A.T(0, 0, -BASE_H),
    "clamp": np.eye(4),
    "ring2": np.eye(4), "ring3": np.eye(4), "ring4": np.eye(4),
    "pin": A.T(0, 0, 4.6) @ A.Ry(-90),
    "hook_bag": A.T(0, 0, 2.3) @ A.Rx(90),
    "hook_mini": A.T(0, 0, 2.3) @ A.Rx(90),
    "strap": np.eye(4),
}
PART_INFO = {
    "base": ("01_base_收纳主体", 1),
    "table": ("02_table_旋转桌板", 1),
    "clamp": ("03_qmount_拉杆夹", 1),
    "ring2": ("04_cup_ring_A_杯架套环A", 1),
    "ring3": ("05_cup_ring_B_杯架套环B", 1),
    "ring4": ("06_cup_ring_C_杯架底环C", 1),
    "pin": ("07_pivot_pin_销轴", 2),
    "hook_bag": ("08_hook_bag_大挂钩", 1),
    "hook_mini": ("09_hook_mini_小双钩", 1),
    "strap": ("10_strap_TPU表带", 2),
}
# plates for the H3C (330 x 320): positions of the part's bbox min corner
PLATES = {
    "plate_A_base_table": [("base", (60, 6)), ("table", (60, 164))],
    "plate_B_small_parts": [("clamp", (20, 20)), ("ring2", (95, 10)), ("ring3", (190, 10)), ("ring4", (95, 105)),
                            ("pin", (20, 120)), ("pin", (20, 160)), ("hook_bag", (180, 105)), ("hook_mini", (240, 105)),
                            ("strap", (20, 200)), ("strap", (20, 240))],
}


def to_mesh(shape, tol=0.05, ang=0.2, merge=True):
    if merge:
        verts, tris = shape.tessellate(tol, ang)
        v = np.array([(p.x, p.y, p.z) for p in verts], dtype=np.float64)
        f = np.array(tris, dtype=np.int64)
        m = trimesh.Trimesh(v, f, process=True)
        m.merge_vertices()
        return m
    # viewer: keep each B-rep face's vertices separate so sharp edges stay sharp
    vs, fs, off = [], [], 0
    for face in shape.Faces():
        v, t = face.tessellate(tol, ang)
        if not t:
            continue
        vs.append(np.array([(p.x, p.y, p.z) for p in v]))
        fs.append(np.array(t) + off)
        off += len(v)
    return trimesh.Trimesh(np.vstack(vs), np.vstack(fs), process=False)


def write_3mf(path, objects):
    """objects: list of (name, [(part_name, trimesh)]) already positioned on the bed.
    Each object is a multi-part object (components) -> import as one object with parts."""
    res, build = [], []
    oid = 1
    for name, parts in objects:
        comp_ids = []
        for pname, m in parts:
            vs = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in m.vertices)
            ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
            res.append(f'<object id="{oid}" name="{escape(pname)}" type="model"><mesh><vertices>{vs}</vertices>'
                       f'<triangles>{ts}</triangles></mesh></object>')
            comp_ids.append(oid)
            oid += 1
        comps = "".join(f'<component objectid="{c}"/>' for c in comp_ids)
        res.append(f'<object id="{oid}" name="{escape(name)}" type="model"><components>{comps}</components></object>')
        build.append(f'<item objectid="{oid}"/>')
        oid += 1
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Title">GateBook ' + VERSION + '</metadata>'
             '<resources>' + "".join(res) + '</resources><build>' + "".join(build) + '</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def main(view_only=False):
    for d in (PRINT, STEP, VIEW):
        os.makedirs(d, exist_ok=True)
    P = A.build_parts()
    ctx = A.build_context()
    S = A.states()

    if not view_only:
        # ---- print STLs (bed orientation) ----
        bed_meshes = {}
        for name, mats in P.items():
            fname, qty = PART_INFO[name]
            bed_meshes[name] = {}
            ms = {mat: to_mesh(A.apply(wp.val(), PRINT_ORIENT[name])) for mat, wp in mats.items()}
            zmin = min(m.bounds[0][2] for m in ms.values())
            xymin = np.min([m.bounds[0][:2] for m in ms.values()], axis=0)
            for mat, m in ms.items():
                m.apply_translation((-xymin[0], -xymin[1], -zmin))
                tag = "TPU" if mat == "tpu" else "PETG"
                m.export(os.path.join(PRINT, f"{fname}_{tag}.stl"))
                bed_meshes[name][mat] = m
            print("stl", fname, {k: len(v.faces) for k, v in ms.items()}, "bed size", np.round(
                np.max([m.bounds[1] for m in ms.values()], axis=0), 1))
        # ---- 3MF plates ----
        for plate, items in PLATES.items():
            objs = []
            for i, (name, (px, py)) in enumerate(items):
                parts = []
                for mat, m in bed_meshes[name].items():
                    mm = m.copy()
                    mm.apply_translation((px, py, 0))
                    parts.append((f"{PART_INFO[name][0]}_{'TPU' if mat == 'tpu' else 'PETG'}", mm))
                objs.append((f"{PART_INFO[name][0]}#{i + 1}", parts))
            write_3mf(os.path.join(PRINT, f"{plate}.3mf"), objs)
            # bed fit check
            allb = np.array([[p[1].bounds for p in o[1]] for o in objs], dtype=object)
            mx = np.max([p[1].bounds[1] for o in objs for p in o[1]], axis=0)
            print("plate", plate, "max extent", np.round(mx, 1))
        # ---- STEP ----
        for name, mats in P.items():
            comp = cq.Compound.makeCompound([wp.val() for wp in mats.values()])
            cq.exporters.export(cq.Workplane().add(comp), os.path.join(STEP, f"{PART_INFO[name][0]}.step"))
        asm = cq.Assembly(name="GateBook_use_state")
        colors = {"petg": cq.Color(0.93, 0.90, 0.84), "tpu": cq.Color(0.78, 0.39, 0.24)}
        for name, mats in P.items():
            for i, m in enumerate(S["use"].get(name, [])):
                for mat, wp in mats.items():
                    asm.add(cq.Workplane().add(A.apply(wp.val(), m)), name=f"{name}_{i}_{mat}", color=colors[mat])
        asm.save(os.path.join(STEP, "00_GateBook_assembly_使用状态.step"))
        print("step done")

    # ---- viewer meshes (part frame) + states ----
    scene = trimesh.Scene()
    for name, mats in P.items():
        for mat, wp in mats.items():
            m = to_mesh(wp.val(), tol=0.06, ang=0.25, merge=False)
            scene.add_geometry(m, geom_name=f"{name}__{mat}", node_name=f"{name}__{mat}")
    for k, wp in ctx.items():
        m = to_mesh(wp.val(), tol=0.2, ang=0.3, merge=False)
        scene.add_geometry(m, geom_name=f"ctx__{k}", node_name=f"ctx__{k}")
    scene.export(os.path.join(VIEW, "gatebook.glb"))
    st = {s: {n: [np.round(m, 6).tolist() for m in ms] for n, ms in d.items()} for s, d in S.items()}
    # extra states for the animation: table angles
    for ang in (0, 45, 90, 135, 180):
        st[f"table_{ang}"] = [np.round(A.Rz(ang, *PIVOTS[0]), 6).tolist()]
    st["meta"] = {"version": VERSION, "pivot": PIVOTS[0], "cup": CUP_C}
    json.dump(st, open(os.path.join(VIEW, "states.json"), "w"))
    print("glb", os.path.getsize(os.path.join(VIEW, "gatebook.glb")) // 1024, "KB")


if __name__ == "__main__":
    main(view_only="--view" in sys.argv)
