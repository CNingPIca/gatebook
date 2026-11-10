"""v1.1 — builds every part, defines assembly states (use / book / exploded),
checks interference and provides transforms for export + viewer."""
import math
import time
from collections import OrderedDict

import numpy as np
import cadquery as cq

from params import *
import base as basemod
import table as tablemod
import small


# ---------------------------------------------------------------- transforms
def T(x=0, y=0, z=0):
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


def Rz(deg, cx=0, cy=0):
    a = math.radians(deg)
    m = np.eye(4)
    m[0, 0], m[0, 1], m[1, 0], m[1, 1] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return T(cx, cy) @ m @ T(-cx, -cy)


def Rx(deg, cy=0, cz=0):
    a = math.radians(deg)
    m = np.eye(4)
    m[1, 1], m[1, 2], m[2, 1], m[2, 2] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return T(0, cy, cz) @ m @ T(0, -cy, -cz)


def Ry(deg):
    a = math.radians(deg)
    m = np.eye(4)
    m[0, 0], m[0, 2], m[2, 0], m[2, 2] = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    return m


def apply(shape, m):
    from OCP.gp import gp_Trsf
    m = np.round(np.asarray(m, dtype=float), 12)
    tr = gp_Trsf()
    tr.SetValues(*[float(v) for v in m[0]], *[float(v) for v in m[1]], *[float(v) for v in m[2]])
    return shape.moved(cq.Location(tr))


def panel_deploy(side):
    """Folded -> deployed transform for the left (0) / right (1) side panel."""
    hy = HINGE_Y if side == 0 else BASE_W - HINGE_Y
    return Rx(DEPLOY_DEG if side == 0 else -DEPLOY_DEG, hy, HINGE_Z)


# ---------------------------------------------------------------- parts
def build_parts():
    t = time.time()
    P = OrderedDict()
    P["base"] = basemod.build()
    P["table"] = tablemod.build()
    P["panel_l"] = small.build_panel(0)
    P["panel_r"] = small.build_panel(1)
    P["hinge_pin"] = small.build_hinge_pin()
    for d in small.ring_dims():
        P[f"ring{d['k']}"] = small.build_ring(d)
    P["pin"] = small.build_pin()
    P["hook_mini"] = small.build_hook("mini")
    P["tube_hook"] = small.build_tube_hook()
    P["strap"] = small.build_strap()
    P["buckle"] = small.build_buckle()
    print(f"parts built in {time.time() - t:.1f}s")
    return P


def foot_z(P=None):
    """Z of the luggage top = lowest point of the deployed TPU feet."""
    tpu = small.build_panel(0)["tpu"].val()
    return apply(tpu, panel_deploy(0)).BoundingBox().zmin


# ---------------------------------------------------------------- context (not printed)
TUBE_W, TUBE_D = 24.0, 16.0
TUBE_CC = 230.0                       # tube centre distance of a typical carry-on
GRIP_ABOVE_TOP = 420.0                # grip underside above the luggage top (handle fully extended)


def build_context(z_top):
    ctx = OrderedDict()
    yc = BASE_W / 2
    x1 = -0.6
    x0 = x1 - TUBE_D
    tubes = None
    for s in (-1, 1):
        ty = yc + s * TUBE_CC / 2
        t = basemod.rbox(x0, ty - TUBE_W / 2, x1, ty + TUBE_W / 2, z_top - 30, z_top + GRIP_ABOVE_TOP + 20, 3.0)
        tubes = t if tubes is None else tubes.union(t)
    ctx["tube"] = tubes
    gz = z_top + GRIP_ABOVE_TOP
    ctx["grip"] = (basemod.rbox(x0 - 6, yc - TUBE_CC / 2 - 22, x1 + 6, yc + TUBE_CC / 2 + 22, gz, gz + 32, 8.0)
                   .edges("not |Z").fillet(5.0))
    sc = basemod.rbox(x0 - 8, yc - 195, x0 + 232, yc + 195, z_top - 550, z_top, 40.0)
    sc = sc.faces(">Z").edges().fillet(25.0)
    # the luggage's own top carry handle (centred): the arched panels clear it
    th = (basemod.rbox(95, yc - 62, 120, yc + 62, z_top - 2, z_top + 18, 6.0).edges("not |Z").fillet(4.0)
          .cut(basemod.rbox(90, yc - 50, 125, yc + 50, z_top - 3, z_top + 9, 0)))
    ctx["suitcase"] = sc.union(th)
    # tether straps: loop bar <-> tube (velcro or TPU), shown as bands
    bands = None
    for i, yb in enumerate(ANCHORS):
        ty = yc + (-1 if i == 0 else 1) * TUBE_CC / 2
        ya, yb2 = yb - BAR_W / 2 - WIN_W / 2, yb + BAR_W / 2 + WIN_W / 2
        pts = [(BACK_WALL + 1.2, ya), (BACK_WALL + 1.2, yb2), (-1.0, yb2), (x0 - 0.3, ty + TUBE_W / 2),
               (x0 - 0.3, ty - TUBE_W / 2), (-1.0, ya)]
        hull = cq.Workplane("XY").polyline(pts).close()
        outer = hull.offset2D(1.8, "arc").extrude(STRAP_W - 0.5)
        inner = cq.Workplane("XY").polyline(pts).close().extrude(STRAP_W + 2).translate((0, 0, -1))
        b = outer.cut(inner).translate((0, 0, WIN_Z[0] + 0.8))
        bands = b if bands is None else bands.union(b)
    ctx["bands"] = bands
    return ctx


# ---------------------------------------------------------------- states
_DROP = CLR + (RING_H - RING_LIP_T - CUP_LIP)
RING_Z_USE = {2: CUP_LIP_T - _DROP}
RING_Z_USE[3] = RING_Z_USE[2] + RING_LIP_T - _DROP
RING_Z_USE[4] = RING_Z_USE[3] + RING_LIP_T - _DROP
RING_Z_BOOK = {2: 3.0, 3: 3.0, 4: 3.0}


def states(table_deg=180.0):
    cx, cy = CUP_C
    S = OrderedDict()
    pin_l = np.eye(4)
    pin_r = T(0, BASE_W - 2 * HINGE_Y, 0)

    use = OrderedDict()
    use["base"] = [np.eye(4)]
    use["table"] = [Rz(table_deg, *PIVOT)]
    use["panel_l"] = [panel_deploy(0)]
    use["panel_r"] = [panel_deploy(1)]
    use["hinge_pin"] = [pin_l, pin_r]
    for k in (2, 3, 4):
        use[f"ring{k}"] = [T(cx, cy, RING_Z_USE[k])]
    use["pin"] = [T(*PIVOT, 0)]
    hx, hy = HOOK_SOCKETS[0]
    use["hook_mini"] = [T(hx, hy) @ Rz(90)]
    # tube hook strapped to the left tube, back face on the tube's outer side
    z_top = foot_z()
    ty = BASE_W / 2 - TUBE_CC / 2
    use["tube_hook"] = [T(-0.6 - TUBE_D - 0.8, ty, z_top + 150) @ Rz(180)]
    use["strap"] = []
    use["buckle"] = []
    S["use"] = use

    book = OrderedDict()
    book["base"] = [np.eye(4)]
    book["table"] = [np.eye(4)]
    book["panel_l"] = [np.eye(4)]
    book["panel_r"] = [np.eye(4)]
    book["hinge_pin"] = [pin_l, pin_r]
    for k in (2, 3, 4):
        book[f"ring{k}"] = [T(cx, cy, RING_Z_BOOK[k])]
    book["pin"] = [T(*PIVOT, 0)]
    floor_top = RING_Z_BOOK[4] + RING_LIP_T
    book["hook_mini"] = [T(cx, cy - 8.1, floor_top + 2.3 + 0.2) @ Rx(90)]
    # big bin (X 30..120, Y 12..103): tube hook flat, two straps rolled flat, two buckles
    book["tube_hook"] = [T(76, 27, FLOOR + 0.85) @ Ry(-90)]
    book["strap"] = []          # rolled up in the big bin (not drawn)
    book["buckle"] = [T(45, 84, FLOOR + 0.05), T(75, 84, FLOOR + 0.05)]
    S["book"] = book

    ex = OrderedDict()
    ex["base"] = [np.eye(4)]
    ex["table"] = [T(0, 0, 70)]
    ex["panel_l"] = [T(0, -40, -60) @ panel_deploy(0)]
    ex["panel_r"] = [T(0, 40, -60) @ panel_deploy(1)]
    ex["hinge_pin"] = [T(-90, 0, 0) @ pin_l, T(-90, 0, 0) @ pin_r]
    for i, k in enumerate((2, 3, 4)):
        ex[f"ring{k}"] = [T(cx, cy, -40 - 32 * i)]
    ex["pin"] = [T(*PIVOT, 120)]
    ex["hook_mini"] = [T(hx, hy, -45) @ Rz(90)]
    ex["tube_hook"] = [T(-120, BASE_W / 2, -40)]
    ex["strap"] = [T(-60, 20, -110) @ Rz(90), T(-60, 190, -110) @ Rz(90)]
    ex["buckle"] = [T(-60, 60, -100), T(-60, 150, -100)]
    S["exploded"] = ex
    return S


def placed(P, state, name):
    out = []
    for m in state.get(name, []):
        for mat, wp in P[name].items():
            out.append((mat, apply(wp.val(), m)))
    return out


def interference(P, S, ctx=None, tol=1.0, only=("use", "book")):
    rep = {}
    for sname in only:
        st = S[sname]
        shp = {}
        for n in st:
            for mat, sh in placed(P, st, n):
                shp.setdefault(f"{n}:{mat}", []).append(sh)
        if sname == "use" and ctx is not None:
            for k in ("tube", "suitcase"):
                shp["ctx_" + k + ":ctx"] = [ctx[k].val()]
        keys = list(shp)
        res = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = keys[i], keys[j]
                if a.split(":")[0] == b.split(":")[0] or (a.startswith("ctx") and b.startswith("ctx")):
                    continue
                v = 0.0
                for sa in shp[a]:
                    for sb in shp[b]:
                        b1, b2 = sa.BoundingBox(), sb.BoundingBox()
                        if (b1.xmax < b2.xmin or b2.xmax < b1.xmin or b1.ymax < b2.ymin or b2.ymax < b1.ymin
                                or b1.zmax < b2.zmin or b2.zmax < b1.zmin):
                            continue
                        try:
                            v += sa.intersect(sb).Volume()
                        except Exception:
                            v += -1
                if abs(v) > tol:
                    res.append((a, b, round(v, 1)))
        rep[sname] = res
    return rep


if __name__ == "__main__":
    P = build_parts()
    zt = foot_z()
    print("luggage top (feet) z =", round(zt, 2))
    ctx = build_context(zt)
    S = states()
    t = time.time()
    rep = interference(P, S, ctx)
    print(f"interference check {time.time() - t:.1f}s")
    for k, v in rep.items():
        print(k, v if v else "no interference")
