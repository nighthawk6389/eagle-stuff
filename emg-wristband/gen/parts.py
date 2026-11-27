"""Part data: pin tables copied from the datasheets, LCSC numbers, footprints.

Every pin table names the document it was read from. Do not edit a table from memory;
open the document (see ../docs/sources.md) and check.
"""
from kisch import box_symbol, power_symbol

# ---------------------------------------------------------------------------------------
# ADS1298IPAGR, TQFP-64.  TI SBAS459K (Aug 2015), "Pin Functions: TQFP Package", pages 10-11,
# cross-checked against the PAG pinout drawing on page 9.
# (number, name, type used for ERC)
# GPIO1-4 are I/O pins that the datasheet says to short to DGND when unused; they are entered
# as passive so that ERC accepts the short. Firmware must leave them as inputs (the reset state).
ADS1298_PINS = {
    1: ("IN8N", "passive"), 2: ("IN8P", "passive"), 3: ("IN7N", "passive"), 4: ("IN7P", "passive"),
    5: ("IN6N", "passive"), 6: ("IN6P", "passive"), 7: ("IN5N", "passive"), 8: ("IN5P", "passive"),
    9: ("IN4N", "passive"), 10: ("IN4P", "passive"), 11: ("IN3N", "passive"), 12: ("IN3P", "passive"),
    13: ("IN2N", "passive"), 14: ("IN2P", "passive"), 15: ("IN1N", "passive"), 16: ("IN1P", "passive"),
    17: ("TESTP_PACE_OUT1", "passive"), 18: ("TESTN_PACE_OUT2", "passive"),
    19: ("AVDD", "power_in"), 20: ("AVSS", "power_in"), 21: ("AVDD", "power_in"), 22: ("AVDD", "power_in"),
    23: ("AVSS", "power_in"), 24: ("VREFP", "passive"), 25: ("VREFN", "passive"), 26: ("VCAP4", "passive"),
    27: ("NC", "no_connect"), 28: ("VCAP1", "passive"), 29: ("NC", "no_connect"), 30: ("VCAP2", "passive"),
    31: ("RESV1", "input"), 32: ("AVSS", "power_in"), 33: ("DGND", "power_in"), 34: ("DIN", "input"),
    35: ("~{PWDN}", "input"), 36: ("~{RESET}", "input"), 37: ("CLK", "bidirectional"), 38: ("START", "input"),
    39: ("~{CS}", "input"), 40: ("SCLK", "input"), 41: ("DAISY_IN", "input"), 42: ("GPIO1", "passive"),
    43: ("DOUT", "tri_state"), 44: ("GPIO2", "passive"), 45: ("GPIO3", "passive"),
    46: ("GPIO4", "passive"), 47: ("~{DRDY}", "output"), 48: ("DVDD", "power_in"),
    49: ("DGND", "power_in"), 50: ("DVDD", "power_in"), 51: ("DGND", "power_in"), 52: ("CLKSEL", "input"),
    53: ("AVSS1", "power_in"), 54: ("AVDD1", "power_in"), 55: ("VCAP3", "passive"), 56: ("AVDD", "power_in"),
    57: ("AVSS", "power_in"), 58: ("AVSS", "power_in"), 59: ("AVDD", "power_in"), 60: ("RLDREF", "passive"),
    61: ("RLDINV", "passive"), 62: ("RLDIN", "passive"), 63: ("RLDOUT", "passive"), 64: ("WCT", "passive"),
}
assert len(ADS1298_PINS) == 64

# Seeed XIAO nRF52840 as an SMD module. Pad numbers follow Seeed's own KiCad symbol and
# footprint "XIAO-nRF52840-SMD" (XIAO_Series_SCH_Symbols.zip / New_XIAO_Series_Footprints.zip
# from the Seeed wiki). Port names from Seeed's schematic v1.2 (2026-08-28), sheet "XIAO".
# Pads 15-22 are the bottom pads; their positions were checked against Seeed's
# "Bottom Key coordinates" sheet (see ../docs/sources.md).
XIAO_PINS = {
    1: ("D0/P0.02", "bidirectional"), 2: ("D1/P0.03", "bidirectional"), 3: ("D2/P0.28", "bidirectional"),
    4: ("D3/P0.29", "bidirectional"), 5: ("D4/P0.04", "bidirectional"), 6: ("D5/P0.05", "bidirectional"),
    7: ("D6/P1.11", "bidirectional"), 8: ("D7/P1.12", "bidirectional"), 9: ("D8/P1.13", "bidirectional"),
    10: ("D9/P1.14", "bidirectional"), 11: ("D10/P1.15", "bidirectional"), 12: ("3V3", "power_out"),
    13: ("GND", "power_in"), 14: ("5V/VBUS", "passive"), 15: ("SWDIO", "passive"), 16: ("SWCLK", "passive"),
    17: ("~{RESET}", "passive"), 18: ("GND", "passive"), 19: ("BAT+", "passive"), 20: ("BAT-/GND", "passive"),
    21: ("NFC1", "passive"), 22: ("NFC2", "passive"),
}

# LP5907MFX-3.0/NOPB, SOT-23-5 (DBV). TI SNVS798Q (Jul 2025), Table 4-2 and Figure 4-3.
LP5907_PINS = {1: ("IN", "power_in"), 2: ("GND", "power_in"), 3: ("EN", "input"),
               4: ("N/C", "no_connect"), 5: ("OUT", "power_out")}

# TPD4E001DRLR, SOT-563 (DRL). TI SLLS682P (Jan 2025), Figure 4-1 and the Pin Functions table.
TPD4E001_DRL_PINS = {1: ("IO1", "passive"), 2: ("IO2", "passive"), 3: ("GND", "power_in"),
                     4: ("IO3", "passive"), 5: ("IO4", "passive"), 6: ("VCC", "power_in")}

DS = {
    "ADS1298": "https://www.ti.com/lit/ds/symlink/ads1298.pdf",
    "LP5907": "https://www.ti.com/lit/ds/symlink/lp5907.pdf",
    "TPD4E001": "https://www.ti.com/lit/ds/symlink/tpd4e001.pdf",
    "XIAO": "https://wiki.seeedstudio.com/XIAO_BLE/",
}


def _p(table, n):
    return (n, table[n][0], table[n][1])


def build_symbols():
    A = ADS1298_PINS
    left = [_p(A, n) for n in (16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)]
    right = [_p(A, n) for n in (39, 40, 34, 43, 47, 38, 36, 37)] + [None] \
        + [_p(A, n) for n in (35, 52)] + [None] \
        + [_p(A, n) for n in (63, 62, 61, 60, 64)] + [None] \
        + [_p(A, n) for n in (24, 25, 28, 30, 55, 26)]
    # pins that are simply strapped sit with the rail they are strapped to
    top = [_p(A, n) for n in (19, 21, 22, 56, 59, 54, 17, 18)] + [None] + [_p(A, n) for n in (48, 50)]
    bottom = [_p(A, n) for n in (20, 23, 32, 57, 58, 53, 33, 49, 51, 41, 42, 44, 45, 46, 31)] + [None] \
        + [_p(A, n) for n in (27, 29)]
    box_symbol("ADS1298IPAG", "U", left=left, right=right, top=top, bottom=bottom, pitch=5.08, tb_pitch=2.54,
               width=50.8, footprint="Package_QFP:TQFP-64_10x10mm_P0.5mm", datasheet=DS["ADS1298"],
               description="8-channel 24-bit biopotential front end, TQFP-64. Pins from TI SBAS459K.")
    X = XIAO_PINS
    box_symbol("XIAO_nRF52840_SMD", "U",
               left=[_p(X, n) for n in (1, 2, 3, 4, 5, 6, 7)] + [None] + [_p(X, n) for n in (15, 16, 17, 18)],
               right=[_p(X, n) for n in (14, 13, 12, 11, 10, 9, 8)] + [None] + [_p(X, n) for n in (19, 20, 21, 22)],
               width=35.56, pitch=5.08, footprint="emgpod:XIAO-nRF52840-SMD", datasheet=DS["XIAO"],
               description="Seeed XIAO nRF52840 soldered down as a module; pads 15-22 are on its underside.")
    L = LP5907_PINS
    box_symbol("LP5907MFX-3.0", "U", left=[_p(L, 1), None, _p(L, 3)], right=[_p(L, 5), None, _p(L, 4)],
               bottom=[_p(L, 2)], width=15.24, footprint="Package_TO_SOT_SMD:SOT-23-5", datasheet=DS["LP5907"],
               description="3.0 V 250 mA low-noise LDO, SOT-23-5. Pins from TI SNVS798Q.")
    T = TPD4E001_DRL_PINS
    box_symbol("TPD4E001DRL", "U", left=[_p(T, 1), _p(T, 2), _p(T, 4), _p(T, 5)],
               right=[_p(T, 6), None, None, _p(T, 3)], width=12.7, footprint="Package_TO_SOT_SMD:SOT-563",
               datasheet=DS["TPD4E001"],
               description="4-channel low-leakage ESD array, SOT-563. Pins from TI SLLS682P.")
    for rail in ("AVDD", "VBAT"):
        power_symbol(rail)


# ---------------------------------------------------------------------------------------
# Catalogue: key -> (value text, footprint, LCSC, manufacturer part, note)
FP_R0402 = "Resistor_SMD:R_0402_1005Metric"
FP_C0402 = "Capacitor_SMD:C_0402_1005Metric"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"
CAT = {
    "ADS1298": ("ADS1298IPAGR", "Package_QFP:TQFP-64_10x10mm_P0.5mm", "C527440", "ADS1298IPAGR"),
    "XIAO": ("XIAO nRF52840", "emgpod:XIAO-nRF52840-SMD", "C17209540", "Seeed 102010448"),
    "LDO": ("LP5907MFX-3.0", "Package_TO_SOT_SMD:SOT-23-5", "C475492", "LP5907MFX-3.0/NOPB"),
    "ESD": ("TPD4E001DRL", "Package_TO_SOT_SMD:SOT-563", "C527516", "TPD4E001DRLR"),
    "NFET": ("AO3400A", "Package_TO_SOT_SMD:SOT-23", "C20917", "AO3400A"),
    "SCHOTTKY": ("B5819W", "Diode_SMD:D_SOD-123", "C8598", "B5819W SL"),
    "FPC20": ("FH12-20S-0.5SH", "Connector_FFC-FPC:Hirose_FH12-20S-0.5SH_1x20-1MP_P0.50mm_Horizontal",
              "C596730", "FH12-20S-0.5SH(55)"),
    "JST_PH2": ("S2B-PH-SM4-TB", "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
                "C295747", "S2B-PH-SM4-TB(LF)(SN)"),
    "TANT22U": ("22u", "Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-B", "C117031", "T491B226M010AT"),
    "R0": ("0R", FP_R0402, "C17168", "0402WGF0000TCE"),
    "R33": ("33R", FP_R0402, "C25105", "0402WGF330JTCE"),
    "R10K": ("10k", FP_R0402, "C25744", "0402WGF1002TCE"),
    "R22K": ("22k", FP_R0402, "C25768", "0402WGF2202TCE"),
    "R100K": ("100k", FP_R0402, "C25741", "0402WGF1003TCE"),
    "R1M": ("1M", FP_R0402, "C26083", "0402WGF1004TCE"),
    "R12_0805": ("12R", "Resistor_SMD:R_0805_2012Metric", "C17445", "0805W8F120JT5E"),
    "C47P": ("47p", FP_C0402, "C1567", "0402CG470J500NT"),
    "C1N": ("1n", FP_C0402, "C1523", "0402B102K500NT"),
    "C1N5": ("1n5", FP_C0603, "C1595", "0603B152K500NT"),
    "C100N": ("100n", FP_C0402, "C1525", "CL05B104KO5NNNC"),
    "C1U": ("1u", FP_C0402, "C52923", "CL05A105KA5NQNC"),
    "C10U": ("10u", FP_C0603, "C19702", "CL10A106KP8NNNC"),
}
SYMBOL_FOR = {"R": "Device:R", "C": "Device:C", "TANT22U": "Device:C_Polarized"}
