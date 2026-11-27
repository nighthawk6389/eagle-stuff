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

Not read from a datasheet yet (footprint details, needed at layout): Hirose FH12-20S-0.5SH pin 1 position,
JST S2B-PH-SM4-TB pad numbering, KEMET T491B polarity mark, B5819W cathode mark. The PDFs are linked from
the JLCPCB part pages listed in `out/stock-check.md`.

Could not be opened from this environment: TI E2E thread 870302 on ADS1299 power sequencing (the site
refused the request). See OPEN.md, item 2.
