"""The main pod, rev A: every part, every net, and where it is drawn.

NET is the intended netlist: (reference, pin number) -> net name, or None for a pin left open.
check.py exports the netlist from the generated KiCad files and compares it with NET, so a
drawing mistake (a wire that misses a pin, a wrong label) cannot go unnoticed.
"""
import kisch
import parts
from kisch import Sheet, uid
from parts import CAT

POWER = {"GND", "+3V3", "AVDD", "VBAT"}
# nets that cross between sheets (drawn as global labels)
GLOBAL = {"SCLK", "MOSI", "MISO", "CS_A", "CS_B", "DRDY_A", "DRDY_B", "ADS_START", "ADS_RESET",
          "ADS_CLK", "AFE_EN", "MOTOR", "VBUS", "RLDINV", "BIAS"}

NET = {}        # (ref, pin) -> net
BOM = {}        # ref -> (value, footprint, lcsc, mpn)
WHERE = {}      # net -> set of sheet file names

LIB = {"ADS1298": "emgpod:ADS1298IPAG", "XIAO": "emgpod:XIAO_nRF52840_SMD", "LDO": "emgpod:LP5907MFX-3.0",
       "ESD": "emgpod:TPD4E001DRL", "NFET": "Transistor_FET:AO3400A", "SCHOTTKY": "Device:D_Schottky",
       "FPC20": "Connector_Generic_MountingPin:Conn_01x20_MountingPin",
       "JST_PH2": "Connector_Generic_MountingPin:Conn_01x02_MountingPin", "TANT22U": "Device:C_Polarized"}
FP_TP = "TestPoint:TestPoint_Pad_D1.0mm"
FP_MOTOR = "Connector_Wire:SolderWire-0.127sqmm_1x02_P3.7mm_D0.48mm_OD1mm"


def lib_for(kind):
    if kind in LIB:
        return LIB[kind]
    return "Device:R" if kind.startswith("R") else "Device:C"


class Draw:
    def __init__(self, sheet):
        self.s = sheet

    # ---- parts
    def add(self, kind, ref, x, y, rot=0, nets=None, ref_at=None, val_at=None, value=None):
        val, fp, lcsc, mpn = CAT[kind]
        lib = lib_for(kind)
        two_pin = lib in ("Device:R", "Device:C", "Device:C_Polarized", "Device:D_Schottky")
        if two_pin and ref_at is None:
            vertical = (rot in (0, 180)) != (lib == "Device:D_Schottky")
            if vertical:
                dx = 2.3 if lib == "Device:R" else 3.0
                ref_at, val_at = (x + dx, y - 1.27, "left"), (x + dx, y + 1.27, "left")
            else:
                dy = 1.95 if lib == "Device:R" else 3.4
                ref_at, val_at = (x, y - dy, ""), (x, y + dy, "")
        p = self.s.place(lib, ref, value or val, x, y, rot, footprint=fp, ref_at=ref_at, val_at=val_at,
                         fields={"LCSC": lcsc, "MPN": mpn}, datasheet="")
        BOM[ref] = (value or val, fp, lcsc, mpn)
        self.nets(p, nets or {})
        return p

    def nets(self, part, mapping):
        for pin, net in mapping.items():
            pin = str(pin)
            assert pin in part.pins, (part.ref, pin)
            assert (part.ref, pin) not in NET, (part.ref, pin)
            NET[(part.ref, pin)] = net
            if net:
                WHERE.setdefault(net, set()).add(self.s.filename)

    # ---- connections
    def attach(self, net, pt, out, shape="passive"):
        if net in POWER:
            if net == "GND":
                rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[out]
            else:
                rot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[out]
            self.s.power(net, pt, rot)
        else:
            rot = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[out]
            if net in GLOBAL:
                self.s.glabel(net, pt, shape, rot)
            else:
                self.s.label(net, pt, rot)

    def stub(self, part, pin, length=2.54, shape="passive"):
        pin = str(pin)
        net = NET[(part.ref, pin)]
        x, y = part.p(pin)
        ox, oy = part.out(pin)
        if net is None:
            self.s.nc((x, y))
            return None
        end = (x + length * ox, y + length * oy)
        if length:
            self.s.wire((x, y), end)
        self.attach(net, end, (ox, oy), shape)
        return end

    def tie(self, part, pins, length=2.54, at=-1, extra=2.54, shape="passive"):
        """Join neighbouring pins that share a net and attach the net name once."""
        pins = [str(p) for p in pins]
        net = NET[(part.ref, pins[0])]
        assert all(NET[(part.ref, p)] == net for p in pins), (part.ref, pins)
        out = part.out(pins[0])
        ends = []
        for p in pins:
            x, y = part.p(p)
            e = (x + length * out[0], y + length * out[1])
            self.s.wire((x, y), e)
            ends.append(e)
        self.s.wire(ends[0], ends[-1])
        a = ends[at]
        b = (a[0] + extra * out[0], a[1] + extra * out[1])
        self.s.wire(a, b)
        self.attach(net, b, out, shape)

    def two(self, kind, ref, x, y, orient, n1, n2, length=2.54, value=None):
        """Two-terminal part with a named stub on each end. orient: H (pin 1 left) or V (pin 1 top)."""
        p = self.add(kind, ref, x, y, 90 if orient == "H" else 0, {1: n1, 2: n2}, value=value)
        self.stub(p, 1, length)
        self.stub(p, 2, length)
        return p

    def bank(self, x, y, groups, pitch=10.16, note_dy=12.0):
        """Row of capacitors to ground. groups: [(top net, [(kind, ref), ...], note)]."""
        for net, caps, note in groups:
            tops = []
            x_first = x
            for kind, ref in caps:
                p = self.add(kind, ref, x, y, 0, {1: net, 2: "GND"})
                self.s.power("GND", p.p(2), 0)
                top = (x, y - 3.81 - 2.54)
                self.s.wire(p.p(1), top)
                tops.append(top)
                x += pitch
            if len(tops) > 1:
                self.s.wire(tops[0], tops[-1])
            end = (x_first, tops[0][1] - 2.54)
            self.s.wire(tops[0], end)
            self.attach(net, end, (0, -1))
            if note:
                self.s.text(note, (x_first - 2.0, y + note_dy), 1.0, justify="left top")
        return x

    def tp(self, ref, net, x, y):
        p = self.s.place("Connector:TestPoint", ref, "TestPoint", x, y, 90, footprint=FP_TP, in_bom=False,
                         show_value=False, ref_at=(x - 4.5, y, "right"))
        self.nets(p, {1: net})
        self.stub(p, 1, 2.54)
        return p


# =======================================================================================
def power_sheet(s):
    d = Draw(s)
    s.text("Battery input and analog rail", (25.4, 33.0), 1.8, bold=True)
    s.text("J1 is wired straight to the XIAO BAT+ / BAT- pads (charger output, Seeed schematic v1.2).\n"
           "Check the cell's polarity against the silk before plugging in: JST-PH wiring is not standardised.",
           (25.4, 38.5), 1.1, justify="left top")
    # battery connector
    j1 = d.add("JST_PH2", "J1", 45.72, 50.8, 0, {1: "VBAT", 2: "GND", "MP": "GND"},
               ref_at=(46.99, 45.72, ""), val_at=(53.5, 52.07, "left"))
    s.wire(j1.p(1), (27.94, 50.8))
    s.power("VBAT", (27.94, 50.8))
    s.power("PWR_FLAG", (33.02, 50.8))
    s.wire(j1.p(2), (35.56, 53.34), (35.56, 58.42))
    s.power("GND", (35.56, 58.42))
    s.wire(j1.p("MP"), (45.72, 60.96), (53.34, 60.96))
    s.power("GND", (45.72, 60.96))
    s.power("PWR_FLAG", (53.34, 60.96))
    # LDO
    u = d.add("LDO", "U2", 111.76, 50.8, 0, {1: "VBAT", 2: "GND", 3: "AVDD_EN", 4: None, 5: "AVDD"},
              ref_at=(104.14, 43.6, "left"), val_at=(111.76, 43.6, "left"))
    s.wire(u.p(1), (76.2, 48.26))
    s.power("VBAT", (76.2, 48.26))
    c = d.add("C1U", "C1", 81.28, 52.07, 0, {1: "VBAT", 2: "GND"})
    s.power("GND", c.p(2))
    d.stub(u, 3, 2.54)
    d.stub(u, 2, 2.54)
    s.wire(u.p(5), (139.7, 48.26))
    s.power("AVDD", (139.7, 48.26))
    c = d.add("C1U", "C2", 129.54, 52.07, 0, {1: "AVDD", 2: "GND"})
    s.power("GND", c.p(2))
    s.text("U2: C1 and C2 are the 1 uF input and output capacitors the LP5907 datasheet asks for.\n"
           "EN has an internal 1 Mohm pull-down and the output a 230 ohm discharge (SNVS798Q).\n"
           "Load: two ADS1298 at 2.75 mA each in HR mode (SBAS459K).", (66.04, 66.0), 1.1, justify="left top")

    # interlock
    s.text("USB interlock: analog rail off whenever VBUS is present", (25.4, 86.5), 1.8, bold=True)
    s.glabel("AFE_EN", (33.02, 99.06), "input", 180)
    r1 = d.add("R10K", "R1", 41.91, 99.06, 90, {1: "AFE_EN", 2: "AVDD_EN"})
    s.wire((33.02, 99.06), r1.p(1))
    s.wire(r1.p(2), (76.2, 99.06))
    s.label("AVDD_EN", (46.99, 99.06))
    r2 = d.add("R100K", "R2", 55.88, 102.87, 0, {1: "AVDD_EN", 2: "GND"})
    s.power("GND", r2.p(2))
    q1 = d.add("NFET", "Q1", 73.66, 109.22, 0, {1: "VBUS_DET", 2: "GND", 3: "AVDD_EN"},
               ref_at=(78.74, 107.95, "left"), val_at=(78.74, 110.49, "left"))
    s.wire(q1.p(3), (76.2, 99.06))
    d.stub(q1, 2, 2.54)
    s.glabel("VBUS", (33.02, 121.92), "input", 180)
    r3 = d.add("R10K", "R3", 41.91, 121.92, 90, {1: "VBUS", 2: "VBUS_DET"})
    s.wire((33.02, 121.92), r3.p(1))
    s.wire(r3.p(2), (66.04, 121.92), (66.04, 109.22), q1.p(1))
    s.label("VBUS_DET", (46.99, 121.92))
    r4 = d.add("R10K", "R4", 50.8, 125.73, 0, {1: "VBUS_DET", 2: "GND"})
    s.power("GND", r4.p(2))
    c3 = d.add("C100N", "C3", 59.69, 125.73, 0, {1: "VBUS_DET", 2: "GND"})
    s.power("GND", c3.p(2))
    s.text("VBUS is the XIAO 5V pin, which Seeed wires straight to the USB connector.\n"
           "With USB present Q1 shorts AVDD_EN to ground; R1 keeps the MCU pin from\n"
           "overriding it, so firmware cannot turn the analog rail on.\n"
           "Trip point: Q1 turns on for VBUS between 1.3 V and 2.9 V\n"
           "(Vgs(th) 0.65 to 1.45 V, AO3400A datasheet; R3/R4 halve VBUS).\n"
           "R2 holds the rail off while the MCU pin floats (reset, bootloader).\n"
           "U2 needs EN above 1.2 V to run: 3.3 V x 100k/110k = 3.0 V.",
           (25.4, 140.0), 1.1, justify="left top")

    # motor
    s.text("Vibration motor (wired coin motor on two pads)", (127.0, 86.5), 1.8, bold=True)
    s.power("VBAT", (152.4, 93.98))
    r5 = d.add("R12_0805", "R5", 152.4, 97.79, 0, {1: "VBAT", 2: "MOT_P"})
    d1 = d.add("SCHOTTKY", "D1", 152.4, 110.49, 270, {1: "MOT_P", 2: "MOT_N"})
    s.wire(r5.p(2), d1.p(1))
    s.wire((152.4, 101.6), (165.1, 101.6), (165.1, 104.14), (170.18, 104.14))
    s.label("MOT_P", (154.94, 101.6))
    j2 = s.place("Connector_Generic:Conn_01x02", "J2", "Motor pads", 175.26, 104.14, 0, footprint=FP_MOTOR,
                 in_bom=False, ref_at=(176.53, 99.9, ""), val_at=(179.5, 105.41, "left"))
    d.nets(j2, {1: "MOT_P", 2: "MOT_N"})
    s.wire(j2.p(2), (165.1, 106.68), (165.1, 116.84), (152.4, 116.84))
    s.label("MOT_N", (154.94, 116.84))
    q2 = d.add("NFET", "Q2", 149.86, 127.0, 0, {1: "MOTOR", 2: "GND", 3: "MOT_N"},
               ref_at=(154.94, 125.73, "left"), val_at=(154.94, 128.27, "left"))
    s.wire(d1.p(2), q2.p(3))
    d.stub(q2, 2, 2.54)
    s.glabel("MOTOR", (127.0, 127.0), "input", 180)
    s.wire((127.0, 127.0), q2.p(1))
    r6 = d.add("R100K", "R6", 137.16, 130.81, 0, {1: "MOTOR", 2: "GND"})
    s.power("GND", r6.p(2))
    s.text("Suggested motor: Leader LCM1027B3605F (LCSC C7528806), a 10 mm coin motor on wire leads.\n"
           "Its datasheet gives 3.0 V rated, 2.7 to 3.3 V operating, 70 mA running, 120 mA starting.\n"
           "R5 drops the battery (up to 4.2 V) into that range: 4.2 V x 43/(43+12) = 3.3 V,\n"
           "taking the running motor as 3.0 V / 70 mA = 43 ohm. Recalculate R5 for any other motor.\n"
           "D1 is the flyback diode, R6 the gate pull-down.", (127.0, 140.0), 1.1, justify="left top")

    # test points
    s.text("Test points", (213.36, 33.0), 1.8, bold=True)
    for i, (ref, net) in enumerate([("TP1", "VBAT"), ("TP2", "AVDD"), ("TP3", "+3V3"), ("TP4", "GND"),
                                    ("TP5", "GND")]):
        d.tp(ref, net, 223.52, 43.18 + 7.62 * i)


def mcu_sheet(s):
    d = Draw(s)
    s.text("Seeed XIAO nRF52840, soldered down as a module", (25.4, 30.0), 1.8, bold=True)
    s.text("Provides the radio and antenna, USB-C, LiPo charger, 3.3 V regulator and USB bootloader.\n"
           "Pads 15 to 22 are on the underside of the XIAO (Seeed bottom-pad drawing).\n"
           "The plain XIAO and the Sense version share this footprint and pinout.",
           (25.4, 35.5), 1.1, justify="left top")
    nets = {1: "CS_A", 2: "CS_B", 3: "DRDY_A", 4: "DRDY_B", 5: "MISO", 6: "SCLK_MCU", 7: "ADS_START",
            8: "ADS_RESET", 9: "AFE_EN", 10: "MOTOR", 11: "MOSI", 12: "+3V3", 13: "GND", 14: "VBUS",
            15: "SWDIO", 16: "SWCLK", 17: "NRST", 18: "GND", 19: "VBAT", 20: "GND", 21: None, 22: None}
    u = d.add("XIAO", "U1", 101.6, 83.82, 0, nets, ref_at=(83.82, 51.5, "left"), val_at=(101.6, 51.5, "left"))
    shapes = {1: "output", 2: "output", 3: "input", 4: "input", 5: "input", 7: "output", 8: "output",
              9: "output", 10: "output", 11: "output", 14: "output"}
    for pin in range(1, 23):
        d.stub(u, pin, 5.08, shapes.get(pin, "passive"))
    r = d.add("R33", "R20", 53.34, 134.62, 90, {1: "SCLK_MCU", 2: "SCLK"})
    d.stub(r, 1, 5.08)
    d.stub(r, 2, 5.08, "output")
    s.text("R20: series resistor at the source of the SPI clock, which fans out to both converters.\n"
           "The value is a starting point, not from a datasheet (see OPEN.md).",
           (25.4, 141.0), 1.1, justify="left top")
    s.text("Pin choice: Nordic's nRF52840 specification v1.5 marks every XIAO pin except D4 (P0.04) and\n"
           "D5 (P0.05) as low-frequency I/O (up to 10 kHz), because they sit next to the radio.\n"
           "The two fast SPI lines, SCLK and MISO, therefore use D5 and D4. MOSI only carries commands.\n"
           "Firmware: drive P0.13 low for the 100 mA charge current (Seeed schematic, R12 and R18).",
           (25.4, 151.0), 1.1, justify="left top")
    s.text("Test points", (175.26, 30.0), 1.8, bold=True)
    tps = ["SCLK", "MOSI", "MISO", "CS_A", "CS_B", "DRDY_A", "DRDY_B", "ADS_START", "ADS_RESET",
           "SWDIO", "SWCLK", "NRST", "GND"]
    for i, net in enumerate(tps):
        d.tp(f"TP{10 + i}", net, 185.42, 40.64 + 7.62 * i)
    s.text("TP19 to TP22: SWD access for rescuing the bootloader with a borrowed probe.",
           (175.26, 143.0), 1.1, justify="left top")


def afe_sheet(s, X):
    """One converter block: strip connector, ESD, input network, ADS1298 and its decoupling."""
    d = Draw(s)
    A = X == "A"
    b = 100 if A else 200
    P = X + "_"
    s.text(f"Converter {X}: electrode inputs, ADS1298 and decoupling", (15.24, 17.0), 2.0, bold=True)
    s.text("Self-contained block (connector, protection, filter, converter, bypass) so the pod can later be split.\n"
           "Supply, reference and bypass parts follow TI SBAS459K figure 106 (single-supply operation).",
           (15.24, 21.0), 1.1, justify="left top")

    # ---- strip connector
    jn = {1: "BIAS", 2: P + "SHIELD", 19: P + "SHIELD", 20: P + "SHIELD", "MP": "GND"}
    for ch in range(1, 9):
        jn[1 + 2 * ch] = f"{P}E{ch}P"
        jn[2 + 2 * ch] = f"{P}E{ch}N"
    j = d.add("FPC20", f"J{b}", 60.96, 58.42, 0, jn, ref_at=(60.96, 31.75, ""), val_at=(66.5, 58.42, "left"))
    for pin in range(1, 21):
        d.stub(j, pin, 5.08)
    d.stub(j, "MP", 2.54)
    s.text("Strip tail connector, 20 way 0.5 mm.\nPin 1 bias, pins 3-18 the eight pairs,\npins 2, 19, 20 shield.",
           (66.5, 62.0), 1.1, justify="left top")

    # ---- ESD arrays at the connector
    s.text("ESD arrays, placed at the connector", (15.24, 99.0), 1.5, bold=True)
    for k in range(5):
        y = 111.76 + 22.86 * k
        if k < 4:
            ios = {1: f"{P}E{2 * k + 1}P", 2: f"{P}E{2 * k + 1}N", 4: f"{P}E{2 * k + 2}P", 5: f"{P}E{2 * k + 2}N"}
        else:
            ios = {1: "BIAS", 2: None, 4: None, 5: None}
        u = d.add("ESD", f"U{b + 1 + k}", 40.64, y, 0, {**ios, 3: "GND", 6: "AVDD"},
                  ref_at=(34.29, y - 6.6, "left"), val_at=(34.29, y + 6.6, "left"))
        for pin in (1, 2, 4, 5):
            d.stub(u, pin, 2.54)
        c = d.add("C100N", f"C{b + 41 + k}", 54.61, y, 0, {1: "AVDD", 2: "GND"})
        s.wire(u.p(6), c.p(1), (59.69, y - 3.81))
        s.power("AVDD", (59.69, y - 3.81))
        s.wire(u.p(3), c.p(2), (59.69, y + 3.81))
        s.power("GND", (59.69, y + 3.81))
    s.text("TPD4E001: 1 nA maximum leakage. VCC on AVDD with 100 nF,\nunused channels left open (TI SLLS682P, section 7.2.2).",
           (15.24, 228.0), 1.1, justify="left top")

    # ---- converter
    XA, YA = 190.5, 157.48
    an = {}
    for n, (name, _) in parts.ADS1298_PINS.items():
        if name.startswith("IN"):
            an[n] = P + name
    fixed = {17: "AVDD", 18: "AVDD", 19: "AVDD", 21: "AVDD", 22: "AVDD", 56: "AVDD", 59: "AVDD", 54: "AVDD",
             20: "GND", 23: "GND", 32: "GND", 57: "GND", 58: "GND", 53: "GND", 33: "GND", 49: "GND", 51: "GND",
             48: "+3V3", 50: "+3V3", 24: P + "VREFP", 25: "GND", 26: P + "VCAP4", 28: P + "VCAP1",
             30: P + "VCAP2", 55: P + "VCAP3", 27: None, 29: None, 31: "GND", 41: "GND", 42: "GND", 44: "GND",
             45: "GND", 46: "GND", 34: "MOSI", 35: P + "PWDN", 36: "ADS_RESET", 38: "ADS_START",
             39: "CS_" + X, 40: "SCLK", 43: P + "DOUT", 47: "DRDY_" + X, 60: None, 64: P + "WCT"}
    an.update(fixed)
    if A:
        an.update({37: "A_CLKO", 52: "+3V3", 61: "RLDINV", 62: "A_RLDOUT", 63: "A_RLDOUT"})
    else:
        an.update({37: "ADS_CLK", 52: "GND", 61: "B_RLDINV", 62: "AVDD", 63: None})
    u = d.add("ADS1298", f"U{b}", XA, YA, 0, an, ref_at=(205.74, 90.3, "left"), val_at=(205.74, 92.9, "left"))
    assert len(an) == 64
    # supplies
    d.tie(u, [19, 21, 22, 56, 59, 54, 17, 18], 2.54, at=3)
    d.tie(u, [48, 50], 2.54, at=0)
    d.tie(u, [20, 23, 32, 57, 58, 53, 33, 49, 51, 41, 42, 44, 45, 46, 31], 2.54, at=7)
    # signal pins on the right
    shape = {39: "input", 40: "input", 34: "input", 47: "output", 38: "input", 36: "input"}
    for pin in (39, 40, 34, 43, 47, 38, 36, 37, 35, 52, 64, 24, 25, 28, 30, 55, 26):
        d.stub(u, pin, 5.08, shape.get(pin, "passive"))
    if A:
        d.tie(u, [63, 62], 5.08, at=0)
        d.stub(u, 61, 5.08)
    else:
        d.stub(u, 63, 0)
        d.stub(u, 62, 5.08)
        d.stub(u, 61, 5.08)
    d.stub(u, 60, 0)
    s.text("Strapped per the datasheet: TESTP/TESTN (unused inputs) to AVDD; DAISY_IN, GPIO1-4 and RESV1 to DGND;\n"
           "pins 27 and 29 are not connected. Firmware must leave GPIO1-4 as inputs, their reset state.",
           (140.0, 236.0), 1.1, justify="left top")

    # ---- input network: series resistor in each line, capacitor at the converter pin
    s.text("Series resistors: 22k is a placeholder\n(10k to 47k, see OPEN.md)", (119.38, 86.0), 1.1,
           justify="left top")
    order = [16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    caps = []
    for i, pin in enumerate(order):
        name = parts.ADS1298_PINS[pin][0]            # IN1P, IN1N, ...
        ch, pol = name[2], name[3]
        y = u.p(pin)[1]
        e, n = f"{P}E{ch}{pol}", P + name
        r = d.add("R22K", f"R{b + 1 + i}", 139.7, y, 90, {1: e, 2: n},
                  ref_at=(139.2, y - 1.9, "right"), val_at=(140.3, y - 1.9, "left"))
        s.wire((121.92, y), r.p(1))
        s.label(e, (121.92, y))
        s.wire(r.p(2), u.p(pin))
        s.label(n, (147.32, y))
        caps.append((n, [("C47P", f"C{b + 1 + i}")], ""))
    s.text("Filter capacitors at the converter input pins (47 pF C0G)", (246.38, 27.0), 1.5, bold=True)
    d.bank(248.92, 48.26, caps[:8], 12.7)
    d.bank(248.92, 78.74, caps[8:], 12.7)

    # ---- bypass
    s.text("Supply bypass (1 uF + 100 nF at each supply group)", (246.38, 93.0), 1.5, bold=True)
    c = b + 20
    sup = [("AVDD", [("C1U", f"C{c}"), ("C100N", f"C{c + 1}")], "AVDD pins\n19, 21, 22"),
           ("AVDD", [("C1U", f"C{c + 2}"), ("C100N", f"C{c + 3}")], "AVDD pins\n56, 59"),
           ("AVDD", [("C1U", f"C{c + 4}"), ("C100N", f"C{c + 5}")], "AVDD1\npin 54"),
           ("+3V3", [("C1U", f"C{c + 6}"), ("C100N", f"C{c + 7}")], "DVDD pins\n48, 50")]
    d.bank(248.92, 109.22, sup, 12.7)
    s.text("Reference and internal nodes", (246.38, 128.5), 1.5, bold=True)
    ref = [(P + "VREFP", [("C10U", f"C{c + 8}"), ("C100N", f"C{c + 9}")], "VREFP to\nVREFN"),
           (P + "VCAP1", [("TANT22U", f"C{c + 10}")], "tantalum"),
           (P + "VCAP2", [("C1U", f"C{c + 11}")], ""),
           (P + "VCAP3", [("C1U", f"C{c + 12}"), ("C100N", f"C{c + 13}")], ""),
           (P + "VCAP4", [("C1U", f"C{c + 14}")], ""),
           (P + "WCT", [("C1N", f"C{c + 15}")], "")]
    d.bank(248.92, 152.4, ref, 12.7)
    s.text("VCAP1 is a tantalum: the datasheet warns that a ceramic there turns vibration into\n"
           "reference noise, and this board carries a vibration motor.", (246.38, 169.0), 1.1, justify="left top")

    # ---- housekeeping parts
    y1, y2, y3 = 190.5, 210.82, 231.14
    s.text("Straps and series parts", (246.38, 179.0), 1.5, bold=True)
    d.two("R10K", f"R{b + 20}", 254.0, y1, "V", "+3V3", P + "PWDN")
    s.text("PWDN held high\n(10k, as on TI's\nevaluation board)", (263.5, y1 - 4.5), 1.0, justify="left top")
    d.two("R33", f"R{b + 21}", 299.72, y1, "H", P + "DOUT", "MISO", 5.08)
    s.text("series resistor at the data output", (287.0, y1 + 5.0), 1.0, justify="left top")
    d.two("R0", f"R{b + 22}", 353.06, y1, "H", P + "SHIELD", "GND", 5.08)
    s.text("strip shield to ground (0 ohm link)", (340.0, y1 + 5.0), 1.0, justify="left top")
    if A:
        s.text("Clock: this converter is the master (CLKSEL high, internal oscillator, CLK_EN set by firmware)",
               (257.5, y2 - 9.0), 1.1)
        d.two("R33", f"R{b + 23}", 266.7, y2, "H", "A_CLKO", "ADS_CLK", 5.08)
        d.tp("TP30", "ADS_CLK", 317.5, y2)
        s.text("Bias drive (right-leg-drive amplifier of converter A)", (246.38, y3 - 12.5), 1.5, bold=True)
        r = d.add("R1M", f"R{b + 24}", 266.7, y3, 90, {1: "A_RLDOUT", 2: "RLDINV"})
        cc = d.add("C1N5", f"C{b + 40}", 266.7, y3 + 10.16, 90, {1: "A_RLDOUT", 2: "RLDINV"})
        s.wire(r.p(1), (257.81, y3))
        s.wire(cc.p(1), (260.35, y3 + 10.16), (260.35, y3))
        s.label("A_RLDOUT", (257.81, y3), 180)
        s.wire(r.p(2), (275.59, y3))
        s.wire(cc.p(2), (273.05, y3 + 10.16), (273.05, y3))
        s.glabel("RLDINV", (275.59, y3), "passive", 0)
        s.text("feedback 1 Mohm and 1.5 nF, the typical\nvalues of SBAS459K figures 33, 43, 94",
               (257.0, y3 + 16.5), 1.0, justify="left top")
        d.two("R22K", f"R{b + 25}", 325.12, y3, "H", "A_RLDOUT", "BIAS", 5.08)
        s.text("bias series resistor, same placeholder\nvalue as the sense lines", (312.0, y3 + 5.0), 1.0,
               justify="left top")
        d.tp("TP31", "BIAS", 381.0, y3)
    else:
        s.text("Clock: this converter takes ADS_CLK from converter A (CLKSEL low)", (257.5, y2 - 9.0), 1.1)
        d.two("R100K", f"R{b + 23}", 266.7, y2, "H", "ADS_CLK", "GND", 5.08)
        s.text("keeps the clock input low until converter A drives it", (254.0, y2 + 3.0), 1.0, justify="left top")
        s.text("Bias amplifier of converter B is not used (left powered down)", (246.38, y3 - 12.5), 1.5, bold=True)
        d.two("R0", f"R{b + 24}", 266.7, y3, "H", "B_RLDINV", "RLDINV", 5.08)
        s.text("joins the two RLDINV pins as in SBAS459K figure 45,\nso converter B's channels can feed the bias loop.\n"
               "RLDIN goes to AVDD (unused pin, footnote 1 of the pin table);\nRLDOUT and RLDREF stay open.",
               (254.0, y3 + 5.0), 1.0, justify="left top")


# =======================================================================================
def build(directory, date):
    parts.build_symbols()
    root_uuid = uid("root")
    root = Sheet("emg-pod.kicad_sch", "EMG wristband main pod, rev A", "A4", 1, root_uuid, date=date)
    root.uuid = root_uuid
    root.path = f"/{root_uuid}"
    defs = [("Power, interlock, motor", "power.kicad_sch", "A4", power_sheet, None),
            ("MCU: XIAO nRF52840", "mcu.kicad_sch", "A4", mcu_sheet, None),
            ("Converter A", "afe_a.kicad_sch", "A3", afe_sheet, "A"),
            ("Converter B", "afe_b.kicad_sch", "A3", afe_sheet, "B")]
    sheets = []
    for i, (name, fn, paper, fun, arg) in enumerate(defs):
        page = i + 2
        x, y = 25.4 + 66.04 * (i % 2), 60.96 + 38.1 * (i // 2)
        su = root.subsheet(name, fn, x, y, 50.8, 22.86, page)
        sh = Sheet(fn, name, paper, page, root_uuid, su, date=date)
        fun(sh, arg) if arg else fun(sh)
        sheets.append(sh)
    root.text("EMG wristband: main pod, rev A", (25.4, 30.0), 3.0, bold=True)
    root.text("16 differential EMG channels at 2 kSPS: two ADS1298 converters, a Seeed XIAO nRF52840,\n"
              "a 3.0 V analog rail that hardware switches off whenever USB is plugged in, and a vibration motor.\n"
              "These files are generated by gen/build.py. Change the generator, not the files.",
              (25.4, 36.0), 1.3, justify="left top")
    root.text("Rails\n"
              "  VBAT   battery node = XIAO BAT+ pad (charger output), 3.0 to 4.2 V\n"
              "  +3V3   XIAO regulator output; converter digital supply (DVDD)\n"
              "  AVDD   3.0 V from U2, converter analog supply; off while USB is present\n\n"
              "XIAO pins\n"
              "  D0  CS_A        D6   ADS_START\n"
              "  D1  CS_B        D7   ADS_RESET\n"
              "  D2  DRDY_A      D8   AFE_EN\n"
              "  D3  DRDY_B      D9   MOTOR\n"
              "  D4  MISO        D10  MOSI\n"
              "  D5  SCLK\n\n"
              "Open questions are in OPEN.md.", (160.0, 60.96), 1.3, justify="left top")
    for sh in [root] + sheets:
        sh.write(directory)
    # consistency of the label scopes
    for net, files in WHERE.items():
        if net in POWER:
            continue
        if net in GLOBAL:
            assert len(files) >= 2, f"global net {net} appears on one sheet only"
        else:
            assert len(files) == 1, f"local net {net} appears on {files}"
    return [root] + sheets
