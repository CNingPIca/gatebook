"""Hand-calc load checks for GateBook (statics + material strength).
All forces N, lengths m, moments N*m, stresses MPa.  Conservative inputs."""
import math

g = 9.81
# ---------------- material data (printed, conservative) ----------------
PETG = dict(rho=1.27, sigma_xy=38.0, sigma_z=20.0, tau=20.0, E=1800.0)   # XY in-layer / Z across layers
TPU = dict(rho=1.21, sigma=25.0, E10=26.0)                                # E10: secant modulus at ~10 % strain
MU_TPU_AL = 0.6     # TPU pad on anodised / painted aluminium tube (dry)
MU_VELCRO_AL = 0.3

# ---------------- loads ----------------
LOAD = dict(device=0.40, cup=0.55, phone=0.22, table_items=0.50, bag=1.5)   # kg
LEAN = 5.0   # kg: forearm leaning on the table edge (misuse case)


def sf(cap, dem):
    return cap / dem if dem > 0 else float("inf")


def v10():
    """v1.0: single V-clamp on ONE tube, base cantilevered 210 mm out."""
    r = {}
    T = [20.0, 40.0]                       # strap tension, hand-tight velcro .. TPU strap
    W = (LOAD["device"] + LOAD["cup"] + LOAD["phone"] + LOAD["table_items"] + LOAD["bag"]) * g
    # V-block 120 deg: tube pressed with P = 2T per strap; pad normal sum = 1.155 P
    for t in T:
        P = 2 * t
        cap_slip = 2 * (MU_TPU_AL * 1.155 * P + MU_VELCRO_AL * P)
        r[f"slip SF (T={t:.0f}N)"] = sf(cap_slip, W)
    # pitch moment about the clamp's lower contact (arms from the tube contact line, x measured +X)
    arms = dict(device=(LOAD["device"], 0.105 + 0.014), cup=(LOAD["cup"], 0.057 + 0.014),
                phone=(LOAD["phone"], 0.200 + 0.014), table_items=(LOAD["table_items"], 0.136 + 0.014),
                bag=(LOAD["bag"], 0.030 + 0.014))
    M = sum(m * g * x for m, x in arms.values())
    M_lean = M + LEAN * g * (0.211 + 0.014)
    lever = 0.067                          # top strap to lower contact
    for t in T:
        cap = 2 * t * lever
        r[f"pitch SF normal (T={t:.0f}N)"] = sf(cap, M)
        r[f"pitch SF lean (T={t:.0f}N)"] = sf(cap, M_lean)
    r["pitch moment normal N*m"] = M
    # luggage side-tip: empty carry-on 3 kg, wheel half-track 0.16 m
    restoring = 3.0 * g * 0.16
    side = (LOAD["device"] * 0.115 + LOAD["cup"] * 0.115 + LOAD["phone"] * 0.115 + LOAD["bag"] * 0.055
            - (0.12 + LOAD["table_items"]) * 0.034) * g
    r["luggage side-tip SF (empty case)"] = sf(restoring, side)
    r["luggage side-tip SF, lean on table"] = sf(restoring, side + LEAN * g * 0.14)
    return r


def v11(p):
    """v1.1: stand on the luggage top (two fold-down side panels), tethered to BOTH tubes."""
    r = {}
    m_dev = p["mass_device"]
    W = (m_dev + LOAD["cup"] + LOAD["phone"] + LOAD["table_items"]) * g
    # 1) side panel in compression (each panel takes about half; one panel worst case 70 %)
    F_panel = 0.7 * (W + LEAN * g)
    A_net = p["panel_A_net"]                        # mm^2 smallest horizontal section
    r["panel compression SF (incl. lean)"] = sf(PETG["sigma_z"] * A_net, F_panel)
    # Euler buckling of the thinnest leg strip (pinned-pinned, conservative)
    I = p["leg_b"] * p["leg_t"] ** 3 / 12
    Pcr = math.pi ** 2 * PETG["E"] * I / p["leg_L"] ** 2
    r["panel leg buckling SF (incl. lean)"] = sf(2 * Pcr, F_panel)
    # 2) forward tip about the front feet with the table swung forward (180 deg)
    xf = p["x_front_feet"]
    Mt = (LOAD["table_items"] * g * (p["x_table_c"] - xf))
    Mr_self = m_dev * g * (xf - p["x_dev_c"]) + LOAD["cup"] * g * (xf - p["x_cup"]) + LOAD["phone"] * g * (xf - p["x_phone"])
    Mr_strap = p["strap_T"] * 2 * p["h_strap"]
    r["forward tip SF, no strap"] = sf(Mr_self, Mt)
    r["forward tip SF, with straps"] = sf(Mr_self + Mr_strap, Mt)
    r["forward tip SF, lean + straps"] = sf(Mr_self + Mr_strap, Mt + LEAN * g * (p["x_table_end"] - xf))
    # 3) side tip of the stand about one panel's feet
    half_track = p["feet_half_track"]
    side_load = LOAD["cup"] * g * p["y_cup_off"]
    r["stand side-tip SF (cup off-centre)"] = sf((m_dev + LOAD["table_items"] + LOAD["phone"]) * g * half_track, side_load)
    # 4) luggage side tip (empty 3 kg case, half-track 0.16 m): only the off-centre cup acts
    r["luggage side-tip SF (empty case)"] = sf(3.0 * g * 0.16, side_load)
    # 5) table pivot pin hold-down at 180 deg (fulcrum = base front edge, pin 12 mm behind it)
    arm_pin = p["pin_behind_fulcrum"]
    F_pin = (LOAD["table_items"] * g * p["table_load_arm"] + 0.12 * g * p["table_load_arm"] * 0.6) / arm_pin
    F_pin_lean = F_pin + LEAN * g * p["table_end_arm"] / arm_pin
    A_head_shear = math.pi * 10.0 * 2.0
    r["pin head shear SF normal"] = sf(PETG["tau"] * A_head_shear, F_pin)
    r["pin head shear SF lean"] = sf(PETG["tau"] * A_head_shear, F_pin_lean)
    # 6) table bending at the root (sandwich: two 0.8 mm skins + 15 % infill ignored)
    b, h, ts = 151.0, 9.0, 0.8
    I_t = 2 * b * ts * ((h - ts) / 2) ** 2
    M_root = LOAD["table_items"] * g * p["table_load_arm"] * 1000
    sig = M_root * (h / 2) / I_t
    r["table bending SF normal"] = sf(PETG["sigma_xy"], sig)
    sig_l = (M_root + LEAN * g * p["table_end_arm"] * 1000) * (h / 2) / I_t
    r["table bending SF lean"] = sf(PETG["sigma_xy"], sig_l)
    r["table tip deflection normal (mm)"] = (LOAD["table_items"] * g) * (p["table_load_arm"] * 1000) ** 3 / (3 * PETG["E"] * I_t)
    # 7) strap anchor bar (vertical PETG bar, printed in Z -> across layers), fixed-fixed, centre load
    Lb, bb, db = p["bar_L"], p["bar_b"], p["bar_d"]
    Mb = 2 * p["strap_T"] * Lb / 8
    Zb = bb * db ** 2 / 6
    r["strap bar bending SF"] = sf(PETG["sigma_z"], Mb / Zb)
    # 8) TPU strap net section
    A_strap = (STRAP_W - STRAP_HOLE) * STRAP_T
    r["TPU strap tensile SF"] = sf(TPU["sigma"] * A_strap, p["strap_T"])
    # 9) bag hook strapped to a tube: slip
    P = 2 * p["strap_T"]
    r["tube-hook slip SF (1.5 kg bag)"] = sf(MU_TPU_AL * 1.155 * P + MU_TPU_AL * P, LOAD["bag"] * g)
    return r


STRAP_W, STRAP_T, STRAP_HOLE = 20.0, 1.8, 4.4

def print_mass(P):
    """Printed-mass estimate: 1.0 mm shell (walls + top/bottom) + 15 % infill; TPU solid."""
    out = {}
    for name, mats in P.items():
        m = 0.0
        for mat, wp in mats.items():
            sh = wp.val()
            V, A = sh.Volume() / 1000, sh.Area() / 100       # cm^3, cm^2
            if mat == "tpu":
                m += V * TPU["rho"]
            else:
                shell = min(V, A * 0.10)
                m += PETG["rho"] * (shell + 0.15 * (V - shell))
        out[name] = m
    return out


def v11_params(masses):
    import params as Pm
    dev_parts = ["base", "table", "panel_l", "panel_r", "hinge_pin", "ring2", "ring3", "ring4", "pin"]
    m_dev = sum(masses[n] * (2 if n == "hinge_pin" else 1) for n in dev_parts) / 1000
    m_tab = masses["table"] / 1000
    x_tab = (2 * Pm.PIVOT[0] - Pm.BASE_L / 2) / 1000         # table centroid when swung 180 deg forward
    x_cg = ((m_dev - m_tab) * 0.074 + m_tab * x_tab) / m_dev
    return dict(
        mass_device=m_dev, panel_A_net=2 * 18.0 * Pm.PANEL_T, leg_b=18.0, leg_t=Pm.PANEL_T, leg_L=62.0,
        x_front_feet=0.1425, x_table_c=x_tab, x_table_end=(2 * Pm.PIVOT[0] + Pm.TBL_OVER) / 1000,
        x_dev_c=x_cg, x_cup=Pm.CUP_C[0] / 1000, x_phone=0.020,
        strap_T=40.0, h_strap=(abs(-93.1) + 12.0) / 1000, feet_half_track=0.116, y_cup_off=(Pm.CUP_C[1] - Pm.BASE_W / 2) / 1000,
        pin_behind_fulcrum=(Pm.BASE_L - Pm.PIVOT[0]) / 1000, table_load_arm=x_tab - Pm.BASE_L / 1000,
        table_end_arm=(2 * Pm.PIVOT[0] + Pm.TBL_OVER - Pm.BASE_L) / 1000,
        bar_L=Pm.WIN_Z[1] - Pm.WIN_Z[0], bar_b=Pm.BAR_W, bar_d=Pm.BACK_WALL)


if __name__ == "__main__":
    import json, sys
    import assembly as A
    P = A.build_parts()
    masses = print_mass(P)
    p = v11_params(masses)
    r10, r11 = v10(), v11(p)
    for k, v in r10.items():
        print(f"v1.0  {k:42s} {v:7.2f}")
    print()
    for k, v in masses.items():
        print(f"mass  {k:42s} {v:7.1f} g")
    print(f"mass  device as carried (book, incl. hook/straps)  {sum(masses[n] * (2 if n in ('hinge_pin', 'strap', 'buckle') else 1) for n in masses):7.1f} g")
    print("device cg x (table 180):", round(p["x_dev_c"] * 1000, 1), "mm")
    for k, v in r11.items():
        print(f"v1.1  {k:42s} {v:7.2f}")
    json.dump({"v10": r10, "v11": r11, "mass_g": masses, "params": p}, open("../out/mech.json", "w"), indent=1, ensure_ascii=False)
