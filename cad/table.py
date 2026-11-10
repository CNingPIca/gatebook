"""Swivel table ("hard cover") v1.1. Same XY frame as the base; sits on Z = BASE_H.
Pivot at the front centre: swings 180 deg forward on the luggage centre line.
Printed right side up (underside on the bed)."""
import math
import cadquery as cq
from params import *
from base import rbox, cyl

Z0 = BASE_H
ZT = BASE_H + TBL_H
X0, Y0 = -TBL_OVER, -TBL_OVER
X1, Y1 = BASE_L + TBL_OVER, BASE_W + TBL_OVER

# detent dimples on the underside at 0 and 180 deg (the TPU nub lives in the base)
DIMPLES = [(PIVOT[0] - DETENT_R, PIVOT[1]), (PIVOT[0] + DETENT_R, PIVOT[1])]


def build():
    body = rbox(X0, Y0, X1, Y1, Z0, ZT, TBL_R)
    body = body.faces(">Z").edges().fillet(1.2)
    body = body.faces("<Z").edges().chamfer(0.5)

    # raised anti-roll lip
    lip_o = rbox(X0, Y0, X1, Y1, ZT - 0.5, ZT + TBL_LIP_H, TBL_R)
    lip_i = rbox(X0 + TBL_LIP_W, Y0 + TBL_LIP_W, X1 - TBL_LIP_W, Y1 - TBL_LIP_W, ZT - 1, ZT + TBL_LIP_H + 1, TBL_R - TBL_LIP_W)
    lip = lip_o.cut(lip_i).faces(">Z").edges().fillet(0.5)
    body = body.union(lip)

    # ---- boarding-pass sleeve: runs along Y, open at the right edge (Y = Y1) ----
    zs0 = Z0 + PASS_Z0
    xc = (PASS_X[0] + PASS_X[1]) / 2
    body = body.cut(rbox(PASS_X[0], PASS_Y0, PASS_X[1], Y1 + 5, zs0, zs0 + PASS_GAP, 3.0))
    flare = (cq.Workplane("XZ").workplane(offset=-(Y1 - 4))
             .rect(PASS_X[1] - PASS_X[0], PASS_GAP).workplane(offset=-4.5)
             .rect(PASS_X[1] - PASS_X[0] + 2, PASS_GAP + 2.0).loft()
             .translate((xc, 0, zs0 + PASS_GAP / 2)))
    body = body.cut(flare)
    # thumb notch: exposes the end of the pass so it can be pinched
    body = body.cut(cyl(xc, Y1, zs0 + PASS_GAP - 0.01, TBL_H + 5, 2 * PASS_NOTCH_R))

    # TPU retention fins on the sleeve floor, leaning inwards (-Y): easy in, hard out
    tpu = None
    fin_h = PASS_GAP - 0.2
    lean = math.radians(35)
    for fy in (90.0, 160.0):
        prof = [(fy, zs0 - 0.6), (fy + 1.0, zs0 - 0.6), (fy + 1.0 - fin_h * math.tan(lean), zs0 + fin_h),
                (fy - fin_h * math.tan(lean), zs0 + fin_h)]
        fin = (cq.Workplane("YZ").workplane(offset=PASS_X[0] + 8).polyline(prof).close()
               .extrude(PASS_X[1] - PASS_X[0] - 16))
        tpu = fin if tpu is None else tpu.union(fin)

    # ---- pivot hole + head counterbore ----
    px, py = PIVOT
    body = body.cut(cyl(px, py, Z0 - 1, TBL_H + 5, PIN_BORE))
    body = body.cut(cyl(px, py, ZT - 2.2, 5, 16.4))

    for (x, y) in DIMPLES:
        body = body.cut(cq.Workplane("XY").add(cq.Solid.makeSphere(DIMPLE_D / 2, cq.Vector(x, y, Z0 - DIMPLE_D / 2 + DIMPLE_DEPTH))))

    # ---- optional magnets (free/back edge of the cover) ----
    for (mx, my) in MAGNETS:
        body = body.cut(cyl(mx, my, Z0 - 1, MAG_H + 1, MAG_D))

    # ---- TPU anti-slip inlay with PETG lettering (reads from the front of the luggage) ----
    inl = rbox(9.0, 9.0, 124.0, 195.0, ZT - TPU_INLAY, ZT + 0.01, 8.0)

    def label(txt, x, y, size, font, kind="regular"):
        pl = cq.Plane(origin=(x, y, ZT - TPU_INLAY), xDir=(0, 1, 0), normal=(0, 0, 1))
        return cq.Workplane(pl).text(txt, size, TPU_INLAY + 0.01, font=font, kind=kind, halign="center", valign="center")

    letters = (label("GATEBOOK", 52.0, 102.0, 15, "Inter", "bold")
               .union(label("候 机 书", 76.0, 102.0, 11, "Noto Serif CJK SC"))
               .union(rbox(63.4, 72.0, 64.6, 132.0, ZT - TPU_INLAY, ZT + 0.01, 0.5))
               .union(label("BOARDING PASS  >>", 104.0, 160.0, 4.2, "Inter", "bold")))
    inlay = inl.cut(letters)
    body = body.cut(inl).union(letters.intersect(inl))
    tpu = tpu.union(inlay)

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
