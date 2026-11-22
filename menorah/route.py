"""Route the board: scripted candle/bar/stem routing (route_plan.py) + maze router for the rest.

    /usr/bin/python3.12 route.py [--plan-only]
Reads out/menorah.kicad_pcb (from build.py), writes out/menorah_routed.kicad_pcb.
"""
import os, sys, shutil, json
import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out", "menorah.kicad_pcb")
DST = os.path.join(HERE, "out", "menorah_routed.kicad_pcb")
VIA_D, VIA_DRILL = 0.7, 0.3


def V(x, y):
    return VECTOR2I(FromMM(float(x)), FromMM(float(y)))


def add_tracks(board, tracks, vias):
    lay = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
    for net, layer, w, pts in tracks:
        ni = board.FindNet(net)
        assert ni is not None, net
        for a, b in zip(pts[:-1], pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(V(*a)); t.SetEnd(V(*b))
            t.SetWidth(FromMM(w)); t.SetLayer(lay[layer]); t.SetNet(ni)
            board.Add(t)
    for net, x, y in vias:
        ni = board.FindNet(net)
        assert ni is not None, net
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(V(x, y)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetWidth(FromMM(VIA_D)); v.SetDrill(FromMM(VIA_DRILL))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(ni)
        board.Add(v)


def trim_dangling(board, tracks, vias):
    """Cut back scripted stubs the maze router did not use (it may join a track part-way along)."""
    from shapely.geometry import Point, LineString, box
    pads = {}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            pads.setdefault(p.GetNetname(), []).append(box(ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom())))
    out = [list(t) for t in tracks]
    for _ in range(4):
        changed = False
        for i, (net, layer, w, pts) in enumerate(out):
            if len(pts) < 2:
                continue
            others = [(LineString(p2), w2) for j, (n2, l2, w2, p2) in enumerate(out) if j != i and n2 == net and l2 == layer and len(p2) > 1]
            vs = [Point(x, y) for n2, x, y in vias if n2 == net]

            def touched(pt, self_line=None):
                q = Point(pt)
                return (any(g.distance(q) < 1e-6 or g.contains(q) for g in pads.get(net, []))
                        or any(v.distance(q) < 0.36 for v in vs)
                        or any(ln.distance(q) < w2 / 2 for ln, w2 in others))
            for end in (0, -1):
                seq = pts if end == -1 else pts[::-1]
                if touched(seq[-1]):
                    continue
                # walk back from the free end to the last vertex / junction that is connected
                keep = None
                for k in range(len(seq) - 1, 0, -1):
                    seg = LineString([seq[k - 1], seq[k]])
                    hits = [seg.project(Point(o.coords[e])) for o, w2 in others for e in (0, -1)
                            if seg.distance(Point(o.coords[e])) < w2 / 2 + 1e-6]
                    hits += [seg.project(v) for v in vs if seg.distance(v) < 0.36]
                    if hits:
                        d = max(hits)
                        p = seg.interpolate(d)
                        keep = seq[:k] + [(round(p.x, 4), round(p.y, 4))]
                        break
                    if touched(seq[k - 1]):
                        keep = seq[:k]
                        break
                if keep is not None and len(keep) < len(seq) or (keep and keep[-1] != seq[-1]):
                    new = keep if end == -1 else keep[::-1]
                    if new != pts:
                        out[i][3] = pts = new
                        changed = True
        if not changed:
            break
    return [tuple(t) for t in out if len(t[3]) > 1]


if __name__ == "__main__":
    import route_plan as RP
    board = pcbnew.LoadBoard(SRC)
    tracks, vias = list(RP.TRACKS), list(RP.VIAS)
    cache = os.path.join(HERE, "out", "maze_result.json")
    if "--reuse" in sys.argv:                       # re-apply the last maze result without re-routing
        t2, v2 = json.load(open(cache))
        tracks += [(n, l, w, [tuple(p) for p in pts]) for n, l, w, pts in t2]; vias += [tuple(v) for v in v2]
    elif "--plan-only" not in sys.argv:
        import maze
        t2, v2 = maze.route(board, tracks, vias)
        t2 = [(n, l, float(w), [(float(x), float(y)) for x, y in pts]) for n, l, w, pts in t2]
        v2 = [(n, float(x), float(y)) for n, x, y in v2]
        json.dump([t2, v2], open(cache, "w"))
        tracks += t2; vias += v2
    # drop degenerate stubs (shorter than a via radius) the grid router sometimes leaves at a layer change
    tracks = [t for t in tracks if sum(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for a, b in zip(t[3][:-1], t[3][1:])) > 0.12]
    tracks = trim_dangling(board, tracks, vias)
    add_tracks(board, tracks, vias)
    pcbnew.SaveBoard(DST, board)
    shutil.copy(SRC.replace(".kicad_pcb", ".kicad_pro"), DST.replace(".kicad_pcb", ".kicad_pro"))
    print("wrote", DST, len(tracks), "tracks", len(vias), "vias")
