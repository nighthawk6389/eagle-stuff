# Menorah enclosure — print notes

A back, an open front frame that clips onto it, and a stand. **Print at 100 % — do not scale.**
The two big parts are about 200 x 155 mm, so they need a 256 x 256 mm plate (Bambu X1 / P1 / A1) and do **not** fit
an A1 mini (180 mm bed).

| File | What it is | Size (mm) | Filament* | Time* |
|---|---|---|---|---|
| `menorah_fit_test_back.stl` + `menorah_fit_test_front.stl` | one candle of each part — **print these first** | 19 x 71 x 11 and 20 x 71 x 4.5 | 8 g | 40 min |
| `menorah_back.stl` | one-piece back; the circuit board drops into it | 200 x 153 x 11.1 | 78 g | 7 h |
| `menorah_front.stl` | open front frame, 17 windows, 28 clip lugs | 201 x 155 x 4.5 | 14 g | 1.5 h |
| `menorah_stand.stl` | stand; the menorah leans back 4 degrees in it | 140 x 68 x 37 | 42 g | 4 h |
| `menorah_enclosure.3mf` | back, front and stand in one file (two plates: back + stand, then front) | | | |

\* generic slicer profile at moderate speed; a Bambu printer on its default profile is roughly twice as fast.

`preview_front.png` shows what you see from the front, `preview_assembled.png` the finished thing in its stand,
`preview_parts.png` the three parts as they lie on the printer.

## Print settings
- Orientation: exactly as exported. Back: flat rear on the bed, open side up. **Front frame: face down, lugs pointing
  up** — the bed gives the visible face its finish. Stand: plate on the bed. **No supports anywhere.**
- 0.2 mm layers, 0.4 mm nozzle, 3 walls, 15 % infill. The back is solid-looking behind the candles; that is infill.
- Material: PLA or PETG. PETG is the more forgiving of the two for the clips. Black hides the board edge best.
- Leave "X-Y hole compensation" and "X-Y contour compensation" at 0. Do not use "Arachne" settings that drop thin
  walls: the clip beads are 0.45 mm features.

## Try the fit first
Print the two `fit_test` pieces (40 minutes). Lay the small frame on the small back with the lugs outside the wall
and press down over each lug until it clicks.
- Clicks on with a firm thumb press and needs a fingernail to lift off: print the rest.
- Will not go on, or a lug turns white or cracks: the beads are too proud. In `enclosure.py` lower `BEAD`
  (0.45 -> 0.35) or raise `LUG_GAP` (0.2 -> 0.3), run it again, or simply scrape the beads with a knife.
- Falls off: raise `BEAD` to 0.55 (and `GROOVE` to 0.65).

## How it goes together
1. Battery (optional, up to 30 x 30 x 7 mm) goes into the deep part of the back first.
2. Lay the circuit board into the back, components down, gold artwork up. It rests on a ledge all round, with
   0.3 mm of play. Hold the board by the base, not by the flames.
3. Lay the frame on top and press down next to each lug, working round from the base. The frame's strips flex
   sideways to let the lugs click into grooves in the back's wall. The frame overlaps the board edge by 1.2 mm
   and so holds the board in.
4. Stand it in the trough of the stand, lettering to the front. Two lugs under the base drop into two pockets
   in the trough. The menorah leans back onto the tall wall.
5. To open it again, lift the frame at one lug with a fingernail and work round.

What stays reachable: the USB-C socket through a slot at the left end of the base (seen from the front); RESET
(upper) and BOOT (lower) through two 4 mm holes in the back at the right end — use a toothpick; the microphone hole
and all nine gold touch rings through the windows. The magnet wand is 10 mm wide and the candle windows 9.6 mm, so
the wand rests on the frame, 1.6 mm above the ring; the magnet is strong enough for that by a wide margin.

## Known limits
- **Not fit-tested.** Everything was generated from the board design file and typical part heights, and checked
  in software only (no collisions between board, parts, back, frame and stand). Print one set and try it.
- The flame tips of the frame are not clipped (a lug there could not flex). They lie flat if the print is flat;
  if one lifts, a dot of glue on the back's rim fixes it.
- The frame hides the board's thin gold border line; the flames, rings, lettering and all LEDs stay visible.
- If the board is tight in the pocket, scrape the inside of the rim lightly. If it rattles, a strip of thin tape
  on the ledge.
- The stand's front lip covers the frame's bottom strip only; the lettering stays clear.
