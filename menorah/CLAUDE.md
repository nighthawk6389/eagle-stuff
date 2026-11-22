# PCB Menorah v1 — project context for Claude Code

Owner: Yaish (GitHub `nighthawk6389`). Goal: a menorah-shaped PCB that behaves like a real menorah,
designed with Claude, assembled by JLCPCB, in hand for the first night of Hanukkah.

## 0. Deadline and status

- **Hanukkah 5787 starts at sundown Fri 2026-12-04.** First candle is lit before sundown (Shabbat); night 2 is lit after Shabbat ends.
- JLCPCB build + DHL is roughly 7–10 days, so **the order has to go in by about Tue 2026-11-24 (Wed at the latest)**.
- Status after the Claude Code session (Sun 2026-11-22):
  - DONE: placement, **full routing**, GND pours on both layers, front gold artwork (flames, hall rings, mic ring,
    border, Hebrew lettering), back silk labels, **DRC with 0 errors / 0 unconnected** (`out/drc_final.rpt`; the only
    remaining entries are 157 harmless "footprint has no library link" warnings), Gerbers + drill, JLCPCB BOM and CPL,
    foot board and wand outlines with Gerbers.
  - NOT DONE: JLCPCB upload / stock check / placement-preview check (needs a human), firmware.
  - There is still **no `.kicad_sch`**. The schematic exists only as `netlist.py`; the board is generated from code.
  - Things that changed from the handoff design are listed in section 8a. **The pin map changed** (section 4).

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
| Battery area (back) | x 108–144, y 120–151 (no parts; tracks only). Usable for a cell up to about **30 x 30 mm** |
| Battery connector J2 | **right end of the base** at (149.7, 129), mouth facing the battery area; + is the lower pin (silk "+" / "-") |
| Buttons (back) | right end of the base: RESET (150.5, 140.2), BOOT (150.5, 146.4) |

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
- **Level shifter U4 SN74LV1T34** (powered from VLED) between ESP32 3.3 V data and the first LED, plus R11 100 Ω series. U4/R11/C11 sit at the **left end of the crossbar under C1**, because the chain now starts at C1. Needed because on USB VLED is about 4.6–4.9 V and SK6812 VIH is about 0.7 x VDD.
- On battery VLED is 3.0–4.2 V; SK6812MINI-E is specified from 3.7 V, so blue/white dim on a low battery. Accepted.
- R5 is 10 k (not 100 k) so D1 reverse leakage cannot hold Q1's gate high.
- R4 = 3.3 k sets charge current to roughly 250–400 mA (TP4057 clones disagree on the formula; all are safe for cells of 500 mAh and up).
- VBAT sense: R6/R7 100 k/100 k + C8 100 n into ADC (IO8).
- TP4057 CHRG (open drain) goes to IO18; use the internal pull-up. STDBY unconnected.
- USB: CC1/CC2 5.1 k to GND, USBLC6-2SC6 ESD on D+/D-, D+ = IO20, D- = IO19.
- EN: R1 10 k pull-up, C2 1 µF, SW2 to GND. BOOT: SW1 on IO0.
- Mic ICS-43434 (I2S): LR tied to GND (left channel).
- Hall sensors DRV5032FA: push-pull, omnipolar, output LOW when a magnet is present, 100 n each.
- Each LED has a 100 n cap; 22 µF VLED bulk at Q2 and at both ends of the crossbar.
- Firmware must cap LED brightness: 47 LEDs at full white is about 1.7 A.

## 4. Pinout (ESP32-S3-WROOM-1, module pad numbers in brackets) — `netlist.py` is authoritative

The pin map was re-done during routing so that every bundle reaches the module without crossings.

| Signal | GPIO | Notes |
|---|---|---|
| HALL_C1 / C2 | IO4 [4] / IO5 [5] | |
| LED_DATA | IO6 [6] | to U4 (under C1), then the LED chain |
| MIC_SCK / MIC_WS / MIC_SD | IO7 [7] / IO15 [8] / IO16 [9] | I2S |
| VLED_EN | IO17 [10] | high = LEDs powered |
| CHRG_N | IO18 [11] | input, pull-up |
| VBAT_SENSE | IO8 [12] | ADC1_CH7 |
| USB D- / D+ | IO19 [13] / IO20 [14] | native USB |
| HALL_SH | IO9 [17] | wake source |
| HALL_C5 / C6 / C7 / C8 | IO10 [18] / IO11 [19] / IO12 [20] / IO13 [21] | |
| HALL_C3 / C4 | IO14 [22] / IO21 [23] | all nine halls are RTC GPIOs (0–21), any can wake the board |
| Spare (test pads) | IO47 [24], IO48 [25] | TP5, TP6 (below the module) |
| BOOT | IO0 [27] | SW1 |
| UART RX / TX | RXD0 [36] / TXD0 [37] | TP4, TP3 (left of the module) |
| Unused, leave alone | IO3, IO45, IO46 (strapping), IO35–37 (PSRAM on R8 modules) | |

Test pads (back, labelled by signal name): GND, 3V3 (power section), TX, RX (left of the module), IO47, IO48 (below it).

**LED chain order** (index 0 first): **C1, C2, C3, C4, SH, C5, C6, C7, C8** — plain left to right as seen from the
front. Inside each candle: body LEDs bottom to top, flame LED last. SH has 7 LEDs, others 5, so the indices are
C1 0–4, C2 5–9, C3 10–14, C4 15–19, SH 20–26, C5 27–31, C6 32–36, C7 37–41, C8 42–46.
Refs D101..D147 follow chain order. `geometry.chain_order()` is authoritative.

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
- Re-checked in the Claude Code session: the LED footprint pad arrangement against marbastlib's `LED_6028R` plus its
  symbol (1 VDD, 2 DOUT, 3 DIN, 4 VSS there; ours renumbers 3/4 to the datasheet), and the IC pinouts in `netlist.py`
  against memory of the datasheets (DRV5032, TP4057, AP2112K, SN74LV1T34, USBLC6-2, AO3401A, 2N7002, ICS-43434,
  ESP32-S3-WROOM-1). No datasheet PDFs were opened in that session, so this is a second look, not proof.
- CC resistors: R2 is on CC2 (pad B5) and R3 on CC1 (pad A5) — swapped from the handoff so the two lines do not cross.
- JST-PH battery polarity differs between vendors. The board is silk-labelled; the battery must be checked before plugging in.

## 6. Design rules

- 2-layer, 1.6 mm, black mask, ENIG. Min drill 0.3 mm (JLCPCB 2-layer limit), via 0.7/0.3.
- Net classes (in `out/menorah.kicad_pro`): Default 0.2 mm track / 0.2 mm clearance; Power 0.5 mm for GND, +3V3, VBUS, VSYS, VBAT, VLED.
- Copper-to-edge 0.25 mm, min clearance 0.15, min track 0.15.
- Front copper: GND pour everywhere. **No tracks or vias on F.Cu** under flames + necks, hall rings (r 3.3), mic ring,
  lettering block (rule areas in the board). Gold artwork = F.Mask openings over that GND pour. The front carries only
  short "hops" in the crossbar, two hall lines in the stem, and wiring in the base (641 mm of track in total).
- Antenna: no copper on either layer in x 55–85, y 117–124.6, plus the keep-out built into the module footprint
  (x 46–94, y 103–124). **Visible consequence:** the front has no copper (so no gold border, and bare laminate under the
  mask) on the base's top-left edge and the left 6 mm of the stem between y 103 and 124.
- The module footprint's 0.2 mm thermal vias are deleted (below drill minimum).
- All vias are 0.7/0.3 and tented. New vias are kept 2 mm from the board edge so the border line stays unbroken
  (exception: two vias at the foot of C8, where the border has a short gap).
- JLCPCB: reverse-mount LEDs and ESP32 modules are "Standard only", so this is **Standard PCBA, single-sided** (about $25.56 setup + $8.21 stencil), not Economic. Ask JLCPCB to add edge rails/fiducials for the irregular outline.

## 7. Files and toolchain

```
geometry.py    outline, candle/LED/hall positions, chain order (single source of truth)
netlist.py     every part: footprint, LCSC, position, rotation, pad->net map (this is the schematic)
build.py       out/menorah.kicad_pcb + .kicad_pro: outline, footprints, nets, keep-outs (unrouted)
route_plan.py  hand-planned routing of candles, crossbar, stem and the main buses in the base (coordinates in code)
maze.py        small grid router (Dijkstra on a 0.05 mm grid) for the remaining ~60 connections in the base + GND vias
route.py       route_plan + maze -> out/menorah_routed.kicad_pcb   (--reuse re-applies out/maze_result.json, --plan-only skips maze)
finish.py      GND pours, front artwork, silk labels -> out/menorah_final.kicad_pcb   <- THE BOARD
drc.py         DRC in a fresh process:  drc.py out/menorah_final.kicad_pcb out/drc_final.rpt
fab.py         out/fab/: Gerbers + drill (zip), bom_jlc.csv, cpl_jlc.csv
extras.py      out/extras/: foot board and magnet wand (bare boards) with Gerber zips
render.py      kicad-cli SVG -> PNG:  render.py out/board.kicad_pcb name LAYERS x 2400 [x0 y0 x1 y1 crop]
menorah.pretty/SK6812MINI-E_Rev.kicad_mod   reverse-mount LED footprint (KiCad 7 syntax)
```

Full rebuild: `build.py && route.py && finish.py && drc.py ... && fab.py` (route.py takes about 2 minutes; use
`route.py --reuse` if only finish.py changed).

- **KiCad 7.0.11** from Ubuntu 24.04 (`apt install kicad kicad-footprints`), run with **`/usr/bin/python3.12`**
  (the `pcbnew` module is built for 3.12; plain `python3` may be a different version). Also needs
  `python3-shapely python3-scipy python3-skimage python3-cairosvg python3-fonttools` and the FreeSerif font
  (`fonts-freefont-ttf`) for the lettering. Footprint libraries at `/usr/share/kicad/footprints/` (constant `KL`).
- KiCad 7 has no `kicad-cli pcb drc`; DRC is `pcbnew.WriteDRCReport(...)` (see `drc.py`). With KiCad 8 or 9 expect
  small API changes.
- `LoadBoard` must run in a fresh process to pick up `.kicad_pro` rules (same-process reload returned defaults).
- **Freerouting was not used.** The routing is the scripted plan plus `maze.py`. `maze.py` has no rip-up, so the
  result depends on the net order in `maze.ORDER`; if a placement change makes a net fail, reorder or script that net.
- All footprints are flipped to the back with `fp.Flip(pos, True)`; coordinates stay front-view.

## 8. Decisions made, and corrections to earlier statements

- Size back to about 20 cm wide (30/40 cm considered and dropped).
- USB-C is on the **side** of the base, not the bottom edge (the bottom sits on the table).
- The shamash is a **fixed LED column** on the board. The thing you hold is a separate magnet wand.
- Mic changed from analog to **digital I2S** (no amplifier, no analog noise problem).
- Candles widened to 12 mm so the back has room for power, data-return and hall traces.
- Cost: earlier estimate of $150–200 for 2 assembled boards assumed Economic assembly. With Standard assembly and about 10 extended part types, expect it higher; **get the real number from the JLCPCB quote** (35% US tariff applies to the goods value).
- No buzzer in v1 (no trusted footprint); spare GPIOs are on test pads instead.

## 8a. Changes made while routing (Claude Code session, 2026-11-22)

- **LED chain order is now left to right** (C1..C4, SH, C5..C8) and the level shifter moved under C1. Every
  candle-to-candle data link is then a short run along the crossbar.
- **LEDs are turned 180°** (DOUT on top) and each LED's capacitor sits in the gap below it; the data link passes
  between the capacitor pads. A candle routes entirely on the back with no vias except GND stitching.
- **Pin map changed** (section 4): halls C1/C2 on the module's east pads, the other seven on the south pads; LED data,
  mic, VLED_EN, CHRG_N, VBAT_SENSE on east pads next to the power section.
- **J2 (battery) and both buttons moved to the right end of the base**; the hall lines run down the east side of the
  power section and along the strip below the module. Battery area is now about 30 x 30 mm.
- VBUS crosses under the module on the **front** (0.8 mm, two vias at each end) just below the antenna keep-out.
- LED-switch parts (Q2, Q3, R8–R10, C9, C10) sit at the foot of the stem, west of the VLED trunk.
- USB D+/D- use four vias (short front hop over the module's west pad row, then under the module on the back).

## 9. Exact next steps

1. **Look at `out/front.png` and `out/back.png`**, and open `out/menorah_final.kicad_pcb` in KiCad if available.
2. **Upload to JLCPCB**: `out/fab/menorah-v1-gerbers.zip`, 2 layers, 1.6 mm, black mask, ENIG, then PCBA: Standard,
   **bottom side**, `bom_jlc.csv`, `cpl_jlc.csv`. Confirm stock per BOM line; swap or drop anything missing
   (the mic is optional: the board works without it).
3. **Check JLCPCB's placement preview part by part.** The CPL is KiCad's own position file with JLC's column names;
   bottom-side rotations often need correcting in the preview (especially D101..D147, U1, J1, J2, MK1, SOT-23s).
   For the LEDs: pad 1 (VDD) is at the lower right and DIN at the lower left **as seen from the front**.
4. Ask JLCPCB to add edge rails/fiducials for the irregular outline. Order with DHL Express DDP by Tue 2026-11-24.
5. Optional second/third bare-board orders: `out/extras/foot-gerbers.zip` (5 pcs, use 2) and `wand-gerbers.zip`.
6. **Firmware** (ESP-IDF or Arduino): LED driver on IO6 with a brightness cap, VLED_EN sequencing (hold LED data low
   while VLED is off), hall scan + wake, flame flicker and burn-down, Hebrew calendar + sunset, NTP, Wi-Fi
   provisioning, OTA, I2S blow detection, battery/charge readout. Use the pin map in section 4.
7. The project lives in `nighthawk6389/eagle-stuff` under `menorah/` (branch `claude/new-session-al2mk2`); move it to
   its own repository if wanted.

Known weak points to keep in mind:
- Nothing here has been checked by a second person or against opened datasheets in this session (section 5).
- Single 0.3 mm vias carry VBAT (battery path, 0.5 mm track, about 73 mm long) — fine for 1 A, not generous.
- A few signals take long routes in the base (EN 134 mm, BOOT 117 mm, MIC_SD 114 mm); fine at these speeds, not tidy.
- The JST connector mouth faces the battery area and the foot-board slot is 4 mm below it; check the plug clears the foot.

## 10. Things the user needs to buy or decide

- Small neodymium disc magnets, 5 x 2 or 6 x 2 mm (bigger ones risk triggering the neighbouring candle, 22 mm away).
- Optional LiPo, single cell with protection, JST-PH, up to about 30 x 30 mm (around 500 mAh gives 2–3 hours of light).
- Location for sunset calculation: Bergen County, NJ.

## 11. Other threads from the same conversation (parked)

- Started from `nighthawk6389/eagle-stuff` (2018 Eagle boards: CSR8635/CSR8645 Bluetooth audio, CSR1010 cadence sensor, Si4356/MRF39 sub-GHz breakouts, FT232, ATmega328 boards; all 2-layer).
- **Spectra 6 e-ink driver board** (chosen as the "hard" project, then set aside for the menorah): 13.3" Good Display GDEP133C02 / Waveshare 13.3" e-Paper (E), 1600 x 1200, 60-pin 0.5 mm FPC, two driver ICs (CS_M / CS_S), external MOSFET/charge-pump parts needed. Plan: phase 1 = ESP32-S3 controller board plugging into Waveshare's driver HAT (10 signals: VCC, GND, DIN, CLK, CS_M, CS_S, DC, RST, BUSY, PWR), server-side dithering, pull-over-Wi-Fi on a timer; phase 2 = integrate the HAT's power section on a 4-layer board. Buy the HAT version as a known-good reference.
