# PCB Menorah v1 — project context for Claude Code

Owner: Yaish (GitHub `nighthawk6389`). Goal: a menorah-shaped PCB that behaves like a real menorah,
designed with Claude, assembled by JLCPCB, in hand for the first night of Hanukkah.

## 0. Deadline and status

- **Hanukkah 5787 starts at sundown Fri 2026-12-04.** First candle is lit before sundown (Shabbat); night 2 is lit after Shabbat ends.
- JLCPCB build + DHL is roughly 7–10 days, so **the order has to go in by about Tue 2026-11-24 (Wed at the latest)**.
- Status at handoff (Sat 2026-11-21 evening):
  - DONE: concept, outline geometry, part selection, netlist-as-code, footprint for the reverse-mount LED, unrouted board with all 157 footprints placed and nets assigned, keep-outs, project rules/net classes.
  - NOT DONE: placement fixes (section 9), routing, copper pours, front artwork (gold flames, rings, border, Hebrew lettering), DRC, Gerbers/BOM/CPL, foot board, shamash wand, firmware.
  - There is **no `.kicad_sch`**. The schematic exists only as `netlist.py`. Nothing has been routed or DRC-checked beyond a placement-only run.

## 1. What it is (architecture goals)

- The **board is the menorah**: black solder mask, ENIG gold, about 196 x 150 mm, 2-layer, 1.6 mm. No enclosure.
- **All parts on the back**, single-sided assembly. The front is clean: gold flames, gold rings, LED windows.
- 9 candles (8 + taller centre shamash). Each candle is a column of addressable LEDs that "burns down"; the top LED sits in a gold flame shape and flickers.
- **Light it by hand**: a hall-effect sensor sits behind a gold ring at the top of every candle. Touch a magnet "shamash wand" to the ring to light that candle (shamash first, then newest candle first, left to right).
- **Knows the night**: firmware gets time over Wi-Fi (NTP), computes the Hebrew date and local sunset, and allows the right number of candles (including the Friday-before-sundown and Saturday-after-nightfall cases).
- **Blow out**: an I2S MEMS mic behind a small hole in the stem detects blowing.
- **Family sync** (firmware only, later): two boards mirror each other over Wi-Fi.
- USB-C power, optional LiPo with charging. ESP32-S3 flashes over its native USB.
- It is a display piece next to a real menorah (an electric menorah generally does not fulfil the mitzvah).

## 2. Mechanical (front view, mm, origin top-left, +y down) — `geometry.py` is the source of truth

| Feature | Value |
|---|---|
| Bounding box | x 2–198, y 2.8–152 |
| Candle centres | x = 9, 31, 53, 75 (C1–C4), 125, 147, 169, 191 (C5–C8); shamash SH at x = 100 |
| Candle body | 12 mm wide (shamash 14), top at y = 38 (shamash 24), down to the crossbar |
| Crossbar | y 70–84, rounded ends |
| Stem | x 88–112, y 84–118 |
| Base | x 45–155, y 118–152 |
| Flame | teardrop, bulb radius 5, on a 5.5 x 4 mm neck (neck carries 4 back-side traces) |
| LEDs | body LEDs every 7 mm, bottom at y = 67 (4 per candle, 6 on shamash) + 1 flame LED each = **47** |
| Hall sensor | centred on the candle, 2 mm below the candle top |
| Foot slots | x = 55 and 145, 1.75 wide, 15.5 deep from the bottom edge (half-lap with 1.6 mm foot boards) |
| Mic port | (100, 96) |
| Hebrew lettering block | x 62–138, y 139.5–149.5: "נס גדול היה שם" |
| USB-C | **left edge of the base** (front view), plug enters sideways at y = 131 |
| Battery area (back) | x 108–144, y 120–151; JST plug needs ~6 mm of that, so label says max 32 x 30 mm |

Night N lights the N right-most candles as seen from the front (C(9-N)..C8).

## 3. Electrical architecture

```
USB-C VBUS --+-- D1 SS34 --> VSYS --+-- U3 AP2112K-3.3 --> +3V3 (ESP32, 9 hall sensors, mic)
             |                      +-- Q2 AO3401A (high side) --> VLED (47 LEDs, U4)
             +-- U2 TP4057 --> VBAT        ^ gate: R8 100k pull-up + C9 100n to VSYS,
             +-- gate of Q1                  R9 10k to Q3 2N7002 drain, Q3 gate = VLED_EN (R10 100k pulldown)
VBAT (J2 JST-PH) -- Q1 AO3401A (D=VBAT, S=VSYS, G=VBUS, R5 10k G->GND) --> VSYS when USB is absent
```

- **VLED is switched** so the LEDs (about 1 mA each idle) draw nothing in sleep. Default off.
- **Level shifter U4 SN74LV1T34** (powered from VLED) between ESP32 3.3 V data and the first LED, plus R11 100 Ω series. Needed because on USB VLED is about 4.6–4.9 V and SK6812 VIH is about 0.7 x VDD.
- On battery VLED is 3.0–4.2 V; SK6812MINI-E is specified from 3.7 V, so blue/white dim on a low battery. Accepted.
- R5 is 10 k (not 100 k) so D1 reverse leakage cannot hold Q1's gate high.
- R4 = 3.3 k sets charge current to roughly 250–400 mA (TP4057 clones disagree on the formula; all are safe for cells of 500 mAh and up).
- VBAT sense: R6/R7 100 k/100 k + C8 100 n into ADC (IO9).
- TP4057 CHRG (open drain) goes to IO10; use the internal pull-up. STDBY unconnected.
- USB: CC1/CC2 5.1 k to GND, USBLC6-2SC6 ESD on D+/D-, D+ = IO20, D- = IO19.
- EN: R1 10 k pull-up, C2 1 µF, SW2 to GND. BOOT: SW1 on IO0.
- Mic ICS-43434 (I2S): LR tied to GND (left channel).
- Hall sensors DRV5032FA: push-pull, omnipolar, output LOW when a magnet is present, 100 n each.
- Each LED has a 100 n cap; 22 µF VLED bulk at Q2 and at both ends of the crossbar.
- Firmware must cap LED brightness: 47 LEDs at full white is about 1.7 A.

## 4. Pinout (ESP32-S3-WROOM-1, module pad numbers in brackets)

| Signal | GPIO | Notes |
|---|---|---|
| HALL_SH | IO4 [4] | RTC-capable, wake source |
| HALL_C8 / C7 / C6 / C5 | IO5 [5] / IO6 [6] / IO7 [7] / IO15 [8] | |
| HALL_C4 / C3 / C2 / C1 | IO16 [9] / IO17 [10] / IO18 [11] / IO8 [12] | all halls are RTC GPIOs |
| USB D- / D+ | IO19 [13] / IO20 [14] | native USB |
| VBAT_SENSE | IO9 [17] | ADC1 |
| CHRG_N | IO10 [18] | input, pull-up |
| VLED_EN | IO11 [19] | high = LEDs powered |
| MIC_SD / MIC_WS / MIC_SCK | IO12 [20] / IO13 [21] / IO14 [22] | I2S |
| LED_DATA | IO21 [23] | to U4, then LED chain |
| Spare (test pads) | IO47 [24], IO48 [25] | TP5, TP6 |
| BOOT | IO0 [27] | SW1 |
| UART RX / TX | RXD0 [36] / TXD0 [37] | TP4, TP3 |
| Unused, leave alone | IO3, IO45, IO46 (strapping), IO35–37 (PSRAM on R8 modules) | |

Test pads (back): TP1 GND, TP2 3V3, TP3 TX, TP4 RX, TP5 IO47, TP6 IO48.

**LED chain order** (index 0 first): SH, C5, C6, C7, C8, C4, C3, C2, C1. Inside each candle: body LEDs bottom to top, flame LED last. SH has 7 LEDs, others 5. Refs D101..D147 follow chain order. `geometry.chain_order()` is authoritative.

## 5. BOM (LCSC / JLCPCB part numbers)

| Ref | Part | LCSC | Package | Notes |
|---|---|---|---|---|
| U1 | ESP32-S3-WROOM-1-N8R8 | C2913201 | module | N8 (C2913198) or N16R8 (C2913202) also fit |
| D101–D147 | SK6812MINI-E | C5149201 | reverse-mount | "Standard only", custom footprint |
| U11–U19 | DRV5032FADBZR | C140921 | SOT-23 | 1 VCC, 2 OUT, 3 GND |
| MK1 | ICS-43434 | C5656610 | LGA-6 | bottom port; last-time-buy at DigiKey, stock risk |
| U2 | TP4057 | C12044 | SOT-23-6 | 1 CHRG, 2 GND, 3 BAT, 4 VCC, 5 STDBY, 6 PROG |
| U3 | AP2112K-3.3TRG1 | C51118 | SOT-23-5 | |
| U4 | SN74LV1T34DBVR | C100024 | SOT-23-5 | 2 A, 3 GND, 4 Y, 5 VCC |
| U5 | USBLC6-2SC6 | C7519 | SOT-23-6 | |
| Q1, Q2 | AO3401A | C15127 | SOT-23 | 1 G, 2 S, 3 D |
| Q3 | 2N7002 | C8545 | SOT-23 | |
| D1 | SS34 | C8678 | SMA | pad 1 = cathode = VSYS |
| J1 | TYPE-C-31-M-12 | C165948 | USB-C 16P | |
| J2 | S2B-PH-SM4-TB | C295747 | JST-PH 2P | pad 1 = VBAT, pad 2 = GND |
| SW1, SW2 | TS-1187A-B-A-B | C318884 | 5.1 mm tact | |
| 100 n 0603 | | C14663 | | x61 |
| 1 µ 0603 | | C15849 | | C2, C4 |
| 10 µ 0805 | | C15850 | | C3, C5 |
| 22 µ 0805 | | C45783 | | C6, C7, C10, C13, C14 |
| 10 k / 100 k / 5.1 k / 3.3 k / 100 Ω 0603 | | C25804 / C25803 / C23186 / C22978 / C22775 | | |

**Verification status — be honest about this:**
- Pinouts checked against datasheets/KiCad symbols: DRV5032, TP4057, SN74LV1T34, ESP32 module, ICS-43434, SK6812MINI-E (pin names).
- LED footprint: geometry copied from `ebastler/marbastlib` `LED_6028R`, cross-checked against Keebio's `SK6812-MINI-E` (same pad arrangement after a 180° turn). Pads renumbered to the datasheet (1 VDD, 2 DOUT, 3 GND, 4 DIN).
- **JLCPCB stock was NOT confirmed for any part** (the part pages did not expose stock). Only the ESP32 N8R8 showed "In Stock: 9884" in a search snippet of unknown date. Passive and discrete LCSC numbers are from memory. **Confirm every line in JLCPCB's BOM-matching screen.**
- JST-PH battery polarity differs between vendors. The board is silk-labelled; the battery must be checked before plugging in.

## 6. Design rules

- 2-layer, 1.6 mm, black mask, ENIG. Min drill 0.3 mm (JLCPCB 2-layer limit), via 0.7/0.3.
- Net classes (in `out/menorah.kicad_pro`): Default 0.2 mm track / 0.2 mm clearance; Power 0.5 mm for GND, +3V3, VBUS, VSYS, VBAT, VLED.
- Copper-to-edge 0.25 mm, min clearance 0.15, min track 0.15.
- Front copper: GND pour everywhere. **No tracks or vias on F.Cu** under flames + necks, hall rings (r 3.3), mic ring, lettering block (rule areas already in the board). Gold artwork = F.Mask openings over that GND pour.
- Antenna: no copper on either layer in x 55–85, y 117–124.6, plus the keep-out built into the module footprint.
- The module footprint's 0.2 mm thermal vias are deleted (below drill minimum).
- JLCPCB: reverse-mount LEDs and ESP32 modules are "Standard only", so this is **Standard PCBA, single-sided** (about $25.56 setup + $8.21 stencil), not Economic. Ask JLCPCB to add edge rails/fiducials for the irregular outline.

## 7. Files and toolchain

```
geometry.py   outline, candle/LED/hall positions, chain order (single source of truth)
netlist.py    every part: footprint, LCSC, position, rotation, pad->net map (this is the schematic)
build.py      builds out/menorah.kicad_pcb + .kicad_pro (outline, footprints, nets, keep-outs)
render.py     kicad-cli SVG export -> PNG:  python3 render.py out/menorah.kicad_pcb name LAYERS x 2000
menorah.pretty/SK6812MINI-E_Rev.kicad_mod   reverse-mount LED footprint (KiCad 7 syntax)
out/          generated board, project, renders, DRC report
```

- Built with **KiCad 7.0.11** Python (`pcbnew`), run as `/usr/bin/python3 build.py`. Footprint libraries expected at `/usr/share/kicad/footprints/` (constant `KL` in `netlist.py`).
- KiCad 7 has no `kicad-cli pcb drc`; DRC is `pcbnew.WriteDRCReport(board, path, pcbnew.EDA_UNITS_MILLIMETRES, True)`. **If Claude Code has KiCad 8 or 9, expect small API changes** (footprint fields instead of `SetProperty`, `kicad-cli pcb drc` available) and re-check that the hand-written footprint loads.
- `LoadBoard` must run in a fresh process to pick up `.kicad_pro` rules (same-process reload returned defaults).
- Planned router: Freerouting 2.1.0 (`java -jar freerouting-2.1.0.jar -de in.dsn -do out.ses`), via `pcbnew.ExportSpecctraDSN` / `ImportSpecctraSES`. **Not yet run.**
- All footprints are flipped to the back with `fp.Flip(pos, True)`; coordinates stay front-view.

## 8. Decisions made, and corrections to earlier statements

- Size back to about 20 cm wide (30/40 cm considered and dropped).
- USB-C is on the **side** of the base, not the bottom edge (the bottom sits on the table).
- The shamash is a **fixed LED column** on the board. The thing you hold is a separate magnet wand.
- Mic changed from analog to **digital I2S** (no amplifier, no analog noise problem).
- Candles widened to 12 mm so the back has room for power, data-return and hall traces.
- Cost: earlier estimate of $150–200 for 2 assembled boards assumed Economic assembly. With Standard assembly and about 10 extended part types, expect it higher; **get the real number from the JLCPCB quote** (35% US tariff applies to the goods value).
- No buzzer in v1 (no trusted footprint); spare GPIOs are on test pads instead.

## 9. Exact next steps

1. **Fix placement errors from the placement-only DRC** (`out/drc0.rpt`): U3, C7, Q2 (y≈122) and C3 (50, 124.2) sit inside the ESP32 module's built-in antenna keep-out (it extends about 15 mm either side of the module above y≈124.5). Move the top row of the power section (U3, C6, C7, Q2, Q3, C10 and their passives) down by about 4 mm and move C3 below y = 126. Re-run `build.py` until `courtyards_overlap` and `items_not_allowed` are zero. (`lib_footprint_issues` and `unconnected_items` are expected at this stage.)
2. Add silk "+" at J2 pad 1 and "−" at pad 2; add "BOOT"/"RESET" labels.
3. **Route**: export DSN, run Freerouting on all nets including GND, import SES. Check that no F.Cu track crosses the rule areas and that Power nets came out 0.5 mm.
4. **Pours**: GND zone on F.Cu and B.Cu, fill, confirm zero unconnected items.
5. **Front artwork** (F.Mask openings over the F.Cu GND pour): flame teardrops; ring (r≈3, 0.6 wide) at each hall position; ring at the mic hole; 0.5 mm border line 0.6 mm inside the outline (skip any segment within 0.45 mm of non-GND F.Cu copper); Hebrew lettering as polygons from a font with Hebrew glyphs (Cardo, FreeSerif or DejaVu Sans are installed here), laid out right to left.
6. **Full DRC** to zero errors; render front and back and look at them.
7. **Independent review before ordering**: re-check every IC pinout in `netlist.py` against its datasheet, the LED footprint orientation against the OPSCO datasheet drawing, USB connector edge overhang (0.45 mm), and JST opening direction (should face +x toward the battery area).
8. **Fab outputs**: Gerbers + drill, JLCPCB BOM CSV (Comment, Designator, Footprint, LCSC), CPL CSV (back side; check rotations in JLCPCB's placement preview, especially the 47 LEDs, U1, J1, MK1).
9. **Foot board** (separate bare-PCB order, 5 pcs, use 2): about 80 x 25 mm, 1.6 mm, slot 1.75 wide x 10 deep from the top so the half-lap sits flush. **Wand** (optional third bare design): small candle-shaped PCB with a 5 mm hole for a glued 5 x 2 mm magnet.
10. Upload to JLCPCB, confirm stock per line, swap or drop anything missing (the mic is optional: the board works without it), order with DHL Express DDP.
11. Push the project to a GitHub repo under `nighthawk6389` (user asked for GitHub integration; no repo exists yet).
12. **Firmware** (ESP-IDF or Arduino, after ordering): LED driver on IO21 with brightness cap, VLED_EN sequencing, hall scan + wake, flame flicker and burn-down, Hebrew calendar + sunset, NTP, Wi-Fi provisioning, OTA updates, I2S blow detection, battery/charge readout.

## 10. Things the user needs to buy or decide

- Small neodymium disc magnets, 5 x 2 or 6 x 2 mm (bigger ones risk triggering the neighbouring candle, 22 mm away).
- Optional LiPo, single cell with protection, JST-PH, up to about 32 x 30 mm (around 500 mAh gives 2–3 hours of light).
- Location for sunset calculation: Bergen County, NJ.

## 11. Other threads from the same conversation (parked)

- Started from `nighthawk6389/eagle-stuff` (2018 Eagle boards: CSR8635/CSR8645 Bluetooth audio, CSR1010 cadence sensor, Si4356/MRF39 sub-GHz breakouts, FT232, ATmega328 boards; all 2-layer).
- **Spectra 6 e-ink driver board** (chosen as the "hard" project, then set aside for the menorah): 13.3" Good Display GDEP133C02 / Waveshare 13.3" e-Paper (E), 1600 x 1200, 60-pin 0.5 mm FPC, two driver ICs (CS_M / CS_S), external MOSFET/charge-pump parts needed. Plan: phase 1 = ESP32-S3 controller board plugging into Waveshare's driver HAT (10 signals: VCC, GND, DIN, CLK, CS_M, CS_S, DC, RST, BUSY, PWR), server-side dithering, pull-over-Wi-Fi on a timer; phase 2 = integrate the HAT's power section on a 4-layer board. Buy the HAT version as a known-good reference.
