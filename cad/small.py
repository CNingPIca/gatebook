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
    """Flat TPU strap, lies on the bed (XY), length along X."""
    s = rbox(0, -STRAP_W / 2, STRAP_L, STRAP_W / 2, 0, STRAP_T, STRAP_W / 2 - 0.01)
    holes = [6.0] + [40.0 + i * STRAP_PITCH for i in range(int((STRAP_L - 46) / STRAP_PITCH) + 1)]
    for x in holes:
        s = s.cut(cyl(x, 0, -1, STRAP_T + 2, STRAP_HOLE))
    return {"tpu": s}


if __name__ == "__main__":
    for d in ring_dims():
        print({k: round(v, 2) if isinstance(v, float) else v for k, v in d.items()})
        r = build_ring(d)
        print("  ring vol", round(r["petg"].val().Volume()), "tpu", round(r["tpu"].val().Volume()), r["petg"].val().isValid())
    p = build_pin()["petg"].val()
    print("pin", p.BoundingBox().zmin, p.BoundingBox().zmax, round(p.Volume()), p.isValid())
    for k in ("bag", "mini"):
        h = build_hook(k)["petg"].val()
        bb = h.BoundingBox()
        print("hook", k, round(bb.xmin, 1), round(bb.xmax, 1), round(bb.ymin, 1), round(bb.ymax, 1), round(bb.zmin, 1), round(bb.zmax, 1), h.isValid())
    st = build_strap()["tpu"].val()
    print("strap", round(st.Volume()), st.isValid())
