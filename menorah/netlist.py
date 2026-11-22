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

# GPIO assignment (firmware pin map)
HALL_GPIO = {"SH": "IO4", "C8": "IO5", "C7": "IO6", "C6": "IO7", "C5": "IO15",
             "C4": "IO16", "C3": "IO17", "C2": "IO18", "C1": "IO8"}   # all RTC-capable -> can wake from sleep
GPIO_NETS = {"IO19": "USB_DN", "IO20": "USB_DP", "IO9": "VBAT_SENSE", "IO10": "CHRG_N", "IO11": "VLED_EN",
             "IO12": "MIC_SD", "IO13": "MIC_WS", "IO14": "MIC_SCK", "IO21": "LED_DATA_3V3",
             "IO47": "EXP_IO47", "IO48": "EXP_IO48", "IO0": "BOOT", "EN": "EN",
             "RXD0": "UART_RX", "TXD0": "UART_TX"}
for cid, io in HALL_GPIO.items():
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
P("C1", *C0603, "100n", C100N, 82.0, 126.1, 90, {"1": "+3V3", "2": "GND"})
P("R1", *R0603, "10k", R10K, 82.0, 129.6, 90, {"1": "+3V3", "2": "EN"})
P("C2", *C0603, "1u", C1U, 82.0, 133.1, 90, {"1": "EN", "2": "GND"})
P("SW1", "Button_Switch_SMD", "SW_Push_1P1T_XKB_TS-1187A", "BOOT", "C318884", 150.5, 124.5, 90, {"1": "BOOT", "2": "GND"})
P("SW2", "Button_Switch_SMD", "SW_Push_1P1T_XKB_TS-1187A", "RESET", "C318884", 150.5, 132.5, 90, {"1": "EN", "2": "GND"})

# ---------------------------------------------------------------- USB-C
usb = {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
       "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
       "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
       "A8": None, "B8": None}
P("J1", "Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12", "USB-C", "C165948", G.BASE_X0 + 3.2, 131.0, 90, usb)
P("R2", *R0603, "5k1", R5K1, 57.6, 126.2, 90, {"1": "CC1", "2": "GND"})
P("R3", *R0603, "5k1", R5K1, 57.6, 135.9, 90, {"1": "CC2", "2": "GND"})
P("U5", "Package_TO_SOT_SMD", "SOT-23-6", "USBLC6-2SC6", "C7519", 57.2, 131.0, 90,
  {"1": "USB_DN", "6": "USB_DN", "3": "USB_DP", "4": "USB_DP", "2": "GND", "5": "VBUS"})
P("C3", *C0805, "10u", C10U, 50.0, 124.2, 0, {"1": "VBUS", "2": "GND"})

# ---------------------------------------------------------------- power
# VBUS --D1--> VSYS <--Q1 (P-FET, on when VBUS absent)-- VBAT ; TP4057 charges VBAT from VBUS
P("D1", "Diode_SMD", "D_SMA", "SS34", "C8678", 89.0, 148.2, 0, {"1": "VSYS", "2": "VBUS"})   # pad1 = cathode
P("U2", "Package_TO_SOT_SMD", "SOT-23-6", "TP4057", "C12044", 86.5, 140.0, 0,
  {"1": "CHRG_N", "2": "GND", "3": "VBAT", "4": "VBUS", "5": None, "6": "PROG"})
P("R4", *R0603, "3k3", R3K3, 86.5, 143.3, 0, {"1": "PROG", "2": "GND"})                      # ~300 mA charge
P("C4", *C0603, "1u", C1U, 86.5, 136.9, 0, {"1": "VBUS", "2": "GND"})
P("C5", *C0805, "10u", C10U, 92.2, 136.6, 0, {"1": "VBAT", "2": "GND"})
P("Q1", *SOT23, "AO3401A", "C15127", 92.0, 140.0, 0, {"1": "VBUS", "2": "VSYS", "3": "VBAT"})  # G,S,D
P("R5", *R0603, "10k", R10K, 92.0, 143.3, 0, {"1": "VBUS", "2": "GND"})   # gate pulldown; low enough to beat D1 leakage
P("J2", "Connector_JST", "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", "LiPo", "C295747", 99.6, 146.6, 270,
  {"1": "VBAT", "2": "GND", "MP": "GND"})
P("U3", "Package_TO_SOT_SMD", "SOT-23-5", "AP2112K-3.3", "C51118", 86.5, 122.4, 0,
  {"1": "VSYS", "2": "GND", "3": "VSYS", "4": None, "5": "+3V3"})
P("C6", *C0805, "22u", C22U, 86.5, 125.8, 0, {"1": "+3V3", "2": "GND"})
P("C7", *C0805, "22u", C22U, 91.3, 122.6, 90, {"1": "VSYS", "2": "GND"})
P("R6", *R0603, "100k", R100K, 86.3, 130.6, 0, {"1": "VBAT", "2": "VBAT_SENSE"})
P("R7", *R0603, "100k", R100K, 90.0, 130.6, 0, {"1": "VBAT_SENSE", "2": "GND"})
P("C8", *C0603, "100n", C100N, 93.7, 130.6, 0, {"1": "VBAT_SENSE", "2": "GND"})

# LED rail switch: VSYS --Q2 (P-FET)--> VLED, driven by Q3 from VLED_EN (default off)
P("Q2", *SOT23, "AO3401A", "C15127", 95.6, 122.4, 0, {"1": "Q2_G", "2": "VSYS", "3": "VLED"})
P("R8", *R0603, "100k", R100K, 95.6, 125.6, 0, {"1": "VSYS", "2": "Q2_G"})
P("C9", *C0603, "100n", C100N, 95.6, 127.5, 0, {"1": "VSYS", "2": "Q2_G"})                     # soft start
P("Q3", *SOT23, "2N7002", "C8545", 100.6, 122.4, 0, {"1": "VLED_EN", "2": "GND", "3": "Q3_D"})
P("R9", *R0603, "10k", R10K, 100.6, 125.6, 0, {"1": "Q2_G", "2": "Q3_D"})
P("R10", *R0603, "100k", R100K, 100.6, 127.5, 0, {"1": "VLED_EN", "2": "GND"})
P("C10", *C0805, "22u", C22U, 104.6, 122.8, 90, {"1": "VLED", "2": "GND"})

# ---------------------------------------------------------------- LED data level shifter + mic (stem)
P("U4", "Package_TO_SOT_SMD", "SOT-23-5", "SN74LV1T34", "C100024", 93.5, 88.3, 0,
  {"1": None, "2": "LED_DATA_3V3", "3": "GND", "4": "LED_DATA_5V", "5": "VLED"})
P("C11", *C0603, "100n", C100N, 93.5, 91.5, 0, {"1": "VLED", "2": "GND"})
P("R11", *R0603, "100R", R100R, 97.6, 88.3, 0, {"1": "LED_DATA_5V", "2": "LED_D0"})
P("MK1", "Sensor_Audio", "InvenSense_ICS-43434-6_3.5x2.65mm", "ICS-43434", "C5656610", G.MIC[0], G.MIC[1] - 0.71, 0,
  {"1": "MIC_WS", "2": "GND", "3": "GND", "4": "MIC_SCK", "5": "+3V3", "6": "MIC_SD"})
P("C12", *C0603, "100n", C100N, 100.0, 99.6, 0, {"1": "+3V3", "2": "GND"})
P("C13", *C0805, "22u", C22U, 40.0, 77.0, 0, {"1": "VLED", "2": "GND"})
P("C14", *C0805, "22u", C22U, 160.0, 77.0, 0, {"1": "VLED", "2": "GND"})

# ---------------------------------------------------------------- expansion / debug pads
for i, net in enumerate(["GND", "+3V3", "UART_TX", "UART_RX", "EXP_IO47", "EXP_IO48"]):
    P(f"TP{i+1}", "TestPoint", "TestPoint_Pad_D1.5mm", net.replace("EXP_", "").replace("UART_", ""), None,
      87.0 + 3.0 * i, 133.6, 0, {"1": net}, no_bom=True)

# ---------------------------------------------------------------- candles: LEDs, caps, hall sensors
chain = G.chain_order()
for i, led in enumerate(chain):
    n = i + 1
    x, y = led["pos"]
    P(f"D{n+100}", MY, "SK6812MINI-E_Rev", "SK6812MINI-E", "C5149201", x, y, 0,
      {"1": "VLED", "2": f"LED_D{n}" if n < len(chain) else None, "3": "GND", "4": f"LED_D{n-1}"},
      candle=led["candle"], kind=led["kind"])
    c = next(c for c in G.candles() if c["id"] == led["candle"])
    if led["kind"] == "body":
        P(f"C{n+100}", *C0603, "100n", C100N, x, y + 3.5, 0, {"1": "VLED", "2": "GND"})
    else:
        P(f"C{n+100}", *C0603, "100n", C100N, x - 4.3, c["top"] + 2.3, 90, {"1": "VLED", "2": "GND"})

for k, c in enumerate(G.candles()):
    hx, hy = c["hall"]
    P(f"U{k+11}", *SOT23, "DRV5032FA", "C140921", hx, hy, 0,
      {"1": "+3V3", "2": f"HALL_{c['id']}", "3": "GND"}, candle=c["id"])
    P(f"C{k+151}", *C0603, "100n", C100N, hx + 4.3, c["top"] + 2.3, 90, {"1": "+3V3", "2": "GND"})

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
