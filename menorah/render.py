"""kicad-cli SVG export -> PNG:  python3.12 render.py out/board.kicad_pcb name LAYERS [mirror|x] [width] [x0 y0 x1 y1 crop in mm]"""
import subprocess, sys, os, re, cairosvg
pcb, name, layers = sys.argv[1], sys.argv[2], sys.argv[3]
mirror = len(sys.argv) > 4 and sys.argv[4] == 'mirror'
width = int(sys.argv[5]) if len(sys.argv) > 5 else 1600
out = os.path.join(os.path.dirname(os.path.abspath(pcb)), name)
cmd = ['kicad-cli', 'pcb', 'export', 'svg', '-o', out + '.svg', '--layers', layers, '--exclude-drawing-sheet', '--page-size-mode', '2']
if mirror: cmd.append('--mirror')
r = subprocess.run(cmd + [pcb], capture_output=True, text=True)
if r.returncode: print(r.stdout[-200:], r.stderr[-300:])
svg = open(out + '.svg').read()
if len(sys.argv) > 9:   # crop: coordinates in board mm (front view)
    x0, y0, x1, y1 = map(float, sys.argv[6:10])
    m = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', svg)
    vx, vy, vw, vh = map(float, m.groups())
    # page-size-mode 2 = board area only; viewBox is in mm with the board bbox origin
    bx, by = float(os.environ.get("BX", 1.98)), float(os.environ.get("BY", 2.775))   # board bbox origin
    svg = re.sub(r'viewBox="[^"]+"', f'viewBox="{x0-bx} {y0-by} {x1-x0} {y1-y0}"', svg, 1)
    svg = re.sub(r'width="[^"]+"', f'width="{x1-x0}mm"', svg, 1)
    svg = re.sub(r'height="[^"]+"', f'height="{y1-y0}mm"', svg, 1)
cairosvg.svg2png(bytestring=svg.encode(), write_to=out + '.png', output_width=width, background_color='white')
print(out + '.png')
