"""Swivel table ("hard cover"). Same XY frame as the base; sits on Z = BASE_H.
Printed right side up (underside on the bed)."""
import math
import cadquery as cq
from params import *
from base import rbox, cyl

Z0 = BASE_H
ZT = BASE_H + TBL_H
X0, Y0 = -TBL_OVER, -TBL_OVER
X1, Y1 = BASE_L + TBL_OVER, BASE_W + TBL_OVER

# dimples on the table underside (the TPU nub lives in the base)
DIMPLE_ANGLES = {0: (135, 45, 315), 1: (225, 315, 45)}
NUB_ANGLES = {0: 135, 1: 225}


def build():
    body = rbox(X0, Y0, X1, Y1, Z0, ZT, TBL_R)
    body = body.faces(">Z").edges().fillet(1.2)
    body = body.faces("<Z").edges().chamfer(0.5)

    # raised anti-roll lip
    lip_o = rbox(X0, Y0, X1, Y1, ZT - 0.5, ZT + TBL_LIP_H, TBL_R)
    lip_i = rbox(X0 + TBL_LIP_W, Y0 + TBL_LIP_W, X1 - TBL_LIP_W, Y1 - TBL_LIP_W, ZT - 1, ZT + TBL_LIP_H + 1, TBL_R - TBL_LIP_W)
    lip = lip_o.cut(lip_i).faces(">Z").edges().fillet(0.5)
    body = body.union(lip)

    # ---- boarding-pass sleeve (open at the far end, X = X1) ----
    zs0 = Z0 + PASS_Z0
    sleeve = rbox(PASS_X0, PASS_Y[0], X1 + 5, PASS_Y[1], zs0, zs0 + PASS_GAP, 3.0)
    body = body.cut(sleeve)
    # entrance flare
    flare = (cq.Workplane("YZ").workplane(offset=X1 - 4)
             .rect(PASS_Y[1] - PASS_Y[0], PASS_GAP).workplane(offset=4.5)
             .rect(PASS_Y[1] - PASS_Y[0] + 2, PASS_GAP + 2.0).loft()
             .translate((0, (PASS_Y[0] + PASS_Y[1]) / 2, zs0 + PASS_GAP / 2)))
    body = body.cut(flare)
    # thumb notch: exposes the last 14 mm of the pass so it can be pinched
    notch = cyl(X1, (PASS_Y[0] + PASS_Y[1]) / 2, zs0 + PASS_GAP - 0.01, TBL_H + 5, 2 * PASS_NOTCH_R)
    body = body.cut(notch)

    # TPU retention fins on the sleeve floor (lean towards the inside: easy in, hard out)
    tpu = None
    fin_h = PASS_GAP - 0.2
    lean = math.radians(35)
    for fx in (95.0, 165.0):
        prof = [(fx, zs0 - 0.6), (fx + 1.0, zs0 - 0.6), (fx + 1.0 - fin_h * math.tan(lean), zs0 + fin_h),
                (fx - fin_h * math.tan(lean), zs0 + fin_h)]
        fin = (cq.Workplane("XZ").polyline(prof).close().extrude(-(PASS_Y[1] - PASS_Y[0] - 16))
               .translate((0, PASS_Y[0] + 8, 0)))
        tpu = fin if tpu is None else tpu.union(fin)

    # ---- pivot holes + head counterbores ----
    for (px, py) in PIVOTS:
        body = body.cut(cyl(px, py, Z0 - 1, TBL_H + 5, PIN_BORE))
        body = body.cut(cyl(px, py, ZT - 2.2, 5, 16.4))

    # ---- detent dimples on the underside ----
    for i, (px, py) in enumerate(PIVOTS):
        for a in DIMPLE_ANGLES[i]:
            x = px + DETENT_R * math.cos(math.radians(a))
            y = py + DETENT_R * math.sin(math.radians(a))
            sph = cq.Workplane("XY").add(cq.Solid.makeSphere(DIMPLE_D / 2, cq.Vector(x, y, Z0 - DIMPLE_D / 2 + DIMPLE_DEPTH)))
            body = body.cut(sph)

    # ---- optional magnets (free end of the cover) ----
    for (mx, my) in MAGNETS:
        body = body.cut(cyl(mx, my, Z0 - 1, MAG_H + 1, MAG_D))

    # ---- TPU anti-slip inlay with PETG lettering ----
    inl = rbox(9.0, 9.0, 176.0, BASE_W - 9.0, ZT - TPU_INLAY, ZT + 0.01, 8.0)
    title = (cq.Workplane("XY").workplane(offset=ZT - TPU_INLAY)
             .center(92.5, 86.0).text("GATEBOOK", 15, TPU_INLAY + 0.01, font="Inter", kind="bold", halign="center", valign="center"))
    sub = (cq.Workplane("XY").workplane(offset=ZT - TPU_INLAY)
           .center(92.5, 62.0).text("候 机 书", 11, TPU_INLAY + 0.01, font="Noto Serif CJK SC", halign="center", valign="center"))
    rule = rbox(62.0, 73.4, 123.0, 74.6, ZT - TPU_INLAY, ZT + 0.01, 0.5)
    letters = title.union(sub).union(rule)
    inlay = inl.cut(letters)
    body = body.cut(inl).union(letters.intersect(inl))
    tpu = tpu.union(inlay)

    # ---- small labels ----
    lab = (cq.Workplane(cq.Plane(origin=(190.5, 74.0, ZT), xDir=(0, 1, 0), normal=(0, 0, 1)))
           .text("BOARDING PASS", 4.2, -0.4, font="Inter", kind="bold", halign="center", valign="center"))
    body = body.cut(lab)

    body = body.cut(tpu)
    return {"petg": body, "tpu": tpu}


if __name__ == "__main__":
    import time
    t = time.time()
    r = build()
    for k, v in r.items():
        s = v.val()
        bb = s.BoundingBox()
        print(k, round(bb.xmin, 1), round(bb.xmax, 1), round(bb.ymin, 1), round(bb.ymax, 1), round(bb.zmin, 2), round(bb.zmax, 2),
              "vol", round(s.Volume()), "valid", s.isValid())
    print(round(time.time() - t, 1), "s")
