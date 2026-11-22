> Second independent pre-order review (2026-11-22), of the board after the first review's fixes and the microphone
> change. Applied afterwards: N1 (per-part CPL rotation offsets and the U1/J1 positions in `fab.py`), N3 (foot slot
> 1.5 mm), N7/N8 (button labels moved out from under the switches, J2 reference hidden, larger test-pad labels,
> CLAUDE.md corrected). Left as is: N2, N4. N5 and N6 are firmware/usage notes.

# Menorah v1 — second independent pre-order review (2026-11-22)

Reviewed: `out/menorah_final.kicad_pcb` (written 11:15:29, newer than every source file), `out/fab/*`, `out/extras/*`,
`netlist.py`, `geometry.py`, `route_plan.py`, `finish.py`, `fab.py`, `extras.py`, both footprints in `menorah.pretty/`.
Read-only: nothing in the repository was changed (renders were made from a copy under `review2/rb/`).

**Bottom line.** The schematic, the new microphone footprint/orientation/wiring and the LED footprint are correct; I
found no electrical blocker and no copper problem. The one thing that can still produce dead boards (or a stalled
order) is the **placement file**: after the F2 fix it is in JLCPCB's bottom-side convention, but it still assumes that
JLCPCB's library parts have the same zero orientation and origin as the KiCad footprints. For 16 placements (all nine
hall sensors, Q1–Q3, U2–U5, MK1) they do not, and U1 and J1 are also offset in position. Everything else is minor.

Legend: **verified** = checked against a file/document opened in this session; **inferred** = my calculation or
engineering judgement.

---

## 1. Findings (most severe first)

### N1 — CPL: 16 rotations and 2 positions do not match JLCPCB's own footprints — **major (blocker if neither you nor JLC's engineer catches it)** — previous F2, *fixed incompletely*

- What was done: `fab.py` line 58 now writes `(180 − KiCad angle) % 360`. That part is right (verified: it is the same
  formula as kicad-jlcpcb-tools and as line 252–254 of `process.py` in bennymeg/Fabrication-Toolkit, the plugin JLCPCB's
  own help article recommends: *"JLC expect 'Rotation' to be 'as viewed from above component', so bottom needs
  inverting"*).
- What is still wrong: no per-part offset is applied, and the X/Y are KiCad footprint anchors.
- Evidence (verified): I fetched the footprint JLCPCB/LCSC publish for each exact LCSC number
  (`https://lceda.cn/api/products/<Cxxxx>/components`, saved in `review2/easyeda/`), mirrored the final board's pads into
  the bottom view and solved for the rotation that puts JLC's pads on ours (`review2/cplcheck.py`). The pad patterns
  match with a pure rotation for every part (so nothing is mirrored and all pin numbering agrees), but:

  | Refs | LCSC | CPL now | Rotation that makes JLC's footprint land on the pads |
  |---|---|---|---|
  | U11–U19 (DRV5032) | C140921 | 0 | **180** |
  | Q1 / Q2 (AO3401A) | C15127 | 0 / 180 | **180 / 0** |
  | Q3 (2N7002) | C8545 | 0 | **180** |
  | U4 (SN74LV1T34) | C100024 | 180 | **0** |
  | U2 (TP4057) | C12044 | 0 | **270** |
  | U3 (AP2112K) | C51118 | 0 | **270** |
  | U5 (USBLC6-2) | C7519 | 90 | **0** |
  | MK1 (ICS-43432) | C574021 | 0 | **90** |
  | D101–D147, D1, J1, J2, U1, SW1/2 | | 180, 0, 90, 90, 0, 0 | same as now (OK) |

  The differences for the 3-pin SOT-23s, U4, U5 and the LEDs are 0°/180° results, so they do not depend on whether
  JLC counts clockwise or anticlockwise. A second source agrees for the SOT-23 family: Fabrication-Toolkit's
  `transformations.csv` has `"^SOT-23",180`.
- Positions (verified): Fabrication-Toolkit exports the centre of the pad bounding box, and JLC's footprint origins are
  at the pad centre. Our CPL has the KiCad anchor: **U1** is listed at (70.00, −130.75) but its pad centre is
  (70.00, −134.4) → 3.6 mm off (the module would be drawn hanging over the top edge of the base); **J1** is listed at
  (48.20, −131.00), pad centre (49.7, −131.00) → 1.5 mm off. All other parts are within 0.1 mm.
- Why it matters: a SOT-23 turned 180° or a SOT-23-6 turned 90° does not fit its pads, so JLC's engineer will normally
  notice; but then they either fix it by their own judgement or send a query, and either outcome is bad two days
  before the deadline. If any of it is placed as written, the hall sensors/FETs/LDO/charger are wrong and the board is dead.
- Confidence: high that the file does not match JLC's published footprints (measured). Medium that JLC's pick-and-place
  zero equals those footprints for every part: the older community table (JLCKicadTools) lists +180 for
  `JST_PH_S…` and `USB_C_Receptacle_HRO…`, whereas today's footprints for C295747 and C165948 need no offset, so
  J1 and J2 must be judged by eye in the preview.
- Smallest fix (no board change), in `fab.py`:
  `ROT_FIX = {"C140921":180,"C15127":180,"C8545":180,"C100024":180,"C12044":270,"C7519":270,"C51118":270,"C574021":90}`
  and `rot = (180 - Rot + ROT_FIX.get(lcsc, 0)) % 360`; write U1 as (70.00, −134.38) and J1 as (49.77, −131.00).
  Then in JLC's preview check every row of the table above plus J1 (mouth to the left board edge), J2 (mouth towards
  the battery area, solder tails towards the right edge), U1 (antenna at the top edge of the base, pads on pads),
  MK1 (long axis vertical, port ring on the ring, pin-1 dot bottom-right seen from the back), LEDs (GND/chamfer at the silk dot).

### N2 — The 3.3 V regulator's ground island hangs on one 0.5 mm track; three "stitching" vias stitch nothing — **minor** — NEW (part of previous F7 was fixed, the re-route undid another part)

- Verified with a connectivity graph of both GND pours, GND tracks, vias and pads (`review2/gndgraph2.py`): the back
  pour piece that carries **U3.2 (LDO GND), C6.2, C1.2, C2.2, C4.2 and R4.2** (x 79.7–89.8, y 124.6–143.0) is connected
  to the rest of ground only through the track (78.75, 125.49)→(80.60, 125.08), 0.5 mm, i.e. C1 → module pad 1.
  Removing that one segment isolates it.
- The two vias meant to tie it to the front plane, (85.40, 129.60) "C2" and (88.50, 132.75) "C4"
  (`route_plan.py` lines 310–313), land on front-pour islands of 8.5 and 8.8 mm² that the re-routed front tracks cut
  off from the main pour (see `review2/rb/pw_front.png`). Of the four new module-ground vias, (74.4, 132.2) and
  (74.4, 134.2) reach the main front pour; (68.6, 132.2) and (68.6, 134.2) reach a 137 mm² front island under the
  module that is itself only tied back to the same back pour.
- Effect (inferred): works. Only the LDO's quiescent current, the PROG current and the bypass currents of C6/C1 flow
  through that track (≈2 mΩ, 1–2 nH); the LDO is in effect star-grounded at the module. But it is a single point of
  failure for the 3.3 V rail, the LDO's input capacitor C7 returns through a ≈50 mm loop, and the USB/ESP32 ground
  island still reaches the main front plane through only three vias: (58.60, 135.05), (74.4, 132.2), (74.4, 134.2).
- Fix (optional, needs route `--reuse` + finish + DRC + fab): add `VIA("GND", …)` where the LDO island and the main
  front pour overlap with room for a 0.7 mm via: around (85, 139.5), (87, 140.5) or (81.8, 133.4)
  (overlap regions: x 81.1–89.4 / y 137.7–141.9 and x 81.2–82.4 / y 132.6–134.2). If there is no time, leave it.

### N3 — Foot boards seat 0.7 mm deeper than designed: the base edge, not the feet, touches the table — **minor (separate bare-board order)** — previous F3, *fix has a side effect*

- Verified: both slots end in a full-width semicircle (main board slot end at y = 135.625, foot slot end at 3.375 mm;
  `extras.py` line 67, `geometry.slot`). A 1.6 mm board entering a 1.75 mm round-ended slot goes
  √(0.875² − 0.8²) = 0.354 mm past the nominal depth, on each of the two slots.
- Result (inferred, geometry): seated foot top is at y = 133.29 (not 134.0) and its bottom at y = 151.29, 0.71 mm
  above the base's bottom edge (152.0). The menorah stands on the 1.6 mm edge of the base and rocks about 1° onto the
  foot tips. The foot top ends 0.19 mm below J2's lower mounting pad (pad edge y = 133.10, x 145.1–148.5), not the
  "1 mm" stated in CLAUDE.md; still clear, but inside JLC's ±0.2 mm routing tolerance.
- Fix: in `extras.py` set the foot slot depth `sd = 1.5` (keep 80 × 18). Seated foot top is then y ≈ 134.3 and the feet
  stand ≈0.3 mm proud of the base edge. No change to the main board.
- Still true from the first review: 1.75 mm slots for a 1.6 mm ±10 % board can come out tight; be ready to file.

### N4 — Signal tracks run round the ends of both foot slots, under the seated feet — **minor** — NEW

- Verified: EN (back) and BOOT (front) pass over the right slot end at y = 135.25, x 144.4–145.6, 0.275 mm from the
  routed slot edge; UART_RX (front) does the same at the left slot, and CC1 (back) crosses x 53.5–56.5, y 132.2–135.2.
  The seated foot straddles exactly this strip (y 133.3–136.1) on both faces.
- Effect: none electrically (the foot is bare FR4, the tracks are under mask). Risks are a nick if the slot is routed
  0.2 mm off (JLC tolerance; 0.2 mm is their copper-to-edge minimum) and mask wear from inserting the feet. Worst
  case is a dead RESET/BOOT button or RX test pad; the board still boots and flashes over USB.
- Fix: none needed for the order; insert the feet once and leave them. On a re-spin move the tracks ≥1 mm from the slot end.

### N5 — C9 = 1 µF: inrush is fixed as intended, but turn-off is now slow — **minor, firmware** — previous F5, fix verified, side effect NEW

- Turn-on (inferred, square-law model from the AO3401A sheet, k ≈ 10 A/V²): the gate reaches threshold ≈2–3 ms after
  VLED_EN, then the rail charges its ≈70 µF in ≈1 ms with a peak of ≈0.9 A (was 2–3 A). So the goal (< 1 A) is met.
  The statement "the LED rail ramps up over about 10 ms" in CLAUDE.md/netlist.py is not accurate; C9 is gate–source,
  so it delays and softens, it does not set a 10 ms slew. Dissipation in Q2 is ½CV² ≈ 0.7 mJ, negligible.
- Turn-off: C9 now discharges through R8 only, τ = 100 ms. Q2 stays on ≈150–200 ms after VLED_EN falls and spends
  ≈40 ms in its linear region. If the LEDs are still drawing ≈1 A at that moment Q2 dissipates roughly 30 mJ in a
  SOT-23 (≈+50…80 °C for an instant; tolerable, not kind).
- Fix: firmware — send "all off", wait a frame, then drop VLED_EN; allow 250 ms before assuming the rail is down.

### N6 — R5 = 2.2 k does what is claimed; a short brown-out window on unplug remains — **minor** — previous F6, fix verified

- Verified values: R5 = C4190 = 0603WAF2201T5E, 2.2 kΩ (jlcpcb.com part page). Adds 5 V/2.2 k = 2.3 mA on USB
  (11 mW in R5). On battery it only carries D1's reverse leakage (tens of µA at room temperature → gate ≈ 0.1 V).
- Inferred: τ = 2.2 k × 11 µF ≈ 24 ms. After unplugging, VSYS sits at VBAT − 0.6…0.7 V (Q1 body diode) for
  ≈20 ms until the gate has fallen ≈0.9 V below it. At VBAT ≤ 3.5 V that puts +3V3 near 2.7–2.8 V for ≈20 ms: a
  brown-out reset on unplug at low battery is still possible, just five times less likely than before.
- Fix (optional, BOM only): do not populate C3 (C4 = 1 µF remains at the charger) → ≈2 ms. Or accept and make the
  firmware restore its state after a reset.

### N7 — Silkscreen details — **cosmetic** — NEW

- "BOOT" and "RESET" are printed at the centre of SW1/SW2 (150.5, 146.6 / 140.4), i.e. under the 5.1 mm switch bodies;
  after assembly nothing tells the buttons apart (RESET is the upper one, nearer J2).
- "J2" reference straddles the board edge (x 154.9–156.1, edge at 155) and will be cut.
- Test-pad labels are 0.6 mm high / 0.09 mm stroke, references 0.7 / 0.12, BOOT/RESET 0.8 / 0.12. JLC's capability
  page asks for ≥1.0 mm height and ≥0.15 mm line width (SparkFun's tutorial says the same: below 0.04" text "turns
  into an unreadable white blob"). The 47 LED dots and the mic dot are 0.4 mm solid dots and are fine.
- "TX" label overlaps R3 pad 1; JLC clips silk on pads.

### N8 — Documentation statements that are no longer exact — **cosmetic**

- CLAUDE.md "the seated foot board stops 1 mm below J2's lower pad" → 0.2 mm (N3).
- CLAUDE.md / netlist.py "ramps up over about 10 ms" (N5).
- CLAUDE.md step 3 "the CPL rotations use JLCPCB's bottom-side convention" is true but reads as if the file were
  ready; see N1.

### Carried over from the first review, unchanged and still valid (not re-argued here)
F7 remainder (ground between the USB/ESP32 island and the main plane on few vias), F8 (single 0.3 mm vias on VBAT),
F10 (hall sensors far more sensitive than "touch"; firmware lock-out), F11a (USB shell tabs have no paste), F11b (no
reset supervisor), F11d (antenna over bare FR4, inside the outline), F11f (no input capacitor at U3), F11g (charge current).

---

## 2. Previous fixes verified

| Fix | Result | How checked |
|---|---|---|
| F1 silk dot at the GND corner | **Correct.** Footprint dot at (−3.9, +1.5) beside pad 3 (GND); in the final board D101's dot is at (5.1, 65.5), GND pad at (6.275, 66.25) = upper-left from the front, upper-right from the back. 47 LED dots present. The flame-LED dots are 0.6 mm inside the outline. | footprint file, `fp_circle` entries in the final board, pad dump |
| F1 wording in CLAUDE.md step 3 | **Correct** and numbering-free. | against the OPSCO sheet (chamfer "C角" at GND) |
| F2 CPL `180 − angle` | Applied correctly, **but incomplete** → N1. | `fab.py`, CPL, two reference plugins, JLC footprints |
| F3 foot 80 × 18, slot 2.5 | Applied (`out/extras/foot.kicad_pcb` bbox 80 × 18, slot to 3.375). Clears J2/C3/U5 and both buttons; **seats 0.7 mm too deep** → N3. | outline read back from the generated board, geometry |
| F5 C9 = 1 µF | Applied in netlist, board (C9 "1u", C15849) and BOM. Does its job; side effect N5. | board properties, BOM, calculation |
| F6 R5 = 2.2 k | Applied (R5 "2k2", C4190 = 2.2 kΩ 1 % 0603, basic part). Residual N6. | board, BOM, JLC part page |
| F9 no soldermask subtraction | **Correct.** `F_Silkscreen.gto` is 485 bytes with an empty aperture list; no `%LPC%` in any Gerber. | Gerber files |
| F7 four vias at the module ground pad | Present at (68.6/74.4, 132.2/134.2), beside the 3.9 mm EPAD, not in it (no via-in-pad). Only two reach the main front pour → N2. | via list, pour graph |
| Ground tie at the stem foot | **Correct.** Via (100.6, 112.6) + 0.5 mm track to C10; C10/Q3/mic ground chain now has two vias to the front plane. | pour graph |
| F11 BOM merge | **Correct.** 24 lines, no duplicate LCSC number, 152 designators = 152 CPL rows, all "Bottom". | script |
| F4 mic → ICS-43432 | **Correct**, see section 3. | datasheet + JLC footprint |
| Base re-route | DRC clean (given); additionally: all 47 front mask shapes lie on the front GND pour, ≥0.45 mm from non-GND front copper, no via under any opening, ≥0.5 mm from the outline; no copper on either layer under the antenna. | `review2/geo.py` |

---

## 3. Checked and found correct

### Microphone (new, reviewed from scratch)

- **Footprint vs datasheet** (verified, InvenSense DS-000038 rev 1.0, figures 3, 15, 16, 17, 18 — PDF in `scratchpad/mic/`):
  pads 0.40 (along the 4 mm axis) × 0.60, pitch 0.65, rows 2.15 apart (±1.075); pad centres 0.375/1.025/1.675 from the
  package centre; port 0.90 from the centre (1.10 from the short edge), i.e. 1.275 from the nearest pad row; ground ring
  Ø1.05/Ø1.65; paste 0.30 × 0.50 on the pads and four Ø1.15/Ø1.65 arcs with 0.1 mm gaps on the ring; no paste on the
  hole; port hole 0.5 mm NPTH (datasheet minimum, JLC minimum). All match the `.kicad_mod` numerically.
- **Pin numbering / chirality** (verified three ways): (1) Fig. 3 "top view, terminal side down" has the port at
  the top, 5-6-7 down the left, 3-2-1 down the right; the footprint (drawn in KiCad's top view) has exactly that.
  (2) Fig. 18 pin-1 dot is consistent with Fig. 3. (3) JLC's own footprint for C574021 has the same pads, ring and a
  0.5 mm hole, and fits ours pad-for-pad with a 90° rotation and no mirroring (max error 0.00 mm).
- **On the board** (verified): seen from the back (the side the part is on) the port is at the top (100, 96.0), WS/SCK/SD
  down the left, VDD/CONFIG/LR down the right — Fig. 3. Seen from the front that is mirrored, as it must be.
  Port hole is on `G.MIC`, centred in the gold ring; nearest via 2.3 mm from the port, outside the package outline.
- **Wiring** (verified against Table 6): 1 LR → GND (left channel), 2 CONFIG → GND, 3 VDD → +3V3, 4 → GND, 5 WS,
  6 SCK, 7 SD. C12 100 nF: 3.7 mm from pin 3, its ground via on the far side as the datasheet asks. R12 100 k from SD
  to GND joined by an explicit track at (101.9, 102.2). VDD 1.62–3.63 V, standby 7–24 µA once the clocks stop.
- **GPIOs** (verified, Espressif module datasheet table 3-1 and hardware guidelines): MIC_SD IO7 [7], MIC_SCK IO15 [8],
  MIC_WS IO16 [9] in netlist, board and CLAUDE.md section 4. IO15/16 are the 32 kHz crystal pins and are plain GPIOs
  when no crystal is fitted. I2S can be mapped to any GPIO (memory).
- Mask/paste plotted correctly: ring-shaped mask opening, separate hole opening, 0.25 mm dams (`review2/rb/mic_mp.png`).

### Pin maps (netlist.py vs datasheet vs KiCad pad positions vs JLC's library)

Every part below was additionally cross-checked against the symbol and footprint JLCPCB/LCSC publish for the exact LCSC
number (fetched today): pin names agree and the pad geometry fits ours with a pure rotation.

| Part | Checked against | Result |
|---|---|---|
| ESP32-S3-WROOM-1-N8R8 | **Fetched** Espressif datasheet table 3-1 (previous reviewer's copy, re-read) + JLC footprint (all 40 pads fit, 0.02 mm) | All pad→GPIO entries correct. IO8 = ADC1_CH7, IO19 = D−, IO20 = D+, halls on RTC GPIOs 4, 5, 9–14, 21. Pad 1 next to the antenna end. |
| SK6812MINI-E | **Fetched** OPSCO "-012 Rev B/1" (LCSC), pages 4–5, + JLC footprint | Emitting-side view: VDD top-left, DOUT bottom-left, DIN top-right, GND bottom-right (chamfer). Board from the front = that turned 180°. JLC's footprint agrees by function (its numbering is 1 GND, 2 DIN, 3 VDD, 4 DOUT; ours is 1 VDD, 2 DOUT, 3 GND, 4 DIN — harmless because the CPL rotation, not the pad number, places the part). Pad pitch 1.5 mm, pads cover the 5.88 mm lead span. Cut-out 3.4 × 3.0 with 0.50 mm dog-bone radii (computed) = JLC's 1.0 mm router; body 3.2 × 2.8. This is the 12 mA/channel version: 47 × 36 mA = 1.7 A, VIH 0.65 × VDD, VDD 3.7–5.5 V. |
| DRV5032FADBZR | **Fetched** TI SLVSDC7H | 1 VCC, 2 OUT, 3 GND; omnipolar, push-pull, 20 Hz. |
| TP4057 | **Fetched** Top Power sheet (LCSC) | 1 CHRG, 2 GND, 3 BAT, 4 VCC, 5 STDBY, 6 PROG; I = 1000 V/R → ≈300 mA; BAT rated −4.2 V (reverse battery survivable). |
| AP2112K-3.3 | **Fetched** Diodes sheet | 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT; EN tied to VIN. |
| SN74LV1T34DBVR | **Fetched** TI SCLS743 | 1 NC, 2 A, 3 GND, 4 Y, 5 VCC; VIH 2.0 V at 5 V; input rated to 5.5/7 V regardless of VCC. |
| USBLC6-2SC6 | **Fetched** ST sheet (LCSC copy) | 1/6 I/O1, 3/4 I/O2, 2 GND, 5 VBUS. |
| AO3401A | **Fetched** AOS sheet + JLC symbol | 1 G, 2 S, 3 D. Q1: D = VBAT, S = VSYS, G = VBUS. Q2: S = VSYS, D = VLED. |
| 2N7002 | **Fetched** CJ sheet | 1 G, 2 S, 3 D; Vth 1–2.5 V. |
| SS34 | KiCad `D_SMA` + JLC footprint | pad 1 = cathode = VSYS. |
| HRO TYPE-C-31-M-12 | KiCad footprint + JLC footprint (every signal pad fits by name) | A5/B5 CC with 5.1 k each, A6/B6 D+, A7/B7 D−; mouth at x = 44.5, 0.5 mm over the left edge. |
| JST S2B-PH-SM4-TB | **Fetched** JST PH catalogue p. 3 + KiCad + JLC footprint + SparkFun | Circuit 1 is on the left looking into the mouth with the board below; KiCad pad 1 is that pin; pad 1 = VBAT ("pin 1 = +" per SparkFun). Mouth at x = 145.3 facing −x (battery area). "+" silk at the pad-1 row. |
| XKB TS-1187A | **Fetched** XKB drawing | A–B common, C–D common; KiCad pads 1/1 = A, B and 2/2 = C, D. |

### Circuit behaviour (inferred unless stated)

- Power path in all four states: no back-feed into VBUS (D1); Q1 off whenever VBUS is present, on (Vgs = −VSYS) on
  battery; charger sits on the VBUS side. A reversed battery is non-destructive (Q1 stays off, TP4057 rated, 31 µA into IO8).
- Q2/Q3: off by default (R10; verified in Espressif's power-up glitch table: GPIO17 has only a 60 µs low-level glitch); on with Vgs = −0.91 × VSYS
  (−2.7 V at 3.0 V; AO3401A < 85 mΩ at −2.5 V, verified).
- U4 is powered from VLED: nothing drives an unpowered LED; driving its input from the ESP32 while VLED is off is within ratings.
- LDO 600 mA ≥ Espressif's 500 mA; EN 10 k / 1 µF as recommended; IO0 only on SW1, IO3/45/46 and IO35–37 open.
- Sleep budget ≈ 110–130 µA (LDO 55, divider 21, halls 9 × 1.6, mic standby 7–24, ESP32 ≈ 8).
- Magnet (5 × 2 mm, Br 1.2 T): ≈110 mT at the sensor through the board; ≈0.35 mT at the neighbour 22 mm away, below
  B_OP(min) 1.5 mT and B_RP(min) 0.5 mT.

### Layout / manufacturability / fab outputs (verified by script unless stated)

- JLC limits (capability pages fetched today): via 0.3/0.7 (min 0.15/0.25), NPTH 0.5 and 0.65 (min 0.5), plated slots
  0.6 × 1.2/1.7 (min 0.5, length ≥ 2 × width), routed slots 1.75 and LED dog-bones r 0.5 (min 1.0 mm slot), copper to
  edge ≥0.25 (min 0.2), board 196 × 150 (Standard PCBA 70 × 70 … 460 × 500), black-mask dam ≥0.13 (mic pads 0.25).
- No pad of one part within 0.4 mm of a pad of another; no body overlap; only J1 (intended) and U1 (0.05 mm) overhang.
- Thermal reliefs on all pour-connected pads (0.25 gap, 0.4 spokes); vias tented (`viasonmask false`); no via hole in an SMD pad.
- Gerber set complete: F/B Cu, Mask, Paste, Silk, Edge.Cuts, PTH + NPTH Excellon; the zip is identical to the folder.

---

## 4. Could not verify — a human should check

1. **JLC's real pick-and-place zero and origin per part** (N1). Their published footprints are the best evidence
   available offline; the placement preview is the proof. J1 and J2 are the two where old community tables disagree
   with today's footprints.
2. JLC stock at the moment of ordering (the part pages give several different stock fields; C5149201 and C574021 are
   extended parts).
3. Whether JLC solders J1's four shell tabs (no paste in the Gerbers).
4. The battery you buy: polarity and protection circuit. The board survives a reversed cell but will not run.
5. How the wand is used: with the wand flat against the ring the magnet's axis points at the sensor; if someone
   touches it edge-on (magnet axis parallel to the board) the field through the sensor is zero dead-centre and it may
   need a small sideways movement to trigger.
6. Inrush, turn-off and unplug timings (N5, N6) are hand calculations, not simulated or measured.
7. RF performance (antenna over bare FR4 inside the outline; back ground pour starts 0.3 mm below the antenna area, the USB connector is 9 mm to its side).
8. Tracks and tented vias on the back copper underneath the module body.
9. Panelisation: Standard PCBA requires rails and fiducials ("added by JLCPCB"); ask that tabs go on the base and
   crossbar, not on the flames or necks.

## Sources actually read

- SparkFun (fetched today, read in full): "Designing PCBs: SMD Footprints", "Designing PCBs: Advanced SMD",
  "Using EAGLE: Board Layout", "PCB Basics", LiPo care → JST-PH page. I could not find a SparkFun tutorial titled
  "common mistakes" (candidate URLs returned 404; sparkfun.com/tutorials/115 "Better PCBs in Eagle" is 404 now); the
  mistakes those tutorials do call out — wrong/unchecked footprints, silk below 8 mil / 0.04", pour isolation, labels,
  checking Gerbers in a separate viewer — were applied above.
- Adafruit NeoPixel Überguide: best practices, powering (previous reviewer's copies, re-read).
- Espressif ESP32-S3 hardware design guidelines: schematic checklist, PCB layout (previous reviewer's copies, re-read);
  ESP32-S3-WROOM-1 datasheet table 3-1.
- JLCPCB: PCB capabilities, PCB assembly capabilities (fetched today); part pages for C574021, C4190, C15849, C25803,
  C5149201, C2913201, C140921.
- LCSC/EasyEDA footprints and symbols for 18 LCSC numbers (lceda.cn; easyeda.com returned 403).
- bennymeg/Fabrication-Toolkit `process.py` and `transformations.csv`; matthewlai/JLCKicadTools `cpl_rotations_db.csv`;
  Bouni/kicad-jlcpcb-tools `fabrication.py` (previous copy).
- Datasheets: ICS-43432 DS-000038, OPSCO SK6812MINI-E-012, TI DRV5032, TI SN74LV1T34, Diodes AP2112, AOS AO3401A,
  Top Power TP4057, ST USBLC6-2, CJ 2N7002, JST PH, XKB TS-1187A. DigiKey was not tried (known 403).

## Scratch files (`review2/`)

`cplcheck.py` + `ee.py` + `easyeda/` JLC footprint fit · `gndgraph2.py` ground connectivity · `geo.py` mask artwork,
antenna, vias on pads · `spacing.py` pad/body/edge spacing · `tracks.py`, `nettracks.py` · `dump.py`, `fpext.py` ·
`rb/*.png` renders (mic, power section, USB, right end) · `dl/` fetched guidance.
