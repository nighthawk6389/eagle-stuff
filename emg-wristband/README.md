# EMG wristband: main pod, rev A

KiCad project for the main pod: two ADS1298 converters, a Seeed XIAO nRF52840 Sense, a 3.0 V analog rail
with a USB interlock, and a vibration-motor driver. The brief is in `CLAUDE.md`. What is still
uncertain is in `OPEN.md`; read that before trusting anything here.

Status (2026-11-28): schematic drawn, ERC clean, not laid out.

## Where things are

| Path | What |
|---|---|
| `out/emg-pod-schematic.pdf` | The schematic for review, five pages |
| `out/bom-jlcpcb.csv` | Bill of materials from the schematic, JLCPCB columns, one LCSC number per line |
| `out/stock-check.md` | Stock and assembly type of every BOM line, with the date it was read |
| `out/erc.rpt` | KiCad's ERC report |
| `pod/` | The KiCad 9 project (`emg-pod.kicad_pro`). Opens in KiCad 9 or newer |
| `pod/lib/` | Every symbol the schematic uses, and Seeed's XIAO footprint |
| `gen/` | The Python that writes the schematic |
| `tools/` | JLCPCB stock lookup |
| `docs/sources.md` | The datasheets and Seeed files each pin table came from |

## The schematic is generated

`gen/build.py` writes the `.kicad_sch` files. **Edits made in KiCad's schematic editor are lost the
next time it runs.** Either keep changing the generator, or stop using it and edit in KiCad from then on.

    python3 gen/build.py           # needs KiCad 9's kicad-cli on the path
    python3 tools/stock_report.py  # re-reads stock from jlcpcb.com

`build.py` does four things: writes the sheets, runs ERC, exports KiCad's netlist and compares all 546
pins with the tables in `gen/design.py` (which take their pin numbers from `gen/parts.py`, copied from
the datasheets), and exports the PDF and BOM. It exits non-zero if ERC or the comparison fails.

- `gen/parts.py`: pin tables and LCSC numbers. Each table names its datasheet.
- `gen/design.py`: which pin goes to which net, and where each part is drawn.
- `gen/kisch.py`, `gen/sexp.py`: KiCad file writing.

## Sheets

1. Overview: rails and the XIAO pin map.
2. Power: battery connector, LP5907 3.0 V analog rail, the USB interlock, the motor driver.
3. MCU: the XIAO and its test points, including SWD.
4. Converter A: strip connector, ESD arrays, input network, ADS1298, bypass, bias drive, clock master.
5. Converter B: the same block, clocked from A, bias amplifier unused.

Converter A parts are numbered 100-199 and converter B parts 200-299, so each block stays
recognisable when the pod is split later.

## Choices made while drawing (details in OPEN.md)

- **XIAO Sense on Standard assembly** (owner's decision). JLCPCB marks the Sense "Standard Only"; every
  other part is cleared for Economic. Standard assembly wants boards of 70 x 70 mm or rails added.
- **47k in every skin-facing line**, so any path through the wearer crosses 94k.
- **Digital supply always on, analog supply gated.** The interlock only switches the 3.0 V rail.
- **Interlock:** a MOSFET holds the regulator's enable low whenever the XIAO's 5V pin (USB VBUS) is up.
- **SPI clock and data-in on D5 and D4**, the only XIAO pins Nordic rates for fast signals.
- **Motor on two wire pads**, with a series resistor sized for a 3 V coin motor on a 4.2 V cell.
- **Tantalum on VCAP1**, because the datasheet warns about ceramics there on boards that vibrate.
