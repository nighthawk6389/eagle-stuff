# Menorah enclosure — print notes

Three parts. They fit one 256 x 256 mm plate (Bambu X1 / P1 / A1). The largest part is 200 x 107 mm, so it does
**not** fit an A1 mini (180 mm bed).

| File | What it is | Size (mm) |
|---|---|---|
| `menorah_back_top.stl` | thin back shell for the candles, crossbar and upper stem | 200 x 107 x 6.1 |
| `menorah_back_base.stl` | deeper back box for the base (electronics, battery) | 114 x 46 x 12 |
| `menorah_stand.stl` | stand with a trough the base box drops into | 140 x 68 x 37 |
| `menorah_enclosure.3mf` | all three parts in one file | |

## Print settings
- Orientation: exactly as exported (flat back on the bed, open side up). **No supports.**
- Material: black PLA or PETG. PETG is a little more forgiving on the snap ridges.
- 0.2 mm layers, 0.4 mm nozzle, 3 walls, 15 % infill. Nothing here needs to be strong.
- Dimensional accuracy matters: the board sits in a pocket with 0.3 mm clearance per side. If the printer's
  "X-Y hole compensation" is in use, leave it at 0 or slightly positive.

## How it goes together
1. The circuit board presses into each shell **from the front**, component side into the shell. It rests on a small
   ledge and clicks under snap ridges on the rim. Fit the base box first, then the top shell. The two shells meet across
   the stem with a 0.3 mm gap and are not joined to each other; the board holds them together.
2. The USB-C connector is at the left end of the base box (seen from the front); the box has an open slot there.
3. Two 4 mm holes in the back of the base box, at the right end seen from the front, reach the buttons:
   upper hole = RESET, lower hole = BOOT. Use a toothpick.
4. The battery (if used) goes inside the base box before the board is pressed in. The cavity is 8 mm deep.
5. Stand the base box in the trough of the stand, front lip towards the front. The tall wall goes behind.

## Known limits
- **Not fit-tested.** These were generated from the board design file and typical part heights before any board
  existed. Print one set and try it before printing more.
- If the board is too tight: scrape the inside of the rim lightly. If it is loose: a small piece of double-sided tape
  on the ledge. If a snap ridge stops the board going in, trim it with a knife; the board will still sit in the pocket.
- Handle the board by the base, not by the flames, when pressing it in.
- The stand's front lip covers the bottom 2.5 mm of the board's front face (below the lettering).
