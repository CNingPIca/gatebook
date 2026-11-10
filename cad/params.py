"""GateBook 候机书 v1.1 — shared parameters (mm).

v1.1 = "stand" architecture: the book stands on the luggage TOP on two
fold-down side panels (vertical load path), centred between the two
handle tubes, and is only tethered to the tubes by two straps.

Base frame:
  X: 0 at the back face (against the handle tubes) -> + forward over the luggage
  Y: 0 .. BASE_W along the handle (left -> right), centre at BASE_W/2
  Z: 0 = underside of the base, + up
"""

VERSION = "v1.1"

CLR = 0.35          # sliding clearance (radial)
CLR_PIN = 0.2       # hinge pin clearance (diametral)

# ---------- base ("page block") ----------
BASE_L = 148.0      # X (A5 short side)
BASE_W = 210.0      # Y (A5 long side, along the handle)
BASE_H = 24.0
BASE_R = 10.0
FLOOR = 3.0
WALL = 2.4
DIV = 2.0
BACK_WALL = 10.0    # carries the strap windows / loop bars
SIDE_BAND = 12.0    # solid side bands carrying the panel hinges

# bins
BACK_BAND = (BACK_WALL, 28.0)          # X range of the back row
MID_BAND = (30.0, 120.0)               # X range of the middle row
FRONT_BAND = (122.0, BASE_L - WALL)    # X range of the front strip (under the table root at 180 deg)
PHONE_Y = (63.0, 147.0)                # phone slot (back row, centred)
PHONE_W = 13.0
PHONE_DEPTH = 18.0
PHONE_LEAN = 15.0                      # top leans back towards the tubes
PHONE_TOP_X = 12.5

# cup well (telescoping drop-down cup holder) — right of centre
CUP_C = (76.0, 150.0)
CUP_BORE = 86.0
CUP_LIP = 2.2
CUP_LIP_T = 2.0
RING_T = 1.6
RING_H = 21.0
RING_LIP_T = 1.6

# strap anchor stations in the back wall: window, loop bar, window (Y ranges)
STRAP_W = 16.0                          # TPU strap width (also fits 15 mm velcro ties)
WIN_W = 4.6
BAR_W = 14.0
ANCHORS = [20.0, 190.0]                 # Y centre of each loop bar
WIN_Z = (3.0, 21.0)

# table pivot (front centre) — the cover swings 180 deg forward on the centre line
PIVOT = (BASE_L - 12.0, BASE_W / 2)
PIVOTS = [PIVOT]
PIN_D = 10.0
PIN_BORE = 10.4
PIN_LEDGE_D = 13.0
PIN_LEDGE_Z = 4.0
DETENT_R = 9.0
DIMPLE_D = 4.2
DIMPLE_DEPTH = 0.35
NUB_D = 4.0
NUB_PROTRUDE = 0.5

# optional magnets 6x3 (cover <-> base)
MAG_D = 6.3
MAG_H = 3.2
MAGNETS = [(5.0, 52.0), (5.0, BASE_W - 52.0)]

# mini-hook bayonet socket (underside, between the legs)
HOOK_SOCKETS = [(112.0, 85.0)]
BAYO_SLOT = (12.4, 5.0)
BAYO_CAV_D = 14.0
BAYO_CAV_H = 3.6
BAYO_BOSS_D = 19.0
BAYO_BOSS_H = 7.5

# ---------- side panels = legs (fold flat under the base like a split back cover) ----------
PANEL_T = 6.0                 # plate thickness (folded: Z in [-PANEL_T, 0])
HINGE_Y = 5.0                 # hinge axis (left panel), along X
HINGE_Z = 3.0                 # axis sits inside the base's side band
KNUCKLE_R = 3.0
HPIN_D = 3.5                  # printed straight hinge pin (no thread)
PANEL_Y0 = 8.27               # plate starts inboard of the axis: its top corner is the 95-deg stop
PANEL_LEN = 92.0              # plate length (folded Y extent from PANEL_Y0)
PANEL_X = (4.0, BASE_L - 4.0)
KNUCKLES = [(13.5, 30.5), (45.5, 62.5), (85.5, 102.5), (117.5, 134.5)]  # base channel X ranges
DEPLOY_DEG = -95.0            # 5 deg splay outward, self-locks under load
FOOT_TPU = 1.5

# ---------- table (hard cover) ----------
TBL_OVER = 1.5
TBL_L = BASE_L + 2 * TBL_OVER          # X
TBL_W = BASE_W + 2 * TBL_OVER          # Y
TBL_H = 9.0
TBL_R = BASE_R + TBL_OVER
TBL_LIP_H = 1.2
TBL_LIP_W = 2.5
TPU_INLAY = 0.8
PASS_X = (30.0, 118.0)                 # 88 wide: 80-82 mm passes, ID cards
PASS_Y0 = 24.0                         # sleeve runs along +Y, open at the right edge
PASS_GAP = 2.2
PASS_Z0 = 2.4
PASS_NOTCH_R = 14.0

# ---------- straps ----------
STRAP_T = 1.8
STRAP_L = 180.0
STRAP_HOLE = 4.4
STRAP_PITCH = 6.0
