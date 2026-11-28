"""Small routing helpers for what the autorouter leaves behind.

Space answers "may a via / a track of this net go here?" on the two outer layers.
maze() finds a path on a 0.1 mm grid: either between two points of one net, or from a pad
to the nearest spot where a via to an inner plane fits.
"""
import heapq
import math

import pcbnew
from pcbnew import FromMM

import board as B

F, BK = pcbnew.F_Cu, pcbnew.B_Cu


def add_via(brd, pt, net, lock=False):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pt)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetWidth(F, FromMM(B.VIA_D))
    v.SetDrill(FromMM(B.VIA_DRILL))
    v.SetLayerPair(F, BK)
    v.SetNet(net)
    v.SetLocked(lock)
    brd.Add(v)
    return v


def add_track(brd, a, b, net, layer, width):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(B.V(*a))
    t.SetEnd(B.V(*b))
    t.SetWidth(FromMM(width))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)


class Space:
    def __init__(self, brd, netname, width=0.2):
        self.brd, self.netname, self.net, self.width = brd, netname, brd.FindNet(netname), width
        self.via_no = {lay: self._others(lay, B.CLEAR + B.VIA_D / 2 + 0.02) for lay in (F, BK)}
        self.track_no = {lay: self._others(lay, B.CLEAR + width / 2 + 0.04, quiet=True) for lay in (F, BK)}
        self.own = {lay: pcbnew.SHAPE_POLY_SET() for lay in (F, BK)}     # this net's own pads
        for fp in brd.GetFootprints():
            for pad in fp.Pads():
                for lay in (F, BK):
                    if pad.GetNetname() == netname and pad.IsOnLayer(lay):
                        pad.TransformShapeToPolygon(self.own[lay], lay, 0, FromMM(0.01), pcbnew.ERROR_INSIDE)
        for lay in (F, BK):
            self.own[lay].Simplify()
        self.pads_no = pcbnew.SHAPE_POLY_SET()           # no via on or touching any pad
        for fp in brd.GetFootprints():
            for pad in fp.Pads():
                for lay in (F, BK):
                    if pad.IsOnLayer(lay):
                        pad.TransformShapeToPolygon(self.pads_no, lay, FromMM(B.VIA_D / 2 + 0.1), FromMM(0.01),
                                                    pcbnew.ERROR_OUTSIDE)
        self.pads_no.Simplify()
        self.holes = [(v.GetPosition().x, v.GetPosition().y) for v in brd.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]

    def _others(self, layer, margin, quiet=False):
        """Where this net's copper may not be on a layer. quiet = also the areas kept for the input lines."""
        ps = pcbnew.SHAPE_POLY_SET()
        for t in self.brd.GetTracks():
            if t.GetNetname() == self.netname:
                continue
            if isinstance(t, pcbnew.PCB_VIA) or t.GetLayer() == layer:
                t.TransformShapeToPolygon(ps, layer, FromMM(margin), FromMM(0.01), pcbnew.ERROR_OUTSIDE)
        for fp in self.brd.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetname() != self.netname and pad.IsOnLayer(layer):
                    pad.TransformShapeToPolygon(ps, layer, FromMM(margin), FromMM(0.01), pcbnew.ERROR_OUTSIDE)
        keep = pcbnew.SHAPE_POLY_SET()
        for z in self.brd.Zones():
            if z.GetIsRuleArea():
                for i in range(z.Outline().OutlineCount()):
                    keep.AddOutline(z.Outline().Outline(i))
        if quiet:
            for lay, x0, y0, x1, y1 in B.quiet_zones():
                if lay == layer:
                    keep.NewOutline()
                    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                        keep.Append(FromMM(B.OX + x), FromMM(B.OY + y))
        if keep.OutlineCount():
            keep.Inflate(FromMM(margin), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, FromMM(0.01))
            ps.Append(keep)
        ps.Simplify()
        return ps

    def via_ok(self, x, y):
        e = B.VIA_D / 2 + 0.35
        if not (e <= x <= B.W - e and e <= y <= B.H - e):
            return False
        pt = B.V(x, y)
        if self.via_no[F].Contains(pt) or self.via_no[BK].Contains(pt) or self.pads_no.Contains(pt):
            return False
        lim = FromMM(B.VIA_DRILL + 0.27) ** 2
        return all((pt.x - hx) ** 2 + (pt.y - hy) ** 2 >= lim for hx, hy in self.holes)

    def track_ok(self, a, b, layer=F):
        n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05))
        no = self.track_no[layer]
        return not any(no.Contains(B.V(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
                       for i in range(n + 1))


def maze(space, start, goal=None, margin=4.0, step=0.1, limit=600000):
    """Route from start (x, y, layer) to goal (x, y, layer or None), or to the nearest via spot if goal is None.

    Returns (tracks, vias): tracks as (layer, [(x, y), ...]) polylines, vias as (x, y). None if no path.
    """
    sx, sy, sl = start
    xs = [sx] + ([goal[0]] if goal else [])
    ys = [sy] + ([goal[1]] if goal else [])
    edge = 0.3 + space.width / 2
    x0, x1 = max(edge, min(xs) - margin), min(B.W - edge, max(xs) + margin)
    y0, y1 = max(edge, min(ys) - margin), min(B.H - edge, max(ys) + margin)
    x0 = sx - int((sx - x0) / step) * step            # put the start point exactly on the grid, so a track
    y0 = sy - int((sy - y0) / step) * step            # can leave a narrow pad along its centre line
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)

    def cell(x, y):
        return int(round((x - x0) / step)), int(round((y - y0) / step))

    def xy(ix, iy):
        return x0 + ix * step, y0 + iy * step

    s = cell(sx, sy)
    g = cell(goal[0], goal[1]) if goal else None
    gl = goal[2] if goal else None
    ok_cache, via_cache = {}, {}
    free = int(0.4 / step)

    def ok(ix, iy, lay):
        if not (0 <= ix <= nx and 0 <= iy <= ny):
            return False
        if abs(ix - s[0]) <= free and abs(iy - s[1]) <= free and lay == sl:
            return True                                    # leaving our own pad
        if g and abs(ix - g[0]) <= free and abs(iy - g[1]) <= free and (gl is None or lay == gl):
            return True
        k = (ix, iy, lay)
        if k not in ok_cache:
            pt = B.V(*xy(ix, iy))
            ok_cache[k] = space.own[lay].Contains(pt) or not space.track_no[lay].Contains(pt)
        return ok_cache[k]

    def via_at(ix, iy):
        k = (ix, iy)
        if k not in via_cache:
            via_cache[k] = space.via_ok(*xy(ix, iy))
        return via_cache[k]

    def h(ix, iy):
        return math.hypot(ix - g[0], iy - g[1]) if g else 0.0

    first = (s[0], s[1], sl)
    best = {first: 0.0}
    prev = {}
    heap = [(h(*s), 0.0, first)]
    end = None
    n = 0
    while heap and n < limit:
        _, c, node = heapq.heappop(heap)
        if c > best.get(node, 1e18):
            continue
        n += 1
        ix, iy, lay = node
        if g:
            if (ix, iy) == g and (gl is None or lay == gl):
                end = node
                break
        elif lay == F and math.hypot(ix - s[0], iy - s[1]) * step >= 0.6 and via_at(ix, iy):
            end = node
            break
        moves = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            if not ok(ix + dx, iy + dy, lay):
                continue
            if dx and dy and not (ok(ix + dx, iy, lay) and ok(ix, iy + dy, lay)):
                continue
            moves.append(((ix + dx, iy + dy, lay), 1.4142 if dx and dy else 1.0))
        if g and via_at(ix, iy):
            other = BK if lay == F else F
            if ok(ix, iy, other):
                moves.append(((ix, iy, other), 25.0))
        for nb, w in moves:
            nc = c + w
            if nc < best.get(nb, 1e18):
                best[nb] = nc
                prev[nb] = node
                heapq.heappush(heap, (nc + h(nb[0], nb[1]), nc, nb))
    if end is None:
        return None
    path = [end]
    while path[-1] != first:
        path.append(prev[path[-1]])
    path.reverse()
    tracks, vias, run = [], [], [path[0]]
    for a, b in zip(path[:-1], path[1:]):
        if a[2] != b[2]:
            tracks.append((a[2], run))
            vias.append(xy(a[0], a[1]))
            run = [b]
        else:
            run.append(b)
    tracks.append((path[-1][2], run))
    if goal is None:
        vias.append(xy(end[0], end[1]))
    out = []
    for lay, cells in tracks:
        pts = [xy(c[0], c[1]) for c in cells]
        slim = [pts[0]]
        for i in range(1, len(pts) - 1):                   # drop points in the middle of a straight run
            ax, ay = slim[-1]
            bx, by = pts[i]
            cx, cy = pts[i + 1]
            if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-9:
                slim.append(pts[i])
        if len(pts) > 1:
            slim.append(pts[-1])
            out.append((lay, slim))
    return out, vias


def lay_down(space, start, result, goal=None):
    """Turn a maze result into tracks and vias; the ends are joined to the exact start and goal points."""
    tracks, vias = result
    brd = space.brd
    if tracks:
        tracks[0][1][0] = (start[0], start[1])
        if goal:
            tracks[-1][1][-1] = (goal[0], goal[1])
    for lay, pts in tracks:
        for a, b in zip(pts[:-1], pts[1:]):
            if a != b:
                add_track(brd, a, b, space.net, lay, space.width)
    for x, y in vias:
        v = add_via(brd, B.V(x, y), space.net)
        space.holes.append((v.GetPosition().x, v.GetPosition().y))
