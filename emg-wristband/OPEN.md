# Open items: main pod rev A

State on 2026-11-28, after the first schematic pass and the owner's decisions. Nothing here is laid out yet.
"Checked" means read from the document named in `docs/sources.md`; anything else is flagged.

## Decided by the owner on 2026-11-28

1. **Sense XIAO on Standard assembly.** The XIAO is now the Sense version, JLCPCB C17401557 (123 in
   stock, "Standard Only"), so the whole order is Standard assembly. This overrides the handoff's
   "no Standard Only parts" rule for this one part. IMU and microphone are on the module; the 11th pin
   carries DRDY_B. Every other BOM line is still cleared for Economic.
2. **Series resistors: 47k** (was the 22k placeholder), on my recommendation. Reasoning below.
3. **Motor on two wire pads**, accepted.

### What Standard assembly changes for the layout

JLCPCB's capabilities page gives 70 x 70 mm as the smallest single board for Standard assembly, and
says it adds 5 mm process rails to smaller boards. The pod is about 40 x 45 mm, so it needs rails or a
small panel. I have this from a search summary of jlcpcb.com/capabilities/pcb-assembly-capabilities,
not from reading the page; confirm it at quote time. To settle at layout.

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

## Still open: digital supply on while the analog supply is off

As drawn, DVDD is the XIAO's 3.3 V rail and is always on; the interlock switches only AVDD.

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
| R101-R116, R201-R216 (sense lines) | 47k | Decided 2026-11-28, reasoning above |
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
- **Connector pin order.** Pin 1 bias, pins 2/19/20 shield, pins 3-18 the pairs in channel order. The
  order may be mirrored at layout to avoid crossings, and the strip must match: the FH12 is a
  bottom-contact connector, which fixes which face of the strip tail carries the contacts.

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

## Not done yet

- Layout, DRC, placement file. The BOM in `out/` is from the schematic only.
- Footprints are assigned but not checked against the datasheet land patterns. To check at layout:
  AO3400A pad numbers (its datasheet draws the lead positions and the pin-1 dot but prints no numbers;
  I used gate 1, source 2, drain 3), B5819W cathode pad, tantalum positive pad, FH12 pin 1, JST pin 1,
  and whether JLCPCB can paste and reflow the pads under the XIAO.
- Stock was read on 2026-11-28 (`out/stock-check.md`); rerun `tools/stock_report.py` before ordering.

## Answers to the handoff's open items

- Sense stock and assembly type: in stock (123), Standard Only; the owner chose Standard assembly.
- XIAO 5V pin and battery pads: the 5V pin is the USB VBUS net, wired straight to the connector and the
  charger input; the BAT pad is the charger output with 2.2 uF on it. Same in Seeed's v1.1 and v1.2
  schematics. On battery the 5V pin is pulled to ground by 100k.
- Electrode series resistor: 47k.
- Supply sequencing: still open, see above.
