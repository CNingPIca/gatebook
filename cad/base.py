"""Base ("page block"): organiser body that hangs on the Q-Mount.
Printed bins-up, underside on the bed."""
import math
import cadquery as cq
from params import *
import clamp as clampmod


def rbox(x0, y0, x1, y1, z0, z1, r):
    b = cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
    if r > 0:
        b = b.edges("|Z").fillet(r)
    return b


def cyl(x, y, z0, h, d):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2, h, cq.Vector(x, y, z0)))


def rounded_rect_ring(L, W, R, inset, z0, h):
    outer = rbox(-2, -2, L + 2, W + 2, z0, z0 + h, 0)
    inner = rbox(inset, inset, L - inset, W - inset, z0 - 1, z0 + h + 1, R - inset)
    return outer.cut(inner)


def build():
    top = BASE_H + 1
    base = rbox(0, 0, BASE_L, BASE_W, 0, BASE_H, BASE_R)
    base = base.faces("<Z").edges().chamfer(0.6)

    # ---- bins ----
    pockets = [
        rbox(4.4, CH_A[0], BIN_X1, CH_A[1], FLOOR, top, 5.0),                  # pen / cable channel
        rbox(4.4, CH_B[0], 68.0, CH_B[1], FLOOR, top, 5.0),                    # small cells
        rbox(70.0, CH_B[0], 124.0, CH_B[1], FLOOR, top, 2.0),
        rbox(126.0, CH_B[0], BIN_X1, CH_B[1], FLOOR, top, 2.0),
        rbox(BIN_X0, MID[0], BAY_X0 - DIV, MID[1], FLOOR, top, 2.0),          # around the cup well
        rbox(BAY_X0, MID[0], BIN_X1, MID[1], FLOOR, top, 3.0),                 # clamp / hook bay
    ]
    for p in pockets:
        base = base.cut(p)

    # cup well: ring wall + bore + bottom lip
    cx, cy = CUP_C
    ring = cyl(cx, cy, 0, BASE_H, CUP_BORE + 2 * 2.0)
    base = base.union(ring)
    base = base.cut(cyl(cx, cy, CUP_LIP_T, BASE_H, CUP_BORE))
    base = base.cut(cyl(cx, cy, -1, CUP_LIP_T + 2, CUP_BORE - 2 * CUP_LIP))
    # 45 deg conical seat: the extended ring self-centres on it
    base = base.cut(cq.Workplane("XY").add(cq.Solid.makeCone(CUP_BORE / 2 - CUP_LIP, CUP_BORE / 2, CUP_LIP,
                                                             cq.Vector(cx, cy, CUP_LIP_T))))
    # finger notch so the rings can be pushed up / pulled down
    base = base.cut(cq.Workplane("XY").box(10, 30, 6, centered=(True, True, False))
                    .edges("|Y").fillet(2.9).translate((cx - CUP_BORE / 2 + 1, cy, BASE_H - 3.5)))

    # ---- phone slot (leans back 15 deg so the screen faces the handle) ----
    lean = math.radians(PHONE_LEAN)
    w_top = PHONE_W / math.cos(lean)
    dz = PHONE_DEPTH * math.cos(lean)
    dx = PHONE_DEPTH * math.sin(lean)
    x0 = PHONE_TOP_X
    sec = [(x0, BASE_H + 1), (x0 + w_top, BASE_H + 1),
           (x0 + w_top - dx - math.tan(lean) * 1, BASE_H - dz), (x0 - dx - math.tan(lean) * 1, BASE_H - dz)]
    slot = (cq.Workplane("XZ").polyline(sec).close().extrude(-(PHONE_Y[1] - PHONE_Y[0]))
            .translate((0, PHONE_Y[0], 0)))
    base = base.cut(slot)
    # cable / drain hole through the slot bottom
    base = base.cut(rbox(x0 - dx + 1.0, 66.0, x0 - dx + w_top - 2.5, 82.0, -1, BASE_H - dz + 0.5, 2.0))

    # ---- table pivots: bore + snap ledge from below ----
    for (px, py) in PIVOTS:
        base = base.cut(cyl(px, py, -1, BASE_H + 2, PIN_BORE))
        base = base.cut(cyl(px, py, -1, PIN_LEDGE_Z + 1, PIN_LEDGE_D))
    # TPU detent nubs (the table carries the 0/90/180 deg dimples)
    tpu = None
    for i, (px, py) in enumerate(PIVOTS):
        a = math.radians(135 if i == 0 else 225)
        x, y = px + DETENT_R * math.cos(a), py + DETENT_R * math.sin(a)
        nub = cyl(x, y, BASE_H - 1.5, 1.5 + NUB_PROTRUDE, NUB_D)
        nub = nub.faces(">Z").edges().fillet(0.4)
        tpu = nub if tpu is None else tpu.union(nub)

    # ---- optional magnet pockets (top of the tube-side wall) ----
    for (mx, my) in MAGNETS:
        base = base.union(cyl(mx, my, FLOOR - 0.5, BASE_H - FLOOR + 0.5, 10.0).intersect(rbox(0, 0, BASE_L, BASE_W, 0, BASE_H, BASE_R)))
        base = base.cut(cyl(mx, my, BASE_H - MAG_H, MAG_H + 1, MAG_D))

    # ---- dovetail groove for the Q-Mount (wedge, wider at the bottom) ----
    grow = CLR_TIGHT
    pre = math.tan(math.radians(TONGUE_TAPER)) * 1.0
    groove = clampmod.make_tongue(-1.0, BASE_H + 2.0, grow=grow + pre).translate((0, BASE_W / 2, 0))
    base = base.cut(groove)
    # ---- SIM-pin hole ----
    base = base.cut(cyl(8.0, 48.0, BASE_H - 14, 15, 1.3))

    # ---- bayonet sockets for the hooks (underside) ----
    for (hx, hy) in HOOK_SOCKETS:
        boss = cyl(hx, hy, FLOOR - 0.5, BAYO_BOSS_H + 0.5, BAYO_BOSS_D)
        base = base.union(boss)
        base = base.cut(cyl(hx, hy, FLOOR, BAYO_CAV_H, BAYO_CAV_D))
        sl = rbox(hx - BAYO_SLOT[0] / 2, hy - BAYO_SLOT[1] / 2, hx + BAYO_SLOT[0] / 2, hy + BAYO_SLOT[1] / 2,
                  -1, FLOOR + 0.5, BAYO_SLOT[1] / 2 - 0.01)
        base = base.cut(sl)
        for a in (45, 135, 225, 315):
            rx = hx + (BAYO_CAV_D / 2) * math.cos(math.radians(a))
            ry = hy + (BAYO_CAV_D / 2) * math.sin(math.radians(a))
            base = base.union(cyl(rx, ry, FLOOR, BAYO_CAV_H, 2.0).intersect(cyl(hx, hy, FLOOR, BAYO_CAV_H, BAYO_CAV_D + 0.5)))

    # ---- "page edge" grooves: makes the closed product read as a book ----
    z = 4.5
    while z < BASE_H - 2.5:
        base = base.cut(rounded_rect_ring(BASE_L, BASE_W, BASE_R, 0.4, z, 0.5))
        z += 1.5

    # ---- underside label ----
    lbl = (cq.Workplane(cq.Plane(origin=(BASE_L / 2 + 30, BASE_W / 2, 0), xDir=(-1, 0, 0), normal=(0, 0, -1)))
           .text("GATEBOOK  " + VERSION, 8, -0.5, halign="center", valign="center"))
    base = base.cut(lbl)
    base = base.cut(tpu)
    return {"petg": base, "tpu": tpu}


if __name__ == "__main__":
    import time
    t = time.time()
    r = build()
    v = r["petg"].val()
    bb = v.BoundingBox()
    print("tpu vol", round(r["tpu"].val().Volume(), 1))
    print("base", bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax, "vol", round(v.Volume()), "valid", v.isValid(), round(time.time() - t, 1), "s")
