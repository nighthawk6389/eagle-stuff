import subprocess, sys, cairosvg
pcb=sys.argv[1]; name=sys.argv[2]; layers=sys.argv[3]; mirror=len(sys.argv)>4 and sys.argv[4]=='mirror'
cmd=['kicad-cli','pcb','export','svg','-o',f'out/{name}.svg','--layers',layers,'--exclude-drawing-sheet','--page-size-mode','2']
if mirror: cmd.append('--mirror')
r=subprocess.run(cmd+[pcb],capture_output=True,text=True); print(r.stdout[-200:],r.stderr[-300:])
cairosvg.svg2png(url=f'out/{name}.svg',write_to=f'out/{name}.png',output_width=int(sys.argv[5]) if len(sys.argv)>5 else 1600,background_color='white')
