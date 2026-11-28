# Documents the schematic was taken from

Read on 2026-11-27. Pin numbers and passive values in `gen/parts.py` and `gen/design.py`
come from these documents, not from memory.

| What | Document | Used for |
|---|---|---|
| ADS1298 | TI SBAS459K (Jan 2010, rev. Aug 2015), https://www.ti.com/lit/ds/symlink/ads1298.pdf | Pin table p. 10-11 and pinout p. 9; fig. 106 (bypass and reference capacitors); sections 9.3.1.6, 9.3.1.7.6, 9.3.2, 9.4.2, 10.1, 11, 12; table 11 (CLKSEL); fig. 33, 43, 45, 94 (bias amplifier) |
| ADS1298 evaluation board | TI SBAU171D, https://www.ti.com/lit/pdf/sbau171 | Cross-check only: 10k pull-ups on PWDN/RESET/CS, RLDREF left open, three AVDD bypass pairs fitted |
| XIAO nRF52840 schematic | Seeed v1.1 (2022-06-24) and v1.2 (2026-08-28) from https://wiki.seeedstudio.com/XIAO_BLE/ | 5V pin = USB VBUS; BAT pad = BQ25101 output; header pin to nRF port map; charge-current pin P0.13 |
| XIAO symbol and footprint | Seeed `XIAO_Series_SCH_Symbols.zip`, `New_XIAO_Series_Footprints.zip` (same wiki page) | Pad numbers 1-22. `pod/lib/emgpod.pretty/XIAO-nRF52840-SMD.kicad_mod` is Seeed's file, unchanged |
| XIAO bottom pads | Seeed `Bottom-pad-positioning.zip` (coordinate sheet and silkscreen drawing) | Checked all eight bottom pads of Seeed's footprint against the coordinate sheet: they match |
| nRF52840 | Nordic product specification v1.5 (Seeed's copy), table 145 | Which pins are "low frequency I/O only" |
| LP5907 | TI SNVS798Q (rev. Jul 2025), https://www.ti.com/lit/ds/symlink/lp5907.pdf | SOT-23-5 pins, 1 uF in and out, EN thresholds 0.4 / 1.2 V, 1 Mohm EN pull-down, 230 ohm discharge |
| TPD4E001 | TI SLLS682P (rev. Jan 2025), https://www.ti.com/lit/ds/symlink/tpd4e001.pdf | DRL pins, 1 nA leakage, 100 nF at VCC, unused channels open, VCC options (7.2.2) |
| AO3400A | Alpha & Omega datasheet rev. 3 (Dec 2011), via LCSC C20917 | Vgs(th) 0.65-1.45 V, Rds(on) at 2.5 V, lead positions (pin-1 dot is at the gate) |
| Motor LCM1027B3605F | Leader spec leader-3605 (2025-08-20), via LCSC C7528806 | 3.0 V rated, 2.7-3.3 V operating, 70 mA, 120 mA start, wire leads |
| RT9013 | Richtek DS9013-09 | Considered for the analog rail and rejected for the lower-noise LP5907 |

## Footprints checked against the datasheets (2026-11-28)

| Footprint (KiCad 9 library unless noted) | Checked against | Result |
|---|---|---|
| TQFP-64_10x10mm_P0.5mm | SBAS459K package drawing PAG (S-PQFP-G64): 0.5 pitch, 11.8-12.2 across the leads, pin 1 at a corner, counter-clockwise | Fits. TI gives no land pattern for this package; pads are 0.3 x 1.48 at 11.32 centre spacing |
| SOT-563 | SLLS682P land pattern DRL0006A: 0.3 x 0.67 pads, 0.5 pitch, 1.48 between rows | KiCad pads are 0.35 x 0.68 at 1.43; same numbering. Accepted |
| Hirose_FH12-20S-0.5SH | Hirose FH12 catalogue p. 4 and p. 10: contact lands 0.3 x 1.3 at 0.5 pitch, 9.5 over 20 contacts, 15.1 over the mounting lands | Matches (mounting lands 1.8 x 2.2 against 1.5 x 2.2) |
| R_Array_Convex_4x0402 | Uniroyal 4D02 specification: 2.0 x 1.0 body, 0.5 pitch, outer terminals 0.4, inner 0.3 | Matches; resistors join facing terminals 1-8, 2-7, 3-6, 4-5 |
| SOT-23 for AO3400A | AO3400A datasheet drawing: the pin-1 dot is at the gate, source beside it, drain alone | Gate 1, source 2, drain 3 |
| SOT-23-5 for LP5907 | SNVS798Q figure 4-3 | 1 IN, 2 GND, 3 EN, 4 N/C, 5 OUT |
| XIAO-nRF52840-SMD (Seeed's file) | Seeed bottom-pad coordinate sheet | All eight bottom pads match |
| JST_PH_S2B-PH-SM4-TB | Not checked: the PDF on the part page is JST's general PH catalogue and has no SM4 land pattern | Library footprint used as is |
| CP_EIA-3528-21_Kemet-B, D_SOD-123 | Not checked against the KEMET and diode drawings | Pad 1 is positive / cathode by KiCad's convention; confirm in JLCPCB's placement preview |

Strip tail, from the same Hirose page: 0.3 mm thick at the contacts (stiffener), 10.5 mm wide for 20 contacts,
contact pads 0.35 wide at 0.5 pitch, at least 3.5 mm insertion depth. The connector is bottom-contact.

TI E2E thread 870302 (ADS1299 power sequencing): read on 2026-11-28 from a copy of the page the owner
saved. What it says, and what it does not, is in OPEN.md.
