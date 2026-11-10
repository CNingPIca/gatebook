"""Small parts: telescoping cup rings, pivot snap-pin, hooks, TPU strap."""
import math
import cadquery as cq
from params import *
from base import rbox, cyl


def tube(od, idd, z0, h):
    return cyl(0, 0, z0, h, od).cut(cyl(0, 0, z0 - 1, h + 2, idd))


def ring_dims():
    """Returns list of dicts for R2, R3, R4 (R1 is the bore in the base)."""
    out = []
    parent_bore = CUP_BORE
    for k in (2, 3, 4):
        parent_lip_id = parent_bore - 2 * CUP_LIP
        od = parent_lip_id - 2 * CLR
        lip_od = od + 2 * CUP_LIP
        idd = od - 2 * RING_T
        out.append(dict(k=k, parent_bore=parent_bore, od=od, lip_od=lip_od, id=idd, lip_id=idd - 2 * CUP_LIP))
        parent_bore = idd
    return out


def build_ring(d):
    H = RING_H
    body = tube(d["od"], d["id"], 0, H)
    # top lip with 45 deg support cone underneath
    zl = H - RING_LIP_T
    lip = tube(d["lip_od"], d["id"], zl, RING_LIP_T)
    cone = (cq.Workplane("XY").add(cq.Solid.makeCone(d["od"] / 2, d["lip_od"] / 2, CUP_LIP, cq.Vector(0, 0, zl - CUP_LIP)))
            .cut(cyl(0, 0, zl - CUP_LIP - 1, CUP_LIP + 2, d["id"])))
    body = body.union(lip).union(cone)
    if d["k"] < 4:
        seat = (cyl(0, 0, 0, RING_LIP_T + CUP_LIP, d["od"] - 0.1)
                .cut(cyl(0, 0, -1, RING_LIP_T + 1.01, d["lip_id"]))
                .cut(cq.Workplane("XY").add(cq.Solid.makeCone(d["lip_id"] / 2, d["id"] / 2, CUP_LIP,
                                                              cq.Vector(0, 0, RING_LIP_T)))))
        body = body.union(seat)
    else:
        floor = cyl(0, 0, 0, RING_LIP_T, d["od"] - 0.1)
        for i in range(8):
            a = math.radians(i * 45 + 22.5)
            floor = floor.cut(cyl(17 * math.cos(a), 17 * math.sin(a), -1, 4, 6.0))
        floor = floor.cut(cyl(0, 0, -1, 4, 7.0))
        body = body.union(floor)
    # TPU friction band on the outside of the top lip (0.15 mm interference)
    tpu = tube(d["parent_bore"] + 0.3, d["lip_od"] - 1.6, zl, RING_LIP_T)
    body = body.cut(tpu)
    return {"petg": body, "tpu": tpu}


def build_pin():
    """Snap pin, assembly coordinates for pivot at (0,0). Head top flush with the table top."""
    head_top = BASE_H + TBL_H - 0.2
    head_bot = head_top - 2.0
    tip = 0.5
    catch = PIN_LEDGE_Z - 0.2
    shank = cyl(0, 0, tip, head_bot - tip + 0.01, PIN_D)
    head = cq.Workplane("XY").add(cq.Solid.makeCone(8.0, 7.4, 2.0, cq.Vector(0, 0, head_bot)))
    barb = (cq.Workplane("XY").add(cq.Solid.makeCone(5.1, 6.0, 2.0, cq.Vector(0, 0, tip)))
            .union(cyl(0, 0, tip + 2.0, catch - tip - 2.0, 12.0)))
    pin = shank.union(head).union(barb)
    slot = rbox(-1.2, -8, 1.2, 8, tip - 1, tip + 15.5, 0)
    pin = pin.cut(slot)
    # flat for printing on its side (slot plane parallel to the bed -> prongs flex along the layers)
    flat = rbox(-10, -10, -4.6, 10, -1, 40, 0)
    pin = pin.cut(flat)
    return {"petg": pin}


def _stroke(path_wp, width, thick):
    return path_wp.offset2D(width / 2, "arc").extrude(thick)


def build_hook(kind="bag"):
    """Bayonet hook. Assembly coords relative to the socket centre, Z=0 = base underside.
    Flat face at Y = -2.3 for printing."""
    t = 6.0
    y0 = -2.3
    tbar = rbox(-5.8, -2.3, 5.8, 2.3, FLOOR + 0.15, FLOOR + 3.15, 0.8)
    neck = cq.Workplane("XY").add(cq.Solid.makeCylinder(2.3, FLOOR + 0.9, cq.Vector(0, 0, -0.4)))
    flange = rbox(-8, y0, 8, y0 + t, -3.4, -0.2, 0).edges("|Y").fillet(1.4)
    hook = tbar.union(neck).union(flange)
    if kind == "bag":
        pts_path = (cq.Workplane("XZ").moveTo(0, -3.0).lineTo(0, -30.0)
                    .threePointArc((11.0, -41.0), (22.0, -30.0)).lineTo(22.0, -24.0))
        body = (pts_path.offset2D(3.0, "arc").extrude(-t).translate((0, y0, 0)))
    else:
        w = (cq.Workplane("XZ").moveTo(0, -3.0).lineTo(0, -14.0)
             .threePointArc((-6.0, -20.0), (-12.0, -14.0)).lineTo(-12.0, -11.0))
        w2 = (cq.Workplane("XZ").moveTo(0, -14.0)
              .threePointArc((6.0, -20.0), (12.0, -14.0)).lineTo(12.0, -11.0))
        body = (w.offset2D(2.4, "arc").extrude(-t).translate((0, y0, 0))
                .union(w2.offset2D(2.4, "arc").extrude(-t).translate((0, y0, 0))))
    hook = hook.union(body)
    return {"petg": hook}


def build_strap():
    """Flat TPU strap (16 mm, also the width of common velcro ties), lies on the bed, length along X.
    Adjustment holes at both ends; the plain middle wraps the loop bar and the tube."""
    s = rbox(0, -STRAP_W / 2, STRAP_L, STRAP_W / 2, 0, STRAP_T, STRAP_W / 2 - 0.01)
    xs = [6.0 + i * STRAP_PITCH for i in range(8)] + [STRAP_L - 6.0 - i * STRAP_PITCH for i in range(12)]
    for x in xs:
        s = s.cut(cyl(x, 0, -1, STRAP_T + 2, STRAP_HOLE + 0.2))
    return {"tpu": s}


def build_buckle():
    """Two-peg buckle: each strap end hooks onto a peg; tension loads the pegs in shear."""
    plate = rbox(-13, -10, 13, 10, 0, 3.0, 4.0)
    for x in (-6.5, 6.5):
        plate = plate.union(cyl(x, 0, 3.0 - 0.01, 3.6, 5.0))
        plate = plate.union(cq.Workplane("XY").add(cq.Solid.makeCone(2.5, 3.6, 1.1, cq.Vector(x, 0, 6.0))))
        plate = plate.union(cyl(x, 0, 7.1, 0.9, 7.2))
    return {"petg": plate}


def build_panel(side=0):
    """Side panel = leg. Modelled in the FOLDED pose under the base (left panel, side 0).
    Plate Z in [-PANEL_T, 0]; knuckles rise into the base's recessed channels."""
    y0, y1 = PANEL_Y0, PANEL_Y0 + PANEL_LEN
    x0, x1 = PANEL_X
    plate = rbox(x0, y0, x1, y1, -PANEL_T, 0, 0)
    plate = plate.edges("|Z").fillet(3.0)
    # lightening window
    plate = plate.cut(rbox(x0 + 18, y0 + 16, x1 - 18, y0 + 62, -PANEL_T - 1, 1, 8.0))
    # arched bottom edge: only the two feet touch the luggage, clears a centred top handle
    plate = plate.cut(rbox(x0 + 32, y1 - 16, x1 - 32, y1 + 5, -PANEL_T - 1, 1, 0).edges("|Z").fillet(10.0))
    # knuckles (16 wide each) with web down into the plate
    kn = None
    for (k0, k1) in KNUCKLES:
        a, b = k0 + 0.5, k1 - 0.5
        c = cq.Workplane("XY").add(cq.Solid.makeCylinder(KNUCKLE_R, b - a, cq.Vector(a, HINGE_Y, HINGE_Z), cq.Vector(1, 0, 0)))
        web = rbox(a, HINGE_Y, b, y0 + 0.4, -PANEL_T, HINGE_Z, 0)
        k = c.union(web)
        kn = k if kn is None else kn.union(k)
    plate = plate.union(kn)
    plate = plate.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder((HPIN_D + 0.4) / 2, x1 - x0 + 2, cq.Vector(x0 - 1, HINGE_Y, HINGE_Z), cq.Vector(1, 0, 0))))
    # snap bumps that hold the folded panel against the base
    for xd in (40.0, 108.0):
        plate = plate.union(cq.Workplane("XY").add(cq.Solid.makeSphere(1.4, cq.Vector(xd, y1 - 5.0 + 0.0 + (PANEL_Y0 + PANEL_LEN - 5.0 - (y1 - 5.0)), -0.9)))
                            .intersect(rbox(xd - 2, y1 - 8, xd + 2, y1 - 2, -0.01, 1, 0)))
    # TPU feet on the bottom edge
    tpu = (rbox(x0 + 1.5, y1 - 0.6, x0 + 32, y1 + FOOT_TPU, -PANEL_T, 0, 0)
           .union(rbox(x1 - 32, y1 - 0.6, x1 - 1.5, y1 + FOOT_TPU, -PANEL_T, 0, 0)))
    plate = plate.cut(tpu)
    out = {"petg": plate, "tpu": tpu}
    if side == 1:
        out = {k: v.mirror("XZ", (0, BASE_W / 2, 0)) for k, v in out.items()}
    return out


def build_hinge_pin():
    """Straight printed pin (no thread). Assembly coords for the left hinge; head sits in the back-face counterbore."""
    head = cq.Workplane("XY").add(cq.Solid.makeCylinder(3.1, 1.8, cq.Vector(0.4, HINGE_Y, HINGE_Z), cq.Vector(1, 0, 0)))
    shaft = cq.Workplane("XY").add(cq.Solid.makeCylinder(HPIN_D / 2, BASE_L - 4.6, cq.Vector(2.1, HINGE_Y, HINGE_Z), cq.Vector(1, 0, 0)))
    barb = cq.Workplane("XY").add(cq.Solid.makeCylinder(HPIN_D / 2 + 0.15, 3.0, cq.Vector(BASE_L - 9.0, HINGE_Y, HINGE_Z), cq.Vector(1, 0, 0)))
    pin = head.union(shaft).union(barb)
    flat = rbox(-1, HINGE_Y - 5, BASE_L + 1, HINGE_Y + 5, HINGE_Z - 5, HINGE_Z - 1.45, 0)   # print flat
    return {"petg": pin.cut(flat)}


def build_tube_hook():
    """Bag hook that straps straight onto a handle tube (bag load goes into the tube, not the stand).
    Flat part: back face X=0 against the tube, Z up; the J curls sideways in the plate plane."""
    T, W = 6.0, 26.0
    plate = rbox(0, -W / 2, T, W / 2, 0, 44.0, 0).edges("|X").fillet(4.0)
    for s in (-1, 1):   # strap slots near both edges
        plate = plate.cut(rbox(-1, s * 9.0 - 1.3, T + 1, s * 9.0 + 1.3, 13.0, 31.0, 1.0))
    path = (cq.Workplane("YZ").moveTo(0.0, 4.0).lineTo(0.0, -16.0)
            .threePointArc((12.0, -28.0), (24.0, -16.0)).lineTo(24.0, -9.0))
    j = path.offset2D(3.5, "arc").extrude(T)
    hook = plate.union(j)
    tpu = rbox(-0.8, -W / 2 + 3, 0.6, W / 2 - 3, 3.0, 41.0, 0)
    hook = hook.cut(tpu)
    return {"petg": hook, "tpu": tpu}


if __name__ == "__main__":
    for fn, args in [(build_panel, (0,)), (build_panel, (1,)), (build_hinge_pin, ()), (build_tube_hook, ()),
                     (build_buckle, ()), (build_strap, ()), (build_pin, ()), (build_hook, ("mini",))]:
        r = fn(*args)
        for k, v in r.items():
            sh = v.val(); bb = sh.BoundingBox()
            print(fn.__name__, args, k, [round(x, 1) for x in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)],
                  round(sh.Volume()), sh.isValid())
