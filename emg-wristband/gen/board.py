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
POWER_NETS = ["VBAT", "AVDD", "+3V3", "GND", "MOT_P", "MOT_N", "VBUS"]

# block centres: converter A on the left half, converter B on the right half
BX = {"A": 12.25, "B": 36.75}
CONN_Y = None                   # set once the connector footprint has been measured
CHIP_Y = 29.9
ROW1, ROW2 = 39.75, 37.7         # resistor-array rows (centre lines)
XIAO_X0, XIAO_Y0 = 28.0, 1.0
BOTTOM = {"TP19", "TP20", "TP21", "TP22"}      # bare pads on the back; no parts are assembled there


def V(x, y):
    return VECTOR2I(FromMM(OX + x), FromMM(OY + y))


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
    # ---- XIAO: USB end at the right edge, antenna end towards the middle of the top edge
    P["U1"] = (XIAO_X0, XIAO_Y0, 270)
    # ---- battery connector, opening towards the top edge
    P["J1"] = (6.0, 5.6, 180)
    # ---- motor driver, on the XIAO side of the board
    P["J2"] = (13.0, 2.2, 0)
    P["R5"] = (13.6, 5.0, 0)
    P["D1"] = (17.9, 5.0, 0)
    P["Q2"] = (22.6, 3.2, 0)
    P["R6"] = (22.6, 6.4, 0)
    # ---- analog regulator and interlock
    P["U2"] = (21.2, 16.9, 0)
    P["C1"] = (18.4, 16.9, 270)
    P["C2"] = (23.9, 16.9, 270)
    for i, r in enumerate(["R1", "R2", "R3", "R4", "C3"]):
        P[r] = (11.6 + 2.1 * i, 14.0, 0)
    P["Q1"] = (14.2, 17.0, 0)
    P["R20"] = (25.0, 21.6, 90)
    # ---- test points
    grid = ["TP10", "TP11", "TP12", "TP13", "TP14", "TP15", "TP16", "TP17", "TP18", "TP3"]
    for i, r in enumerate(grid):
        P[r] = (11.6 + 2.2 * (i % 7), 9.6 + 2.2 * (i // 7), 0)
    P["TP1"] = (2.0, 13.0, 0)
    P["TP4"] = (2.0, 15.4, 0)
    P["TP5"] = (9.3, 17.4, 0)
    P["TP2"] = (5.5, 17.4, 0)
    # SWD rescue pads on the back of the board, beneath the XIAO's own SWD pads
    P["TP19"] = (47.0, 6.2, 0)
    P["TP20"] = (47.0, 13.6, 0)
    P["TP21"] = (44.5, 6.2, 0)
    P["TP22"] = (44.5, 13.6, 0)
    P["TP30"] = (2.0, 17.8, 0)
    P["TP31"] = (2.0, 20.2, 0)
    # ---- the two converter blocks, identical
    for X, b in (("A", 100), ("B", 200)):
        bx, cy = BX[X], CHIP_Y
        P[f"U{b}"] = (bx, cy, 90)                      # inputs (pins 1-16) face the strip connector
        P[f"J{b}"] = (bx, CONN_Y, 0)
        for m in range(4):
            P[f"RN{b + 1 + m}"] = (bx - 3.0 + 2.0 * m, ROW1 if m % 2 == 0 else ROW2, 90)
        # filter capacitors: converter pins 1-8 on the left of the chip, 9-16 on the right
        order = [16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        for pin in range(1, 17):
            ref = f"C{b + 1 + order.index(pin)}"
            if pin <= 8:
                P[ref] = (bx - 10.75, cy + 4.2 - 1.2 * (pin - 1), 180)
            else:
                P[ref] = (bx + 10.75, cy + 4.2 - 1.2 * (16 - pin), 0)
        c = b + 20
        left = [(f"C{c + 6}", -5.4), (f"C{c + 7}", -4.2), (f"C{c + 4}", -3.0), (f"C{c + 5}", -1.8),
                (f"C{c + 13}", -0.6), (f"C{c + 12}", 0.6), (f"C{c + 3}", 1.8), (f"C{c + 2}", 3.0),
                (f"C{c + 15}", 4.2)]
        for ref, dy in left:
            P[ref] = (bx - 7.75, cy + dy, 180)
        right = [(f"C{c}", 5.3), (f"C{c + 1}", 4.2), (f"C{c + 9}", 3.1), (f"C{c + 14}", -1.2),
                 (f"C{c + 11}", -2.7)]
        for ref, dy in right:
            P[ref] = (bx + 7.75, cy + dy, 0)
        P[f"C{c + 8}"] = (bx + 7.85, cy + 1.0, 270)       # 10 uF 0603 on VREFP, pad 1 next to pin 24
        P[f"C{c + 10}"] = (bx + 5.2, cy - 8.3, 180)        # 22 uF tantalum on VCAP1
        # digital-side resistors above the chip
        P[f"R{b + 21}"] = (bx - 1.3, cy - 8.1, 90)         # DOUT series
        P[f"R{b + 23}"] = (bx + 0.2, cy - 8.1, 90)         # clock series (A) / pull-down (B)
        P[f"R{b + 20}"] = (bx + 1.7, cy - 8.1, 270)        # PWDN pull-up
        # ESD arrays and their capacitors, either side of the resistor arrays
        # ESD arrays and their capacitors in the corners beside the connector; the bias one above it
        for n, dx, y in [(4, -10.2, 42.2), (3, -10.2, 46.0), (2, 10.2, 42.2), (1, 10.2, 46.0)]:
            P[f"U{b + n}"] = (bx + dx, y, 90)              # pads in two rows, so every one can be reached
            P[f"C{b + 40 + n}"] = (bx + dx, y + 1.9, 0)
        P[f"U{b + 5}"] = (bx - 9.6, 37.9, 90)
        P[f"C{b + 45}"] = (bx - 9.6, 40.0, 0)
        P[f"R{b + 22}"] = (bx + 6.2, 40.2, 0)             # shield link
        if X == "A":
            P["R124"] = (bx - 7.75, cy + 5.4, 180)
            P["C140"] = (bx - 5.9, 38.0, 90)
            P["R125"] = (bx - 5.7, 40.3, 0)
        else:
            P["R224"] = (bx - 7.75, cy + 5.4, 180)
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

    # outline, 1 mm corner radius
    r = 1.0
    pts = [(r, 0), (W - r, 0), (W, r), (W, H - r), (W - r, H), (r, H), (0, H - r), (0, r)]
    for i in range(0, 8, 2):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*pts[i]))
        s.SetEnd(V(*pts[i + 1]))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FromMM(0.1))
        board.Add(s)
    for (cx, cy), (sx, sy) in [((W - r, r), (W - r, 0)), ((W - r, H - r), (W, H - r)), ((r, H - r), (r, H)),
                               ((r, r), (0, r))]:
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
            fp.SetField("LCSC", design.BOM[ref][2]) if hasattr(fp, "SetField") else None
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

    # ---- fixed routes: every electrode line runs straight from the connector through its resistor to its pin
    for X, b in (("A", 100), ("B", 200)):
        bx = BX[X]
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
            # branch under the chip to a via; the filter capacitor is reached from there on the back
            vy = CHIP_Y + (4.2 if k % 2 == 0 else 3.3)
            track(up, (x, vy), in_net, width=FINE)
            via((x, vy), in_net)
            # branch under the connector body to a via; the ESD array is reached from there
            ey = jp[1] + (1.6 if k % 2 == 0 else 2.5)
            track(jp, (x, ey), e_net, width=FINE)
            via((x, ey), e_net)

    # ---- planes: layer 2 is ground everywhere; layer 3 carries AVDD under the converters, ground elsewhere
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
        z.SetLocalClearance(FromMM(0.2))
        z.SetMinThickness(FromMM(0.2))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)
        return z

    full = [(0, 0), (W, 0), (W, H), (0, H)]
    zone("GND", pcbnew.In1_Cu, full, 0, "ground plane")
    zone("GND", pcbnew.In2_Cu, full, 0, "ground fill")
    zone("AVDD", pcbnew.In2_Cu, [(1.0, 22.5), (W - 1.0, 22.5), (W - 1.0, H - 1.0), (1.0, H - 1.0)], 1, "analog supply")

    # ---- antenna keep-out: no copper on any layer under and beside the XIAO's antenna end
    k = pcbnew.ZONE(board)
    k.SetIsRuleArea(True)
    k.SetZoneName("antenna keep-out")
    ls = pcbnew.LSET()
    for lay in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        ls.AddLayer(lay)
    k.SetLayerSet(ls)
    k.SetDoNotAllowTracks(True)
    k.SetDoNotAllowVias(True)
    k.SetDoNotAllowPads(False)
    k.SetDoNotAllowFootprints(False)
    (k.SetDoNotAllowZoneFills if hasattr(k, "SetDoNotAllowZoneFills") else k.SetDoNotAllowCopperPour)(True)
    o = k.Outline()
    o.NewOutline()
    for x, y in [(25.8, 3.7), (31.6, 3.7), (31.6, 12.8), (25.8, 12.8)]:
        o.Append(FromMM(OX + x), FromMM(OY + y))
    board.Add(k)

    out = os.path.join(POD, "emg-pod-unrouted.kicad_pcb")
    pcbnew.SaveBoard(out, board)
    print(f"{len(fps)} footprints, {len(nets)} nets, connector origin y = {CONN_Y}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
