# Open items: main pod rev A

State on 2026-11-28, after the schematic, the owner's decisions, the first layout, an independent
review, the rework that followed it, three small additions, the assembly frame and a second review
of all that. Nothing has been ordered or built. **Read "Second review" below before ordering: one of
its findings should be fixed first.** "Checked" means read from the document named in `docs/sources.md`; anything else is
flagged. The layout's own open points are in "Layout" below.

## Decided by the owner on 2026-11-28

1. **Sense XIAO on Standard assembly.** The XIAO is now the Sense version, JLCPCB C17401557 (120 in
   stock, "Standard Only"), so the whole order is Standard assembly. This overrides the handoff's
   "no Standard Only parts" rule for this one part. IMU and microphone are on the module. Every other
   BOM line is still cleared for Economic.
2. **Series resistors: 47k** (was the 22k placeholder), on my recommendation. Reasoning below.
3. **Motor on two wire pads**, accepted.
4. **Digital supply stays on while the analog supply is off**, accepted on my reading of the datasheet
   (section below).
5. **Review findings**: the owner approved everything I recommended. Done: converters powered down
   with the analog rail, a link in their digital supply, pull resistors on the SPI lines, a notch
   under the antenna (which costs the second DRDY pin), and the layout faults. Accepted as they are,
   to test on the first board: the ESD arrays on stubs and the filter capacitors' distance from the
   pins. Details under "Independent review" below.
6. **Three additions and the assembly frame** (asked for after the rework). A 3.3 V pad on the back
   beside the SWD pads, a ground post for a scope clip, a 1206 motor resistor, and the pod drawn
   inside a 74 x 74 mm frame for Standard assembly (next section).

### What Standard assembly changes for the order

Read on 2026-11-28 from jlcpcb.com/capabilities/pcb-assembly-capabilities: Standard assembly takes
single boards from 70 x 70 mm to 460 x 500 mm, and lists edge rails and fiducials as "Necessary"
(Economic: 10 x 10 mm upwards, rails and fiducials "Not necessary").

The pod is 49 x 49 mm, so it is ordered inside a frame: `pod/emg-pod-panel.kicad_pcb`, written by
`gen/panel.py`, with its own files in `out/fab-panel/` and a picture in `out/panel-top.png`.

- 74 x 74 mm outside (the minimum is 70; the second review pointed out that exactly 70 leaves nothing
  to spare). The pod sits in the middle with a routed slot around it, 2 mm wide (3 mm on the right,
  where the XIAO's USB socket overhangs). Rails 10 mm left and right, 10.5 mm top and bottom.
- Five tabs, 5 mm wide, hold the pod: top edge x 15.5 to 20.5, right edge y 19 to 24, bottom edge
  x 22 to 27 (between the strip connectors), left edge y 9 to 14 and y 17.5 to 22.5. Each has a row of
  six 0.5 mm holes, 0.8 mm apart, lying just outside the pod's edge, so the pod's outline and its
  0.3 mm copper setback are untouched.
- Three 1 mm fiducials (2 mm mask opening) and four 2 mm tooling holes on the rails, all centred
  3.85 mm from the frame's edges. No copper in the frame otherwise.
- The script does not move the pod or refill its zones. It compares every track, via, pad and zone
  fill with the single board (identical), and the placement file is byte-for-byte the single
  board's. DRC on the frame: 0 errors, 0 warnings (`out/drc-panel.rpt`).

To order: upload `out/fab-panel/emg-pod-panel-gerbers.zip` (74 x 74 mm, 4 layers), with
`bom-jlcpcb.csv` and `cpl-jlcpcb.csv` from the same folder, and do not ask JLCPCB to add rails.
`out/fab/` still holds the single board, for a bare-board order or another assembler.

After delivery: **cut each tab** along its row of holes with flush cutters and file what is left.
Do not snap them. 0402 ceramic capacitors stand 1.35 mm from the left and right edges from y = 26
down (the nearest tab ends 2.7 mm from one), the tantalum C230 is 1.65 mm from the right edge
beside the tab there, and at the bottom tab a via of an electrode line is 0.59 mm from the edge. Until filed, the remains of a tab stand up to 0.5 mm proud of a 49 mm board
whose limit is 50 mm.

Not verified:

- **Nobody at JLCPCB has seen the frame.** Their rule pages describe panels of several boards (board
  spacing 1.6 or 2 mm, tabs of 5 mm with perforations, holes 0.5 to 0.8 mm with 0.2 to 0.3 mm between
  them, rails of 5 mm or more, the fiducial and tooling-hole sizes above). I applied those numbers to
  a frame around one board. Their engineers check every assembly order and may ask for changes.
- **Which "Delivery Format" to tick.** JLCPCB's ordering notes accept customer-made panels under
  "Panel by Customer" (up to 10 designs) and say that under "Single PCB" a customer-panelised file
  may hold up to 5 designs. I found no statement for one board in a frame. I would choose "Panel by
  Customer", 1 column by 1 row, and say in the order remark that the frame is the assembly rail.
- **Where the order number is printed.** I could not read JLCPCB's page on it. Pick the option on the
  order form that puts it on the frame or leaves it off.
- **No USB plug while the pod is in the frame.** The rail starts 1.5 mm beyond the socket's mouth and
  a plug's body would hit it (second review, by estimate: the XIAO's height is not published). Cut
  the pod out before the first power-up over USB.
- **Routing of the slots.** The slot corners are drawn square; the cutter leaves them rounded, so a
  sliver of laminate joins each tab's flanks to the pod beside the outermost holes. Flush cutters
  deal with it.

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

DVDD is the XIAO's 3.3 V rail (through link R21) and is always on; the interlock switches only AVDD.
The owner accepted this on 2026-11-28 on my reading of the datasheet, given below. It is still not
confirmed by TI, so the first board gets the check at the end of this section before electrodes go on
skin. Since the rework both converters are also held in power-down (PWDN low) whenever AVDD is off,
so their digital sections are not running in that state, and R21 gives a place to measure the DVDD
current: lift it and bridge its pads with a meter.

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
| R120, R220 (chip-select pull-ups), R22, R23 (START and SCLK pull-downs) | 100k | My choice. They only have to define the lines while the MCU pins float |
| R1, R2 (enable divider, also the converters' PWDN) | 1k, 10k | Calculated on the power sheet from SBAS459K's digital input limits: high is 0.91 x DVDD against 0.8 needed **if the MCU pin delivers the full 3.3 V; it does not quite, see F2 under "Second review"**; low holds at 0.2 V against the 10 uA each of the two PWDN inputs. The reviewer suggested 1 Mohm for R2; that would not hold the node low against that input current, so I chose these instead. Cost: 0.3 mA while the analog rail is on |
| R3, R4, C3 (interlock) | 10k, 10k, 100 nF | Calculated on the power sheet from the AO3400A datasheet |
| R21 (link in the converters' digital supply) | 0 ohm | So the DVDD current can be measured |
| R223 (clock pull-down on converter B) | 100k | My choice, so the input is not floating before firmware enables converter A's clock output |
| R5 (motor) | 12 ohm, 1206, 0.25 W (C17913) | Calculated on the power sheet for the Leader LCM1027B3605F (3.0 V rated, 3.3 V maximum, 70 mA). 1206 because a stalled motor at 4.2 V puts about 0.15 W into it (power sheet). Recalculate for any other motor |

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

- Converter B has no clock after a pin reset: RESET is shared and clears converter A's CLK_EN bit. Set
  CLK_EN on A again, wait 2^18 clock periods (the datasheet's reset timing only starts once the
  external clock is valid), then reset B with the SPI RESET command.
- Pins: START is on D3, D6 is not connected, only converter A's DRDY reaches the MCU (D2).
- AFE_EN (D8) switches the analog rail and, through the same net, releases both converters from
  power-down. After raising it wait 2^18 clock periods (128 ms at 2.048 MHz) and for VCAP1, then
  pulse RESET. Keep SCLK, MOSI, START and RESET low until then. The chip selects have pull-ups.
- Set CLK_EN on converter A before talking to converter B, which has no clock until then.
- Leave GPIO1-4 of both converters as inputs (reset default); they are shorted to ground.
- Keep converter B's bias amplifier powered down; select the internal reference and enable the bias
  amplifier on converter A only.
- Refuse to stream while USB is detected (second layer behind the interlock), and take AFE_EN low:
  with USB attached and AFE_EN high the pin pushes 3.3 mA through R1 into the interlock transistor.
- Configure D8 (AFE_EN) as a high-drive output, so the converters' PWDN level has margin (F2 below).
- Drive P0.13 low for the 100 mA charge current.
- With AFE_EN low the converters are in power-down; do not clock SPI at them in that state.

## Independent review, 2026-11-28, and what was done about it

A second reviewer (a fresh AI session with only the files, asked to act as a PCB design engineer)
went through the schematic, the board and the outputs against published guidance (SparkFun's layout
tutorials, TI SBAS459K sections 11-12, TI SLVA680A, the antenna maker's sheet, JLCPCB's pages). It found
nothing that stops the circuit working, and the pin maps of every polarised part and of the XIAO
footprint correct. I re-measured its main findings on the board before acting on them. The owner
then approved the changes I recommended; the board was re-routed with them.

Changed:

- **R1. Converters never powered down.** PWDN of both converters is now on AVDD_EN, the regulator's
  enable net, so they are in power-down whenever the analog rail is off (MCU in reset, USB plugged
  in, firmware idle). The enable divider became 1k / 10k for that (table above). R21, a 0 ohm link,
  now feeds the converters' digital supply (net DVDD) from the XIAO's 3.3 V. Still to measure on the
  first board: the DVDD current with AFE_EN low. The pod still has no power switch; with the
  converters down, what is left is the XIAO's own sleep current.
- **R2. Antenna.** The board is cut away under and in front of the antenna: a notch 7 mm wide from
  the top edge down to y = 12.4 mm (x 25 to 32). The chip antenna, at (29.1, 8.1) by Seeed's board
  file, now has no pod copper or laminate within 2.7 mm below it and 3.3 mm in front of it, and is open
  to the top edge. The D6 land lay in the notch and is gone; START moved to D3; converter B's DRDY no
  longer reaches the MCU (the brief allows one DRDY) but keeps its test point. Whether the range is
  now good is still a measurement for the first board.
- **R3. Floating SPI lines.** 100k pull-ups on both chip selects (R120, R220), 100k pull-downs on START
  and SCLK (R22, R23).
- **R6. Slots in the planes.** Plane clearance around vias is now 0.15 mm, which leaves a 0.2 mm web
  between the vias of a row. `gen/fab.py` tests layers 2 and 3 between every such pair of vias.
- **R7. Input lines over the digital supply.** The split on layer 3 moved to y = 26.0 mm; the whole
  fan-out now lies over the analog supply. Pins 48 and 50 share one DVDD via just above the split.
- **R8. Vias under bare metal of the XIAO.** The top layer has keep-outs, for copper and for vias, under
  the module's two NFC pads and its four USB shell legs (positions from Seeed's v1.2 board file).
  The NFC lands were not restored; DRC now rejects anything placed there.
- **R9. Vias close to pads.** The ESD arrays' vias moved out to 0.25 mm from their pads, and vias
  placed by the scripts keep 0.2 mm. Measured against the pads' bounding boxes, 12 of the 441 vias
  are still within 0.15 mm (it was about 90); round pads make that an overestimate, and all pass
  the 0.127 mm clearance rule. Plugged vias remain unavailable; order them tented.
- **R10. Tombstoning risk.** The ground pads of the small capacitors and resistors (85 pads) no longer
  join the pours; each has its own track to a via, so both pads of a part see thin copper.
- **R11. Silkscreen.** Text is 1.0 mm high with 0.15 mm strokes. Q1, Q2 and D1 now have their
  references printed. The ESD arrays and passives still have none; use the placement file.
- The placement file gives the XIAO's centre (it gave a corner).

Accepted as they are (owner, on my recommendation), to test on the first board:

- **R4. ESD arrays on stubs.** Each array is reached through 10 to 18 mm of track and two vias (TI
  SLVA680A wants neither). The 47k in each line still protects the converter. One consequence for
  the safety note above: if a clamp channel fails short, one electrode is tied to ground or AVDD
  with no resistor, and the bias amplifier then drives through R125 alone, up to 64 uA. So "any path
  crosses 94k" holds only while every array is healthy.
- **R5. Filter capacitors 8.5 to 19 mm from the converter pins.** Irrelevant at EMG frequencies; it may
  let the 2.4 GHz transmitter in. Look for bursts at the radio's connection interval in a
  shorted-input recording. The remedy would be a 0201 capacitor across each pair at the pins.

Added afterwards, at the owner's request:

- **Motor resistor R5** is a 1206 part rated 0.25 W (was 0805); a stalled motor at 4.2 V puts about
  0.15 W into it.
- **TP23, 3.3 V**, a bare pad on the back at (44.5, 17.3) beside the SWD pads, so a probe can sense
  the target's supply. It hangs on the XIAO's 3V3 pin, before link R21.
- **TP6, scope ground**: a plated 1.0 mm hole in a 2.0 mm pad at (6.5, 20.8), marked GND. Solder a
  wire loop into it for bring-up and cut it off before the pod goes into a shell.

Still not done: reference designators on the silkscreen for the ESD arrays and passives.

## Second review, 2026-11-28: the rework, the additions and the frame

A third session, again with only the files, reviewed what changed since the first review. It found no
blocker, re-ran ERC and DRC (clean), and confirmed the counts, the pin tables it checked, the plane
geometry and the frame's numbers against JLCPCB's capabilities page. I re-measured F1, F3 and the
figures in F2 and F7 myself; F4, F5 and F6 are the reviewer's measurements, not repeated by me.
**None of F1 to F6 has been acted on: they change the circuit or need a new routing run, and that is
the owner's call.** My recommendation is at the end of each.

- **F1. A clock track runs under a slot in the XIAO's board. Fix before ordering.** Seeed's v1.2
  board file has two milled slots, 1.27 x 0.51 mm, at (33.07 to 34.34, 3.41 to 3.92) and (33.07 to
  34.34, 15.86 to 16.37) in this board's coordinates, where the shield can's solder line is
  interrupted: almost certainly the slots its locating tabs sit in. I missed them when I listed the
  bare metal under the module (I only looked for pads). The fixed SCLK_MCU track from pad 6 runs
  straight down at x = 33.42 and passes under the first slot; if a tab reaches the underside, only
  solder mask is between the grounded shield and the SPI clock. The USB socket's two 0.6 mm peg
  holes at (44.21, 7.00) and (44.21, 12.78) have a CS_B track and a ground via under them (plastic
  pegs, presumably, so less serious). *Recommended: add all four to the keep-outs and take the track
  out of pad 6 sideways; needs a routing run.*
- **F2. PWDN's high level has less margin than I wrote.** The table above says 0.91 x DVDD. That
  assumed the MCU pin delivers DVDD exactly. Nordic's product specification guarantees a standard-
  drive output only VDD - 0.4 V at 0.5 mA (and at least 1 mA at that drop). The divider takes 0.3 mA,
  so on a resistive output the drop is at most 0.12 V and PWDN sees about 0.87 x DVDD, against 0.8
  needed; read literally (0.4 V drop) there is no margin at all. The enable net is also 41 mm long
  with no capacitor. *Recommended: set D8 to high drive in firmware (added to the firmware list
  above; costs nothing), and add 100 nF from AVDD_EN to ground with the next routing run.*
- **F3. RESET and MOSI still float while the MCU's pins are high-impedance.** The rework gave the
  chip selects, START and SCLK pull resistors but not these two. SBAS459K 11.1 wants all digital
  inputs low before power-up, and floating inputs may add to the DVDD current the R21 measurement
  is meant to show. *Recommended: two more 100k pull-downs.*
- **F4. The ground pads taken out of the pours now have long returns.** All 85 reach a via through
  0.2 mm track only: 2 mm or more for 46 of them, up to 4.55 mm for eight of the 47 pF input
  capacitors and for the reference capacitors C128 and C228. About 4 nH in series makes a 47 pF
  capacitor useless above roughly 350 MHz, which makes the accepted point R5 (2.4 GHz pickup)
  worse. *Recommended: join those pads to the pour through thermal-relief spokes instead of
  isolating them, which keeps most of the tombstoning benefit; needs a routing run.*
- **F5. The analog rail reaches its plane through 23.7 mm of 0.25 mm track and five vias**, passing
  under converter A (about 50 milliohm and 20 nH; harmless at 7 mA DC, poor for a low-noise rail).
  *Recommended: a fixed 0.5 mm route with two vias straight down from the regulator.*
- **F6. Antenna.** The module's own copper-free window lies wholly over the notch. Pod copper is
  3.57 mm in front of the antenna, 2.96 mm below it and 2.43 mm to its right (behind the module's
  own ground). The antenna maker asks for 3 mm and for a place "at the edge of the PCB"; this one
  sits 6.4 mm deep in a 7 mm slot with pod ground along its open side. Nothing to change on paper;
  it stays a measurement for the first board, as before.
- **F7. Frame.** Done: the frame is 74 x 74 mm (was exactly the 70 mm minimum) and its text is now
  9.9 mm from the nearest fiducial (was 0.11 mm outside one's mask opening); `gen/panel.py` checks
  that. Recorded above: no USB plug in the frame, the via 0.59 mm from the bottom tab's edge, and
  the 50.5 mm width with the USB socket.
- **Notes.** The scope ground post TP6 is tied solidly to four copper layers and will be slow to
  solder (thermal relief would help). TP23 (3.3 V) is a bare pad 3.7 mm from the bare ground pad
  TP22 on the face a cell would rest on: insulate. The notch's two corners at the top edge are
  sharp.

The reviewer also found seven statements in these documents that were wrong or stale (the number of
nets on the back under the notch, one track length, the PWDN margin, the footprint's name, the count
of back pads, the list of bare metal under the XIAO, and the 50 mm claim). All are corrected.

It could not check: whether the shield tabs, USB legs or pegs actually protrude under a real XIAO,
or the module's height (nothing published, no module); how the ADS1298's digital pins behave in
power-down (the datasheet is silent); radio range; JLCPCB's acceptance of the frame.

Mechanical, from datasheets (reviewer only unless stated). Nothing here is decided:

- Tallest part is the battery connector J1, 5.5 mm (JST). The XIAO's height is not published.
- Cell (the design document says about 200 mAh; no part chosen) under the board: about 11 mm before
  shell. On top over the converters: about 8 mm, resting on a tantalum. Keep it away from the notch.
  Under the board it lies on the vias, the SWD pads and the motor joints: insulate it.
- The battery plug leaves over the top edge and needs 8 to 10 mm of shell beyond it.
- The XIAO's reset button is at about (47.1, 4.2): reachable only through a hole from above.
- Parts stand within 0.3 to 0.45 mm of every edge, so a panel needs routed tabs (V-cut needs 0.4 mm
  copper clearance, the board has 0.3) and there is no lip to clamp. The assembly frame above does
  that. The pod itself has no mounting holes and no fiducials; the frame carries the fiducials.
- The strip tails enter with contacts facing the pod; whether the pod sits beside or on top of the
  strip decides which face of the tail carries them. The FH12 is rated for 20 insertions.

## Layout

The board is `pod/emg-pod.kicad_pcb`: 49 x 49 mm with a 7 x 12.4 mm notch in the top edge, four layers,
127 assembled parts, all on top.
KiCad 9.0.9 DRC, with the rules listed in `docs/sources.md`, reports 0 errors, 0 warnings and nothing
unconnected (`out/drc.rpt`). `gen/fab.py` also compared all 554 pads with the net tables in
`gen/design.py`: no difference. DRC checks the board against its own rules and nets; it says nothing
about whether the circuit works, and nothing here has been built.

How it was routed: `gen/board.py` draws 938 fixed tracks and vias (the electrode lines and what is
listed in `README.md`); Freerouting and `gen/finish.py` did the rest. 441 vias in all, 215 of them
ground.

With the notch, everything between the XIAO and the left half passes a corridor 13 mm high below it.
To keep that routable, the enable divider (R1, R2) sits beside the XIAO's AFE_EN pad, the test points
for 3V3, CS_B and DRDY_B are on the right where those nets live, and the nets from the XIAO's top
row and battery pad that must reach the left half, plus VBUS, have fixed lanes on the back. Six of
the seven lanes are used in this run (CS_A, DRDY_A, START, MISO, VBAT, VBUS); the router took the
seventh net, SCLK_MCU, along the front instead, and its unused lane was removed.

### Where the layout departs from the handoff

- **Size: 49 x 49 mm**, not "about 40 x 45". The laminate is inside the 50 x 50 limit with 1 mm to
  spare, but the XIAO's USB socket overhangs the right edge and reaches x = 50.5 mm by Seeed's board
  file, so the assembled pod is 50.5 mm wide. Each
  converter block is 24.5 mm wide: the chip, a column of bypass capacitors and a column of eight
  filter capacitors on each side of it, all on the top. It gets smaller only with parts on the back
  or 0201 capacitors, and both were ruled out.
- **The antenna end of the XIAO is at an edge only because the board is notched there.** The USB
  socket has to be at the right edge and the module is 21 mm long, so its antenna end lies 28 mm in
  from the left edge. The notch (R2 above) gives the antenna an edge of its own. The module's
  antenna end overhangs it; the module is held by its other 13 edge pads and the six underneath.
  Compare signal strength with a bare XIAO at bring-up.
- **Supplies share layer 3.** DVDD above y = 26.0 mm, the 3.0 V analog rail below, ground fill in the
  rest. Layer 2 is one ground plane with no splits; its openings are via holes and the notch.
- **Five bare pads on the back** (SWDIO, SWCLK, NRST, GND, 3V3) under and beside the XIAO's own SWD
  pads, for a probe. No parts are assembled there, so assembly stays single-sided. The scope ground
  post TP6 is a plated hole and so shows on the back too.
- **"Route each pair together"** holds from connector to converter: the two lines of a pair are
  neighbours all the way, 0.5 mm apart, over the ground plane. It does not hold for the short
  branches to the ESD arrays and the filter capacitors, which fan out on the back one by one.

### Not verified

- **Assembly frame.** Drawn and DRC clean, not seen by JLCPCB. See "What Standard assembly changes
  for the order" above.
- **Rotations in the placement file** (`cpl-jlcpcb.csv`, the same in `out/fab/` and `out/fab-panel/`) are KiCad's angles with no correction
  for JLCPCB's reel directions. Check every polarised part in JLCPCB's placement preview before
  paying: U1, U2, U100, U200, the ten ESD arrays, Q1, Q2, D1, C130, C230, J1, J100, J200.
- **Tracks and vias under the strip connectors.** Each electrode line has a branch and a via under the
  connector body (that is where the ESD arrays tap in). Hirose's land drawing marks no area as
  closed to copper there, and the vias are covered by solder mask in the Gerbers, but I have not seen
  it confirmed that the FH12's housing or contacts cannot touch the board surface. Order with vias
  tented (or plugged), and look under a connector on the first board.
- **JST battery connector footprint**, tantalum and diode pad 1: as before, not checked against the
  makers' drawings (`docs/sources.md`).
- **The XIAO's two NFC pads have no lands** (footprint `XIAO-nRF52840-SMD-pod`, which also drops the
  D6 land). They are unused; the
  module's pads rest on solder mask there. Whether JLCPCB can paste and reflow the pads under the
  module at all is still not confirmed.
- **Same-net track spacing.** JLCPCB's page lists 0.25 mm; nothing here checks it.
- **Thermal and current checks: none done.** Tracks on VBAT, the motor nets and VBUS are 0.25 mm;
  the largest load on them is the motor, 70 mA (120 mA at start).
- **No signal-integrity or noise analysis.** The digital lines are long: SCLK is 26.5 mm from the XIAO
  to its series resistor R20 and 55 mm of track from there to the two converters, MISO is 62 mm, the
  converter clock from A to B 44 mm. Each has a 33 ohm series resistor at its source. Nothing was
  simulated.
- **Digital signals near the inputs.** The routers were kept out of the areas around the input lines
  (the fan-out on the back around each converter, the stubs under it on the front), and `gen/fab.py`
  confirms no routed track is inside them. It also measures how close the tracks and vias of any
  other signal come to those of an input line on the same layer. In this run one comes within
  1 mm: the converters' RESET line runs for 1.3 mm at 0.61 mm (centre to centre) from one input
  line of converter B, on the back at (37 to 38.3, 26.1), just outside the reserved area. RESET
  only changes at start-up. Next are the converter clock and AVDD_EN at 1.06 mm. Crossings
  on the opposite outer layer have both planes in between and are not counted. Whether that is quiet
  enough is for the first board to show: record with the inputs shorted and look for the 2 kHz frame
  rate and its harmonics.
- **The autorouted part was not reviewed track by track.** I looked at the pictures of both copper
  layers and rely on DRC for the rest. The fixed routes (electrode lines, their fan-outs, supply and
  ground vias at the converters, VCAP1, CLKSEL) are drawn by `gen/board.py` and were checked there.
- Stock was read on 2026-11-28 (`out/stock-check.md`); rerun `tools/stock_report.py` before ordering.

## Answers to the handoff's open items

- Sense stock and assembly type: in stock (120), Standard Only; the owner chose Standard assembly.
- XIAO 5V pin and battery pads: the 5V pin is the USB VBUS net, wired straight to the connector and the
  charger input; the BAT pad is the charger output with 2.2 uF on it. Same in Seeed's v1.1 and v1.2
  schematics. On battery the 5V pin is pulled to ground by 100k.
- Electrode series resistor: 47k.
- Supply sequencing: on my reading the datasheet does not forbid it, but TI has not confirmed that; accepted by the owner. The converters are now also in power-down while the analog rail is off. Check at bring-up (above).
