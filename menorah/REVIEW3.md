> Third independent pre-order review (2026-11-22), approached as a pre-mortem and from the Gerbers backwards. It found
> nothing to change on the main board or its fab files. Acted on: T1 and T6 (order options and remarks, now in
> CLAUDE.md section 9), T2 (orientation table added to CLAUDE.md), T7 (wand given copper and a magnet-spot marking;
> feet left copper-free), T3/T5/T8 (usage and firmware notes in CLAUDE.md), stale comments fixed. Not done: T4 (USB
> presence detection) would need new parts and a re-route after three reviews; documented as an optional bodge instead.

# Menorah v1 — third independent pre-order review (2026-11-22)

Reviewed: `out/fab/gerber/*` (parsed directly, independently of the KiCad board), `out/fab/bom_jlc.csv`,
`out/fab/cpl_jlc.csv`, `out/fab/menorah-v1-gerbers.zip`, `out/extras/*`, `out/menorah_final.kicad_pcb` (from a copy),
`netlist.py`, `geometry.py`, `route_plan.py`, `finish.py`, `fab.py`, `extras.py`, `CLAUDE.md`, `REVIEW.md`, `REVIEW2.md`.
Read-only: nothing in the repository was modified (`git status` clean; renders were made from a copy in `review3/rb/`).

**Bottom line.** I found no blocker and nothing that needs a change to the main board or its fab files. The Gerbers,
drill files, BOM and CPL describe a consistent, manufacturable board whose copper implements `netlist.py` exactly.
What I did find is outside the board file: two things to do on the JLCPCB order form / in the placement preview
(findings 1 and 2), and a set of usage, firmware and accessory-board points that the part-by-part reviews could not see
(3–8).

Legend: **verified** = read from a file, a Gerber feature or a document I opened in this session;
**inferred** = my calculation or engineering judgement.

---

## 1. Findings (most severe first)

### T1 — 47 moisture-sensitive LEDs in one series chain, no baking requested, no spares — **major (order option + purchase; no file change)** — angles 1, 4

- What is wrong
  - JLCPCB's own data for C5149201 (SK6812MINI-E) says `moistureSensitivityLevelEn: "MSL 5a"`, "Assembly Difficulty High"
    (**verified**: `review2/jlc/jlc_C5149201.html`, saved from jlcpcb.com today by the second reviewer). MSL 5a means a
    24-hour floor life once the reel bag is open.
  - JLCPCB's after-sales FAQ (**verified**, fetched today, saved as `review3/dl/jlc_faq.html`,
    https://jlcpcb.com/help/article/common-pcba-after-sales-issues-and-faq, section "LED Assembly and Moisture
    Sensitivity Considerations"): *"When assembling boards containing a large number of LED components, and where the
    Moisture Sensitivity Level (MSL) is ≥ MSL 3, we strongly recommend selecting the baking service before assembly. …
    If issues arise due to the omission of LED baking or shipment without adequate testing, such cases are not eligible
    for after-sales complaints or compensation."*
  - On this board the 47 LEDs are one unbroken data chain D101 → D147 (**verified**: `netlist.py` lines 122–128 and the
    copper Gerbers). An SK6812 has no bypass: one dead or intermittently failing LED darkens every LED after it. A
    failure in C1 (indices 0–4) blanks the whole menorah. Moisture damage also shows up as a *latent* failure (works at
    delivery, fails after days of thermal cycling), which is exactly the "fails after a week" case.
  - Neither `CLAUDE.md` section 9 nor the two reviews mention baking, spare LEDs, or having a test program ready.
- Confidence: high on the facts. The failure probability is not knowable; with 47 LEDs per board even 0.5 % per LED is
  about a 1-in-5 chance per board of a broken chain (**inferred**).
- Smallest fix
  1. On the PCBA order page select the **baking service** for components (JLCPCB's wording), or write it in the order
     remark. Ask what it does to the lead time before paying; if it costs a day you cannot afford, that is your call,
     but then do items 2 and 3.
  2. Buy 10 spare SK6812MINI-E domestically now (for example Adafruit product 4960) so a dead LED can be swapped with
     a soldering iron on the back. A dead LED can also be bridged DIN→DOUT with a wire to get the rest of the chain back.
  3. Have a 20-line test sketch ready before the boards arrive (IO6 low, IO17 high, then walk one lit pixel through
     all 47 at low brightness). A blank module shows nothing, so without it LED faults are found only when the real
     firmware exists.

### T2 — The placement preview cannot reveal a 180° error on 50 parts unless you know where pin 1 belongs — **major if it goes wrong, low probability (order-time check; no file change)** — angles 2, 5

- What I checked (**verified**): I re-derived the bottom-side convention from scratch and placed the footprint JLCPCB
  publishes for each LCSC number with the rows of the *final* `cpl_jlc.csv` (rotate anticlockwise by the CPL angle in
  the footprint's own top view, mirror left–right, translate) and compared every pad with the pad flashes in the
  copper Gerber (`review3/cpl1.py`, `cpl2.py`, `ee1.py`). Every part lands on its pads (worst 0.21 mm, where KiCad's and
  JLC's land patterns differ in pad spacing) at exactly one of the four rotations, by pad *name*: LED GND/DIN/VDD/DOUT, D1 cathode on VSYS,
  TP4057 and USBLC6 pin 1 on pad 1, mic pads and ring. The CPL equals the table in REVIEW2 N1 row for row. So the N1
  fix was applied correctly and is self-consistent.
- What remains: that model is the one the KiCad plugins use (`180 − angle + offset`, **verified** in
  kicad-jlcpcb-tools `fabrication.py`), not something JLCPCB documents. A KiBot issue (seen only as a search-result
  excerpt, not opened) reports that JLCPCB has changed its bottom-side rotation handling several times, and the
  community rotation tables disagree with today's JLC footprints for the USB-C and JST connectors (REVIEW2). The
  preview is the only proof, as `CLAUDE.md` already says.
- The gap: `CLAUDE.md` step 3 tells you to "check every SOT-23/-5/-6" but not what correct looks like. For four part
  types a 180° turn fits the pads perfectly and looks fine in the preview:

  | Part | Correct position, seen from the back (assembly side) | Same thing by landmark (does not depend on how the viewer mirrors) | If 180° wrong |
  |---|---|---|---|
  | D101–D147 (47×) | GND / chamfer / JLC pin 1 at the **upper-right** pad | on the silk dot; the pad row nearer the candle's GND-via column, upper pad | all LEDs reversed, rail loaded |
  | D1 (SS34) | cathode bar on the **left** | the end nearest C7 and the stem (pad at x = 90.6), away from the module | no USB power, battery back-feeds VBUS |
  | U2 (TP4057) | pin-1 dot **upper-left** | the corner nearest C5 (pad at 91.64, 136.05), on the Q1 side | no charging, VBUS on the wrong pins |
  | U5 (USBLC6-2) | pin-1 dot **lower-left** | the row facing R3, at the end nearest the ESP32 module (pad at 58.15, 132.14) | VBUS clamped to GND through the diodes |

  (**verified** from the Gerber pad positions, `review3/pin1.py`; coordinates are front-view mm as everywhere in the
  project.) For reference, parts that cannot be silently wrong: U3 pin 1 upper-left, U4 pin 1 lower-right, MK1 pin 1
  lower-right with the port ring at the top, U1 pad 1 upper-left with the antenna at the top (all seen from the back),
  and every SOT-23-3 (the single-pin side must match).
- Also **verified** in JLCPCB's FAQ: placement is "finalized … based on the CPL … and the PCB silkscreen markings", and a
  silkscreen dot at pin 1 "helps avoid engineering confirmation delays". The board's silk agrees with the pads for all
  of the above (LED dot at the GND corner = pin 1 in JLC's numbering, diode bar, mic dot), so their engineer and the
  CPL will be looking at the same thing.
- Smallest fix: add the table above to step 3 of `CLAUDE.md` and use it in the preview.

### T3 — The wand only works in one pose; touching a ring with its tip does nothing — **minor (usage, separate bare-board order, firmware debounce)** — angles 1, 4

- What is wrong: `extras.py` puts the magnet hole at the centre of the wand's flame bulb, **13.0 mm from the tip**
  (**verified**: `G.flame(5.0, 22.0)` → bulb centre y = 13.8, tip end y = 0.8). The DRV5032 measures only the field
  component through the board.
- Field at the sensor for a 5 × 2 mm N35 disc, exact cylinder model (`review3/wand.py`, **inferred**; thresholds
  **verified** in TI SLVSDC7H: B_OP 1.5 / 3.0 / 4.8 mT min / typ / max, B_RP 0.5 / 1.5 / 3.0):

  | Pose | Field through the sensor | Result |
  |---|---|---|
  | Bulb flat on the ring (magnet over the ring) | 119 mT | always triggers |
  | Wand flat, magnet 6–8.7 mm to the side | 3.0–3.6 mT (reversed sign) | typical part yes, least sensitive part no |
  | Wand flat, magnet 4.9–5.4 mm to the side | < 1.5 mT (the field changes sign at 5.0 mm) | **releases** |
  | Wand flat, **tip** on the ring (magnet 13 mm away) | 1.3 mT | no (only parts at the sensitive limit) |
  | Tip on the ring, wand tilted 20° / 45° | 0.8 / 0.4 mT | no |
  | Wand held like a match, perpendicular, any sideways offset | ≤ 0.9 mT | never |

- Consequences: "touch the wand to the ring" works only if the user lays the flame-shaped end flat over the ring.
  Sliding the wand across a ring gives on → off → on (the sign change), so one gesture can produce two edges.
  No magnet position in a flat PCB wand makes a tip-touch reliable at all angles (checked 4.5, 6 and 8.8 mm).
- Confidence: high on the geometry and thresholds; ±20 % on the field values (magnet grade, die depth).
- Smallest fix: no change needed to the menorah. Tell users (and yourself) "cover the ring with the wand's flame, flat";
  optionally add a silk or gold ring around the magnet hole in `extras.py` so the active spot is obvious. Firmware:
  latch on the first low edge and ignore further edges on that pin for about 0.5 s.

### T4 — Firmware cannot tell whether USB power is present — **minor (firmware feasibility; optional two-resistor bodge)** — angle 3

- What is wrong (**verified** in `netlist.py`): the only power-related inputs are CHRG_N (IO18) and VBAT_SENSE (IO8).
  CHRG is low only *while charging* (TP4057 sheet, `review/ds/C12044.txt`: high impedance in every other state; it
  pulses with a 0.5–2 s period when no battery is fitted). STDBY (pin 5) is not connected, VBUS is not routed to any
  GPIO, and CC is not readable. After the charge completes, "on USB with a full battery" and "on battery" look
  identical, and "no battery" looks like "full battery" (VBAT_SENSE reads the charger's 4.2 V on C5).
- Why it matters: any policy that depends on the power source (stay awake and keep Wi-Fi up on USB, deep-sleep on
  battery; brightness cap; "plugged in" indication) has nothing reliable to key on. USB plug-in can wake the board from
  deep sleep only when the battery needs charging (CHRG_N on IO18 is an RTC pin and can join the ext1 mask).
- Confidence: high.
- Smallest fix: none before ordering. After delivery, if wanted: two 0603 resistors from VBUS (C3 pad 1 or D1 anode)
  to GND with the midpoint wired to test pad IO47 or IO48 (150 k on top, 220 k to GND: about 3.0 V at 5 V). On a re-spin
  route STDBY or a VBUS divider to a GPIO. Otherwise firmware heuristics: CHRG low ⇒ USB; USB-Serial-JTAG host present
  ⇒ USB; battery voltage not falling under load ⇒ probably USB.

### T5 — The assembled menorah weighs about 46–56 g: a 15–20 gram-force push at a ring slides or tips it, and a USB-C cable will steer it — **minor (usage)** — angle 4

- Numbers (**inferred**, `review3` mass script from the Gerber outline: board 11 652 mm², FR4 + copper ≈ 40 g, parts
  ≈ 6 g, optional cell ≈ 10 g; centre of mass 56–65 mm above the table, x ≈ 98–103, between the feet at x = 55/145):
  pushing backwards at a candle ring (112–126 mm above the table) tips it at 14–19 gf and slides it at about 14–17 gf
  (µ = 0.3). Sideways it is stable (the plug axis is only 21 mm up; 84–103 gf to tip, it slides first). The feet have
  0.15 mm play in their slots and are held by friction only.
- Why it matters: the lighting gesture, the 160 gf tact switches and any normal USB-C cable all exceed what the object
  can resist. The hall sensors do trigger without contact, but people will touch.
- Smallest fix: museum putty or thin rubber bumpers under the four foot ends, a drop of glue in each half-lap joint,
  and a thin, flexible USB-C cable. No file change.

### T6 — Handling and depanelling: the hall-sensor capacitors sit in the highest-strain spot of each candle — **minor (order remark + handling; no file change)** — angle 4

- What is there (**verified** from the Gerbers and `netlist.py` line 139): C151–C159 (100 nF across +3V3) stand with
  their long axis *along* the candle, their upper pad 0.46 mm below the candle shoulder, directly beside the root of the
  5.5 mm flame neck. C13/C14 (22 µF across VLED) lie along the crossbar arms (already noted in REVIEW F11e).
- Why it matters (**inferred**, beam estimate, no FEA): bending a flame out of plane concentrates strain at the neck
  root. About 5 N (0.5 kgf) at a flame tip gives roughly 1 700 µε nominal there, more at the fillet; ordinary 0603
  capacitors start to crack around 1 500–2 500 µε. A cracked capacitor across +3V3 can turn into a short days later
  (the LDO's current limit and thermal shutdown keep that from being dangerous, but the board is dead). The most likely
  moment is not use but **snapping off the edge rails**: JLCPCB ships Standard PCBA with the rails attached
  (**verified**, capabilities page and FAQ).
- Smallest fix
  - Order remark: "Irregular outline. Please attach rails/tabs only on the straight bottom edge of the base (y = 152)
    and the lower edge of the crossbar; no tabs on flames, flame necks, candle tops or next to J1 (USB-C overhangs the
    left edge of the base by 0.5 mm)."
  - Remove the rails by cutting each tab with flush cutters while supporting the board next to the tab; do not flex.
    Always pick the menorah up by the base.
  - JLCPCB's FAQ recommends "bubble-wrap packaging or separator packaging" against surface scratches; worth selecting
    for a board whose front is glossy black and gold.

### T7 — Foot and wand boards contain no copper at all — **minor (separate optional orders)** — angles 2, 4

- **Verified**: in both zips `F_Cu`/`B_Cu` are empty (479 bytes) and the drill files have no hits; the only content is
  the outline and one back-silk label (`review3/ex/`).
- Why it matters: (a) forum reports (seen only as search-result excerpts, not opened) go both ways on whether JLCPCB
  accepts a copper-less board without a query; a query costs a day. (b) Black mask over bare laminate is visibly lighter and browner than black mask over
  copper — `CLAUDE.md` section 6 already describes that effect for the antenna area — so black feet and a black wand
  will not match the menorah.
- Smallest fix: for the **wand**, add a copper fill on both layers in `extras.py` (pulled back 0.5 mm from the edge;
  a gold flame at the tip is then free). For the **feet**, I would leave them copper-free and answer a query if one
  comes: an 80 × 18 mm floating copper plate would stand 6–10 mm from the module antenna (left foot at x = 55,
  antenna at x 61–79). They are seen edge-on, so the shade matters less.

### T8 — Firmware notes that follow from the hardware as built — **minor (firmware only)** — angle 3

| # | Note | Basis |
|---|---|---|
| a | Before deep sleep drive MIC_SCK (IO15) and MIC_WS (IO16) low and hold them (both are RTC pins). Otherwise SCK floats and the microphone may not stay in standby. | **verified**: ICS-43432 DS-000038 "Standby Mode": stop "both the SCK and WS clock signals and [pull] those signals to ground" |
| b | There can never be a 32 kHz crystal (IO15/16 carry the microphone). Deep-sleep time runs on the internal RC oscillator, which drifts with temperature. After a wake from deep sleep, re-sync NTP before deciding which night it is; do not trust the RTC near sunset. | **verified**: ESP-IDF "System Time" (RTC clock sources); pin map |
| c | Drive IO6 low *before* raising VLED_EN, and keep it driven; U4's input floats otherwise and the first LEDs latch garbage. If LED flicker is ever seen, set IO6 to the weakest drive strength: the 3.3 V data line is 155 mm long and unterminated at the source (R11 is after U4). | **verified** length (board), **inferred** signal integrity |
| d | Budget for a 500 mA source: the board cannot read CC. Charger ≈ 300 mA + ESP32 ≈ 100 mA leaves about 100 mA for LEDs on a plain USB-A port. | **inferred** |
| e | Hall inputs: latch on the first edge (T3); a wand left on a ring holds an ext1 "any low" wake asserted, so mask that pin before sleeping. | **verified**: ESP-IDF sleep modes (ESP_EXT1_WAKEUP_ANY_LOW, GPIO 0–21) |
| f | First flash of a blank module: hold BOOT, tap RESET, then flash over USB. There is no power LED; the first sign of life is the "USB JTAG/serial debug unit" enumerating. | **inferred** from Espressif boot-mode behaviour |
| g | Sleep budget: add D1's reverse leakage (5–20 µA typical, flows VSYS → D1 → R5) to the 110–130 µA in REVIEW2. | **inferred** |

---

## 2. Hypotheses tested and ruled out

Fab artefacts (all **verified** by my own Gerber/Excellon parser, `review3/gerb.py`, `g2b.py`–`g8.py`):

- **Copper does not implement the netlist** — connectivity rebuilt from the two copper Gerbers plus plated-hole
  geometry only: 83 nets, 0 opens, 0 shorts, 0 floating copper pieces, no pad missing or extra; the Gerbers' own net
  attributes agree with the geometry. Still true after shrinking or growing all copper by 0.09 mm.
- **Outline not closed / cut-outs missing** — 1 950 segments form exactly 48 closed loops (outline + 47 LED cut-outs of
  3.60 × 3.27 mm); every endpoint has degree 2, no near-miss gaps.
- **Copper, mask, paste or silk over an edge or in a cut-out** — nothing on any layer within 0.24 mm of a routed edge
  except one silk line (below). LED pads are 0.27 mm from their own cut-out, as in the reference footprints.
- **Vias not tented** — no mask opening on either side touches any of the 191 via pads (closest: the gold border line
  passes 0.09 mm from 41 candle via pads; C3's pad opening touches a VBUS via pad of the same net by 5 µm).
- **Front mask artwork over bare laminate or over signal copper** — 0 mm² of opening off copper; only GND is exposed
  (1 606 mm²); gold stops 0.4 mm from every LED window and from the outline.
- **Paste layer wrong** — 152 footprints with paste = 152 CPL rows = 152 BOM designators. No paste on the six test
  pads or the four USB shell slots; the microphone ring has the four arcs its datasheet asks for; nothing printed off a
  pad. The 188 LED pads *do* have paste, and must: the reverse-mount LED's leads are soldered to those back-side pads.
- **Drill and Gerber frames differ** — all 195 plated hits sit inside copper with ≥ 0.1 mm annulus on both layers; the
  three NPTH coincide with their mask openings; metric, decimal; no hole within 0.5 mm of another or of an edge.
- **Zip differs from the folder** — 13 files, byte-identical.
- **Stray features a CAM operator would query** — the zero-size aperture is used only for filled regions; no clear
  polarity anywhere; 2 zero-length track stubs and 4 doubled USB pad flashes (overlapping A/B pads), all harmless.
  80 mask slivers of about 0.01 mm² where hall rings meet the border line will simply not print.
- **CPL fix misapplied** — see T2: independently re-derived, all parts fit.

Electrical / bring-up:

- **Tact-switch pairs wired across the contact (EN or IO0 held low for ever)** — XKB drawing (`review/ds/sw-1.png`):
  A–B and C–D are the common pairs, each along one row, matching KiCad pads 1/1 and 2/2 and JLC's footprint. **verified**
- **ROM drives a hall pin in USB-OTG download mode** — GPIO21 (HALL_C4) is listed as INPUT. **verified** (Espressif
  hardware design guidelines, saved copy)
- **Power-up glitches** — IO17 (VLED_EN) glitches low, i.e. off; the 60 µs low glitch on the hall pins is a harmless
  contention with push-pull outputs; IO18's high glitch meets an open drain. **verified** (glitch table)
- **Wake from deep sleep impossible with idle-high sensors** — ESP_EXT1_WAKEUP_ANY_LOW exists on the S3 for GPIO 0–21
  and works with RTC peripherals off; sensors are push-pull and stay powered. **verified** (ESP-IDF docs)
- **Charger status pin back-feeds or leaks** — CHRG is rated 10 V, ≤ 1 µA leakage. **verified**
- **TP4057 overheats** — about 0.5 W at 300 mA; the sheet's θJA 150 °C/W and 120 °C thermal regulation make it
  self-limiting. It will be too hot to touch during bulk charge; the battery zone starts 17 mm away. **verified/inferred**
- **D1 leakage lifts Q1's gate on battery** — tens of µA × 2.2 kΩ = tens of mV. **inferred**
- **Hot-plug or rail ramp turns the LED rail on** — C9 is gate-to-source, so the gate follows VSYS. **inferred**
- **LED data ringing or crosstalk corrupts data / fakes a hall edge** — ring-back stays below U4's threshold and is
  nanoseconds wide; coupling into the adjacent hall line (0.21 mm gap, 30 mm) is about 0.3 V for 20 ns. **inferred**
- **Mic SD floating half of each frame picks up SCK** — only in the unused channel slot. **inferred**
- **Wi-Fi blocked by copper** — both layers are copper-free for 15 mm either side of the antenna row and the antenna is
  at the top edge of the base; nearest copper is 0.4–0.6 mm below the antenna area (the module's own ground side).
  **verified** from the Gerbers

Process / physical:

- **JLCPCB prints an order number on the clean front** — "Order Number is not available since May 2026"; "No mark will
  be added on the PCB by default". **verified** (jlcpcb.com help, "How to mark on PCB")
- **JLCPCB drills tooling holes into the artwork** — only for Economic PCBA; this board must be Standard (rails).
  **verified** (FAQ)
- **Board wash destroys the microphone** — no-clean flux, not washed unless requested. **verified** (FAQ)
- **Fragile necks from 47 cut-outs and two slots** — narrowest web 2.65 mm (flame LED corner to flame edge); the board
  stays one piece when eroded by 1.25 mm all round. **verified**
- **Feet collide with parts or plugs after the slot change** — seated foot top at y = 134.29, feet 0.29 mm proud of the
  base; 1.19 mm below J2's pad, 1.2 mm from SW1/SW2 pads, ≥ 1.23 mm from J1, R3, U5, TP3, TP4; the JST plug and the
  USB plug pass clear. **verified** geometry
- **Exposed copper under the battery** — no back mask opening inside the battery zone. **verified**
- **Silk labels contradict the nets** — "+" is at the VBAT pad row, "−" at the GND row; RESET is beside SW2 (EN), BOOT
  beside SW1 (IO0); TX, RX, IO47, IO48, GND, +3V3 sit at the pads carrying those nets. **verified** (Gerber silk
  positions against pad nets)
- **Documentation disagrees with the files** — pin table, chain order (D101 at C1 bottom … D147 at C8 flame), BOM
  values, foot dimensions and the J2 clearance in `CLAUDE.md` all match `netlist.py`, the CPL and the geometry. Only
  stale items: `netlist.py` line 96 comment "soft start (10 ms)", and "22 µF … at both ends of the crossbar" (they are
  at x = 42 and 158).
- Noted, no action: the battery-zone silk line at x = 144 runs 0.05 mm from the right foot slot and will be chipped
  (hidden by the foot); the four gold USB shell slots and two peg holes are visible on the front at the left end of the
  base; the 191 tented vias will show as small dimples in the black.

---

## 3. Disagreements with the earlier reviews

1. **REVIEW F10** ("it triggers anywhere within ≈ 9 mm (worst part) to ≈ 14 mm (most sensitive part) sideways"): the
   dipole estimate ignores that the through-board field changes sign about 5 mm off-axis. With an exact cylinder model
   the outer lobe peaks at 3.6 mT, below the least sensitive part's 4.8 mT, so a worst-case sensor triggers only within
   about 4.5 mm; a typical one within about 8.7 mm with a dead band at 4.9–5.4 mm; the most sensitive within about
   12.3 mm. The conclusion "no false trigger of the neighbour" stands (0.32 mT at 22 mm). See T3.
2. **REVIEW2 N1** ("The differences for the 3-pin SOT-23s, U4, U5 and the LEDs are 0°/180° results, so they do not
   depend on whether JLC counts clockwise or anticlockwise"): U5's correction is a 90° one (90 → 0), as are U2, U3 and
   MK1. Those four do depend on the handedness of the convention. I re-derived it and the applied values are
   consistent, so the fix stands; the stated independence does not.
3. **REVIEW2 sleep budget** (110–130 µA) assumes the microphone is in standby and leaves out D1's leakage; see T8 a, g.
   Small.

Everything else I touched agreed with the earlier reviews.

---

## 4. Could not verify — what a human should do

1. **JLCPCB's real pick-and-place orientation** — check the preview with the table in T2, then tick "Confirm parts
   placement".
2. **How JLCPCB will rail an outline whose top is nine flame tips** — their default is 5 mm rails on two sides with
   V-cut, which this outline does not allow. Put the remark from T6 in the order and expect a question; answer it the
   same day.
3. **Lead time** — JLCPCB states Standard PCBA build time "≥ 4 days" on top of PCB fabrication (capabilities page),
   plus shipping. Ordering on Tuesday makes the first night (Fri 4 Dec) uncertain; every item above that touches the
   order can be done today. Baking may add time: ask.
4. **Whether JLCPCB solders the four USB shell tabs** (no paste in the Gerbers; carried over from both reviews) —
   inspect on arrival, hand-solder if dry.
5. **Whether a copper-less foot/wand order passes without a query** (T7).
6. **The magnetic numbers in T3 and the strain numbers in T6** are calculations. After delivery, try the wand in the
   poses of T3 before writing the hall logic.
7. **Whether black mask closes every 0.3 mm via tent** on the front — cosmetic only.
8. **RF range** — geometry is good (section 2); not measured.

## Sources actually read in this session

- JLCPCB: "Common PCBA after-sales issues and FAQ" (full text saved), "How to mark on PCB", "How to add edge
  rails/fiducials for PCB assembly order", PCB assembly capabilities, PCB assembly FAQs part 2; saved part pages for
  C5149201, C574021, C2913201 (from the earlier reviews' folders).
- Espressif: ESP32-S3 hardware design guidelines, schematic checklist (saved copy: pin defaults, power-up glitches,
  USB-OTG download pads); ESP-IDF stable docs for ESP32-S3 "Sleep Modes" and "System Time".
- Datasheets (earlier reviewers' copies, re-read where cited): TI DRV5032 SLVSDC7H, InvenSense ICS-43432 DS-000038,
  Top Power TP4057, XKB TS-1187A drawing; EasyEDA/LCSC footprints and symbols for 18 LCSC numbers.
- Tools: Bouni kicad-jlcpcb-tools `fabrication.py` (earlier copy); KiBot notes on position files (search result).

## Scratch files (`review3/`)

`gerb.py` Gerber/Excellon parser · `g1.py` aperture usage · `g2b.py` outline loops and webs · `g3.py` layer-vs-layer ·
`g4.py` connectivity vs netlist · `g5.py` paste/mask/silk/CPL · `g6.py` front mask artwork · `g7.py` etch tolerance ·
`g8.py` edge, cut-out, battery-zone and foot distances · `cpl1.py`, `cpl2.py`, `ee1.py` CPL placement check ·
`pin1.py` pin-1 table · `wand.py` hall field · `b1.py` texts and track lengths · `rb/` renders from a board copy ·
`ex/` unpacked zips · `dl/jlc_faq.html`.
