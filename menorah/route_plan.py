"""Deterministic (hand-planned) routing for the regular parts of the board: candles, crossbar, stem.

Everything here is on the BACK layer except the short front "hops" that carry each candle's
hall/+3V3 lines across the bar buses.  Coordinates are front-view mm like the rest of the project.

Produces two lists consumed by route.py:
    TRACKS = [(net, layer, width, [(x, y), ...]), ...]     layer is "F" or "B"
    VIAS   = [(net, x, y), ...]

Candle cross-section on the back (x relative to the candle centre):
    -4.45  GND trunk (1.0 wide, stitched to the front GND pour)
    -2.725 / +2.725  LED pads (DIN + GND on the left, VDD + DOUT on the right; LEDs are turned 180 deg)
    +3.90  VLED trunk      +4.46  data return (flame DOUT -> next candle)
    +4.87  hall output     +5.38  +3V3 for the hall sensor
The LED-to-LED data link runs right->left through the gap between two LEDs and passes between
the pads of that gap's decoupling capacitor, so no vias are needed anywhere in a candle body.
"""
import geometry as G
import netlist as N

TRACKS, VIAS = [], []

# crossbar bus levels (y, back layer)
Y_LINK = 73.0          # candle-to-candle data links
Y_VBUS = 74.5          # VLED bus, 1.0 wide
Y_T = 75.8             # +3V3 bus
Y_HL = {"C4": 76.7, "C3": 77.5, "C2": 78.3, "C1": 79.1}                  # left half hall lines
Y_DATA = 79.9          # LED_DATA_3V3 (ESP32 -> level shifter under C1)
Y_HR = {"SH": 76.7, "C5": 77.5, "C6": 78.3, "C7": 79.1, "C8": 79.9}      # right half hall lines

# stem columns (x, back layer), left -> right.  Hall columns are 0.66 apart so each one can drop
# through a via in line (a "staircase") and continue on the FRONT at the same x.
X_DATA = 94.5
X_HL = {"C1": 95.16, "C2": 95.82, "C3": 96.48, "C4": 97.14}
X_TL = 97.9
X_SCK, X_WS, X_SD = 98.45, 102.65, 103.1      # microphone lines (mic sits at 100, 95.3)
X_V = 103.9            # VLED trunk, 0.8 wide (directly below the shamash VLED drop)
X_TR = 104.7
X_HR = {"SH": 105.45, "C5": 106.11, "C6": 106.77, "C7": 107.43, "C8": 108.09}
X_EAST = dict(X_HR, C3=108.75, C4=109.41)      # back columns down the east side of the power section
Y_STAIR = {"C1": 103.2, "C2": 104.0, "C3": 104.8, "C4": 105.6}
Y_HOP = {"C4": 113.5, "C3": 114.16}            # front rows that carry C3/C4 across the stem foot
Y_STEM_END = 112.0     # scripted back columns stop here; maze.py continues into the base

# ESP32 module pads
PAD_X = 78.75
EAST_ROW = {"C1": 129.30, "C2": 130.57}                        # east pads 4, 5
Y_FROW = {"C1": 126.1, "C2": 126.55}                           # front rows just below the VBUS lane
X_FAN = {"C1": 81.3, "C2": 81.75}
X_PADVIA = 80.4
SOUTH = ["SH", "C5", "C6", "C7", "C8", "C3", "C4"]             # south pads 17..23, east -> west
X_SOUTH = {c: 74.445 - 1.27 * k for k, c in enumerate(SOUTH)}
Y_STRIP = {c: 144.45 + 0.45 * k for k, c in enumerate(SOUTH)}  # rows in the strip below the module
Y_SOUTH_PAD = 143.25
Y_VBUS_F = 125.2       # VBUS crosses under the module on the front, right below the antenna keep-out

W_SIG, W_T, W_PWR = 0.2, 0.4, 0.5


def T(net, pts, w=W_SIG, layer="B"):
    pts = [(round(x, 4), round(y, 4)) for x, y in pts]
    out = [pts[0]]
    for p in pts[1:]:
        if p != out[-1]:
            out.append(p)
    if len(out) > 1:
        TRACKS.append((net, layer, w, out))


def VIA(net, x, y):
    VIAS.append((net, round(x, 4), round(y, 4)))


def led_table():
    """candle id -> list of dicts (bottom -> top, flame last) with chain index n (1-based)."""
    tab = {}
    for i, led in enumerate(G.chain_order()):
        tab.setdefault(led["candle"], []).append(dict(n=i + 1, pos=led["pos"], kind=led["kind"]))
    return tab


def route_candle(c, leds, last):
    x0, Y = c["x"], c["top"]
    cid = c["id"]

    def A(dx, y):                      # absolute point from candle-relative x and absolute y
        return (x0 + dx, y)

    body = [l for l in leds if l["kind"] == "body"]
    flame = [l for l in leds if l["kind"] == "flame"][0]
    n_last = len(N.PARTS)              # unused, kept for clarity

    # ---------------------------------------------------------------- body LEDs
    for i, led in enumerate(body):
        y = led["pos"][1]
        din = f"LED_D{led['n'] - 1}"
        # data in: comes up between the pads of this LED's capacitor, then left under the LED window
        upper = [A(0, y + 2.825), A(-0.5, y + 2.325), A(-2.2, y + 2.325), A(-2.725, y + 1.8), A(-2.725, y + 0.75)]
        if i == 0:
            T(din, [A(0, Y_LINK - 0.5)] + upper)
        else:
            T(din, [A(2.725, y + 6.25), A(2.725, y + 5.25), A(2.2, y + 4.725), A(0.525, y + 4.725),
                    A(0, y + 4.2)] + upper)
        # VLED: trunk -> capacitor -> VDD pad
        T("VLED", [A(3.9, y + 3.5), A(0.775, y + 3.5)], W_PWR)
        T("VLED", [A(2.725, y + 3.5), A(2.725, y + 0.75)], W_PWR)
        # GND: LED pad and capacitor pad to the trunk, one stitching via per LED
        T("GND", [A(-2.725, y - 0.75), A(-4.45, y - 0.75)], W_PWR)
        if i == 0:      # bottom capacitor: the trunk stops short of the bar edge (C1 sits on the rounded bar end)
            T("GND", [A(-0.775, y + 3.5), A(-3.55, y + 3.5), A(-4.45, y + 2.6)], W_PWR)
        else:
            T("GND", [A(-0.775, y + 3.5), A(-4.45, y + 3.5)], W_PWR)
            VIA("GND", x0 - 4.45, y + 3.5)

    y_top = body[-1]["pos"][1]
    assert abs(y_top - (Y + 8)) < 1e-6, (cid, y_top, Y)
    fy = flame["pos"][1]
    assert abs(fy - (Y - 8.2)) < 1e-6

    # ---------------------------------------------------------------- trunks
    T("GND", [A(-4.45, 69.6), A(-4.45, Y + 3.3)], 1.0)
    VIA("GND", x0 - 4.45, 69.6)
    VIA("GND", x0 - 4.45, Y + 4.7)
    # VLED: bus -> trunk -> across under the hall sensor -> flame capacitor -> neck -> flame LED
    T("VLED", [A(3.9, 70.5 if last else Y_VBUS), A(3.9, Y + 5.25), A(-2.3, Y + 5.25), A(-2.825, Y + 4.725), A(-2.825, Y + 3.3)], W_PWR)
    T("VLED", [A(-2.825, Y + 3.3), A(-2.825, Y + 1.625), A(-1.0, Y - 0.2), A(-1.0, Y - 1.0), A(1.5, Y - 3.5),
               A(1.5, Y - 4.9), A(2.725, Y - 6.125), A(2.725, fy + 0.75)], 0.4)
    # GND up the neck to the flame LED (wraps round the outside of the DIN pad)
    T("GND", [A(-4.4, Y + 3.3), A(-4.4, Y + 1.7), A(-2.2, Y - 0.5), A(-2.2, Y - 4.2), A(-3.85, Y - 5.85),
              A(-3.85, fy - 0.75), A(-2.725, fy - 0.75)], 0.4)
    # data: top body LED -> flame LED (crosses to the left below the hall sensor, passes under the flame cap)
    T(f"LED_D{flame['n'] - 1}",
      [A(2.725, y_top - 0.75), A(2.725, Y + 6.425), A(2.2, Y + 5.9), A(-3.075, Y + 5.9), A(-3.6, Y + 5.375),
       A(-3.6, Y + 1.65), A(-1.6, Y - 0.35), A(-1.6, Y - 4.5), A(-2.725, Y - 5.625), A(-2.725, fy + 0.75)])
    # data return: flame DOUT -> down the neck -> right side of the candle -> bar
    if not last:
        ret = f"LED_D{flame['n']}"
        T(ret, [A(2.725, fy - 0.75), A(3.85, fy - 0.75), A(3.85, Y - 5.9), A(2.25, Y - 4.3), A(2.25, Y - 3.45),
                A(-0.4, Y - 0.8), A(-0.4, Y - 0.05), A(-2.05, Y + 1.6), A(-2.05, Y + 4.1), A(-1.55, Y + 4.6),
                A(4.26, Y + 4.6), A(4.46, Y + 4.8), A(4.46, Y_LINK - 0.5), A(4.96, Y_LINK)])

    # ---------------------------------------------------------------- hall sensor block (right of the sensor)
    hall = f"HALL_{cid}"
    T("GND", [A(-0.9375, Y + 2.0), A(2.6, Y + 2.0), A(3.0, Y + 2.325)], 0.3)
    T("GND", [A(3.0, Y + 2.325), A(4.45, Y + 2.325)], 0.4)
    VIA("GND", x0 + 4.45, Y + 2.325)
    T("+3V3", [A(0.9375, Y + 1.05), A(2.2, Y + 1.05), A(2.475, Y + 0.775), A(4.88, Y + 0.775),
               A(5.38, Y + 1.275), A(5.38, 67.5 if last else 69.8)], W_T)
    if last:
        T("VLED", [A(2.725, 70.5), A(2.725, Y_VBUS)], W_PWR)
        T(hall, [A(0.9375, Y + 2.95), A(1.19, Y + 3.2), A(4.21, Y + 3.2), A(4.46, Y + 3.45), A(4.46, 69.3), A(4.75, 69.9)])
        T("+3V3", [A(5.38, 67.5), A(5.3, 68.0)], W_T)
    else:
        T(hall, [A(0.9375, Y + 2.95), A(1.19, Y + 3.2), A(4.62, Y + 3.2), A(4.87, Y + 3.45), A(4.87, 70.77)])
    return x0


def route_all():
    tab = led_table()
    cs = {c["id"]: c for c in G.candles()}
    order = ["C1", "C2", "C3", "C4", "SH", "C5", "C6", "C7", "C8"]
    for k, cid in enumerate(order):
        c = cs[cid]
        x0 = c["x"]
        last = cid == order[-1]
        route_candle(c, tab[cid], last)
        hall = f"HALL_{cid}"
        left = cid in Y_HL
        yh = Y_HL[cid] if left else Y_HR[cid]

        # ---- data link to the next candle (back, along Y_LINK)
        if not last:
            nxt = cs[order[k + 1]]
            flame_n = [l for l in tab[cid] if l["kind"] == "flame"][0]["n"]
            T(f"LED_D{flame_n}", [(x0 + 4.96, Y_LINK), (nxt["x"] - 0.5, Y_LINK), (nxt["x"], Y_LINK - 0.5)])

        # ---- hall + 3V3: hop over link / VLED bus / other lines on the front, land on their bus level
        if not last:
            hv, tv = (x0 + 6.1, 72.0), (x0 + 7.2, 71.62)
            T(hall, [(x0 + 4.87, 70.77), hv])
            T("+3V3", [(x0 + 5.38, 69.8), tv], W_T)
            VIA(hall, *hv); VIA("+3V3", *tv)
            T(hall, [hv, (hv[0], yh)], W_SIG, "F")
            T("+3V3", [tv, (tv[0], Y_T)], W_T, "F")
            VIA(hall, hv[0], yh); VIA("+3V3", tv[0], Y_T)
            h_land, t_land = hv[0], tv[0]
        else:
            # C8 sits on the rounded end of the bar, which is narrower than the candle where they meet:
            # hall and +3V3 go to the front inside the candle foot and slant into the bar end.
            hv, tv = (x0 + 4.75, 69.9), (x0 + 5.3, 68.0)
            VIA(hall, *hv); VIA("+3V3", *tv)
            T("+3V3", [tv, (x0 + 2.5, 70.8), (x0 + 2.5, Y_T)], W_T, "F")
            T(hall, [hv, (x0 + 3.3, 71.35), (x0 + 3.3, yh)], W_SIG, "F")
            VIA("+3V3", x0 + 2.5, Y_T); VIA(hall, x0 + 3.3, yh)
            h_land, t_land = x0 + 3.3, x0 + 2.5

        # ---- hall line: along the bar and down the stem on the back, then one of three ways to the module
        xs = X_HL[cid] if left else X_HR[cid]
        bar = [(h_land, yh), (xs + (-0.5 if left else 0.5), yh), (xs, yh + 0.5)]

        def strip(x_e, y_from):
            """back: down the east side, west along the strip below the module, up into the south pad"""
            ys_, xp = Y_STRIP[cid], X_SOUTH[cid]
            return [(x_e, y_from), (x_e, ys_ - 0.5), (x_e - 0.5, ys_), (xp + 0.3, ys_), (xp, ys_ - 0.3), (xp, Y_SOUTH_PAD)]

        if cid in EAST_ROW:        # C1, C2: via "staircase" to the front, front bus to a via beside east pad 4 / 5
            ys, row, yr, xf = Y_STAIR[cid], EAST_ROW[cid], Y_FROW[cid], X_FAN[cid]
            T(hall, bar + [(xs, ys)])
            VIA(hall, xs, ys)
            pv = (X_PADVIA, row)
            T(hall, [(xs, ys), (xs, yr - 0.4), (xs - 0.4, yr), (xf + 0.3, yr), (xf, yr + 0.3),
                     (xf, row - (xf - pv[0])), pv], W_SIG, "F")
            VIA(hall, *pv)
            T(hall, [pv, (PAD_X, row)])
        elif cid in Y_HOP:         # C3, C4: front hop across the stem foot, then join the east columns
            ys, yh2, xe = Y_STAIR[cid], Y_HOP[cid], X_EAST[cid]
            T(hall, bar + [(xs, ys)])
            VIA(hall, xs, ys)
            T(hall, [(xs, ys), (xs, yh2 - 0.4), (xs + 0.4, yh2), (xe, yh2)], W_SIG, "F")
            VIA(hall, xe, yh2)
            T(hall, strip(xe, yh2))
        else:                      # SH, C5..C8: back all the way
            T(hall, bar + strip(xs, yh + 0.5)[1:])
        c["_t_land"] = t_land

    # ---- VLED bus + trunk down the stem to Q2 (C10 sits on the trunk)
    xl, xr = cs["C1"]["x"] + 3.9, cs["C8"]["x"] + 2.725
    T("VLED", [(xl, Y_VBUS), (xr, Y_VBUS)], 1.0)
    T("VLED", [(X_V, Y_VBUS), (X_V, 120.5)], 0.8)

    # ---- +3V3 buses (left and right half), each turning down the stem
    T("+3V3", [(cs["C1"]["_t_land"], Y_T), (X_TL - 0.5, Y_T), (X_TL, Y_T + 0.5), (X_TL, Y_STEM_END)], W_T)
    T("+3V3", [(cs["C8"]["_t_land"], Y_T), (X_TR + 0.5, Y_T), (X_TR, Y_T + 0.5), (X_TR, Y_STEM_END)], W_T)

    # ---- level shifter under C1: LED_D0 = R11 -> first LED, LED_DATA_5V = U4.Y -> R11, supply, input line
    c1 = cs["C1"]["x"]
    T("LED_D0", [(c1, 73.475), (c1, Y_LINK - 0.5)])
    T("LED_DATA_5V", [(8.998, 76.65), (9.0, 75.125)], 0.3)
    T("VLED", [(8.998, 78.55), (10.2, 78.55), (10.425, 78.775), (12.9, 78.775), (12.9, Y_VBUS)], W_PWR)
    T("GND", [(6.723, 76.65), (5.3, 76.65)], 0.3)
    VIA("GND", 5.3, 76.65)
    T("GND", [(11.2, 77.225), (11.2, 75.95)], 0.3)
    VIA("GND", 11.2, 75.95)
    T("LED_DATA_3V3", [(6.723, 77.6), (5.6, 77.6), (5.6, Y_DATA - 0.5), (6.1, Y_DATA), (X_DATA - 0.5, Y_DATA),
                       (X_DATA, Y_DATA + 0.5), (X_DATA, Y_STEM_END)])

    # ---- VLED bulk capacitors hang below the buses, fed from the VLED bus by a front hop
    for ref, x in (("C13", 42.0), ("C14", 158.0)):
        xv, xg = x + 0.95, x - 0.95
        VIA("VLED", xv, Y_VBUS)
        T("VLED", [(xv, Y_VBUS), (xv, 80.75)], 0.6, "F")
        VIA("VLED", xv, 80.75)
        T("VLED", [(xv, 80.75), (xv, 82.2)], 0.6)
        VIA("GND", xg, 80.75)
        T("GND", [(xg, 80.75), (xg, 82.2)], 0.6)

    # ---- microphone (MK1 at 100, 95.29; C12 above it), all on the back
    T("MIC_WS", [(100.9, 93.926), (X_WS - 0.25, 93.926), (X_WS, 94.176), (X_WS, Y_STEM_END)])
    T("MIC_SD", [(100.0, 93.926), (100.0, 93.2), (X_SD - 0.25, 93.2), (X_SD, 93.45), (X_SD, Y_STEM_END)])
    T("MIC_SCK", [(99.1, 94.748), (X_SCK, 94.748), (X_SCK, Y_STEM_END)])
    T("+3V3", [(99.1, 93.926), (99.1, 93.0), (99.525, 92.575), (99.525, 92.3)], 0.3)
    T("+3V3", [(99.525, 92.3), (99.525, 91.3), (X_TL, 91.3)], 0.3)
    T("GND", [(100.9, 94.748), (101.95, 94.748)], 0.3)
    VIA("GND", 101.95, 94.75)
    T("GND", [(100.9, 94.748), (100.55, 95.55)], 0.25)
    T("GND", [(101.075, 92.3), (102.2, 92.3)], 0.3)
    VIA("GND", 102.2, 92.3)

    # ---- USB: the two VBUS pad pairs of J1 are bridged on the front, over the D+/D-/CC lines leaving the connector;
    #      from there VBUS crosses under the module on the front to the power section (two vias at each end)
    T("VBUS", [(52.245, 128.55), (53.75, 128.55)], 0.6)
    T("VBUS", [(52.245, 133.45), (53.75, 133.45)], 0.6)
    VIA("VBUS", 53.75, 128.55); VIA("VBUS", 53.75, 133.45)
    T("VBUS", [(53.75, 128.55), (53.75, 133.45)], 0.6, "F")
    T("VBUS", [(53.75, 128.55), (54.8, 128.15)], 0.6)
    T("VBUS", [(53.75, 128.55), (53.75, 126.4), (54.95, Y_VBUS_F), (86.1, Y_VBUS_F)], 0.8, "F")
    VIA("VBUS", 85.0, Y_VBUS_F); VIA("VBUS", 86.1, Y_VBUS_F)
    T("VBUS", [(85.0, Y_VBUS_F), (86.1, Y_VBUS_F), (86.6, Y_VBUS_F + 0.5), (86.6, 127.6)], 0.8)
    # ---- VSYS: D1 cathode -> C7 -> front hop over the signal lines -> LED switch Q2 (source), R8, C9
    T("VSYS", [(90.6, 126.9), (93.6, 126.9)], 0.4)
    T("VSYS", [(93.6, 126.65), (94.6, 126.65), (95.0, 127.05), (95.0, 128.7)], 0.6)
    VIA("VSYS", 95.0, 127.6); VIA("VSYS", 95.0, 128.7)
    T("VSYS", [(95.0, 127.6), (95.0, 128.7)], 0.8, "F")
    T("VSYS", [(95.0, 128.0), (97.9, 128.0), (100.3, 125.6), (100.3, 118.2), (99.3, 118.2)], 0.8, "F")
    VIA("VSYS", 100.3, 118.2); VIA("VSYS", 99.3, 118.2)
    T("VSYS", [(99.3, 118.2), (98.8, 118.7), (98.8, 119.675)], 0.5)
    T("VSYS", [(100.3, 118.2), (100.3, 119.675)], 0.5)
    T("VSYS", [(98.8, 119.675), (100.3, 119.675), (100.425, 119.55), (102.025, 119.55)], 0.5)
    # ---- U5 ground pin sits between the two data pins: escape under the body to a via
    T("GND", [(57.2, 132.137), (57.2, 131.0), (59.75, 131.0)], 0.25)
    VIA("GND", 59.75, 131.0)

    # ---- module north-east corner: C1 straight onto the GND / 3V3 pads, R1 (EN pull-up) onto the EN pad
    T("GND", [(PAD_X, 125.49), (80.6, 125.075)], 0.5)
    T("+3V3", [(PAD_X, 126.76), (80.6, 126.625)], 0.5)
    T("+3V3", [(80.6, 126.625), (81.2, 126.9), (82.125, 127.825), (82.125, 128.1)], 0.4)
    T("EN", [(PAD_X, 128.03), (80.475, 128.1)], 0.3)
    T("EN", [(80.475, 128.1), (80.75, 128.4), (81.55, 129.2), (82.625, 129.6)])

    # ---- two ground pads the maze router cannot reach a via from
    T("GND", [(102.4375, 125.55), (102.075, 126.3), (102.075, 127.3)], 0.4)       # Q3 source -> R10 ground pad
    T("GND", [(84.175, 129.6), (85.4, 129.6)], 0.4)                               # C2
    VIA("GND", 85.4, 129.6)
    T("GND", [(88.525, 134.0), (88.5, 132.75)], 0.4)                              # C4
    VIA("GND", 88.5, 132.75)

    # ---- short escapes for the remaining east pads (6..12) so nothing can box them in
    for k, net in enumerate(["LED_DATA_3V3", "MIC_SCK", "MIC_WS", "MIC_SD", "VLED_EN", "CHRG_N", "VBAT_SENSE"]):
        y = 131.84 + 1.27 * k
        T(net, [(PAD_X, y), (80.5, y)])

    # USB D-/D+ (module pads 13/14): back from U5, a short front hop across the module's west pad column,
    # then on the back underneath the module (south of the ground pad) to the pads from the inside
    T("USB_DN", [(58.15, 132.137), (59.75, 132.137)])
    VIA("USB_DN", 59.75, 132.137)
    T("USB_DN", [(59.75, 132.137), (64.4, 132.137)], W_SIG, "F")
    VIA("USB_DN", 64.4, 132.137)
    T("USB_DN", [(64.4, 132.137), (64.4, 136.55), (64.85, 137.0), (76.6, 137.0), (77.0, 137.4), (77.0, 140.33),
                 (77.4, 140.73), (PAD_X, 140.73)])
    T("USB_DP", [(56.25, 132.137), (56.25, 133.5), (59.75, 133.5)])
    VIA("USB_DP", 59.75, 133.5)
    T("USB_DP", [(59.75, 133.5), (63.3, 133.5)], W_SIG, "F")
    VIA("USB_DP", 63.3, 133.5)
    T("USB_DP", [(63.3, 133.5), (63.3, 137.05), (63.75, 137.5), (75.5, 137.5), (75.9, 137.9), (75.9, 141.6),
                 (76.3, 142.0), (PAD_X, 142.0)])


route_all()

if __name__ == "__main__":
    print(len(TRACKS), "tracks,", len(VIAS), "vias")
