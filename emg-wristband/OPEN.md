# Open items: main pod rev A

State on 2026-11-27, after the first schematic pass. Nothing here is laid out yet.
"Checked" means read from the document named in `docs/sources.md`; anything else is flagged.

## Decisions for the owner

### 1. No IMU and no microphone as drawn, because JLCPCB marks them "Standard Only"

- XIAO nRF52840 **Sense**: JLCPCB C17401557, 123 in stock, **Standard Only**. The handoff rules it out.
- Plain XIAO nRF52840: **C17209540**, 352 in stock, Economic and Standard, about $10.77. This is what the
  schematic uses. The number in the handoff, C37327670, is a second listing of the same board with 0 stock.
- The fallback IMU cannot be placed either: LSM6DS3TR-C (C967633) is Standard Only, and so were all
  13 other 6-axis IMUs I checked (LSM6DSO, LSM6DSL, BMI270, ICM-42607, ICM-42670, QMI8658, MPU-6500, ...).
- So the 11th pin carries DRDY_B, and rev A as drawn has no motion sensor and no push-to-talk microphone.

The Sense and the plain XIAO share one footprint and pinout, so the schematic is the same either way.
Choose one:

| Option | Gets | Costs |
|---|---|---|
| A. Keep the plain XIAO (as drawn) | Economic assembly, everything placed by JLCPCB | No IMU, no microphone |
| B. Order Standard assembly and place the Sense | IMU and microphone | Standard-assembly fees for the whole order; change one LCSC number |
| C. Leave the XIAO off the order and solder a Sense by hand | IMU and microphone at Economic prices | Hand work: 14 edge pads plus the bottom battery and SWD pads (needs holes under them or a hot plate) |

### 2. The converters' digital supply stays on while the interlock holds the analog supply off

This was the handoff's sequencing question. What the datasheet (SBAS459K) says:

- Section 11.1 sets no order between AVDD and DVDD. It asks for all inputs low until supplies are stable,
  then a reset pulse after 2^18 clock periods and once VCAP1 is above 1.1 V.
- The recommended-operating table lists AVDD - DVDD from -2.1 V to +3.6 V. With DVDD at 3.3 V and AVDD
  at 0 V the difference is -3.3 V, outside that row.
- The absolute-maximum table has no limit between AVDD and DVDD.

My reading: -2.1 V is exactly the smallest allowed AVDD (1.5 V in bipolar use) minus the largest DVDD
(3.6 V), so the row describes running conditions, not an off state. A search summary of TI forum
thread 870302 (ADS1299, the sister part) reports a TI engineer saying the limit "only applies to normal
operation", **but I could not open the thread to read it myself** (the site refused the request).
Please read it before ordering:
https://e2e.ti.com/support/data-converters-group/data-converters/f/data-converters-forum/870302/ads1299-power-sequencing-digital-and-analog-inputs

Why I did not gate both supplies: with DVDD switched off, the MCU could still drive 3.3 V into unpowered
digital inputs (absolute maximum is DVDD + 0.3 V), and a hardware interlock cannot rely on firmware to
park those pins. Gating both properly needs a load switch plus a buffer that isolates six lines.
If TI's answer is "do not", that is the change to make, on the MCU and power sheets only.

### 3. Vibration motor: two solder pads, not a placed part

The coin motors JLCPCB stocks are on wire leads (LCM1027B3605F, C7528806, is listed for Economic
assembly but is a wired part), so J2 is two wire pads as the handoff allows. R5 (12 ohm) is sized for
that motor from its datasheet; any other motor needs R5 recalculated. A 3 V motor on a 4.2 V cell with
no resistor would run above its 3.3 V limit.

## Values that are placeholders or my choice, not from a datasheet

| Part | Value | Status |
|---|---|---|
| R101-R116, R201-R216 (sense lines) | 22k | Handoff placeholder, final value 10k to 47k |
| R125 (bias line) | 22k | My choice: same as the sense lines, so every skin-facing line has the same limit. To be set with them |
| C101-C116, C201-C216 (input filter) | 47 pF C0G to ground | My choice. Corner 154 kHz with 22k (72 kHz at 47k, 339 kHz at 10k). The datasheet (10.1.3) only says a single pole is usually enough and a wide bandwidth protects common-mode rejection. Every pF here also loads a dry electrode, so smaller may be better |
| R124, C140 (bias feedback) | 1 Mohm, 1.5 nF | Datasheet "typical values for example only". Loop stability with real electrodes is untested |
| R20, R121, R221, R123 (series, SCLK / DOUT / CLK) | 33 ohm | My choice; the datasheet says "termination resistors as needed". Can be fitted as 0 ohm |
| R120, R220 (PWDN pull-up) | 10k | From TI's evaluation board, not the datasheet text |
| R1, R2, R3, R4, C3 (interlock) | 10k, 100k, 10k, 10k, 100 nF | Calculated on the power sheet from the LP5907 and AO3400A datasheets |
| R223 (clock pull-down on converter B) | 100k | My choice, so the input is not floating before firmware enables converter A's clock output |
| R5 (motor) | 12 ohm 0805 | Calculated from the motor datasheet, see item 3 |

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
- Stock was read on 2026-11-27 (`out/stock-check.md`); rerun `tools/stock_report.py` before ordering.

## Answers to the handoff's open items

- Sense stock and assembly type: item 1 above.
- XIAO 5V pin and battery pads: the 5V pin is the USB VBUS net, wired straight to the connector and the
  charger input; the BAT pad is the charger output with 2.2 uF on it. Same in Seeed's v1.1 and v1.2
  schematics. On battery the 5V pin is pulled to ground by 100k.
- Electrode series resistor: still open.
- Supply sequencing: item 2 above.
