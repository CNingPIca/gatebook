"""Base ("page block") v1.1 — organiser body; stands on two fold-down side panels.
Printed bins-up, underside flat on the bed (hinge ears are recessed into it)."""
import math
import cadquery as cq
from params import *


def rbox(x0, y0, x1, y1, z0, z1, r):
    b = cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
    if r > 0:
        b = b.edges("|Z").fillet(r)
    return b


def cyl(x, y, z0, h, d):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2, h, cq.Vector(x, y, z0)))


def xcyl(y, z, x0, length, d):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2, length, cq.Vector(x0, y, z), cq.Vector(1, 0, 0)))


def rounded_rect_ring(L, W, R, inset, z0, h):
    outer = rbox(-2, -2, L + 2, W + 2, z0, z0 + h, 0)
    inner = rbox(inset, inset, L - inset, W - inset, z0 - 1, z0 + h + 1, R - inset)
    return outer.cut(inner)


def hinge_y(side):
    return HINGE_Y if side == 0 else BASE_W - HINGE_Y


def build():
    top = BASE_H + 1
    base = rbox(0, 0, BASE_L, BASE_W, 0, BASE_H, BASE_R)
    base = base.faces("<Z").edges().chamfer(0.6)

    yl, yr = SIDE_BAND, BASE_W - SIDE_BAND
    pockets = [
        # back row (strap loop space + small items)
        rbox(BACK_BAND[0], yl, BACK_BAND[1], PHONE_Y[0] - DIV, FLOOR, top, 2.0),
        rbox(BACK_BAND[0], PHONE_Y[1] + DIV, BACK_BAND[1], yr, FLOOR, top, 2.0),
        # middle row: big bin (left) + cup area (right)
        rbox(MID_BAND[0], yl, MID_BAND[1], CUP_C[1] - CUP_BORE / 2 - 4.0, FLOOR, top, 3.0),
        rbox(MID_BAND[0], CUP_C[1] - CUP_BORE / 2 - 2.0, MID_BAND[1], yr, FLOOR, top, 2.0),
        # front strip, either side of the pivot column
        rbox(FRONT_BAND[0], yl, FRONT_BAND[1], PIVOT[1] - 13.0, FLOOR, top, 2.0),
        rbox(FRONT_BAND[0], PIVOT[1] + 13.0, FRONT_BAND[1], yr, FLOOR, top, 2.0),
    ]
    for p in pockets:
        base = base.cut(p)

    # ---- cup well ----
    cx, cy = CUP_C
    base = base.union(cyl(cx, cy, 0, BASE_H, CUP_BORE + 4.0))
    base = base.cut(cyl(cx, cy, CUP_LIP_T, BASE_H, CUP_BORE))
    base = base.cut(cyl(cx, cy, -1, CUP_LIP_T + 2, CUP_BORE - 2 * CUP_LIP))
    base = base.cut(cq.Workplane("XY").add(cq.Solid.makeCone(CUP_BORE / 2 - CUP_LIP, CUP_BORE / 2, CUP_LIP,
                                                             cq.Vector(cx, cy, CUP_LIP_T))))
    base = base.cut(cq.Workplane("XY").box(30, 10, 6, centered=(True, True, False))
                    .edges("|X").fillet(2.9).translate((cx, cy - CUP_BORE / 2 + 1, BASE_H - 3.5)))

    # ---- phone slot: back row centre, leans back 15 deg so the screen faces the user in front ----
    lean = math.radians(PHONE_LEAN)
    w = PHONE_W / math.cos(lean)
    dz = PHONE_DEPTH * math.cos(lean)
    dx = PHONE_DEPTH * math.sin(lean)
    x0 = PHONE_TOP_X
    t1 = math.tan(lean) * 1.0
    sec = [(x0 - t1, BASE_H + 1), (x0 + w - t1, BASE_H + 1), (x0 + w + dx, BASE_H - dz), (x0 + dx, BASE_H - dz)]
    slot = (cq.Workplane("XZ").polyline(sec).close().extrude(-(PHONE_Y[1] - PHONE_Y[0]))
            .translate((0, PHONE_Y[0], 0)))
    base = base.cut(slot)
    base = base.cut(rbox(x0 + dx + 1.5, BASE_W / 2 - 8, x0 + dx + w - 2.0, BASE_W / 2 + 8, -1, BASE_H - dz + 0.5, 2.0))

    # ---- strap windows + loop bars in the back wall ----
    for yc in ANCHORS:
        for ya in (yc - BAR_W / 2 - WIN_W, yc + BAR_W / 2):
            base = base.cut(rbox(-1, ya, BACK_WALL + 0.5, ya + WIN_W, WIN_Z[0], WIN_Z[1], 0))
        # round the bar's two back corners so the strap does not chafe
        for s in (-1, 1):
            ye = yc + s * BAR_W / 2
            corner = rbox(-1, ye - 1.6, 1.6, ye + 1.6, WIN_Z[0], WIN_Z[1], 0).cut(
                cyl(1.6, ye - s * 1.6, WIN_Z[0] - 1, WIN_Z[1] - WIN_Z[0] + 2, 3.2))
            base = base.cut(corner.intersect(rbox(-1, yc - BAR_W / 2, 1.6, yc + BAR_W / 2, WIN_Z[0], WIN_Z[1], 0)))

    # ---- table pivot ----
    px, py = PIVOT
    base = base.cut(cyl(px, py, -1, BASE_H + 2, PIN_BORE))
    base = base.cut(cyl(px, py, -1, PIN_LEDGE_Z + 1, PIN_LEDGE_D))
    nx, ny = px - DETENT_R, py
    tpu = cyl(nx, ny, BASE_H - 1.5, 1.5 + NUB_PROTRUDE, NUB_D).faces(">Z").edges().fillet(0.4)
    base = base.cut(tpu)

    # ---- optional magnets (cover catch) ----
    for (mx, my) in MAGNETS:
        base = base.cut(cyl(mx, my, BASE_H - MAG_H, MAG_H + 1, MAG_D))

    # ---- mini-hook bayonet socket ----
    for (hx, hy) in HOOK_SOCKETS:
        base = base.union(cyl(hx, hy, FLOOR - 0.5, BAYO_BOSS_H + 0.5, BAYO_BOSS_D))
        base = base.cut(cyl(hx, hy, FLOOR, BAYO_CAV_H, BAYO_CAV_D))
        base = base.cut(rbox(hx - BAYO_SLOT[0] / 2, hy - BAYO_SLOT[1] / 2, hx + BAYO_SLOT[0] / 2, hy + BAYO_SLOT[1] / 2,
                             -1, FLOOR + 0.5, BAYO_SLOT[1] / 2 - 0.01))
        for a in (45, 135, 225, 315):
            rx = hx + (BAYO_CAV_D / 2) * math.cos(math.radians(a))
            ry = hy + (BAYO_CAV_D / 2) * math.sin(math.radians(a))
            base = base.union(cyl(rx, ry, FLOOR, BAYO_CAV_H, 2.0).intersect(cyl(hx, hy, FLOOR, BAYO_CAV_H, BAYO_CAV_D + 0.5)))

    # ---- side-panel hinges: knuckle channels + pin bore (recessed: underside stays flat) ----
    for side in (0, 1):
        hy = hinge_y(side)
        for (k0, k1) in KNUCKLES:
            if side == 0:
                ch = rbox(k0, -1, k1, hy + KNUCKLE_R + 1.5, -1, HINGE_Z + KNUCKLE_R + 0.6, 0)
            else:
                ch = rbox(k0, hy - KNUCKLE_R - 1.5, k1, BASE_W + 1, -1, HINGE_Z + KNUCKLE_R + 0.6, 0)
            base = base.cut(ch)
        base = base.cut(xcyl(hy, HINGE_Z, -1, BASE_L - 1.0, HPIN_D + 0.1))
        base = base.cut(xcyl(hy, HINGE_Z, -1, 3.4, 6.6))           # pin-head counterbore (back face)
        # snap dimples for the folded panel tips
        ytip = (PANEL_Y0 + PANEL_LEN - 5.0) if side == 0 else BASE_W - (PANEL_Y0 + PANEL_LEN - 5.0)
        for xd in (40.0, 108.0):
            base = base.cut(cq.Workplane("XY").add(cq.Solid.makeSphere(1.6, cq.Vector(xd, ytip, -1.0))))

    # ---- "page edge" grooves ----
    z = 7.5
    while z < BASE_H - 2.5:
        base = base.cut(rounded_rect_ring(BASE_L, BASE_W, BASE_R, 0.4, z, 0.5))
        z += 1.5

    # ---- underside label ----
    lbl = (cq.Workplane(cq.Plane(origin=(BASE_L / 2, BASE_W / 2 - 25, 0), xDir=(0, 1, 0), normal=(0, 0, -1)))
           .text("GATEBOOK  " + VERSION, 7, -0.5, halign="center", valign="center"))
    base = base.cut(lbl)
    return {"petg": base, "tpu": tpu}


if __name__ == "__main__":
    import time
    t = time.time()
    r = build()
    v = r["petg"].val()
    bb = v.BoundingBox()
    print("base", round(bb.xmin, 2), round(bb.xmax, 2), round(bb.ymin, 2), round(bb.ymax, 2), round(bb.zmin, 2), round(bb.zmax, 2),
          "vol", round(v.Volume()), "valid", v.isValid(), round(time.time() - t, 1), "s")
