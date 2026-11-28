#!/usr/bin/python3
"""Build the unrouted pod board from the design tables: outline, footprints, nets, fixed input routes.

    /usr/bin/python3 gen/board.py        (needs KiCad 9's pcbnew module)

Writes pod/emg-pod-unrouted.kicad_pcb. gen/route.py takes it from there.
Coordinates are millimetres, origin at the top-left corner of the board, y downwards.
"""
import os
import sys
import tempfile

import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402

ROOT = os.path.dirname(HERE)
POD = os.path.join(ROOT, "pod")
KL = "/usr/share/kicad/footprints/"
W, H = 49.0, 49.0
OX, OY = 100.0, 60.0            # where the board sits on the KiCad page

CLEAR = 0.127                   # copper clearance (5 mil); JLCPCB's 4-layer minimum is tighter
TRACK = 0.15
FINE = 0.127                    # the fixed electrode routes, which pass between vias
VIA_D, VIA_DRILL = 0.5, 0.3
POWER_NETS = ["VBAT", "AVDD", "+3V3", "DVDD", "GND", "MOT_P", "MOT_N", "VBUS"]

# block centres: converter A on the left half, converter B on the right half
BX = {"A": 12.25, "B": 36.75}
CONN_Y = None                   # set once the connector footprint has been measured
CHIP_Y = 29.9
SPLIT_Y = 26.0                  # layer 3: DVDD above this line, AVDD below. The whole fan-out (first lane at
                                # CHIP_Y - 3.2) has to lie over AVDD; the DVDD vias sit just above the line.
ROW1, ROW2 = 39.75, 37.7         # resistor-array rows (centre lines)
FAN_PITCH = 1.2                  # filter-capacitor pitch = spacing of the fan-out lanes under the converter
FAN_TOP = 2.8                    # first turn row of the fan, below the chip centre
ESD_X = 10.0                     # ESD arrays: distance of their column from the block centre line
ESD_N, ESD_S, ESD_BIAS = 40.9, 46.6, 37.75
ESD_END, ESD_MID, ESD_LANE = 1.175, 1.56, 1.675    # array centre to: via beside an end pad, via beyond a
                                                   # middle pad (both 0.25 mm clear of the pad), outer lane
TAP = {"A": 1.6, "B": 2.5, "C": 3.4, "D": 4.3}     # tap-via rows under the strip connector, below the pad row
TAP_ROW = "ABABDCDC" "DCDCBABA"  # row of the tap via of line k: each array's four lines leave as one bundle
XIAO_X0, XIAO_Y0 = 28.0, 1.0
NOTCH = (25.0, 32.0, 12.4)       # x from, x to, depth: the board is cut away under and in front of the XIAO's
                                 # chip antenna (centre 29.1, 8.1 by Seeed's coordinate sheet), open to the top edge
# Bare metal on the XIAO's underside that has no land here (Seeed's v1.2 board file, moved to board mm):
# the two NFC pads and the four USB shell legs, each with a margin. No top copper and no via under them.
MODULE_METAL = [(27.75, 12.85, 30.80, 16.45), (46.67, 13.45, 49.05, 14.93), (46.67, 4.85, 49.05, 6.33),
                (42.44, 13.43, 44.87, 14.95), (42.44, 4.83, 44.87, 6.35)]
BOTTOM = {"TP19", "TP20", "TP21", "TP22", "TP23"}      # bare pads on the back; no parts are assembled there


def V(x, y):
    return VECTOR2I(FromMM(OX + x), FromMM(OY + y))


def chip_via_y(k):
    """Row of the via under the converter for input line k (0 = pin 1): alternate rows, 0.5 mm pin pitch."""
    return CHIP_Y + (4.2 if k % 2 == 0 else 3.3)


def fan(side, i):
    """Fan-out of the i-th input line counted from the outside on one side (-1 left, +1 right).

    Returns (line index k, y of its filter capacitor). The two outer lines run straight out from their
    vias; the others climb to their own turn row first.
    """
    k = i if side < 0 else 15 - i
    if i >= 2:
        return k, round(CHIP_Y + FAN_TOP - FAN_PITCH * (i - 2), 3)
    lower = k % 2 == 0
    return k, round(CHIP_Y + FAN_TOP + FAN_PITCH * (2 if lower else 1), 3)


def quiet_zones():
    """Areas kept for the input lines: (layer, x0, y0, x1, y1). The routers lay nothing there.

    On the back, the fan-out from each converter to its filter capacitors; on the front, the stubs under
    each converter from the input pins to their vias. The fixed routes inside them are drawn by main().
    They are not KiCad keep-outs (those would reject the fixed routes too): gen/route.py hands them to
    the autorouter, gen/lastmile.py honours them, gen/fab.py checks the result.
    """
    zones = []
    for bx in BX.values():
        zones.append((pcbnew.B_Cu, bx - 11.05, CHIP_Y - 3.6, bx + 11.05, CHIP_Y + 5.6))
        zones.append((pcbnew.F_Cu, bx - 3.95, CHIP_Y + 2.9, bx + 3.95, CHIP_Y + 6.4))
    return zones


def outline(inset=0.0):
    """Corners of the board outline, clockwise from the top-left, optionally drawn inside by inset."""
    i, (n0, n1, nd) = inset, NOTCH
    return [(i, i), (n0 - i, i), (n0 - i, nd + i), (n1 + i, nd + i), (n1 + i, i), (W - i, i), (W - i, H - i), (i, H - i)]


def load(fp_id):
    lib, name = fp_id.split(":")
    path = os.path.join(POD, "lib", "emgpod.pretty") if lib == "emgpod" else KL + lib + ".pretty"
    fp = pcbnew.FootprintLoad(path, name)
    assert fp is not None, fp_id
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def placement():
    """ref -> (x, y, rotation)."""
    P = {}
    # ---- XIAO: USB end at the right edge, antenna end over the notch in the top edge
    P["U1"] = (XIAO_X0, XIAO_Y0, 270)
    # ---- battery connector, opening towards the top edge
    P["J1"] = (6.0, 5.6, 180)
    # ---- motor driver, on the XIAO side of the board
    P["J2"] = (13.0, 2.2, 0)
    P["R5"] = (13.1, 5.0, 0)
    P["D1"] = (17.9, 5.0, 0)
    P["Q2"] = (22.6, 3.2, 0)
    P["R6"] = (22.6, 6.4, 0)
    # ---- analog regulator and interlock
    P["U2"] = (21.2, 16.9, 0)
    P["C1"] = (18.4, 16.9, 270)
    P["C2"] = (23.9, 16.9, 270)
    for i, r in enumerate(["R3", "R4", "C3"]):          # VBUS divider of the interlock
        P[r] = (11.6 + 2.1 * i, 14.0, 0)
    P["R1"] = (32.6, 20.45, 270)                      # enable divider, right below the XIAO's AFE_EN pad
    P["R2"] = (33.8, 20.45, 90)
    P["Q1"] = (14.2, 17.0, 0)
    P["R20"] = (24.7, 21.6, 90)
    P["R23"] = (26.0, 21.6, 90)                       # SCLK pull-down
    P["R22"] = (27.3, 21.6, 90)                       # START pull-down
    P["R21"] = (40.6, 20.6, 0)                        # link from the XIAO's 3V3 pin to DVDD
    # ---- test points. The shared SPI lines have theirs on the left, where the lines pass on their way to
    #      converter A; what only exists on the right (3V3, converter B's select and DRDY) is tested there,
    #      so that nothing crosses the corridor below the notch just to reach a test point.
    grid = ["TP10", "TP11", "TP12", "TP13", "TP15", "TP17", "TP18"]
    for i, r in enumerate(grid):
        P[r] = (11.6 + 2.4 * (i % 5), 9.4 + 2.6 * (i // 5), 0)
    P["TP3"] = (42.9, 20.4, 0)
    P["TP16"] = (29.2, 22.0, 0)
    P["TP14"] = (31.3, 22.0, 0)
    P["TP1"] = (2.0, 12.8, 0)
    P["TP4"] = (2.0, 15.4, 0)
    P["TP5"] = (9.3, 17.4, 0)
    P["TP2"] = (5.5, 17.4, 0)
    # SWD rescue pads on the back of the board, beneath the XIAO's own SWD pads
    P["TP19"] = (47.0, 6.2, 0)
    P["TP20"] = (47.0, 13.6, 0)
    P["TP21"] = (44.5, 6.2, 0)
    P["TP22"] = (44.5, 13.6, 0)
    P["TP23"] = (44.5, 17.3, 0)                       # 3.3 V for the probe, on the back with the SWD pads
    P["TP6"] = (6.5, 20.8, 0)                         # plated hole for a scope ground wire
    P["TP30"] = (2.0, 18.0, 0)
    P["TP31"] = (BX["A"] - 7.75, 37.3, 0)            # bias output: beside the bias parts, below converter A
    # ---- the two converter blocks, identical
    for X, b in (("A", 100), ("B", 200)):
        bx, cy = BX[X], CHIP_Y
        P[f"U{b}"] = (bx, cy, 90)                      # inputs (pins 1-16) face the strip connector
        P[f"J{b}"] = (bx, CONN_Y, 0)
        for m in range(4):
            P[f"RN{b + 1 + m}"] = (bx - 3.0 + 2.0 * m, ROW1 if m % 2 == 0 else ROW2, 90)
        # filter capacitors: converter pins 1-8 on the left of the chip, 9-16 on the right, in fan-out order
        order = [16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        for side in (-1, 1):
            for i in range(8):
                k, y = fan(side, i)
                P[f"C{b + 1 + order.index(k + 1)}"] = (bx + side * 10.9, y, 180 if side < 0 else 0)
        c = b + 20
        left = [(f"C{c + 6}", -5.4), (f"C{c + 7}", -4.2), (f"C{c + 4}", -3.0), (f"C{c + 5}", -1.8),
                (f"C{c + 13}", -0.6), (f"C{c + 12}", 0.6), (f"C{c + 3}", 1.8), (f"C{c + 2}", 3.0),
                (f"C{c + 15}", 4.2)]
        for ref, dy in left:
            P[ref] = (bx - 7.6, cy + dy, 180)
        right = [(f"C{c}", 5.3), (f"C{c + 1}", 4.2), (f"C{c + 9}", 3.1), (f"C{c + 14}", -1.2),
                 (f"C{c + 11}", -2.7)]
        for ref, dy in right:
            P[ref] = (bx + 7.6, cy + dy, 0)
        P[f"C{c + 8}"] = (bx + 7.7, cy + 1.0, 270)       # 10 uF 0603 on VREFP, pad 1 next to pin 24
        P[f"C{c + 10}"] = (bx + 9.2, cy - 6.5, 90)         # 22 uF tantalum on VCAP1, positive pad at the bottom
        # digital-side resistors above the chip
        # each of these sits straight above the converter pin it belongs to (43 DOUT, 39 CS, 37 CLK)
        P[f"R{b + 21}"] = (bx - 1.25, cy - 8.1, 90)        # DOUT series
        P[f"R{b + 20}"] = (bx + 0.75, cy - 8.1, 270)       # chip-select pull-up
        P[f"R{b + 23}"] = (bx + 2.0, cy - 8.1, 90)         # clock series (A) / pull-down (B)
        # ESD arrays in a column at each end of the connector, their capacitors between them;
        # the bias array sits above the left column
        for side, north, south in ((-1, 4, 3), (1, 1, 2)):
            cx = bx + side * ESD_X
            P[f"U{b + north}"] = (cx, ESD_N, 90)
            P[f"U{b + south}"] = (cx, ESD_S, 90)
            P[f"C{b + 40 + north}"] = (cx, 43.2, 0)
            P[f"C{b + 40 + south}"] = (cx, 44.3, 0)
        P[f"U{b + 5}"] = (bx - ESD_X, ESD_BIAS, 90)
        P[f"C{b + 45}"] = (bx - ESD_X, ESD_BIAS - 1.7, 0)
        P[f"R{b + 22}"] = (bx + 6.2, 40.2, 0)             # shield link
        if X == "A":
            P["R124"] = (bx - 7.6, cy + 5.4, 180)
            P["C140"] = (bx - 5.9, 38.0, 90)
            P["R125"] = (bx - 5.7, 40.3, 0)
        else:
            P["R224"] = (bx - 7.6, cy + 5.4, 180)
    return P


def main():
    global CONN_Y
    design.build(tempfile.mkdtemp(), "")
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = FromMM(CLEAR)
    ds.m_MinClearance = FromMM(CLEAR)
    ds.m_ViasMinSize = FromMM(0.5)
    ds.m_MinThroughDrill = FromMM(0.25)
    ds.m_ViasMinAnnularWidth = FromMM(0.1)
    ds.m_CopperEdgeClearance = FromMM(0.3)
    ds.m_HoleToHoleMin = FromMM(0.25)
    ds.m_HoleClearance = FromMM(0.2)
    ds.SetBoardThickness(FromMM(1.6))
    ns = ds.m_NetSettings
    dflt = ns.GetDefaultNetclass()
    dflt.SetClearance(FromMM(CLEAR))
    dflt.SetTrackWidth(FromMM(TRACK))
    dflt.SetViaDiameter(FromMM(VIA_D))
    dflt.SetViaDrill(FromMM(VIA_DRILL))
    pw = pcbnew.NETCLASS("Power")
    pw.SetClearance(FromMM(CLEAR))
    pw.SetTrackWidth(FromMM(0.25))
    pw.SetViaDiameter(FromMM(VIA_D))
    pw.SetViaDrill(FromMM(VIA_DRILL))
    ns.SetNetclass("Power", pw)
    for n in POWER_NETS:
        ns.SetNetclassPatternAssignment(n, "Power")

    # outline: 1 mm radius at the four corners, and the notch under the antenna with 1 mm inner radii
    r = 1.0
    n0, n1, nd = NOTCH
    segs = [((r, 0), (n0, 0)), ((n0, 0), (n0, nd - r)), ((n0 + r, nd), (n1 - r, nd)), ((n1, nd - r), (n1, 0)),
            ((n1, 0), (W - r, 0)), ((W, r), (W, H - r)), ((W - r, H), (r, H)), ((0, H - r), (0, r))]
    for a, b in segs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a))
        s.SetEnd(V(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FromMM(0.1))
        board.Add(s)
    # arcs run clockwise on the screen from their start point
    for (cx, cy), (sx, sy) in [((W - r, r), (W - r, 0)), ((W - r, H - r), (W, H - r)), ((r, H - r), (r, H)),
                               ((r, r), (0, r)), ((n0 + r, nd - r), (n0 + r, nd)), ((n1 - r, nd - r), (n1, nd - r))]:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetCenter(V(cx, cy))
        s.SetStart(V(sx, sy))
        s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FromMM(0.1))
        board.Add(s)

    nets = {}

    def net(name):
        if name not in nets:
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
            nets[name] = ni
        return nets[name]

    # measure the strip connector so that its mouth sits at the bottom edge
    probe = load(design.PARTS["J100"][0])
    bb = probe.GetBoundingBox(False)
    CONN_Y = round(H - 0.3 - ToMM(bb.GetBottom()), 2)
    place = placement()
    missing = sorted(set(design.PARTS) - set(place))
    assert not missing, f"no position for {missing}"

    fps = {}
    for ref, (fp_id, value, in_bom) in sorted(design.PARTS.items()):
        fp = load(fp_id)
        x, y, rot = place[ref]
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(V(x, y))
        fp.SetOrientationDegrees(rot)
        if ref in design.BOM:
            fp.SetField("LCSC", design.BOM[ref][2])
            fp.GetFieldByName("LCSC").SetVisible(False)
        if not in_bom:
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.Value().SetVisible(False)
        t = fp.Reference()
        t.SetTextSize(VECTOR2I(FromMM(0.6), FromMM(0.6)))
        t.SetTextThickness(FromMM(0.1))
        if ref[0] in "CR" and not ref.startswith("RN"):
            t.SetVisible(False)
        board.Add(fp)
        if ref in BOTTOM:                                # flipping needs the footprint to be on a board
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num == "":
                continue
            key = (ref, num)
            assert key in design.NET, key
            if design.NET[key]:
                pad.SetNet(net(design.NET[key]))
        fps[ref] = fp

    def pad_xy(ref, num):
        for pad in fps[ref].Pads():
            if pad.GetNumber() == str(num):
                p = pad.GetPosition()
                return round(ToMM(p.x) - OX, 4), round(ToMM(p.y) - OY, 4)
        raise KeyError((ref, num))

    def track(a, b, netname, layer=pcbnew.F_Cu, width=TRACK, lock=True):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(*a))
        t.SetEnd(V(*b))
        t.SetWidth(FromMM(width))
        t.SetLayer(layer)
        t.SetNet(net(netname))
        t.SetLocked(lock)
        board.Add(t)

    def via(p, netname, lock=True):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(V(*p))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetWidth(pcbnew.F_Cu, FromMM(VIA_D)) if v.SetWidth.__doc__ and "layer" in (v.SetWidth.__doc__ or "").lower() \
            else v.SetWidth(FromMM(VIA_D))
        v.SetDrill(FromMM(VIA_DRILL))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(net(netname))
        v.SetLocked(lock)
        board.Add(v)

    BCU = pcbnew.B_Cu

    def path(points, netname, layer=pcbnew.F_Cu, width=TRACK, first=None):
        """A locked polyline. first = width of the first segment, where it differs."""
        for n, (a, b) in enumerate(zip(points[:-1], points[1:])):
            a, b = (round(a[0], 4), round(a[1], 4)), (round(b[0], 4), round(b[1], 4))
            if a != b:
                track(a, b, netname, layer, first if (first and n == 0) else width)

    def expect(ref, num, netname):
        assert design.NET[(ref, str(num))] == netname, (ref, num, design.NET[(ref, str(num))], netname)

    # ---- fixed routes, front: every electrode line runs straight from the connector through its resistor
    #      to its converter pin, with one branch to a via under the converter and one under the connector
    for X, b in (("A", 100), ("B", 200)):
        bx = BX[X]
        xs, e_nets, in_nets, taps = [], [], [], []
        for k in range(16):
            x = round(bx - 3.75 + 0.5 * k, 4)
            m, i = divmod(k, 4)
            rn = f"RN{b + 1 + m}"
            e_net = design.NET[(f"J{b}", str(3 + k))]
            in_net = design.NET[(f"U{b}", str(1 + k))]
            jp, a1, a8, up = pad_xy(f"J{b}", 3 + k), pad_xy(rn, 1 + i), pad_xy(rn, 8 - i), pad_xy(f"U{b}", 1 + k)
            for p in (jp, a1, a8, up):
                assert abs(p[0] - x) < 1e-3, (X, k, p, x)       # all four pads are in one straight line
            assert design.NET[(rn, str(1 + i))] == e_net and design.NET[(rn, str(8 - i))] == in_net
            assert jp[1] > a1[1] > a8[1] > up[1]
            track(jp, a1, e_net, width=FINE)
            track(a8, up, in_net, width=FINE)
            track(up, (x, chip_via_y(k)), in_net, width=FINE)
            via((x, chip_via_y(k)), in_net)
            ty = round(jp[1] + TAP[TAP_ROW[k]], 3)
            track(jp, (x, ty), e_net, width=FINE)
            via((x, ty), e_net)
            xs.append(x), e_nets.append(e_net), in_nets.append(in_net), taps.append(ty)
        jy = pad_xy(f"J{b}", 3)[1]
        yA, yB, yC, yD = (round(jy + TAP[r], 3) for r in "ABCD")

        # ---- back: fan-out from the vias under the converter to a via beside each filter capacitor.
        #      The lanes are FAN_PITCH apart, so a via to a plane fits between any two of them.
        order = [16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        for side in (-1, 1):
            xv = round(bx + side * 9.6, 3)
            for i in range(8):
                k, yc = fan(side, i)
                ref = f"C{b + 1 + order.index(k + 1)}"
                cp = pad_xy(ref, 1)
                expect(ref, 1, in_nets[k])
                assert abs(cp[1] - yc) < 1e-3 and abs(cp[0] - (bx + side * 10.42)) < 0.02, (ref, cp)
                vy = chip_via_y(k)
                if i >= 2:
                    path([(xs[k], vy), (xs[k], yc), (xv, yc)], in_nets[k], BCU, first=FINE)
                else:
                    d = abs(yc - vy)
                    path([(xs[k], vy), (xv - side * d, vy), (xv, yc)], in_nets[k], BCU)
                via((xv, yc), in_nets[k])
                track((xv, yc), cp, in_nets[k])

        # ---- supply and ground pins of the converter: a via to the plane just inside the pad row, in the
        #      gaps between the fan-out lanes. (pins, via position from the chip centre, extra corner)
        chip_vias = [
            ((49,), (-4.05, -3.75), None),
            ((48,), (-3.75, -4.45), None),
            ((50,), (-3.75, -4.45), [(-3.70, -3.25), (-3.25, -3.70), (-3.25, -4.00)]),
            ((51,), (-4.05, -2.60), None),
            ((53,), (-4.05, -1.40), None),
            ((54, 56), (-4.05, -0.20), None),
            ((57, 58), (-4.05, 1.00), None),
            ((59,), (-4.05, 2.20), None),
            ((44, 45, 46), (-2.25, -4.05), None),
            ((41, 42), (-0.50, -4.05), None),
            ((33,), (3.75, -4.45), None),
            ((31, 32), (4.05, -3.75), None),
            ((23, 25), (4.05, -0.20), None),
            ((21, 22), (4.05, 1.00), None),
            ((20,), (4.05, 2.20), None),
            ((17, 18, 19), (3.25, 2.20), [(3.80, 2.75)]),
        ]
        made = set()
        for pins, (vx, vy), corner in chip_vias:
            netname = design.NET[(f"U{b}", str(pins[-1]))]
            vp = (round(bx + vx, 3), round(CHIP_Y + vy, 3))
            knees = []
            for n in pins:
                expect(f"U{b}", n, netname)
                q = pad_xy(f"U{b}", n)
                dx, dy = bx - q[0], CHIP_Y - q[1]
                if abs(dx) > abs(dy):                       # pin on the left or right side
                    knee = (round(q[0] + (0.9 if dx > 0 else -0.9), 3), q[1])
                else:
                    knee = (q[0], round(q[1] + (0.9 if dy > 0 else -0.9), 3))
                track(q, knee, netname, width=FINE)
                knees.append(knee)
            if corner:                                      # the pins are joined, the last one leads to the via
                path(knees, netname, width=FINE)
                path([knees[-1]] + [(round(bx + cx_, 3), round(CHIP_Y + cy_, 3)) for cx_, cy_ in corner] + [vp],
                     netname, width=FINE)
            else:
                for knee in knees:
                    track(knee, vp, netname, width=FINE)
            if vp not in made:                              # pins 48 and 50 share theirs
                via(vp, netname)
                made.add(vp)

        # DVDD bypass capacitors: joined, with their own via to the DVDD plane
        d1, d2 = pad_xy(f"C{b + 26}", 1), pad_xy(f"C{b + 27}", 1)
        dvdd = design.NET[(f"U{b}", "48")]
        expect(f"C{b + 26}", 1, dvdd), expect(f"C{b + 27}", 1, dvdd)
        track(d1, d2, dvdd, width=0.2)
        dv = (round(d1[0] + 0.92, 3), d1[1])
        assert dv[1] < SPLIT_Y - 0.6, dv
        track(d1, dv, dvdd, width=0.2)
        via(dv, dvdd)

        # the three resistors above the converter: a straight link from each one's pin
        for pin, ref, num in ((43, f"R{b + 21}", 1), (39, f"R{b + 20}", 2), (37, f"R{b + 23}", 1)):
            q, rp = pad_xy(f"U{b}", pin), pad_xy(ref, num)
            netname = design.NET[(f"U{b}", str(pin))]
            expect(ref, num, netname)
            assert rp[1] < q[1] and abs(rp[0] - q[0]) < 0.3, (ref, rp, q)
            path([q, (q[0], round(rp[1] + 0.25 + abs(rp[0] - q[0]), 3)), (rp[0], round(rp[1] + 0.25, 3)), rp], netname)

        # CLKSEL (pin 52) is strapped: to the via of ground pin 51, or to that of supply pin 50
        q = pad_xy(f"U{b}", 52)
        strap = design.NET[(f"U{b}", "52")]
        knee = (round(q[0] + 0.9, 3), q[1])
        track(q, knee, strap, width=FINE)
        if strap == "GND":
            track(knee, (round(bx - 4.05, 3), round(CHIP_Y - 2.6, 3)), strap, width=FINE)
        else:
            expect(f"U{b}", 50, strap)
            path([knee, (bx - 4.05, CHIP_Y - 2.0), (bx - 3.6, CHIP_Y - 2.0), (bx - 3.25, CHIP_Y - 2.35),
                  (bx - 3.25, CHIP_Y - 3.7)], strap, width=FINE)

        # VCAP1 (pin 28): out between the two capacitors beside it, then up to the tantalum's positive pad.
        # Nothing can cross the fan-out on the back, so this one is drawn here.
        q, tp = pad_xy(f"U{b}", 28), pad_xy(f"C{b + 30}", 1)
        vcap = design.NET[(f"U{b}", "28")]
        expect(f"C{b + 30}", 1, vcap)
        assert tp[1] < q[1] and abs(tp[0] - (bx + 9.2)) < 0.02, tp
        path([q, (bx + 6.6, q[1]), (bx + 6.8, q[1] - 0.2), (bx + 8.85, q[1] - 0.2), (bx + 8.85, tp[1])], vcap)
        tn = pad_xy(f"C{b + 30}", 2)
        expect(f"C{b + 30}", 2, "GND")
        track(tn, (tn[0], round(tn[1] - 1.02, 3)), "GND", width=0.25)
        via((tn[0], round(tn[1] - 1.02, 3)), "GND")

        # ---- ESD arrays. Each takes the four lines of one bundle: on the back from the tap vias under the
        #      connector to a via beside each pad. North array = bundle above the tap rows, south = below.
        def cell(ref, cx, cy):
            """Vias around one array (rotated 90 degrees): beside its end pads, beyond its middle pads."""
            at = {n: pad_xy(ref, n) for n in range(1, 7)}
            assert abs(at[2][0] - cx) < 1e-3 and abs(at[2][1] - (cy + 0.71)) < 0.02, (ref, at)
            assert at[1][0] < cx < at[3][0] and at[6][0] < cx < at[4][0] and at[5][1] < cy, (ref, at)
            v = {1: (round(cx - ESD_END, 3), at[1][1]), 2: (cx, round(cy + ESD_MID, 3)),
                 3: (round(cx + ESD_END, 3), at[3][1]), 4: (round(cx + ESD_END, 3), at[4][1]),
                 5: (cx, round(cy - ESD_MID, 3)), 6: (round(cx - ESD_END, 3), at[6][1])}
            for n in range(1, 7):
                netname = design.NET[(ref, str(n))]
                if netname:
                    track(at[n], v[n], netname, width=0.2 if netname in POWER_NETS else TRACK)
                    via(v[n], netname)
            return v, at

        N1, N2, N3, N4 = round(yA - 1.1, 3), round(yA - 0.8, 3), round(yA - 0.5, 3), yA      # north lanes
        S3, S4 = round(yD + 0.5, 3), round(yD + 0.8, 3)                                    # south lanes 3, 4
        for side, north, south in ((-1, 4, 3), (1, 1, 2)):
            cx = round(bx + side * ESD_X, 3)
            vn, pn = cell(f"U{b + north}", cx, ESD_N)
            vs, ps = cell(f"U{b + south}", cx, ESD_S)
            for (ref, v) in ((f"U{b + north}", vn), (f"U{b + south}", vs)):
                expect(ref, 3, "GND"), expect(ref, 6, "AVDD")
            cn1, cn2 = pad_xy(f"C{b + 40 + north}", 1), pad_xy(f"C{b + 40 + north}", 2)
            cs1, cs2 = pad_xy(f"C{b + 40 + south}", 1), pad_xy(f"C{b + 40 + south}", 2)
            expect(f"C{b + 40 + north}", 1, "AVDD"), expect(f"C{b + 40 + south}", 2, "GND")
            assert cn1[1] - 0.31 > vn[2][1] + VIA_D / 2 + CLEAR and cs1[1] + 0.31 < vs[5][1] - VIA_D / 2 - CLEAR
            path([pn[3], cn2, cs2], "GND")                  # ground: north array pin 3, both capacitors
            path([cn1, cs1, ps[6]], "AVDD")                 # supply: both capacitors, south array pin 6
            e, w = round(cx + ESD_LANE, 3), round(cx - ESD_LANE, 3)
            top = round(vs[5][1] - 0.5, 3)                  # lane that passes over the top of the south array
            north, south = f"U{b + north}", f"U{b + south}"
            if side < 0:
                xj = bx - 5.2
                routes = [
                    # north bundle, heading west
                    (3, north, 4, [(xs[3], yB), (xs[3], N1), (e, N1), (e, vn[4][1]), vn[4]], FINE),
                    (2, north, 2, [(xs[2], yA), (xs[2], N2), (cx + (N2 - vn[2][1]), N2), vn[2]], None),
                    (1, north, 1, [(xs[1], yB), (xs[1], N3), (vn[1][0], N3), vn[1]], FINE),
                    (0, north, 5, [(xs[0], yA), (w, N4), (w, vn[5][1]), vn[5]], None),
                    # south bundle: the first line goes round the top and down the far side
                    (5, south, 1, [(xs[5], yC), (xj, yC), (xj - (yC - top), top), (w, top), (w, vs[1][1]), vs[1]], None),
                    (4, south, 5, [(xs[4], yD), (xj, yD), (xj - (yD - vs[5][1]), vs[5][1]), vs[5]], None),
                    (6, south, 4, [(xs[6], yD), (xs[6], S3), (xj, S3), (xj - (S3 - vs[4][1]), vs[4][1]), vs[4]], None),
                    (7, south, 2, [(xs[7], yC), (xs[7], S4), (xj, S4), (xj - (vs[2][1] - S4), vs[2][1]), vs[2]], FINE),
                ]
            else:
                xj = bx + 5.2
                routes = [
                    # north bundle, heading east
                    (12, north, 5, [(xs[12], yB), (xs[12], N1), (w, N1), (w, vn[5][1]), vn[5]], FINE),
                    (13, north, 1, [(xs[13], yA), (xs[13], N2), (vn[1][0], N2), vn[1]], None),
                    (14, north, 2, [(xs[14], yB), (xs[14], N3), (cx - (N3 - vn[2][1]), N3), vn[2]], FINE),
                    (15, north, 4, [(xs[15], yA), (e, N4), (e, vn[4][1]), vn[4]], None),
                    # south bundle
                    (11, south, 4, [(xs[11], yC), (xj, yC), (xj + (yC - top), top), (vs[4][0], top), vs[4]], None),
                    (10, south, 5, [(xs[10], yD), (xj, yD), (xj + (yD - vs[5][1]), vs[5][1]), vs[5]], None),
                    (9, south, 1, [(xs[9], yC), (xs[9], S3), (xj, S3), (xj + (vs[1][1] - S3), vs[1][1]), vs[1]], FINE),
                    (8, south, 2, [(xs[8], yD), (xs[8], S4), (xj - 0.2, S4),
                                   (xj - 0.2 + (vs[2][1] - S4), vs[2][1]), vs[2]], None),
                ]
            for k, ref, pin, pts, first in routes:
                assert abs(pts[0][1] - taps[k]) < 1e-3, (k, pts[0], taps[k])
                expect(ref, pin, e_nets[k])
                path(pts, e_nets[k], BCU, first=first)

        # ---- bias array: vias for its three connected pins, and its capacitor
        cx = round(bx - ESD_X, 3)
        ub, cb = f"U{b + 5}", f"C{b + 45}"
        vb, pb = cell(ub, cx, ESD_BIAS)
        expect(ub, 1, "BIAS"), expect(cb, 1, "AVDD")
        track(pad_xy(cb, 1), pb[6], "AVDD", width=0.2)
        gv = (round(pad_xy(cb, 2)[0] + 0.72, 3), pad_xy(cb, 2)[1])
        track(pad_xy(cb, 2), gv, "GND", width=0.2)
        via(gv, "GND")

    # ---- XIAO signals that must reach the left half, and the battery: down under the module on the front,
    #      then west on the back below the notch, one lane each, ending left of the notch (staggered, so a
    #      via fits at each end). (pad, x of the run under the module, lane y, x where the lane ends, width)
    bus = [(3, 41.85, 13.0, 24.4, TRACK), (4, 37.75, 13.48, 23.7, TRACK), (5, None, 13.96, 24.4, TRACK),
           (6, None, 14.44, 23.7, TRACK), (19, None, 14.98, 24.4, 0.25), (1, 45.8, 15.48, 23.7, TRACK),
           (14, None, 16.1, 24.4, 0.25)]
    names = {1: "CS_A", 3: "DRDY_A", 4: "ADS_START", 5: "MISO", 6: "SCLK_MCU", 19: "VBAT", 14: "VBUS"}
    for pin, xv, lane, xl, wd in bus:
        expect("U1", pin, names[pin])
        q = pad_xy("U1", pin)
        xv = q[0] if xv is None else xv
        if pin in (19, 14):                                 # a pad under the module, or one of the lower row:
            pts = [q, (xv, lane)]                           # straight from it to its lane
        else:                                               # an edge pad: out of its land, sideways if a land is in the way
            pts = [q, (q[0], 3.3)] + ([(xv, round(3.3 + abs(xv - q[0]), 3))] if xv != q[0] else []) + [(xv, lane)]
        path(pts, names[pin], width=wd)
        via((xv, lane), names[pin])
        track((xv, lane), (xl, lane), names[pin], layer=BCU, width=wd)      # the routers carry on from its end
    # the XIAO's 3.3 V pin: to the link R21, to its test point, and through a via to the pad on the back
    for ref, pin in (("U1", 12), ("R21", 1), ("TP3", 1), ("TP23", 1)):
        expect(ref, pin, "+3V3")
    p12, r21, tp3, tp23 = pad_xy("U1", 12), pad_xy("R21", 1), pad_xy("TP3", 1), pad_xy("TP23", 1)
    assert p12[0] - 1.0 < r21[0] < p12[0] + 1.0 and r21[1] > p12[1], (p12, r21)
    track(r21, (r21[0], 19.2), "+3V3", width=0.25)                  # up into the land
    v33 = (41.9, 20.1)
    track((41.6, 19.0), v33, "+3V3", width=0.25)                    # out of the land to a via
    track(tp3, v33, "+3V3", width=0.25)
    via(v33, "+3V3")
    path([v33, (v33[0], 19.4), (tp23[0] - 0.5, tp23[1]), tp23], "+3V3", BCU, width=0.25)

    # the enable divider hangs on the AFE_EN pad
    expect("R1", 1, "AFE_EN"), expect("U1", 9, "AFE_EN"), expect("R1", 2, "AVDD_EN"), expect("R2", 1, "AVDD_EN")
    a1 = pad_xy("R1", 1)
    assert abs(a1[1] - 19.94) < 0.02 and pad_xy("U1", 9)[0] - 1.0 < a1[0] < pad_xy("U1", 9)[0] + 1.0, a1
    track(a1, (a1[0], 19.1), "AFE_EN")                      # into the land above it
    track(pad_xy("R1", 2), pad_xy("R2", 1), "AVDD_EN")

    # ---- ground pads that sit among signal tracks get their own via, so they do not depend on the pour:
    #      the shield links and, on converter B, the clock pull-down
    for b in (100, 200):
        for ref, step in ((f"R{b + 22}", (0.75, 0)), (f"R{b + 23}", (0, -0.75))):
            for num in ("1", "2"):
                if design.NET[(ref, num)] == "GND":
                    q = pad_xy(ref, num)
                    vp = (round(q[0] + step[0], 3), round(q[1] + step[1], 3))
                    track(q, vp, "GND", width=0.2)
                    via(vp, "GND")

    # ---- fixed ground: a bus through each capacitor column, with vias where the fan-out lanes leave room
    def chain(points, ends):
        for a, b in zip(points[:-1], points[1:]):
            track(a, b, "GND", width=0.2)
        for e, at in ends:
            track(at, e, "GND", width=0.2)
            via(e, "GND")

    order = [16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    for X, b in (("A", 100), ("B", 200)):
        bx, cy, c = BX[X], CHIP_Y, b + 20
        for side, pins in ((-1, range(1, 9)), (1, range(9, 17))):
            pts = sorted((pad_xy(f"C{b + 1 + order.index(p)}", 2) for p in pins), key=lambda q: q[1])
            chain(pts, [((pts[0][0], round(pts[0][1] - 0.95, 3)), pts[0]), ((pts[-1][0], round(pts[-1][1] + 0.95, 3)), pts[-1])])
        left = sorted((pad_xy(f"C{c + n}", 2) for n in (6, 7, 4, 5, 13, 12, 3, 2, 15)), key=lambda q: q[1])
        lx = left[0][0]
        gaps = [round(cy + FAN_TOP - FAN_PITCH * (n + 0.5), 3) for n in (0, 3)]     # between two lanes
        chain(left, [((lx, round(left[0][1] - 0.95, 3)), left[0])] + [((round(lx - 0.775, 3), g), (lx, g)) for g in gaps])
        r1 = sorted((pad_xy(f"C{c + n}", 2) for n in (0, 1, 9)), key=lambda q: q[1])
        chain(r1 + [], [((r1[-1][0], round(r1[-1][1] + 0.95, 3)), r1[-1])])
        track(r1[0], pad_xy(f"C{c + 8}", 2), "GND", width=0.2)
        # the two capacitors beside pin 28 are not joined, so that the VCAP1 track can pass between them
        g_up, g_dn = pad_xy(f"C{c + 11}", 2), pad_xy(f"C{c + 14}", 2)
        chain([g_up], [((g_up[0], round(g_up[1] - 1.1, 3)), g_up)])
        chain([g_dn], [((round(g_dn[0] + 0.775, 3), round(g_dn[1] - 0.2, 3)), g_dn)])

    # ---- planes: layer 2 is ground everywhere; layer 3 carries DVDD (top) and AVDD (bottom).
    #      Clearance 0.15 mm: with 0.2 the clearances of neighbouring vias 1 mm apart merge into slots.
    def zone(netname, layer, pts, prio=0, name=""):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net(netname))
        z.SetAssignedPriority(prio)
        z.SetZoneName(name)
        o = z.Outline()
        o.NewOutline()
        for x, y in pts:
            o.Append(FromMM(OX + x), FromMM(OY + y))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetLocalClearance(FromMM(0.15))
        z.SetMinThickness(FromMM(0.15))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)
        return z

    full = [(0, 0), (W, 0), (W, H), (0, H)]
    zone("GND", pcbnew.In1_Cu, full, 0, "ground plane")
    zone("GND", pcbnew.In2_Cu, full, 0, "ground fill")
    zone("DVDD", pcbnew.In2_Cu, [(1.0, 1.0), (W - 1.0, 1.0), (W - 1.0, SPLIT_Y - 0.2), (1.0, SPLIT_Y - 0.2)], 1,
         "digital supply")
    zone("AVDD", pcbnew.In2_Cu, [(1.0, SPLIT_Y + 0.2), (W - 1.0, SPLIT_Y + 0.2), (W - 1.0, H - 1.0), (1.0, H - 1.0)], 1,
         "analog supply")

    # ---- nothing on the top layer, and no via, under bare metal of the XIAO that has no land here
    for n, (x0, y0, x1, y1) in enumerate(MODULE_METAL):
        k = pcbnew.ZONE(board)
        k.SetIsRuleArea(True)
        k.SetZoneName(f"under the module {n + 1}")
        k.SetLayer(pcbnew.F_Cu)
        k.SetDoNotAllowTracks(True)
        k.SetDoNotAllowVias(True)
        k.SetDoNotAllowPads(False)
        k.SetDoNotAllowFootprints(False)
        (k.SetDoNotAllowZoneFills if hasattr(k, "SetDoNotAllowZoneFills") else k.SetDoNotAllowCopperPour)(True)
        k.AddPolygon(pcbnew.VECTOR_VECTOR2I([V(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]))
        board.Add(k)

    # ---- every pad of a plane net that is not yet on a fixed track of that net gets a via of its own, as
    #      close as one fits. Without this, which pads end up cut off depends on what the router leaves free.
    #      Supply pads only where their plane is (layer 3 is split at SPLIT_Y); ground everywhere.
    import math
    import lastmile as L
    ring = sorted(((dx * 0.05, dy * 0.05) for dx in range(-44, 45) for dy in range(-44, 45)
                   if 0.55 <= math.hypot(dx, dy) * 0.05 <= 2.2), key=lambda o: o[0] ** 2 + o[1] ** 2)
    for netname, y_from, y_to in (("DVDD", 1.5, SPLIT_Y - 0.6), ("AVDD", SPLIT_Y + 0.6, H - 1.5), ("GND", 0.0, H)):
        space = L.Space(board, netname)
        fixed = [t for t in board.GetTracks() if t.GetNetname() == netname and not isinstance(t, pcbnew.PCB_VIA)]
        own, none = 0, []
        for ref in sorted(fps):
            for pad in fps[ref].Pads():
                if pad.GetNetname() != netname or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                    continue
                if any(pad.HitTest(t.GetStart()) or pad.HitTest(t.GetEnd()) for t in fixed):
                    continue
                layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
                x, y = ToMM(pad.GetPosition().x) - OX, ToMM(pad.GetPosition().y) - OY
                for dx, dy in ring:
                    vp = (round(x + dx, 3), round(y + dy, 3))
                    if y_from <= vp[1] <= y_to and space.via_ok(*vp) and space.track_ok((x, y), vp, layer):
                        track((x, y), vp, netname, layer=layer, width=0.2)
                        via(vp, netname)
                        space.holes.append((V(*vp).x, V(*vp).y))
                        own += 1
                        break
                else:
                    none.append(f"{ref}.{pad.GetNumber()}")
        print(f"{netname} vias placed beside pads: {own}" + (f"; none at {', '.join(none)}" if none else ""))

    # ---- capacitors and resistors: a ground pad that has its track to a via is kept out of the pours, so both
    #      pads of the part see thin copper and heat alike in the oven. Its connection is the track.
    gnd_tracks = [t for t in board.GetTracks() if t.GetNetname() == "GND" and not isinstance(t, pcbnew.PCB_VIA)]
    apart = 0
    for ref in sorted(fps):
        if ref[0] not in "CR" or ref.startswith("RN"):
            continue
        for pad in fps[ref].Pads():
            if pad.GetNetname() == "GND" and any(pad.HitTest(t.GetStart()) or pad.HitTest(t.GetEnd()) for t in gnd_tracks):
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_NONE)
                apart += 1
    print(f"ground pads of small parts kept out of the pours: {apart}")

    out = os.path.join(POD, "emg-pod-unrouted.kicad_pcb")
    pcbnew.SaveBoard(out, board)
    print(f"{len(fps)} footprints, {len(nets)} nets, connector origin y = {CONN_Y}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
