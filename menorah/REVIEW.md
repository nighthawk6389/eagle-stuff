> Independent pre-order review, written by a separate reviewer agent on 2026-11-22 against the board as it was
> before the fixes below. Applied afterwards: F1 (silk dot moved to the GND corner), F2 (CPL uses 180 − angle),
> F3 (foot is 80 x 18 mm, 2.5 mm slot), F5 (C9 = 1 µF), F6 (R5 = 2.2 k), F9 (no soldermask subtraction on silk),
> F7 in part (four vias on the module ground pad), F11 BOM line merge. Open: F4 (microphone stock). The rest are notes.

# Menorah v1 — independent pre-order design review

Reviewed 2026-11-22 against `out/menorah_final.kicad_pcb`, `out/fab/*`, `netlist.py`, `geometry.py`, `route_plan.py`,
`finish.py`, `fab.py`, `extras.py`, `menorah.pretty/SK6812MINI-E_Rev.kicad_mod`. Read-only: nothing in the repository
was modified (renders were made from a copy in the scratch directory).

**Bottom line.** The schematic (netlist) is correct: every IC/transistor/diode/connector pin map was checked against a
datasheet fetched today and no swapped pin, wrong FET orientation or wrong polarity was found. The copper is sound.
What can still make assembled boards dead on arrival is **how the placement data and the LED polarity mark will be
read by JLCPCB** (findings 1 and 2), and the **foot boards do not fit the populated board** (finding 3). None of these
needs re-routing.

Legend: *verified* = checked against a document/file I opened in this session; *inferred* = engineering estimate.

---

## 1. Findings (most severe first)

### F1 — LED polarity mark is on the wrong corner, and the "pad 1" hint in CLAUDE.md contradicts JLC's datasheet — **major, becomes a blocker if acted on** (all 47 LEDs reversed)

- What is wrong
  - `menorah.pretty/SK6812MINI-E_Rev.kicad_mod` puts its only silkscreen polarity mark (a circle) at `(3.9, -1.5)`,
    next to pad 1 = **VDD**. In the final board the circle sits at (+3.9, +1.5) mm from each LED centre (front view),
    i.e. at the VLED pad; 47 circles are present on B.SilkS (*verified*, pcbnew dump).
  - The physical part's only orientation feature is the chamfered corner ("C角"), which is the **GND** pin
    (*verified*, OPSCO datasheet, both revisions). On this board GND is the pad at (-2.73, -0.75) from the LED centre
    (front view) — the corner **diagonally opposite** the silk circle.
  - The two footprints this one was derived from mark the GND/chamfer corner: marbastlib `LED_6028R` has its triangle
    at (-3.5, 1.25) next to its VSS pad, Keebio `SK6812-MINI-E` has it next to pad 3 (GND) (*verified*, both files
    fetched from GitHub). Our footprint moved the mark to the opposite corner.
  - The datasheet JLCPCB/LCSC currently serve for C5149201 (file "SK6812MINI-E-012 Rev B/1", fetched via
    lcsc.com/datasheet/C5149201.pdf, page 4) numbers the pins **1 = GND, 2 = DIN, 3 = VDD, 4 = DOUT**. The older
    REV02 datasheet (Adafruit CDN) numbers them 1 = VDD, 2 = DOUT, 3 = GND, 4 = DIN. Same physical arrangement,
    different numbers. Our footprint uses the old numbering, so "pin 1" in JLC's library is very likely the GND/chamfer
    corner, while "pad 1" in CLAUDE.md section 9 step 3 ("pad 1 (VDD) is at the lower right") is VDD.
- Why it matters: anyone (JLC's engineer, or the owner in the placement preview) who lines up the part's pin-1/chamfer
  with the silk circle, or who follows the "pad 1 lower right" hint using JLC's pin numbering, rotates every LED by
  180°. That swaps VDD↔GND and DIN↔DOUT on all 47 LEDs: nothing lights and the LED rail is loaded through the LEDs'
  protection structures as soon as VLED_EN goes high. Combined with F2 (raw KiCad rotations: the LEDs are exported as
  0° where JLC's bottom-side convention would want 180°), the wrong placement would even *look* self-consistent in the
  preview (part pin-1 dot on top of the board's silk dot).
- Confidence: high on the facts (all verified). Medium on the outcome, because I cannot see JLC's library orientation
  for C5149201 or what their operator will do.
- Electrical side is fine (see section 2): the pad→net assignment matches the datasheet when the part is seen from
  the emitting side through the board.
- Smallest fix
  1. In `SK6812MINI-E_Rev.kicad_mod` move the silk circle to the GND corner: `(center -3.9 1.5) (end -3.8 1.5)`
     (footprint coordinates; pad 3 is at (-2.725, 0.75)). Only silkscreen changes; re-run
     `build.py && route.py --reuse && finish.py && drc.py … && fab.py`.
  2. Replace the hint in CLAUDE.md section 9 step 3 with a numbering-free statement: **"chamfered corner = GND = upper-left
     as seen from the front = upper-right as seen from the back (assembly side); VDD is diagonally opposite
     (lower-right from the front)"**, and put the same sentence in the JLC order remark.
  3. Check one LED in JLC's preview against that sentence, not against pin numbers.

### F2 — CPL rotations are raw KiCad angles, not JLCPCB's bottom-side convention — **major**

- What is wrong: `fab.py` lines 49–60 copy `Rot` from `kicad-cli pcb export pos --side back` straight into the CPL.
  For bottom-side parts JLCPCB mirrors the angle. Both widely used exporters apply `rot_jlc = (180 − rot_kicad) mod 360`
  before any per-package correction (*verified*: Bouni/kicad-jlcpcb-tools `fabrication.py` lines 686–689, "bottom angles
  need to be mirrored on Y-axis"; matthewlai/JLCKicadTools `cpl_fix_rotations.py` lines 166–173, "Around 2022 July:
  rotation = (-rotation + 180) % 360").
- Effect: of 151 placements, 128 are at 0° or 180° (`cut -d, -f5 cpl_jlc.csv | sort | uniq -c`: 52 × 0, 76 × 180,
  10 × 90, 13 × −90). All 128 come out 180° turned relative to the design unless corrected. Harmless for 0603/0805
  passives; wrong for D101–D147 (0), U1 (180), D1 (180), Q1/Q3 (180), Q2 (0), U2/U3 (180), U4 (0), U11–U19 (180),
  MK1 (180), SW1/SW2 (180, symmetric so harmless). The 90°/−90° parts (J1, J2, U5, …) are unaffected by the mirror
  but still subject to JLC library offsets (the community table has e.g. HRO TYPE-C-31-M-12 +180, JST_PH_S +180,
  ESP32-W +270, SOT-23 family ±90/180 depending on KiCad library version).
- Confidence: high that the file is not in JLC's convention; the exact per-part offsets cannot be known offline.
- Positions are fine (*verified*): CPL X/Y use the same frame as the Gerbers (X positive, Y negative, not mirrored);
  e.g. MK1 paste apertures in `B_Paste.gbp` sit at x 100.65–101.15, y −93.7…−94.9 around CPL MK1 (100.0, −95.29).
- Smallest fix: in `fab.py` write `(180 - float(r["Rot"])) % 360` for the rotation column, regenerate, then check
  **every polarised part type** in JLC's preview (D1xx by the F1 rule; U1 antenna towards the top edge of the base;
  SOT-23/-5/-6 pin-1; D1 cathode bar towards the stem side, pad 1 at x = 90.6; J1 mouth to the left edge; J2 mouth
  towards the battery area; MK1 port over the hole). Tick "Confirm parts placement" when ordering.

### F3 — Foot boards as generated collide with J2 and C3 — **major (mechanical; fix is in the separate foot order)**

- What is wrong: `extras.py` makes the foot 25 mm tall with a 10 mm slot. Seated flush with the bottom edge
  (y = 152) the foot occupies x = slot ± 0.8 mm for **y = 127…152 on both faces** of the main board. On the back:
  - right foot (x 144.2–145.8): J2's body front/mouth is at x = 145.25–145.3, y = 125.0–133.0, and its lower mounting
    pad spans x 145.1–148.5, y 131.6–133.1. The foot overlaps the connector by ~0.5 mm and stands directly in front
    of the mouth for y ≥ 127, so the foot cannot be seated with J2 fitted and the battery plug cannot be inserted.
  - left foot (x 54.2–55.8): C3 (0805, VBUS) body x 54.1–55.5, y 126.2–128.3 and its pad at y 127.65–128.65 are
    inside the foot volume; U5's body edge (x 55.70) is within 0.1–0.2 mm of it.
  (*verified* geometrically from pad/fab extents in the final board; script `foot.py`.)
- CLAUDE.md ("the foot-board slot is 4 mm below it; check the plug clears the foot") only considered the slot in the
  main board, not the 10 mm of foot that rises above the slot top (y = 136.5).
- Confidence: high.
- Smallest fix (no change to the main board): make the foot ≤ 17.5–18 mm tall with a 2–2.5 mm slot (foot top at
  y ≥ 134, clear of J2's pad at 133.1 and of C3), or keep 25 mm and add a relief notch on the half that sits behind
  the board (≥ 9 mm high × ≥ 10 mm deep from the slot). Do not order `foot-gerbers.zip` as it is.
- Related, minor: slot 1.75 mm for a 1.6 mm ±10 % board with ±0.2 mm routing tolerance (JLC capability page) can come
  out tight; be ready to file, or widen both slots to ~1.9 mm if the outline is ever regenerated.

### F4 — MK1 (ICS-43434, C5656610) has zero stock at JLCPCB — **major for the order flow, not for function**

- jlcpcb.com/partdetail/C5656610 fetched today: stock 0 (JLC) / 0 (overseas). Every other BOM line resolved to the
  intended part with stock (table in section 2).
- Fix: remove MK1 from `bom_jlc.csv` and `cpl_jlc.csv` (board works without it, as CLAUDE.md says) or pick an
  in-stock pin-compatible I2S bottom-port mic and re-verify its footprint. Leaving it in will stall the order at BOM
  matching.

### F5 — LED rail inrush when Q2 turns on — **minor (firmware workaround exists; one-value BOM fix)**

- C9 = 100 nF gate-source with R9 = 10 k gives τ ≈ 0.9 ms; the gate crosses threshold at ≈ 3.6 V/ms, so Q2 goes from
  off to several amps in ≈ 0.2 ms while charging ~60–70 µF of VLED capacitance (3 × 22 µF + 47 × 100 nF) from a
  22 µF VSYS capacitor. Estimated peak 2–3 A for ≈ 0.2 ms (*inferred*, hand calculation from AO3401A transfer curve).
  On USB this is probably tolerated; on a weak battery (cell + protection ≈ 0.2–0.3 Ω, plus 68 mΩ VBAT track and Q1)
  VSYS can dip ≈ 1 V, the LDO drops out and can back-drain C6 through its pass device → possible brown-out reset at
  the moment the candles are lit.
- Fix: change C9 to 1 µF 0603 (C15849, already in the BOM) → τ ≈ 9 ms, peak ≈ 0.8 A. No layout change. Firmware
  alternative: ramp VLED_EN with a few short pulses before holding it high.

### F6 — USB unplug hands over through Q1's body diode for 50–100 ms — **minor**

- Q1's gate is VBUS. After unplugging, VBUS is held up by C3 + C4 (11 µF) and discharged by R5 = 10 k (τ ≈ 0.1 s).
  Until the gate has fallen ≈ 1.5 V below VBAT, the system runs through the body diode: VSYS ≈ VBAT − 0.6…0.8 V
  (*inferred*). With a 3.4–3.6 V battery and LEDs on, +3V3 sags to ≈ 2.6–2.9 V for tens of ms → possible brown-out
  reset on unplug at low battery. No damage.
- Fix (BOM only): R5 → 2.2 k (adds 2.3 mA on USB) or do not populate C3 (C4 = 1 µF stays; this also brings the
  capacitance seen by VBUS closer to the USB 10 µF inrush limit).

### F7 — Ground between the USB/ESP32 island and the rest of the board hangs on two vias — **minor**

- The back pour piece that holds J1's GND pins, the shell and all three ESP32 GND pads (1, 40, EPAD 41) connects to
  the main front pour through exactly two 0.3 mm vias, (58.6, 135.05) and (71.5, 130.8), plus one 0.5 mm track
  (U1.1 → C1.2). (*verified*: pour-piece/via graph, `gndgraph.py`.)
- A resistive-sheet simulation of both GND layers (`gndsim3.py`, 0.1 mm grid, 35 µm copper) gives: LED return from
  the stem to the USB GND pins 13.6 mΩ, with 50 % of the current in the first via and 36 % in the second;
  ESP32 GND → LDO GND 4 mΩ; LDO GND → USB GND 8.9 mΩ; stem → J2 GND 5.2 mΩ. So DC drop is negligible, but at an
  uncapped 1.7 A + 0.3 A charge the two vias carry ≈ 1.0 A and 0.7 A, and the ESP32 EPAD has a single via to the
  front plane (the footprint's thermal vias were deleted). Espressif's layout guide asks for "sufficient ground
  copper and dense ground vias" near the module.
- Also noted: C10 (22 µF VLED bulk at Q2), Q3's source and the microphone share one small back-pour chain that
  reaches main ground through a single via at the mic (101.95, 94.75). Works; C10 is less effective than it looks.
- Fix (optional, low risk, needs a rebuild): add 6–10 GND vias (0.3 mm) with `VIA("GND", …)` in `route_plan.py` where
  both layers already have pour — 3–4 inside/around the EPAD, 2–3 next to J1's GND pins, 1–2 next to C10 — then
  re-run finish/DRC. If there is no time, leave it and keep the firmware brightness cap.

### F8 — Single 0.3 mm vias in series on power paths — **minor**

- VBAT J2 → Q1: 68 mΩ, two single vias in series at (150.2, 130.6) and (95.0, 137.9), each carrying the full battery
  current (net simulation, `netsim.py`). VBUS J1 → D1: 25 mΩ; the via at (53.75, 128.55) carries ≈ 72 % of the USB
  current. A 0.3 mm via is comfortable to ≈ 1–1.5 A. Fine with a brightness cap (≤ ≈ 1 A LED current); warm at an
  uncapped 1.7 A + system + charge. Tracks themselves are adequate: VLED 1.0 mm bus / 0.8 mm trunk (28 mΩ, 46 mm),
  VBUS 0.8 mm, VSYS 0.6–0.8 mm with paired vias.
- Fix: enforce the cap in firmware (the LCSC datasheet for the LED itself says to use ≤ 70 % grey level when all
  three colours are lit); add a second via beside each if a rebuild happens anyway.

### F9 — Front "silkscreen" Gerber carries only clear-polarity data — **minor, check in JLC's viewer**

- `menorah_final-F_Silkscreen.gto` (339 kB) contains no dark objects, only an `%LPC%` block with the mask shapes,
  because `fab.py` passes `--subtract-soldermask` and there is no front silk. A CAM tool that ignores polarity would
  print white ink over all the gold artwork. JLC normally honours polarity and also clips silk off exposed copper,
  so the risk is low, but it is free to remove: drop `--subtract-soldermask` or omit F.SilkS, and confirm that JLC's
  Gerber viewer shows an empty top silkscreen. (A file `out/jlcpcb_preview.png` appeared in `out/` at 03:43 during this
  review; I did not create it. It shows the front with gold artwork and no white ink, which is the expected result
  if it came from JLC's viewer.)

### F10 — Hall sensors are far more sensitive than "touch the ring" implies — **minor, firmware**

- DRV5032FA: B_OP 1.5/3.0/4.8 mT (min/typ/max), B_RP 0.5/1.5/3.0 mT (*verified*, TI SLVSDC7H table 6.6). A 5 × 2 mm
  N35 disc gives ≈ 120 mT at the sensing element with the magnet on the ring (1.6 mm FR4 + package), so detection is
  certain. Dipole estimate: it triggers anywhere within ≈ 9 mm (worst part) to ≈ 14 mm (most sensitive part)
  sideways, and 12–17 mm above the board. The neighbour at 22 mm sees ≈ 0.35 mT (5 × 2) or ≈ 0.5 mT (6 × 2) — below
  B_OP(min), so no false trigger with the wand resting on a ring, but two adjacent candles can both read "magnet"
  while the wand is in between, and a 6 × 2 magnet is at B_RP(min). (*inferred* from datasheet thresholds.)
- Fix: firmware (first-edge wins, short lock-out, enforce the lighting order); keep to 5 × 2 mm magnets.

### F11 — Smaller items

| # | Severity | Item | Evidence / fix |
|---|---|---|---|
| a | minor | USB-C shell tabs are plated slots with no paste; whether JLC solders them is not visible from the files. | After delivery check the four tabs; hand-solder if dry. Mechanical strength of J1 depends on them. |
| b | minor | No reset supervisor. Espressif's checklist warns that the 10 k/1 µF EN RC "alone may not meet the timing requirements" with slow supply rise/fall "such as during battery charging". | RESET button exists; in firmware go to deep sleep below ≈ 3.3 V battery. |
| c | minor | MIC_SD has no pull-down (ICS-43434 datasheet asks for 100 k). | Enable the internal pull-down on IO16. |
| d | minor | ESP32 antenna sits over bare FR4 (108 mm² of laminate under it), not overhanging the edge; stem copper starts 15 mm to the side. No copper under the antenna on either layer (*verified*). | Meets the footprint keep-out, not Espressif's preferred "antenna outside the board". Expect some range loss; fine for home Wi-Fi. |
| e | minor | C13/C14 (0805, 22 µF across VLED) lie along the crossbar's long axis at x = 42 / 158; flexing the arms stresses them. No fuse on VBUS or battery. | Use a protected cell only (already stated). Handle by the base. |
| f | minor | AP2112 has no input capacitor of its own; C7 (22 µF) is ≈ 9 mm away through two vias (7–10 mΩ). | Works in practice; add 1 µF at U3 pin 1 on a re-spin. |
| g | minor | R4 = 3.3 k → ≈ 250–300 mA (TP4057 table: 10 k → 100 mA, 2 k → 400 mA). | Too high for cells under ≈ 300 mAh; fine for ≥ 500 mAh. |
| h | cosmetic | BOM has two lines for C318884 (SW1 "BOOT", SW2 "RESET"). | Merge into one line. |
| i | cosmetic | R11 = 100 Ω; Adafruit recommends 300–500 Ω at the first pixel. | Works either way. |
| j | cosmetic | Mask bridge between J1's 0.3 mm pads will be below JLC's 0.13 mm black-mask minimum and will be removed. | Normal for this connector. |
| k | info | USB D+/D− use 4 and 2 vias and are not routed as a pair (lengths ≈ 41.5 / 39.9 mm). | Acceptable for full-speed USB. |
| l | info | No fiducials on the board; Standard PCBA needs edge rails and fiducials (JLC PCBA capability page). | Select "added by JLCPCB"; expect mouse-bite nubs on the black edge. |

---

## 2. Checked and found correct

### Pin maps (netlist.py vs datasheet vs KiCad footprint pad positions in the final board)

| Part | Checked against | Result |
|---|---|---|
| ESP32-S3-WROOM-1-N8R8 (U1) | **Fetched** Espressif module datasheet v1.8, table 3-1 | All 41 pad→name entries in `ESP` match. IO8 = ADC1_CH7, IO19 = USB_D−, IO20 = USB_D+, all nine hall GPIOs are RTC_GPIO, IO35–37 reserved for octal PSRAM, IO47/48 are 3.3 V on R8. Pad 1 at (78.75, 125.49), antenna end at y = 118 (top edge of the base). |
| SK6812MINI-E (D101–D147) | **Fetched** OPSCO REV02 (Adafruit CDN) and OPSCO "-012 Rev B/1" (LCSC, has an explicit BOTTOM VIEW); **fetched** marbastlib `LED_6028R` and Keebio `SK6812-MINI-E` | Emitting-side view: VDD top-left, DOUT bottom-left, GND bottom-right (chamfer), DIN top-right. Board, seen from the front: VDD lower-right, DOUT upper-right, GND upper-left, DIN lower-left = the datasheet turned 180°. Matches the datasheet's bottom view when seen from the back. Pad positions (±2.725, ±0.75), 1.35 × 0.82 and the 3.4 × 3.0 mm cut-out with r ≈ 0.5 mm dog-bones are identical to marbastlib. Chain D101.DOUT→D102.DIN … D147.DOUT open. |
| DRV5032FADBZR (U11–U19) | **Fetched** TI SLVSDC7H | SOT-23: 1 VCC, 2 OUT, 3 GND; FA = omnipolar, push-pull, 20 Hz. Element centred in the package, footprint centred on the ring. |
| ICS-43434 (MK1) | **Fetched** InvenSense DS-000069 v1.2 (LCSC copy), pages 10 and 17 | 1 WS, 2 LR, 3 GND, 4 SCK, 5 VDD, 6 SD; LR tied to GND. KiCad footprint pad layout matches fig. 3 turned 180°. Port: 0.5 mm NPTH at (100, 96) = datasheet minimum = JLC minimum. Paste apertures present in `B_Paste.gbp`. |
| TP4057 (U2) | **Fetched** Top Power datasheet (LCSC C12044) | 1 CHRG, 2 GND, 3 BAT, 4 VCC, 5 STDBY, 6 PROG. Reverse-battery tolerant (BAT −4.2 V). |
| AP2112K-3.3 (U3) | **Fetched** Diodes DS39724 | SOT25: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT; EN tied to VIN. 600 mA, 6 V max operating, dropout 125 mV typ @ 300 mA. |
| SN74LV1T34DBVR (U4) | **Fetched** TI SCLS743E | 1 NC, 2 A, 3 GND, 4 Y, 5 VCC. V_IH = 2.02 V at VCC 4.5–5 V; V_I rated to 7 V independent of VCC, so driving A with VLED off is safe. |
| USBLC6-2SC6 (U5) | **Fetched** ST datasheet (LCSC copy; st.com timed out) | 1/6 I/O1, 3/4 I/O2, 2 GND, 5 VBUS. |
| AO3401A (Q1, Q2) | **Fetched** AOS Rev 3.1 | G/S on the two-pin side, D alone; body diode conducts D→S. Q1: D = VBAT, S = VSYS (diode feeds VSYS from the battery, blocks back-charging). Q2: S = VSYS, D = VLED (diode blocked when off). |
| 2N7002 (Q3) | **Fetched** CJ datasheet (LCSC C8545) | 1 G, 2 S, 3 D; V_th 1–2.5 V, adequate for 0.4 mA from 3.3 V. |
| SS34 (D1) | **Fetched** MDD datasheet (LCSC C8678) + KiCad `D_SMA` | Pad 1 = cathode = VSYS at (90.6, 127.6); 3 A, 0.55 V @ 3 A. |
| HRO TYPE-C-31-M-12 (J1) | **Fetched** HRO drawing (LCSC C165948) | Pin names match; CC1/CC2 each 5.1 k to GND. Drawing puts the PCB edge 5.79 mm from the peg holes → 3.19 mm from footprint origin; the board edge is 3.20 mm from it (x = 45.0 vs origin 48.2). Mouth overhangs the edge ≈ 0.45 mm. Slots 0.6 × 1.2 / 1.7 mm within JLC's 0.5 mm plated-slot limit. |
| JST S2B-PH-SM4-TB (J2) | **Fetched** JST PH catalogue (jst-mfg.com) + SparkFun LiPo page | KiCad pad 1 = JST circuit No. 1. Pad 1 = VBAT, matching SparkFun's "pin 1 as +VBATT (red wire)". Mouth at x ≈ 145.3 facing the battery area. "+" silk is at the pad-1 row (y = 130), "−" at y = 128. |
| XKB TS-1187A (SW1, SW2) | **Fetched** XKB drawing (LCSC C318884) | Terminals A–B common, C–D common; KiCad pads 1/1 and 2/2 follow that. Land pattern 7.0/5.0 × 4.5/3.0 matches. |

### Circuit behaviour (analysis; datasheet values where stated)

- Power path: USB only, battery only, both, plug-in — no back-feed to VBUS (D1), Q1 off whenever VBUS is present,
  charger on the VBUS side so charge termination is not disturbed by the load.
- Q2/Q3: default off (R10 pull-down; IO17 only has a low-level power-up glitch per Espressif's table). On: V_GS =
  −0.91 × VSYS, i.e. −2.7 V at 3.0 V battery; AO3401A is specified < 85 mΩ at −2.5 V.
- U4 is powered from VLED, so the first LED's DIN is never driven while the LEDs are unpowered.
- LDO: 600 mA ≥ Espressif's 500 mA recommendation; EN RC 10 k / 1 µF as recommended; C1 100 nF at pin 2, C6 22 µF.
- Strapping pins: IO0 only to SW1; IO3, IO45, IO46 unconnected. IO35–37 unconnected.
- VBAT divider 100 k/100 k + 100 nF into ADC1 (usable with Wi-Fi).
- No single-pin nets; unconnected pads are only the intended ones (U1 spare GPIOs, U2.5, U3.4, U4.1, J1 SBU, D147.2).

### Layout / fab outputs

- All front mask artwork (47 shapes, 1598 mm²) lies entirely on the front GND fill; none of it is within 0.2 mm of
  non-GND front copper; no via is exposed by it; nearest artwork to the outline 0.5 mm (`art.py`).
- Vias are tented in both mask Gerbers (no flash at via positions); no via hole inside any SMD pad.
- Edge.Cuts: 1950 segments/arcs, every endpoint has even degree (closed contours), 47 LED cut-outs included.
- No copper on either layer under the antenna area (x 61–79, y 118–124); nearest copper 0.6–0.8 mm below it.
- JLC limits (capability page fetched today): via 0.3/0.7, NPTH ≥ 0.5, non-plated slot ≥ 1.0, plated slot ≥ 0.5,
  copper-to-edge ≥ 0.2, Standard PCBA board ≥ 70 × 70 mm — all met.
- Gerber set: F/B Cu, Mask, Paste, Silk, Edge.Cuts, PTH and NPTH Excellon (+ drill maps). F.Paste empty as expected.
- BOM: 24 lines, 151 designators = 151 CPL rows. Every LCSC number resolves on jlcpcb.com to the intended part
  (ESP32-S3-WROOM-1-N8R8, CC0603KRX7R9BB104, 0603WAF1002/1003/5101/3301/1000, CL10A105, CL21A106, CL21A226,
  TS-1187A-B-A-B, TYPE-C-31-M-12, USBLC6-2SC6, SS34, TP4057, AO3401A, S2B-PH-SM4-TB, AP2112K-3.3TRG1, 2N7002,
  SN74LV1T34DBVR, SK6812MINI-E, DRV5032FADBZR), all in stock today except MK1 (F4).
- Hebrew lettering renders right-to-left correctly on the front.

---

## 3. Could not verify — a human should check before/after ordering

1. JLCPCB's library orientation and origin for each part (especially C5149201, U1, J1, J2, MK1) — only visible in
   their placement preview. Use the rule in F1 for the LEDs.
2. Whether JLC solders J1's shell tabs (F11a).
3. Whether JLC's CAM renders the top silkscreen as empty (F9).
4. Inrush and unplug behaviour (F5, F6) are hand estimates, not simulated or measured.
5. RF performance with the antenna over FR4 and the thin ground tie (F7, F11d).
6. Underside of the ESP32 module: USB D+/D− run on the back copper beneath it (y ≈ 137). I did not find a statement
   in the module datasheet about exposed test points there; the tracks are under solder mask.
7. The battery you buy: polarity (many generic cells are reversed) and that it has a protection circuit.
8. Stock was read from jlcpcb.com part pages today; confirm again in the BOM-matching screen.

## Sources actually read

- Datasheets fetched: Espressif ESP32-S3-WROOM-1 v1.8; OPSCO SK6812MINI-E REV02 and -012 Rev B/1; TI DRV5032;
  TI SN74LV1T34; Diodes AP2112; AOS AO3401A; Top Power TP4057; ST USBLC6-2; MDD SS34; CJ 2N7002; InvenSense
  ICS-43434; HRO TYPE-C-31-M-12; JST PH; XKB TS-1187A.
- Guidance: Espressif ESP32-S3 hardware design guidelines (schematic checklist, PCB layout); JLCPCB PCB capabilities
  and PCB assembly capabilities; Adafruit NeoPixel Überguide (best practices, powering); SparkFun LiPo battery care
  (JST-PH page). SparkFun "PCB Basics" was fetched but only its overview was read; I did not read SparkFun's
  design-guidance or common-mistakes tutorials.
- Reference designs: marbastlib `LED_6028R`, Keebio `SK6812-MINI-E`, Bouni kicad-jlcpcb-tools, JLCKicadTools.
- Unreachable: st.com (timeout), invensense.tdk.com / product.tdk.com (HTML wrapper / 403), onsemi and Nexperia
  (not found / 403) — LCSC copies were used instead.

## Scratch files (this directory)

`dump.py` pad dump · `foot.py` foot collision · `tracks.py` widths/vias · `art.py` mask artwork vs copper ·
`pieces.py`, `gndgraph.py` pour connectivity · `gndsim3.py`, `netsim.py` resistive-sheet simulations
(`gnd_usb.png`, `gnd_bat.png`) · `ant.py` antenna copper · `viapad.py` · `jlcall.py` JLC part lookup ·
`dl/`, `ds/`, `ref/` fetched datasheets, guides and reference footprints · `rb/` render copies.
