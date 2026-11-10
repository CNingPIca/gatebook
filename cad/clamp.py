"""Q-Mount: V-block clamp that straps to ONE telescoping tube below the grip.
Local frame: front face X=0 (towards the base), back (V-groove) X=-CL_D,
Y centred, Z 0..CL_H along the tube."""
import math
import cadquery as cq
from params import *


def _v_geometry():
    half = V_MOUTH / 2
    depth = half / math.tan(math.radians(V_ANGLE / 2))
    apex_x = -CL_D + depth
    return half, depth, apex_x


def tongue_profile(grow=0.0):
    """Dovetail trapezoid in the XY plane (root embedded 1 mm behind X=0)."""
    r = TONGUE_ROOT / 2 + grow
    t = TONGUE_TIP / 2 + grow
    # root edge at X=-1 (embedded); flanks are straight lines root->tip
    k = (t - r) / TONGUE_H
    r_emb = r - k * 1.0
    pts = [(-1.0, -r_emb), (TONGUE_H + grow, -t - k * grow),
           (TONGUE_H + grow, t + k * grow), (-1.0, r_emb)]
    return pts


def make_tongue(z0, h, grow=0.0):
    pts = tongue_profile(grow)
    return (cq.Workplane("XY").workplane(offset=z0).polyline(pts).close()
            .extrude(h, taper=TONGUE_TAPER))


def build():
    half, depth, apex_x = _v_geometry()

    body = (cq.Workplane("XY").box(CL_D, CL_W, CL_H, centered=(False, True, False))
            .translate((-CL_D, 0, 0)))
    body = body.edges("|Z").fillet(3.0)
    body = body.faces(">Z or <Z").edges().fillet(1.2)

    # V-groove (prism along Z)
    v_pts = [(-CL_D - 0.01, half), (apex_x, 0.0), (-CL_D - 0.01, -half)]
    vcut = cq.Workplane("XY").polyline(v_pts).close().extrude(CL_H + 2).translate((0, 0, -1))
    body = body.cut(vcut)
    # apex relief (round tubes never touch the apex)
    relief = cq.Workplane("XY").center(apex_x - 0.6, 0).circle(1.6).extrude(CL_H + 2).translate((0, 0, -1))
    body = body.cut(relief)

    # strap channels: front recess + side recess
    for z0, z1 in CH_Z:
        h = z1 - z0
        front = cq.Workplane("XY").box(CH_DEPTH + 1, CL_W + 2, h, centered=False).translate((-CH_DEPTH, -CL_W / 2 - 1, z0))
        sides = cq.Workplane("XY").box(CL_D + 2, CL_W + 2, h, centered=False).translate((-CL_D - 1, -CL_W / 2 - 1, z0))
        keep = cq.Workplane("XY").box(CL_D + 4, CL_W - 2.0, h + 2, centered=False).translate((-CL_D - 2, -(CL_W - 2.0) / 2, z0 - 1))
        body = body.cut(front).cut(sides.cut(keep))

    # dovetail tongue (wedge: wider at the bottom, seats under gravity)
    tongue = make_tongue(TONGUE_Z[0], TONGUE_Z[1] - TONGUE_Z[0])
    body = body.union(tongue)

    # side pegs for the printed TPU strap (axis along Y)
    side_y = CL_W / 2 - 1.0
    for z in PEG_Z:
        for s in (-1, 1):
            stem = cq.Workplane("XY").add(cq.Solid.makeCylinder(PEG_STEM / 2, PEG_LEN + 1.0,
                                                               cq.Vector(PEG_X, s * (side_y - 1.0), z), cq.Vector(0, s, 0)))
            head = cq.Workplane("XY").add(cq.Solid.makeCone(PEG_HEAD / 2, PEG_HEAD / 2 - 0.8, 1.2,
                                                            cq.Vector(PEG_X, s * (side_y + PEG_LEN - 1.2), z), cq.Vector(0, s, 0)))
            body = body.union(stem).union(head)

    # "UP" arrow debossed on both side faces
    for s in (-1, 1):
        # 1.2 mm thick prism straddling the side face -> 0.6 mm deep deboss
        tri = (cq.Workplane("XZ").polyline([(-12.5, 44.0), (-4.5, 44.0), (-8.5, 51.0)]).close()
               .extrude(-1.2).translate((0, s * (CL_W / 2) - 0.6, 0)))
        body = body.cut(tri)

    # TPU pads on both V faces (proud by 0.4 mm)
    tpu = None
    p1 = (-CL_D, half)
    d = (apex_x - p1[0], 0 - p1[1])
    L = math.hypot(*d)
    d = (d[0] / L, d[1] / L)
    for s in (1, -1):
        ds = (d[0], d[1] * s)
        ps = (p1[0], p1[1] * s)
        # body-side normal: rotate the face direction towards +X/outwards
        n = (ds[1] * s, -ds[0] * s)
        if n[0] < 0:
            n = (-n[0], -n[1])
        a0, a1 = 1.8, L - 3.2
        A = (ps[0] + ds[0] * a0, ps[1] + ds[1] * a0)
        B = (ps[0] + ds[0] * a1, ps[1] + ds[1] * a1)
        pts = [(A[0] - n[0] * 0.4, A[1] - n[1] * 0.4), (B[0] - n[0] * 0.4, B[1] - n[1] * 0.4),
               (B[0] + n[0] * PAD_T, B[1] + n[1] * PAD_T), (A[0] + n[0] * PAD_T, A[1] + n[1] * PAD_T)]
        pad = cq.Workplane("XY").polyline(pts).close().extrude(CL_H - 8).translate((0, 0, 4))
        tpu = pad if tpu is None else tpu.union(pad)
    body = body.cut(tpu)
    return {"petg": body, "tpu": tpu}


if __name__ == "__main__":
    r = build()
    for k, v in r.items():
        bb = v.val().BoundingBox()
        print(k, round(bb.xmin, 2), round(bb.xmax, 2), round(bb.ymin, 2), round(bb.ymax, 2), round(bb.zmin, 2), round(bb.zmax, 2), "vol", round(v.val().Volume()))
