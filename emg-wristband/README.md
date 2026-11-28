# EMG wristband: main pod, rev A

KiCad project for the main pod: two ADS1298 converters, a Seeed XIAO nRF52840 Sense, a 3.0 V analog rail
with a USB interlock, and a vibration-motor driver. The brief is in `CLAUDE.md`. What is still
uncertain is in `OPEN.md`; read that before trusting anything here.

Status (2026-11-28): schematic drawn and ERC clean; board laid out and routed, 49 x 49 mm with a notch
under the antenna, four layers; reviewed once and reworked; fabrication files written, for the single
board and for the board in a 74 x 74 mm assembly frame; reviewed a second time, with findings still
open (`OPEN.md`, "Second review"). Nothing has been ordered or built. The layout's open points are under
"Layout" in `OPEN.md`.

## Where things are

| Path | What |
|---|---|
| `out/emg-pod-schematic.pdf` | The schematic for review, five pages |
| `out/bom-jlcpcb.csv` | Bill of materials from the schematic, JLCPCB columns, one LCSC number per line |
| `out/stock-check.md` | Stock and assembly type of every BOM line, with the date it was read |
| `out/erc.rpt` | KiCad's ERC report |
| `out/fab/` | The single board: Gerbers and drill files (also zipped), `cpl-jlcpcb.csv` (placement) and the BOM |
| `out/fab-panel/` | The same board in its 74 x 74 mm assembly frame: **the files for a JLCPCB Standard-assembly order** |
| `out/drc.rpt`, `out/drc-panel.rpt` | KiCad's DRC reports for the routed board and for the frame |
| `out/board-top.png`, `out/board-bottom.png`, `out/panel-top.png` | KiCad's rendering of the bare board, both sides, and of the frame |
| `pod/` | The KiCad 9 project (`emg-pod.kicad_pro`, schematic and `emg-pod.kicad_pcb`) and the frame (`emg-pod-panel.kicad_pcb`). Opens in KiCad 9 or newer |
| `pod/lib/` | Every symbol the schematic uses, and Seeed's XIAO footprint (plus a copy without the two NFC pads) |
| `gen/` | The Python that writes the schematic and the board |
| `tools/` | JLCPCB stock lookup |
| `docs/sources.md` | The datasheets and Seeed files each pin table came from |

## The schematic is generated

`gen/build.py` writes the `.kicad_sch` files. **Edits made in KiCad's schematic editor are lost the
next time it runs.** Either keep changing the generator, or stop using it and edit in KiCad from then on.

    python3 gen/build.py           # needs KiCad 9's kicad-cli on the path
    python3 tools/stock_report.py  # re-reads stock from jlcpcb.com

`build.py` does four things: writes the sheets, runs ERC, exports KiCad's netlist and compares all 552
pins with the tables in `gen/design.py` (which take their pin numbers from `gen/parts.py`, copied from
the datasheets), and exports the PDF and BOM. It exits non-zero if ERC or the comparison fails.

- `gen/parts.py`: pin tables and LCSC numbers. Each table names its datasheet.
- `gen/design.py`: which pin goes to which net, and where each part is drawn. The board is built from
  the same tables, so schematic and board cannot disagree about a net.
- `gen/kisch.py`, `gen/sexp.py`: KiCad file writing.

## The board is generated too

Five steps, each a script. **Edits made in KiCad's board editor are lost when they run again**, same
as for the schematic.

    /usr/bin/python3 gen/board.py                      # placement, rules, fixed routes -> pod/emg-pod-unrouted.kicad_pcb
    /usr/bin/python3 gen/route.py freerouting-2.1.0.jar   # autoroute the rest (Freerouting, about 9 minutes)
    /usr/bin/python3 gen/finish.py                     # leftovers, ground pours, plane vias, silkscreen -> pod/emg-pod.kicad_pcb
    /usr/bin/python3 gen/fab.py                        # Gerbers, drill, placement file -> out/fab/
    /usr/bin/python3 gen/panel.py                      # the board in its assembly frame -> pod/emg-pod-panel.kicad_pcb, out/fab-panel/

They need the `pcbnew` Python module that comes with KiCad 9 (the system Python on Ubuntu) and, for
`route.py`, Java and the Freerouting 2.1.0 jar from github.com/freerouting/freerouting (not in this repo).

- `gen/board.py` holds everything that was decided by hand: the outline, the design rules, where each
  part sits, and the routes that must not be left to an autorouter. Those are the 32 electrode lines
  (connector, resistor array, converter pin, in one straight line on the top layer), their fan-out on
  the back to the filter capacitors and to the ESD arrays, the via to a plane for every supply and
  ground pin of the converters, VCAP1, a ground via beside every ground pad, and lanes on the back for
  the seven nets that cross from the XIAO to the left half below the notch (five signals, the battery
  and VBUS; a lane the routers end up not using is removed again). The outline, with its
  notch under the XIAO's antenna, and the keep-outs under the module's bare pads are there too. It also names the
  areas reserved for the input lines (`quiet_zones`): the fan-out on the back around each converter
  and the stubs under it on the front. The routers lay nothing there.
- `gen/route.py` hands the rest to Freerouting. Ground is left out of that: ground pads are joined by
  the plane, the pours on both outer layers and the vias `finish.py` adds.
- `gen/finish.py` completes what Freerouting gave up on with a small grid router (`gen/lastmile.py`),
  pours ground on the outer layers, gives supply pads a via to their plane, stitches the pours to the
  ground plane, removes dead-end stubs, and runs KiCad's DRC. It prints what is still open, if anything.
- `gen/fab.py` writes the Gerbers, drill files and placement file, checks every pad's net against
  `gen/design.py`, checks that no routed track entered a reserved area and that the planes are
  filled between the vias of each row, reports how close other signals come to an input line and
  how close vias come to pads, and writes the full DRC report. It exits non-zero unless DRC has no
  errors, nothing is unconnected, the reserved areas are clean and the planes have no gaps.

- `gen/panel.py` copies the finished board into a 74 x 74 mm frame (JLCPCB's smallest size for
  Standard assembly is 70 x 70): a routed slot around the board, five tabs with a row of small holes each,
  three fiducials and four tooling holes on the rails. It does not move the board or refill its
  zones, checks that all copper is the same as in the single board, and runs DRC on the result.
  Run it again whenever `pod/emg-pod.kicad_pcb` changes. How to order and what is unverified:
  `OPEN.md`.

Any change to `gen/board.py` moves many of the autorouted tracks on the next run. The board in `pod/`
is the result of one run, and `out/fab/` and `out/fab-panel/` were made from exactly that file.

Layers: 1 signal and parts, 2 ground (one plane, no splits), 3 supplies (DVDD above y = 26.0 mm, AVDD
below, ground
fill elsewhere), 4 signal. No parts on the back; five bare pads are there, under the XIAO (SWD, ground and 3.3 V for a probe).

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
  other part is cleared for Economic. Standard assembly wants boards of at least 70 x 70 mm with rails and fiducials, hence the frame.
- **47k in every skin-facing line**, so any path through the wearer crosses 94k.
- **Digital supply always on, analog supply gated.** The interlock only switches the 3.0 V rail.
- **Interlock:** a MOSFET holds the regulator's enable low whenever the XIAO's 5V pin (USB VBUS) is up.
- **SPI clock and data-in on D5 and D4**, the only XIAO pins Nordic rates for fast signals.
- **Motor on two wire pads**, with a series resistor sized for a 3 V coin motor on a 4.2 V cell.
- **Tantalum on VCAP1**, because the datasheet warns about ceramics there on boards that vibrate.
