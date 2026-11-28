# Documents the schematic and the board were taken from

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

## JLCPCB limits the board was sized against (read 2026-11-28)

From jlcpcb.com/capabilities/pcb-capabilities, multilayer boards, 1 oz outer copper. The right-hand
column is what `gen/board.py` uses.

| Limit on the page | This board |
|---|---|
| Track and spacing 0.09 / 0.09 mm | Tracks 0.127 mm and up, clearance 0.127 mm |
| Via hole 0.15 mm minimum, diameter at least 0.1 mm larger; holes of 0.25 mm or less cost more below 0.45 mm diameter | One via size: 0.3 mm hole, 0.5 mm diameter |
| Via hole to track 0.2 mm; via hole to via hole 0.2 mm | 0.2 mm and 0.25 mm set as rules |
| Plated pad hole to track 0.28 mm (0.35 mm recommended); pad annular ring 0.2 mm | Only the two motor wire pads (0.7 mm hole, 1.7 mm pad, measured on the board): ring 0.5 mm, so tracks stay 0.63 mm from the hole |
| Copper to a routed board edge 0.2 mm | 0.3 mm |
| SMD pad to pad, different nets, 0.15 mm; pad to track 0.1 mm | Closest pads are the ESD arrays' at 0.15 mm (library footprint); pad to track 0.127 mm |
| Inner layer: via hole to copper 0.2 mm | Planes keep 0.15 mm from the via pad, 0.25 mm from the hole (0.2 mm from the pad merged the clearances of neighbouring vias into slots) |
| Silkscreen: 1.0 mm text height, 0.15 mm line (the reviewer's reading; JLCPCB's ordering notes say the same) | All text 1.0 mm or 1.5 mm high, strokes 0.15 mm or more |
| Same-net track spacing 0.25 mm | **Not checked.** KiCad has no rule for it and the autorouted tracks were not inspected for it |

The page states no default via covering for 4-layer boards. The Gerbers have no solder-mask openings
on vias (tented), which matters under the strip connectors: see OPEN.md.

From jlcpcb.com/capabilities/pcb-assembly-capabilities: Economic assembly takes single boards from
10 x 10 mm, single-sided, rails and fiducials "Not necessary"; Standard takes 70 x 70 mm to
460 x 500 mm, single or double sided, rails and fiducials "Necessary". Finest IC pin spacing 0.4 mm
(Economic) and 0.35 mm (Standard); the board's finest is 0.5 mm.

### What the assembly frame was drawn to (read 2026-11-28)

Read through a page-fetching helper from JLCPCB's capability and help pages on panels, edge rails,
fiducials and tooling holes; I did not see the pages myself, and they describe panels of several
boards. The right-hand column is what `gen/panel.py` draws.

| On JLCPCB's pages | The frame |
|---|---|
| Standard assembly: 70 x 70 mm minimum; edge rails and fiducials "Necessary" | 74 x 74 mm, rails on all four sides |
| Edge rails at least 5 mm | 10 mm and 10.5 mm |
| Fiducials: 1 mm copper, 2 mm mask opening, three or four, centred 3.85 mm from the panel edges | Three, as described, not symmetric |
| Tooling holes for assembly: 2 mm | Four, unplated, centred 3.85 mm from the edges |
| Board spacing in a panel 1.6 or 2 mm | Slot 2 mm (3 mm on the USB side) |
| Break-off tabs at least 5 mm wide with perforations; holes 0.5 to 0.8 mm, 0.2 to 0.3 mm between them | Tabs 5 mm; six 0.5 mm holes per tab, 0.3 mm between them |
| Smallest unplated hole 0.5 mm; unplated hole to track 0.2 mm | Holes touch the pod's edge from outside; the pod's copper is 0.3 mm inside it |
| Ordering notes (jlcpcb.com/help/article/instructions-for-ordering, updated 2026-11-10): outline, slots and cut-outs drawn 0.15 mm wide on the outline layer; "Panel by Customer" takes up to 10 designs, a customer-panelised "Single PCB" up to 5; boards of 50 x 50 mm or less are hard to mill and panelising is recommended; silkscreen text at least 1 mm high with 0.15 mm lines | Outline 0.15 mm wide; one design; text 1.0 mm |

Not found on any page read: how one board in a customer-drawn frame is classified on the order form,
and where the order number is printed.

Motor resistor R5: C17913, UNI-ROYAL 1206W4F120JT5E, 12 ohm 1 %, 250 mW, as listed in the public
JLCPCB parts index at jlcsearch.tscircuit.com (read 2026-11-28); stock and assembly type from the
part page (`out/stock-check.md`).

## Other layout notes

- Hirose FH12 catalogue p. 10 (land drawing for the 0.5 mm bottom-contact type): shows the contact and
  mounting lands only, with no area marked as closed to copper under the body. The tap tracks and
  vias of the electrode lines run there.
- The XIAO footprint on the board is `XIAO-nRF52840-SMD-pod`: Seeed's file without pads 21 and 22 (the
  two NFC pads, unconnected here), without pad 7 (D6, which would lie in the notch) and without its
  silkscreen outline. The other 19 pads are untouched. Seeed's unchanged file is kept beside it.
- Where things are on the XIAO, from Seeed's v1.2 board file (a KiCad 10 file, read as text because
  KiCad 9 cannot open it), moved by (-110.03, -95.114) mm into this board's coordinates: chip antenna
  ANT1 (AN3216, 3.2 x 1.6 mm) centred at (29.07, 8.09); NFC pads 2.0 x 1.0 mm at (29.26, 13.70) and
  (29.26, 15.61); USB shell legs, plated slots of about 1.8 x 0.9 mm, at (47.86, 5.59), (47.86, 14.19),
  (43.66, 5.59) and (43.66, 14.19). The notch and the keep-outs in `gen/board.py` come from these.
  **Not yet in the keep-outs** (found by the second review, confirmed in the same file): two milled
  slots of 1.27 x 0.51 mm in the module's board at (33.07 to 34.34, 3.41 to 3.92) and (33.07 to
  34.34, 15.86 to 16.37), taken to be for the shield can's tabs, and the USB socket's two unplated
  0.6 mm peg holes at (44.21, 7.00) and (44.21, 12.78). The socket's drawing reaches x = 50.46.
- `TestPoint_Pad_D1.0mm_bare` in the project library is KiCad's `TestPoint_Pad_D1.0mm` without its
  silkscreen ring, so the net labels fit between the pads.
- Freerouting 2.1.0 (github.com/freerouting/freerouting) did the autorouted part of the board.
