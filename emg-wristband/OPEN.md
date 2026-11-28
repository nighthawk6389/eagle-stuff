# Open items: main pod rev A

State on 2026-11-28, after the schematic, the owner's decisions and the first layout. Nothing has been
ordered or built. "Checked" means read from the document named in `docs/sources.md`; anything else is
flagged. The layout's own open points are in "Layout" below.

## Decided by the owner on 2026-11-28

1. **Sense XIAO on Standard assembly.** The XIAO is now the Sense version, JLCPCB C17401557 (123 in
   stock, "Standard Only"), so the whole order is Standard assembly. This overrides the handoff's
   "no Standard Only parts" rule for this one part. IMU and microphone are on the module; the 11th pin
   carries DRDY_B. Every other BOM line is still cleared for Economic.
2. **Series resistors: 47k** (was the 22k placeholder), on my recommendation. Reasoning below.
3. **Motor on two wire pads**, accepted.
4. **Digital supply stays on while the analog supply is off**, accepted on my reading of the datasheet
   (section below).

### What Standard assembly changes for the order

Read on 2026-11-28 from jlcpcb.com/capabilities/pcb-assembly-capabilities: Standard assembly takes
single boards from 70 x 70 mm to 460 x 500 mm, and lists edge rails and fiducials as "Necessary"
(Economic: 10 x 10 mm upwards, rails and fiducials "Not necessary").

The pod is 49 x 49 mm. A 5 mm rail on two sides makes it 59 x 49 mm, still under 70 in both
directions, so rails alone are not enough: it needs a panel (2 x 2 boards is 98 x 98 mm before rails)
or rails about 10.5 mm wide on all four sides. **Not settled.** The files in `out/fab/` are for the
single board, with no rails, no fiducials and no panel. Choose at quote time whether JLCPCB builds the
panel or a panel drawing is added here.

### Why 47k

- Any current through the wearer goes in through one skin-facing line and out through another, so it
  crosses two of these resistors: 94k. A fault that puts 3.3 V across that path drives 35 uA; the full
  4.2 V of the cell, 45 uA. With 22k those were 75 and 95 uA. The 50 uA single-fault figure I am
  comparing against is the patient-auxiliary-current limit of IEC 60601-1 **as I remember it; I have
  not read the standard**, and this is a hobby device, not a medical one.
- Noise cost is small. Two 47k resistors add 0.90 uVrms in the 524 Hz band; the converter itself is
  1.1 uVrms at 2 kSPS and gain 6 (SBAS459K table 1). Together 1.42 uVrms, against 1.26 with 22k, and
  against the 2.46 uVrms Meta reports for its whole system.
- The input filter corner moves to 72 kHz with the 47 pF capacitors, still far above the signal band.

## Accepted, to check at bring-up: digital supply on while the analog supply is off

As drawn, DVDD is the XIAO's 3.3 V rail and is always on; the interlock switches only AVDD. The owner
accepted this on 2026-11-28 on my reading of the datasheet, given below. It is still not confirmed by
TI, so the first board gets the check at the end of this section before electrodes go on skin.

What the owner's saved copy of TI forum thread 870302 (ADS1299, the sister part) says. Two TI engineers:

- Ryan Andrews: "The primary concern is that the pins could become damaged if voltage is applied to the
  pins before DVDD is enabled. For example, if your MCU is powered before DVDD of the ADS1299 is
  enabled, the MCU SPI/GPIO outputs may apply voltage to the ADS1299 digital inputs, which can damage
  the device." Pins on pull-ups may rise with the supply. MCU outputs should stay high-impedance until
  DVDD is up; then reset the part and check its device ID.
- Alexander Smith: ignoring the power-up sequence most likely leaves the part in an unknown state, with
  a wrong device ID and false readings.

What that settles: DVDD should not be switched off behind a powered MCU, which is the argument for the
design as drawn (DVDD and the MCU share one rail, so no input can exceed DVDD). It also supports the
PWDN pull-ups and the CLKSEL straps.

What it does **not** settle: the thread never mentions the AVDD - DVDD row of the operating table
(-2.1 V to +3.6 V; this design sits at -3.3 V while AVDD is off). My earlier note that TI had said the
row "only applies to normal operation" came from a search-engine summary and is **not in the thread**;
treat it as unsupported. My own reading stands (-2.1 V is the lowest allowed AVDD, 1.5 V, minus the
highest DVDD, 3.6 V, so it describes running conditions; the absolute-maximum table has no such
limit), but it is a reading, not a statement from TI.

To close it, ask TI on the forum: "ADS1298, AVSS = DGND, DVDD = 3.3 V always on. Is it acceptable to
hold AVDD and AVDD1 at 0 V for hours (analog LDO disabled) and later power them up and pulse RESET?
Does the AVDD - DVDD >= -2.1 V row apply while AVDD is off?" If the answer is no, the fix is a load
switch on DVDD plus a buffer isolating the six MCU-driven lines, on the MCU and power sheets only.
Bring-up check either way: measure DVDD current with AVDD off.

## Values that are placeholders or my choice, not from a datasheet

| Part | Value | Status |
|---|---|---|
| RN101-RN104, RN201-RN204 (sense lines, four resistors each) | 47k, 5 % | Decided 2026-11-28, reasoning above. Arrays (C2028) because 32 single 0402 parts did not fit between connector and converter; their 5 % tolerance only shifts the filter corner |
| R125 (bias line) | 47k | Same as the sense lines, so every skin-facing line has the same limit |
| C101-C116, C201-C216 (input filter) | 47 pF C0G to ground | My choice. Corner 72 kHz with 47k. The datasheet (10.1.3) only says a single pole is usually enough and a wide bandwidth protects common-mode rejection. Every pF here also loads a dry electrode, so smaller may be better |
| R124, C140 (bias feedback) | 1 Mohm, 1.5 nF | Datasheet "typical values for example only". Loop stability with real electrodes is untested |
| R20, R121, R221, R123 (series, SCLK / DOUT / CLK) | 33 ohm | My choice; the datasheet says "termination resistors as needed". Can be fitted as 0 ohm |
| R120, R220 (PWDN pull-up) | 10k | From TI's evaluation board, not the datasheet text |
| R1, R2, R3, R4, C3 (interlock) | 10k, 100k, 10k, 10k, 100 nF | Calculated on the power sheet from the LP5907 and AO3400A datasheets |
| R223 (clock pull-down on converter B) | 100k | My choice, so the input is not floating before firmware enables converter A's clock output |
| R5 (motor) | 12 ohm 0805 | Calculated on the power sheet for the Leader LCM1027B3605F (3.0 V rated, 3.3 V maximum, 70 mA). Recalculate for any other motor |

## Things I assumed and did not prove

- **Bypass layout.** Figure 106 shows one 1 uF + 100 nF pair on AVDD/AVDD1 and one on DVDD. I drew four
  pairs per converter (two AVDD pin groups, AVDD1, DVDD), which is what TI's evaluation board fits.
- **RLDINV link (R224).** Figure 45 joins the RLDINV pins of all devices; I did that through a 0 ohm
  link. It is a high-impedance node running between the two blocks. Remove R224 if it picks up noise;
  then only converter A's eight channels feed the bias loop.
- **RLDREF left open** on both converters (internal mid-supply reference chosen in firmware). The
  datasheet gives no instruction for the unused pin; TI's evaluation board leaves it open by default.
- **ESD array channels.** Each array still guards two whole pairs, but which channel takes which line
  was chosen so the four lines reach the array on the back without crossing (table `ESD_IO` in
  `gen/design.py`). The channels of a TPD4E001 are identical, so this changes nothing electrically.
- **ESD array supply.** TPD4E001 VCC is on AVDD (datasheet option a). With AVDD off the electrode lines
  clamp about a diode drop above ground. Option b (VCC on its capacitor only) is the alternative.
- **SPI pins.** SCLK and MISO are on D5 and D4, the only two XIAO pins Nordic does not mark as
  low-frequency I/O. This departs from Seeed's default SPI pins (D8-D10). MOSI is on D10, a
  low-frequency pin, on the argument that it only carries occasional commands.
- **Interlock is one transistor.** If Q1 or its joints fail open, the hardware lock is gone and only the
  firmware check remains. Suggested firmware self-test: with USB attached, raise AFE_EN and confirm the
  converters stay dead.
- **Interlock threshold on battery.** The XIAO's own diode D1 leaks from VIN back to VBUS. R3 + R4 (20k)
  in parallel with Seeed's 100k keep that below Q1's threshold up to about 78 uA of leakage. Not measured.
- **Battery polarity.** J1 pin 1 is VBAT, pin 2 ground (same as the menorah board). There is no
  reverse-polarity protection on the pod or on the XIAO.
- **Low battery.** U2 can only hold 3.0 V while the cell is above 3.0 V plus its dropout (120 mV typical
  at the full 250 mA, less at this load). Below that AVDD follows the cell down; the converters work to 2.7 V.
- **Connector pin order, now fixed by the layout.** Pin 1 bias, pins 2, 19 and 20 shield, pins 3 to 18
  the lines in converter pin order: 8N, 8P, 7N, 7P ... 1N, 1P (channel 8 first). Each line runs
  straight from its connector pin to its converter pin. The strip must match, and the FH12 is a
  bottom-contact connector, which fixes which face of the strip tail carries the contacts. Both
  connectors open towards the bottom edge of the board.

## Firmware must do these (the hardware depends on it)

- Hold SCLK, MOSI, both CS, START and RESET low while AVDD comes up; then wait 2^18 clock periods
  (128 ms at 2.048 MHz) and for VCAP1, then pulse RESET.
- Set CLK_EN on converter A before talking to converter B, which has no clock until then.
- Leave GPIO1-4 of both converters as inputs (reset default); they are shorted to ground.
- Keep converter B's bias amplifier powered down; select the internal reference and enable the bias
  amplifier on converter A only.
- Refuse to stream while USB is detected (second layer behind the interlock).
- Drive P0.13 low for the 100 mA charge current.
- Do not enable pull-ups toward the converters while AVDD is off.

## Layout

The board is `pod/emg-pod.kicad_pcb`: 49 x 49 mm, four layers, 124 assembled parts, all on top.
KiCad 9.0.9 DRC, with the rules listed in `docs/sources.md`, reports 0 errors, 0 warnings and nothing
unconnected (`out/drc.rpt`). `gen/fab.py` also compared all 547 pads with the net tables in
`gen/design.py`: no difference. DRC checks the board against its own rules and nets; it says nothing
about whether the circuit works, and nothing here has been built.

How it was routed: `gen/board.py` draws 861 fixed tracks and vias (the electrode lines and what is
listed in `README.md`); Freerouting and `gen/finish.py` did the rest. 466 vias in all, 239 of them
ground.

### Where the layout departs from the handoff

- **Size: 49 x 49 mm**, not "about 40 x 45". It is inside the 50 x 50 limit with 1 mm to spare. Each
  converter block is 24.5 mm wide: the chip, a column of bypass capacitors and a column of eight
  filter capacitors on each side of it, all on the top. It gets smaller only with parts on the back
  or 0201 capacitors, and both were ruled out.
- **The antenna end of the XIAO is not at a board edge.** The USB socket has to be at an edge and the
  module is 21 mm long, so its other end, with the antenna, lies 28 mm in from the left edge, 1 mm
  below the top edge, pointing at the test points and the regulator. All four layers are kept free
  of copper in a 5 x 8.4 mm window under and in front of it (x 26.2 to 31.2, y 4.0 to 12.4 mm). **That
  window is my guess; I found no Seeed drawing of the antenna's position or of the clearance it
  needs.** Expect less range than a bare XIAO. Check at bring-up by comparing signal strength with a
  bare one at the same distance. If it is poor: cut a slot in the board under the antenna, or turn
  the module round so the antenna reaches the right edge and plug USB in across the board.
- **Supplies share layer 3.** +3V3 above y = 27.6 mm, the 3.0 V analog rail below, ground fill in the
  rest. Layer 2 is ground with no splits; its only openings are via holes and the antenna window.
- **Four bare pads on the back** (SWDIO, SWCLK, NRST, GND) under the XIAO's own SWD pads, for a probe.
  No parts are assembled there, so assembly stays single-sided.
- **"Route each pair together"** holds from connector to converter: the two lines of a pair are
  neighbours all the way, 0.5 mm apart, over the ground plane. It does not hold for the short
  branches to the ESD arrays and the filter capacitors, which fan out on the back one by one.

### Not verified

- **Assembly panel.** See "What Standard assembly changes for the order" above.
- **Rotations in the placement file** (`out/fab/cpl-jlcpcb.csv`) are KiCad's angles with no correction
  for JLCPCB's reel directions. Check every polarised part in JLCPCB's placement preview before
  paying: U1, U2, U100, U200, the ten ESD arrays, Q1, Q2, D1, C130, C230, J1, J100, J200.
- **Tracks and vias under the strip connectors.** Each electrode line has a branch and a via under the
  connector body (that is where the ESD arrays tap in). Hirose's land drawing marks no area as
  closed to copper there, and the vias are covered by solder mask in the Gerbers, but I have not seen
  it confirmed that the FH12's housing or contacts cannot touch the board surface. Order with vias
  tented (or plugged), and look under a connector on the first board.
- **JST battery connector footprint**, tantalum and diode pad 1: as before, not checked against the
  makers' drawings (`docs/sources.md`).
- **The XIAO's two NFC pads have no lands** (footprint `XIAO-nRF52840-SMD-noNFC`). They are unused; the
  module's pads rest on solder mask there. Whether JLCPCB can paste and reflow the pads under the
  module at all is still not confirmed.
- **Same-net track spacing.** JLCPCB's page lists 0.25 mm; nothing here checks it.
- **Thermal and current checks: none done.** Tracks on VBAT, the motor nets and VBUS are 0.25 mm;
  the largest load on them is the motor, 70 mA (120 mA at start).
- **No signal-integrity or noise analysis.** The autorouter did not keep the digital lines short: SCLK
  is 29 mm from the XIAO to its series resistor R20 and 63 mm of track from there to the two
  converters, MISO is 63 mm, the converter clock from A to B 51 mm. Each has a 33 ohm series resistor
  at its source. Nothing was simulated.
- **Digital signals near the inputs.** The routers were kept out of the areas around the input lines
  (the fan-out on the back around each converter, the stubs under it on the front), and `gen/fab.py`
  confirms no routed track is inside them. It also measures how close the tracks and vias of any
  other signal come to those of an input line on the same layer: the nearest is one via of the
  converter clock, 0.61 mm centre to centre from a fan-out lane of converter B. No other signal
  comes within 1 mm (CS_A 1.06 mm, START 1.07 mm, CS_B 1.19 mm). Crossings on the opposite outer
  layer have both planes in between and are not counted. Whether that is quiet enough is for the
  first board to show: record with the inputs shorted and look for the 2 kHz frame rate and its
  harmonics.
- **The autorouted part was not reviewed track by track.** I looked at the pictures of both copper
  layers and rely on DRC for the rest. The fixed routes (electrode lines, their fan-outs, supply and
  ground vias at the converters, VCAP1, CLKSEL) are drawn by `gen/board.py` and were checked there.
- Stock was read on 2026-11-28 (`out/stock-check.md`); rerun `tools/stock_report.py` before ordering.

## Answers to the handoff's open items

- Sense stock and assembly type: in stock (123), Standard Only; the owner chose Standard assembly.
- XIAO 5V pin and battery pads: the 5V pin is the USB VBUS net, wired straight to the connector and the
  charger input; the BAT pad is the charger output with 2.2 uF on it. Same in Seeed's v1.1 and v1.2
  schematics. On battery the 5V pin is pulled to ground by 100k.
- Electrode series resistor: 47k.
- Supply sequencing: on my reading the datasheet does not forbid it, but TI has not confirmed that; accepted by the owner, check at bring-up (above).
