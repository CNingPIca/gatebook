"""Builds every part, defines assembly states (use / book / exploded), checks
interference and exports print files + viewer meshes."""
import json
import math
import os
import time
from collections import OrderedDict

import numpy as np
import cadquery as cq

from params import *
import base as basemod
import table as tablemod
import clamp as clampmod
import small

OUT = os.path.join(os.path.dirname(__file__), "..", "out")


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


def Rx(deg):
    a = math.radians(deg)
    m = np.eye(4)
    m[1, 1], m[1, 2], m[2, 1], m[2, 2] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return m


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


# ---------------------------------------------------------------- context (not printed)
TUBE_W, TUBE_D = 24.0, 16.0          # a typical rectangular carry-on tube


def tube_x():
    half = V_MOUTH / 2
    x_face = -CL_D + (half - TUBE_W / 2) / math.tan(math.radians(V_ANGLE / 2)) - 0.4
    return x_face - TUBE_D, x_face


GRIP_Z0 = 150.0
SUITCASE_TOP = -300.0
TUBE_GAP = 230.0                      # centre distance between the two tubes


def build_context():
    x0, x1 = tube_x()
    ctx = OrderedDict()
    yc = BASE_W / 2
    tz0, tz1 = SUITCASE_TOP - 20, GRIP_Z0 + 22
    tube = basemod.rbox(x0, yc - TUBE_W / 2, x1, yc + TUBE_W / 2, tz0, tz1, 3.0)
    tube2 = tube.translate((0, -TUBE_GAP, 0))
    ctx["tube"] = tube.union(tube2)
    grip = (basemod.rbox(x0 - 6, yc - TUBE_GAP - 22, x1 + 6, yc + 22, GRIP_Z0, GRIP_Z0 + 32, 8.0)
            .edges("not |Z").fillet(5.0))
    ctx["grip"] = grip
    sc = basemod.rbox(x0 - 6, yc - TUBE_GAP / 2 - 195, x0 + 230, yc - TUBE_GAP / 2 + 195, SUITCASE_TOP - 520, SUITCASE_TOP, 40.0)
    sc = sc.faces(">Z").edges().fillet(25.0)
    ctx["suitcase"] = sc
    # two straps wrapped around clamp + tube (velcro / TPU band), in the strap channels
    xc0 = x0 - 0.2
    pts = [(-CH_DEPTH + 0.01, -CL_W / 2 + 3), (-CH_DEPTH + 0.01, CL_W / 2 - 3), (-CL_D + 2, CL_W / 2), (xc0 + 2, TUBE_W / 2),
           (xc0, TUBE_W / 2 - 3), (xc0, -TUBE_W / 2 + 3), (xc0 + 2, -TUBE_W / 2), (-CL_D + 2, -CL_W / 2)]
    bands = None
    for z0, z1 in CH_Z:
        outer = cq.Workplane("XY").polyline(pts).close().offset2D(1.8, "arc").extrude(STRAP_W - 0.4)
        inner = cq.Workplane("XY").polyline(pts).close().extrude(STRAP_W + 2).translate((0, 0, -1))
        b = outer.cut(inner).translate((0, yc, z0 + 1.0 + CLAMP_Z_OFF))
        bands = b if bands is None else bands.union(b)
    ctx["bands"] = bands
    return ctx


# ---------------------------------------------------------------- parts
def build_parts():
    t = time.time()
    P = OrderedDict()
    P["base"] = basemod.build()
    P["table"] = tablemod.build()
    P["clamp"] = clampmod.build()
    for d in small.ring_dims():
        P[f"ring{d['k']}"] = small.build_ring(d)
    P["pin"] = small.build_pin()
    P["hook_bag"] = small.build_hook("bag")
    P["hook_mini"] = small.build_hook("mini")
    P["strap"] = small.build_strap()
    print(f"parts built in {time.time() - t:.1f}s")
    return P


RING_Z_BOOK = {2: 3.0, 3: 3.0, 4: 3.0}
# extended: each ring's 45-deg lip cone sits on the parent's 45-deg seat
_DROP = CLR + (RING_H - RING_LIP_T - CUP_LIP)
RING_Z_USE = {2: CUP_LIP_T - _DROP}
RING_Z_USE[3] = RING_Z_USE[2] + RING_LIP_T - _DROP
RING_Z_USE[4] = RING_Z_USE[3] + RING_LIP_T - _DROP


def states(table_deg=90.0):
    cx, cy = CUP_C
    pa = PIVOTS[0]
    S = OrderedDict()
    use = OrderedDict()
    use["base"] = [np.eye(4)]
    use["table"] = [Rz(table_deg, *pa)]
    use["clamp"] = [T(0, BASE_W / 2, CLAMP_Z_OFF)]
    for k in (2, 3, 4):
        use[f"ring{k}"] = [T(cx, cy, RING_Z_USE[k])]
    use["pin"] = [T(*pa, 0)]
    hx, hy = HOOK_SOCKETS[0]
    hx2, hy2 = HOOK_SOCKETS[1]
    use["hook_bag"] = [T(hx, hy) @ Rz(-90)]
    use["hook_mini"] = [T(hx2, hy2) @ Rz(90)]
    use["strap"] = []
    S["use"] = use

    book = OrderedDict()
    book["base"] = [np.eye(4)]
    book["table"] = [np.eye(4)]
    # clamp lies on its back in the bay: clamp X->Z, Y->X, Z->Y
    Rc = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], dtype=float)
    book["clamp"] = [T(BAY_X0 + 2.0 + CL_W / 2 + PEG_LEN - 1.0, MID[0] + 5.0, FLOOR + CL_D + 0.05) @ Rc]
    for k in (2, 3, 4):
        book[f"ring{k}"] = [T(cx, cy, RING_Z_BOOK[k])]
    book["pin"] = [T(*pa, 0)]
    # hooks stored lying flat inside the collapsed cup (on the R4 floor)
    floor_top = RING_Z_BOOK[4] + RING_LIP_T
    book["hook_bag"] = [T(cx - 8.5, cy - 18.9, floor_top + 2.3 + 0.1) @ Rx(90)]
    book["hook_mini"] = [T(cx, cy - 8.1, floor_top + 6.0 + 2.3 + 0.3) @ Rx(90)]
    # two straps flat in the long channel
    book["strap"] = [T(BIN_X1 - 4 - STRAP_L, (CH_A[0] + CH_A[1]) / 2, FLOOR + 0.05),
                     T(BIN_X1 - 4 - STRAP_L, (CH_A[0] + CH_A[1]) / 2, FLOOR + STRAP_T + 0.1)]
    S["book"] = book

    ex = OrderedDict()
    ex["base"] = [np.eye(4)]
    ex["table"] = [T(0, 0, 70)]
    ex["clamp"] = [T(-70, BASE_W / 2, CLAMP_Z_OFF)]
    for i, k in enumerate((2, 3, 4)):
        ex[f"ring{k}"] = [T(cx, cy, -40 - 32 * i)]
    ex["pin"] = [T(*pa, 120)]
    ex["hook_bag"] = [T(hx, hy, -45) @ Rz(-90)]
    ex["hook_mini"] = [T(hx2, hy2, -45) @ Rz(90)]
    ex["strap"] = [T(-150, BASE_W / 2 - 40, -60) @ Rz(90), T(-125, BASE_W / 2 - 40, -60) @ Rz(90)]
    S["exploded"] = ex
    return S


def placed(P, state, name):
    out = []
    for m in state.get(name, []):
        for mat, wp in P[name].items():
            out.append((mat, apply(wp.val(), m)))
    return out


def interference(P, S, ctx=None, pairs=None, tol=1.0):
    """Report intersection volume (mm^3) between parts in each state."""
    rep = {}
    for sname in ("use", "book"):
        st = S[sname]
        names = [n for n in st if st[n]]
        shp = {}
        for n in names:
            for mat, sh in placed(P, st, n):
                shp.setdefault(f"{n}:{mat}", []).append(sh)
        if sname == "use" and ctx is not None:
            for k in ("tube", "grip"):
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
                        bb1, bb2 = sa.BoundingBox(), sb.BoundingBox()
                        if (bb1.xmax < bb2.xmin or bb2.xmax < bb1.xmin or bb1.ymax < bb2.ymin or bb2.ymax < bb1.ymin
                                or bb1.zmax < bb2.zmin or bb2.zmax < bb1.zmin):
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
    ctx = build_context()
    S = states()
    t = time.time()
    rep = interference(P, S, ctx)
    print(f"interference check {time.time() - t:.1f}s")
    for k, v in rep.items():
        print(k, v if v else "no interference")
