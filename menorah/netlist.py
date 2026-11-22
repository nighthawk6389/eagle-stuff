"""Menorah v1 netlist-as-code: every part, its footprint, LCSC number, position and pin->net map.

Positions are front-view mm (see geometry.py); every part is placed on the back.
This file IS the schematic: PARTS is consumed by build.py and by the BOM/doc generators.
"""
import geometry as G

KL = "/usr/share/kicad/footprints/"
import os
MY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "menorah.pretty")

# ESP32-S3-WROOM-1 pad numbers (from KiCad symbol RF_Module:ESP32-S3-WROOM-1)
ESP = {"GND": ["1", "40", "41"], "3V3": "2", "EN": "3", "IO4": "4", "IO5": "5", "IO6": "6", "IO7": "7",
       "IO15": "8", "IO16": "9", "IO17": "10", "IO18": "11", "IO8": "12", "IO19": "13", "IO20": "14",
       "IO3": "15", "IO46": "16", "IO9": "17", "IO10": "18", "IO11": "19", "IO12": "20", "IO13": "21",
       "IO14": "22", "IO21": "23", "IO47": "24", "IO48": "25", "IO45": "26", "IO0": "27", "IO35": "28",
       "IO36": "29", "IO37": "30", "IO38": "31", "IO39": "32", "IO40": "33", "IO41": "34", "IO42": "35",
       "RXD0": "36", "TXD0": "37", "IO2": "38", "IO1": "39"}

# GPIO assignment (firmware pin map).  Chosen for routability:
#   module east pads 4,5      <- hall C1, C2 (front bus under the antenna keep-out edge)
#   module east pads 6..12    <- LED data, mic, VLED_EN, CHRG_N, VBAT_SENSE (all local to the power section / stem)
#   module south pads 17..23  <- hall SH, C5..C8, C3, C4 (come round the east side and along the bottom strip)
HALL_GPIO = {"C1": "IO4", "C2": "IO5", "SH": "IO9", "C5": "IO10", "C6": "IO11", "C7": "IO12", "C8": "IO13",
             "C3": "IO14", "C4": "IO21"}        # all RTC-capable (GPIO0..21) -> any candle can wake the board
GPIO_NETS = {"IO19": "USB_DN", "IO20": "USB_DP",
             "IO6": "LED_DATA_3V3", "IO7": "MIC_SCK", "IO15": "MIC_WS", "IO16": "MIC_SD",
             "IO17": "VLED_EN", "IO18": "CHRG_N", "IO8": "VBAT_SENSE",        # IO8 = ADC1_CH7
             "IO47": "EXP_IO47", "IO48": "EXP_IO48", "IO0": "BOOT", "EN": "EN",
             "RXD0": "UART_RX", "TXD0": "UART_TX"}
for cid, io in HALL_GPIO.items():
    assert io not in GPIO_NETS
    GPIO_NETS[io] = f"HALL_{cid}"

PARTS = []


def P(ref, lib, fp, value, lcsc, x, y, rot, nets, **kw):
    PARTS.append(dict(ref=ref, lib=lib, fp=fp, value=value, lcsc=lcsc, x=x, y=y, rot=rot, nets=nets, **kw))


R0603 = ("Resistor_SMD", "R_0603_1608Metric")
C0603 = ("Capacitor_SMD", "C_0603_1608Metric")
C0805 = ("Capacitor_SMD", "C_0805_2012Metric")
SOT23 = ("Package_TO_SOT_SMD", "SOT-23")
C100N, C1U, C10U, C22U = "C14663", "C15849", "C15850", "C45783"
R10K, R100K, R5K1, R3K3, R100R = "C25804", "C25803", "C23186", "C22978", "C22775"

# ---------------------------------------------------------------- MCU
u1 = {}
for name, pads in ESP.items():
    for pad in (pads if isinstance(pads, list) else [pads]):
        u1[pad] = "GND" if name == "GND" else "+3V3" if name == "3V3" else GPIO_NETS.get(name)
P("U1", "RF_Module", "ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N8R8", "C2913201", *G.U1_POS, 0, u1)
P("C1", *C0603, "100n", C100N, 80.6, 125.85, 90, {"1": "+3V3", "2": "GND"})
P("R1", *R0603, "10k", R10K, 81.3, 128.1, 0, {"1": "+3V3", "2": "EN"})
P("C2", *C0603, "1u", C1U, 83.4, 129.6, 180, {"1": "EN", "2": "GND"})
P("SW1", "Button_Switch_SMD", "SW_Push_1P1T_XKB_TS-1187A", "BOOT", "C318884", 150.5, 146.4, 0, {"1": "BOOT", "2": "GND"})
P("SW2", "Button_Switch_SMD", "SW_Push_1P1T_XKB_TS-1187A", "RESET", "C318884", 150.5, 140.2, 0, {"1": "EN", "2": "GND"})

# ---------------------------------------------------------------- USB-C
usb = {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
       "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
       "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
       "A8": None, "B8": None}
P("J1", "Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12", "USB-C", "C165948", G.BASE_X0 + 3.2, 131.0, 90, usb)
P("R2", *R0603, "5k1", R5K1, 57.6, 126.2, 90, {"1": "CC2", "2": "GND"})   # CC2 pad (B5) is the upper one
P("R3", *R0603, "5k1", R5K1, 57.6, 135.9, 90, {"1": "CC1", "2": "GND"})
P("U5", "Package_TO_SOT_SMD", "SOT-23-6", "USBLC6-2SC6", "C7519", 57.2, 131.0, 90,
  {"1": "USB_DN", "6": "USB_DN", "3": "USB_DP", "4": "USB_DP", "2": "GND", "5": "VBUS"})
P("C3", *C0805, "10u", C10U, 54.8, 127.2, 90, {"1": "VBUS", "2": "GND"})

# ---------------------------------------------------------------- power
# VBUS --D1--> VSYS <--Q1 (P-FET, on when VBUS absent)-- VBAT ; TP4057 charges VBAT from VBUS
P("D1", "Diode_SMD", "D_SMA", "SS34", "C8678", 88.6, 127.6, 0, {"1": "VSYS", "2": "VBUS"})   # pad1 = cathode
P("U2", "Package_TO_SOT_SMD", "SOT-23-6", "TP4057", "C12044", 90.5, 137.0, 0,
  {"1": "CHRG_N", "2": "GND", "3": "VBAT", "4": "VBUS", "5": None, "6": "PROG"})
P("R4", *R0603, "3k3", R3K3, 87.0, 136.3, 90, {"1": "PROG", "2": "GND"})                      # ~300 mA charge
P("C4", *C0603, "1u", C1U, 89.3, 134.0, 0, {"1": "VBUS", "2": "GND"})
P("C5", *C0805, "10u", C10U, 93.7, 134.3, 0, {"1": "VBAT", "2": "GND"})
P("Q1", *SOT23, "AO3401A", "C15127", 96.0, 137.0, 0, {"1": "VBUS", "2": "VSYS", "3": "VBAT"})  # G,S,D
P("R5", *R0603, "10k", R10K, 96.9, 134.0, 0, {"1": "VBUS", "2": "GND"})   # gate pulldown; low enough to beat D1 leakage
P("J2", "Connector_JST", "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", "LiPo", "C295747", 149.7, 129.0, 90,
  {"1": "VBAT", "2": "GND", "MP": "GND"})
P("U3", "Package_TO_SOT_SMD", "SOT-23-5", "AP2112K-3.3", "C51118", 85.6, 132.2, 0,
  {"1": "VSYS", "2": "GND", "3": "VSYS", "4": None, "5": "+3V3"})
P("C6", *C0805, "22u", C22U, 84.5, 135.0, 180, {"1": "+3V3", "2": "GND"})
P("C7", *C0805, "22u", C22U, 93.6, 127.6, 270, {"1": "VSYS", "2": "GND"})
P("R6", *R0603, "100k", R100K, 89.5, 142.6, 0, {"1": "VBAT", "2": "VBAT_SENSE"})
P("R7", *R0603, "100k", R100K, 93.2, 142.6, 0, {"1": "VBAT_SENSE", "2": "GND"})
P("C8", *C0603, "100n", C100N, 96.9, 142.6, 0, {"1": "VBAT_SENSE", "2": "GND"})

# LED rail switch: VSYS --Q2 (P-FET)--> VLED, driven by Q3 from VLED_EN (default off)
P("Q2", *SOT23, "AO3401A", "C15127", 102.9625, 120.5, 180, {"1": "Q2_G", "2": "VSYS", "3": "VLED"})
P("R8", *R0603, "100k", R100K, 100.3, 120.5, 270, {"1": "VSYS", "2": "Q2_G"})
P("C9", *C0603, "100n", C100N, 98.8, 120.5, 270, {"1": "VSYS", "2": "Q2_G"})                     # soft start
P("Q3", *SOT23, "2N7002", "C8545", 101.5, 124.6, 0, {"1": "VLED_EN", "2": "GND", "3": "Q3_D"})
P("R9", *R0603, "10k", R10K, 98.7, 123.9, 270, {"1": "Q2_G", "2": "Q3_D"})
P("R10", *R0603, "100k", R100K, 102.9, 127.3, 0, {"1": "VLED_EN", "2": "GND"})
P("C10", *C0805, "22u", C22U, 102.95, 117.4, 0, {"1": "VLED", "2": "GND"})

# ---------------------------------------------------------------- LED data level shifter + mic (stem)
P("U4", "Package_TO_SOT_SMD", "SOT-23-5", "SN74LV1T34", "C100024", 7.86, 77.6, 180,
  {"1": None, "2": "LED_DATA_3V3", "3": "GND", "4": "LED_DATA_5V", "5": "VLED"})
P("C11", *C0603, "100n", C100N, 11.2, 78.0, 90, {"1": "VLED", "2": "GND"})
P("R11", *R0603, "100R", R100R, 9.0, 74.3, 90, {"1": "LED_DATA_5V", "2": "LED_D0"})
P("MK1", "Sensor_Audio", "InvenSense_ICS-43434-6_3.5x2.65mm", "ICS-43434", "C5656610", G.MIC[0], G.MIC[1] - 0.71, 0,
  {"1": "MIC_WS", "2": "GND", "3": "GND", "4": "MIC_SCK", "5": "+3V3", "6": "MIC_SD"})
P("C12", *C0603, "100n", C100N, 100.3, 92.3, 180, {"1": "+3V3", "2": "GND"})
P("C13", *C0805, "22u", C22U, 42.0, 82.2, 0, {"1": "VLED", "2": "GND"})
P("C14", *C0805, "22u", C22U, 158.0, 82.2, 0, {"1": "VLED", "2": "GND"})

# ---------------------------------------------------------------- expansion / debug pads
TP_POS = [(101.0, 140.6), (101.0, 137.4), (58.3, 139.4), (58.3, 142.2), (65.555, 146.8), (62.9, 146.8)]
for i, net in enumerate(["GND", "+3V3", "UART_TX", "UART_RX", "EXP_IO47", "EXP_IO48"]):
    P(f"TP{i+1}", "TestPoint", "TestPoint_Pad_D1.5mm", net.replace("EXP_", "").replace("UART_", ""), None,
      *TP_POS[i], 0, {"1": net}, no_bom=True)

# ---------------------------------------------------------------- candles: LEDs, caps, hall sensors
chain = G.chain_order()
for i, led in enumerate(chain):
    n = i + 1
    x, y = led["pos"]
    P(f"D{n+100}", MY, "SK6812MINI-E_Rev", "SK6812MINI-E", "C5149201", x, y, 180,
      {"1": "VLED", "2": f"LED_D{n}" if n < len(chain) else None, "3": "GND", "4": f"LED_D{n-1}"},
      candle=led["candle"], kind=led["kind"])
    c = next(c for c in G.candles() if c["id"] == led["candle"])
    if led["kind"] == "body":
        P(f"C{n+100}", *C0603, "100n", C100N, x, y + 3.5, 0, {"1": "VLED", "2": "GND"})
    else:
        P(f"C{n+100}", *C0603, "100n", C100N, x - 3.6, c["top"] + 3.3, 0, {"1": "VLED", "2": "GND"})

for k, c in enumerate(G.candles()):
    hx, hy = c["hall"]
    P(f"U{k+11}", *SOT23, "DRV5032FA", "C140921", hx, hy, 0,
      {"1": "+3V3", "2": f"HALL_{c['id']}", "3": "GND"}, candle=c["id"])
    P(f"C{k+151}", *C0603, "100n", C100N, hx + 3.0, c["top"] + 1.55, 270, {"1": "+3V3", "2": "GND"})

POWER_NETS = ["GND", "+3V3", "VBUS", "VSYS", "VBAT", "VLED"]

if __name__ == "__main__":
    import collections
    nets = collections.defaultdict(list)
    for p in PARTS:
        for pad, net in p["nets"].items():
            if net:
                nets[net].append(f"{p['ref']}.{pad}")
    print(len(PARTS), "parts,", len(nets), "nets")
    for n, pins in sorted(nets.items()):
        if len(pins) < 2:
            print("  SINGLE-PIN NET:", n, pins)
    for n in ["VBUS", "VSYS", "VBAT", "Q2_G", "Q3_D", "PROG", "EN", "BOOT", "LED_D0", "LED_D46", "LED_D47", "VLED_EN", "CHRG_N"]:
        print(f"  {n}: {nets.get(n)}")
