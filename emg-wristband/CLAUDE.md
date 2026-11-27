# EMG wristband: main pod, rev A

Handoff for designing the main pod PCB in KiCad. The full design doc
(architecture, parts list, cost) is at
https://claude.ai/artifact/Qyi9dvYaMobC5WEkHjQgmW

## What this is

A 16-channel, 2 kSPS surface-EMG wristband modeled on Meta's sEMG-RD research
band, so Meta's public recordings can pre-train the gesture model. Two boards:

- **Main pod (this repo, first):** 4-layer rigid PCB that digitizes 16
  differential channels and streams them over Bluetooth LE.
- **Electrode strip (later):** 2-layer flex with 48 gold pads. Blocked on the
  owner's wrist measurement. Do not start it yet.

## Working rules

- Take every pin number, pin function and passive value from the datasheet,
  never from memory. If a datasheet is not available, stop and say so.
- Pick parts by LCSC number and check JLCPCB assembly stock before placing.
- All parts on the top side. JLCPCB Economic assembly, single-sided. Do not
  pick any part that JLCPCB marks "Standard Only".
- Flag anything uncertain in `OPEN.md` instead of guessing.
- Commit small, with ERC clean at every commit.

## Blocks

### Converters: 2x ADS1298IPAGR (LCSC C527440), TQFP-64
- Datasheet: TI SBAS459K. Follow its power, reference and bypass
  recommendations exactly.
- Single 3.0 V analog supply (AVSS at ground), 3.3 V digital supply from the
  XIAO, internal 2.4 V reference.
- One clock for both chips: chip A runs its internal oscillator with clock
  output enabled; chip B takes that clock as an external input.
- Shared START so both sample together. Shared SPI bus with a separate chip
  select per chip. DRDY of each chip to its own MCU pin; RESET shared on one
  pin; PWDN tied per the datasheet (no spare pin for it).
- All 8 inputs of each chip are differential pairs to the electrode
  connectors, DC-coupled. Firmware sets gain 6 and does the 20 Hz high-pass.
- Bias drive: use chip A's right-leg-drive amplifier, out to the bias net
  through a series resistor. Chip B's amplifier is left unused per datasheet.

### Electrode inputs
- Two 20-pin, 0.5 mm FPC connectors, one per strip tail. Each carries 8
  sense pairs (16 lines), bias and shield. Keep the two lines of a pair on
  adjacent pins; put bias and shield on the end pins.
- Every sense line: one series resistor (placeholder 22 k, final value TBD
  between 10 k and 47 k), then a small RC filter at the converter pin, plus
  low-leakage ESD protection at the connector.
- Route each pair together, over solid ground, away from the radio and the
  charger.

### Radio and MCU: Seeed XIAO nRF52840 Sense, soldered down as a module
- Use Seeed's published footprint, schematic and bottom-pad drawing. The
  board is 21 x 17.8 mm with 14 castellated edge pins (11 GPIO, 5V, 3V3, GND)
  and battery pads underneath.
- It already provides: nRF52840 with antenna, USB-C, LiPo charger (BQ25101),
  3.3 V regulator, reset button, LEDs, 6-axis IMU, and a USB bootloader. Do
  not duplicate any of these on the pod.
- Find the JLCPCB part number for the Sense version and confirm it is
  cleared for Economic assembly. If it is not stocked, use the plain XIAO
  nRF52840 (JLCPCB C37327670) and add an LSM6DS3TR-C on the SPI bus with its
  own chip select.
- Pin budget (11 GPIO): SPI clock, data in, data out; chip select A; chip
  select B; DRDY from chip A; shared START; shared converter RESET; analog
  rail enable; vibration motor. That is 10. The last pin is chip B DRDY, or
  the IMU chip select if the plain XIAO is used (both chips share a clock
  and START, so one DRDY is enough).
- The Sense version is preferred over the plain XIAO: its PDM microphone is
  wanted for push-to-talk.
- Keep the XIAO antenna end at a board edge, clear of copper per Seeed's
  guidance, and as far from the converters as the outline allows.
- Add test pads under the XIAO's SWD bottom pads so a borrowed probe can
  rescue a corrupted bootloader.

### Power
- USB-C, charging and the 3.3 V digital rail all come from the XIAO. The
  3.3 V pin feeds the converters' digital supply.
- Two-pin battery connector on the pod, wired to the XIAO battery pads.
  Set the XIAO charge current to 100 mA in firmware.
- Analog rail: separate low-noise 3.0 V LDO for the converter analog supply,
  fed from the battery node.
- **Safety interlock (required):** the analog LDO enable must be forced off
  in hardware whenever USB VBUS is present, regardless of firmware. Check
  Seeed's schematic for how the 5V pin relates to VBUS before designing this.

### Vibration motor
- One 3 V coin vibration motor for gesture feedback, switched low-side by a
  small N-channel MOSFET from one GPIO, with a flyback diode and a gate
  pull-down. Power it from the battery node, never from the analog rail.
- Prefer a motor JLCPCB can place. If none is stocked for Economic assembly,
  leave two solder pads for a wired coin motor.
- Place it and its traces on the XIAO side of the board, as far from the
  electrode inputs as the outline allows. Firmware will mark EMG samples
  taken while it runs.

## Layout targets

- 4 layers: signal, ground, power, signal. Unbroken ground plane.
- Outline about 40 x 45 mm, hard limit 50 x 50 mm.
- Analog on one side of the board, the XIAO on the other.
- Test points: both supply rails, converter clock, DRDY, SPI, bias output.

## Done means

1. ERC and DRC clean.
2. Schematic PDF exported for review.
3. BOM and placement files in JLCPCB format, every line with an LCSC number
   and a stock check.
4. `OPEN.md` lists what is still unverified.

## Not in rev A

Fuel gauge, on-board storage, the flex strip, the band shell.

## Planned version two (do not build now)

After rev A works, the pod will be split into three slim segments: one
converter on each side, the XIAO and battery in the center, joined by the
flex strip. To make that split easy later, keep each converter with its own
input network, decoupling and FPC connector as a self-contained block in
both the schematic sheets and the layout.

## Known open items

- JLCPCB stock and assembly type for the XIAO nRF52840 Sense.
- How the XIAO's 5V pin and battery pads connect internally (interlock and
  analog LDO input depend on it).
- Final series-resistor value on the electrode lines.
- Whether the ADS1298 may sit with its digital supply on while the interlock
  holds the analog supply off. Check the datasheet's supply-sequencing rules;
  if it may not, gate both supplies together.

## Decided, do not reopen

- ADS1298, not ADS131E08: the cheaper part has 25 times the input bias
  current and TI advises against it for biosignals.
- XIAO, not a bare E73 module: the E73 is Standard-only assembly at JLCPCB
  and needs a debug probe.

## Status (added 2026-11-27 by the first schematic session)

- Schematic drawn in `pod/`, generated by `gen/build.py` (see `README.md`). ERC clean. No layout yet.
- Read `OPEN.md` first. Three items there need the owner's decision: the Sense XIAO and every IMU are
  "Standard Only" at JLCPCB (the schematic uses the plain XIAO, C17209540, with no IMU); the digital
  supply stays on while the interlock holds the analog supply off; the motor is on two wire pads.
- The first two "Known open items" above are answered in `OPEN.md`; the other two are still open.
