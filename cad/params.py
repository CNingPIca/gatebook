"""GateBook 候机书 — shared parameters (mm).

Assembly frame (base frame):
  X: 0 at the tube-side end face of the base, + towards the far end (over the suitcase)
  Y: 0 .. BASE_W across the base
  Z: 0 = underside of the base, + up
The Q-Mount clamp sits at X < 0, its front face on X = 0.
"""

VERSION = "v1.0"

# ---------- global print tolerances ----------
CLR = 0.35          # sliding clearance (radial) for moving parts
CLR_TIGHT = 0.15    # dovetail clearance per flank

# ---------- book / base ----------
BASE_L = 210.0      # X  (A5 long side)
BASE_W = 148.0      # Y  (A5 short side)
BASE_H = 24.0       # Z
BASE_R = 10.0       # corner radius
FLOOR = 3.0
WALL = 2.4
DIV = 2.0           # internal divider thickness
END_WALL = 12.0     # thick tube-side wall that carries the dovetail groove

# bins (Y bands)
CH_A = (WALL, 27.0)            # long pen/cable channel (Y range)
CH_B = (121.0, BASE_W - WALL)  # three small cells (Y range)
MID = (29.0, 119.0)            # middle band: cup well + clamp bay
BIN_X0 = END_WALL
BIN_X1 = 178.4                 # far-end solid block starts here
BAY_X0 = 104.0                 # clamp bay start (divider before it)

# cup well (telescoping cup holder)
CUP_C = (57.0, 74.0)
CUP_BORE = 86.0
CUP_LIP = 2.2       # radial lip overlap
CUP_LIP_T = 2.0     # base bottom lip thickness
RING_T = 1.6        # ring wall
RING_H = 21.0       # ring height
RING_LIP_T = 1.6    # ring top/bottom lip thickness

# phone slot (far end, leans back 15 deg)
PHONE_Y = (32.0, 116.0)
PHONE_W = 13.0
PHONE_DEPTH = 18.0
PHONE_LEAN = 15.0
PHONE_TOP_X = 188.0            # slot front edge at top surface

# table pivots (two sockets -> table can swing to either side)
PIV_INSET = 15.0
PIVOTS = [(BASE_L - PIV_INSET, PIV_INSET), (BASE_L - PIV_INSET, BASE_W - PIV_INSET)]
PIN_D = 10.0
PIN_BORE = 10.4
PIN_LEDGE_D = 13.0
PIN_LEDGE_Z = 4.0
DETENT_R = 11.5
DIMPLE_D = 4.2
DIMPLE_DEPTH = 0.35
NUB_D = 4.0
NUB_PROTRUDE = 0.5

# magnets (optional, 6x3 mm)
MAG_D = 6.3
MAG_H = 3.2
MAGNETS = [(6.0, 14.0), (6.0, BASE_W - 14.0)]

# hook bayonet sockets (underside)
HOOK_SOCKETS = [(30.0, 14.0), (30.0, BASE_W - 14.0)]
BAYO_SLOT = (12.4, 5.0)
BAYO_CAV_D = 14.0
BAYO_CAV_H = 3.6
BAYO_BOSS_D = 19.0
BAYO_BOSS_H = 7.5   # above floor

# ---------- table (hard cover) ----------
TBL_OVER = 1.5                     # cover overhang like a hardcover book
TBL_L = BASE_L + 2 * TBL_OVER
TBL_W = BASE_W + 2 * TBL_OVER
TBL_H = 9.0
TBL_R = BASE_R + TBL_OVER
TBL_LIP_H = 1.2
TBL_LIP_W = 2.5
TPU_INLAY = 0.8
# boarding-pass sleeve inside the table
PASS_Y = (30.0, 118.0)             # 88 wide: fits 80-82 mm passes and ID cards
PASS_X0 = 24.0
PASS_GAP = 2.2
PASS_Z0 = 2.4                      # bottom skin thickness (from table underside)
PASS_NOTCH_R = 14.0

# ---------- Q-Mount clamp ----------
CL_H = 80.0         # along tube
CL_W = 46.0
CL_D = 17.0         # body depth (X), front face at X=0
V_MOUTH = 36.0
V_ANGLE = 120.0
PAD_T = 1.2         # TPU pad thickness
CH_DEPTH = 2.0      # strap channel depth on front face
CH_Z = [(2.0, 24.0), (56.0, 78.0)]
TONGUE_Z = (28.0, 52.0)             # = BASE_H tall
TONGUE_ROOT = 14.0
TONGUE_TIP = 20.0
TONGUE_H = 3.5
TONGUE_TAPER = 2.0                  # deg per side, wider at the bottom (gravity wedge)
PEG_Z = [13.0, 67.0]
PEG_X = -8.5
PEG_STEM = 4.5
PEG_HEAD = 7.0
PEG_LEN = 3.5
# clamp sits so that the base underside (Z=0) is at clamp z = TONGUE_Z[0]
CLAMP_Z_OFF = -TONGUE_Z[0]

# ---------- TPU strap ----------
STRAP_W = 20.0
STRAP_T = 1.8
STRAP_L = 130.0
STRAP_HOLE = 4.4
STRAP_PITCH = 6.0
