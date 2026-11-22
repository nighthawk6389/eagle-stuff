"""Small two-layer grid (maze) router for the connections route_plan.py does not script.

Dijkstra (skimage MCP_Geometric) on a 0.05 mm grid, three planes: F.Cu, a sparse "via" plane, B.Cu.
Clearances come from distance transforms of the copper already on the board; every new track
and via is re-checked with exact geometry (shapely) before it is accepted.
"""
import sys, time, math, collections
import numpy as np
import pcbnew
from pcbnew import ToMM
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage.draw import polygon as sk_polygon
from skimage.graph import MCP_Geometric
from shapely.geometry import Polygon, Point, LineString, box
from shapely.strtree import STRtree
from shapely.ops import unary_union

RES = 0.05
X0, Y0 = 1.0, 2.0
W, H = int(round((199.0 - X0) / RES)) + 1, int(round((153.0 - Y0) / RES)) + 1
CLR, EDGE_CLR = 0.2, 0.25
VIA_R = 0.35
F, B = 0, 1
LAYER_NAME = {F: "F", B: "B"}

NET_WIDTH = {"VBUS": 0.6, "VSYS": 0.6, "VBAT": 0.5, "+3V3": 0.5, "VLED": 0.5, "GND": 0.4}
ORDER = ["USB_DP", "USB_DN", "CC1", "CC2", "PROG", "Q2_G", "Q3_D", "EXP_IO47", "EXP_IO48",
         "VBUS", "VSYS", "VBAT", "VBAT_SENSE", "CHRG_N", "VLED_EN",
         "LED_DATA_3V3", "MIC_SCK", "MIC_WS", "MIC_SD",
         "+3V3", "EN", "VLED", "BOOT", "UART_TX", "UART_RX"]
COST_B, COST_F, COST_VIA = 1.0, 2.5, 120.0
BASE_Y = 110.0


def c2x(c): return X0 + c * RES
def r2y(r): return Y0 + r * RES
def x2c(x): return int(round((x - X0) / RES))
def y2r(y): return int(round((y - Y0) / RES))


def paint(arr, poly, value):
    if poly.is_empty:
        return
    polys = poly.geoms if poly.geom_type == "MultiPolygon" else [poly]
    for p in polys:
        xs, ys = np.array(p.exterior.coords.xy)
        rr, cc = sk_polygon((ys - Y0) / RES, (xs - X0) / RES, arr.shape)
        arr[rr, cc] = value


def poly_from_chain(ch):
    return [(ToMM(ch.CPoint(j).x), ToMM(ch.CPoint(j).y)) for j in range(ch.PointCount())]


class Router:
    def __init__(self, board, tracks, vias, log=print):
        self.log = log
        self.board = board
        self.netid = {}
        self.items = {F: [], B: []}          # (geom, net) exact copper per layer
        self.trees = {F: None, B: None}
        self.dirty = {F: True, B: True}
        self.new_tracks, self.new_vias = [], []
        self.failed = []

        # ---- board outline
        ps = pcbnew.SHAPE_POLY_SET()
        board.GetBoardPolygonOutlines(ps)
        polys = []
        for i in range(ps.OutlineCount()):
            holes = [poly_from_chain(ps.Hole(i, h)) for h in range(ps.HoleCount(i))]
            polys.append(Polygon(poly_from_chain(ps.Outline(i)), holes))
        self.outline = unary_union(polys)
        inside = np.zeros((H, W), bool)
        for p in (self.outline.geoms if self.outline.geom_type == "MultiPolygon" else [self.outline]):
            paint(inside, Polygon(p.exterior), True)
            for h in p.interiors:
                paint(inside, Polygon(h).buffer(1e-4), False)

        self.occ = np.zeros((2, H, W), np.int16)
        self.no_track = np.zeros((2, H, W), bool)
        self.no_via = np.zeros((H, W), bool)
        padmask = np.zeros((H, W), bool)
        self.net_items = collections.defaultdict(list)   # net -> [(kind, layers, geom, anchors[(layer,x,y)])]
        self.anchor_xy = {}                               # (layer,r,c) -> exact (x,y) of a pad centre
        holes = []

        nc = 0
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                bb = pad.GetBoundingBox()
                x, y = ToMM(pad.GetPosition().x), ToMM(pad.GetPosition().y)
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    holes.append(Point(x, y).buffer(ToMM(pad.GetDrillSize().x) / 2, 16))
                    continue
                if pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
                    g = Point(x, y).buffer(ToMM(pad.GetSize().x) / 2, 16)
                else:
                    g = box(ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))
                net = pad.GetNetname()
                if not net:
                    nc += 1
                    net = f"__nc{nc}"
                layers = [l for l, kl in ((F, pcbnew.F_Cu), (B, pcbnew.B_Cu)) if pad.IsOnLayer(kl)]
                self._add_item(net, "pad", layers, g, [(l, x, y) for l in layers])
                paint(padmask, g.buffer(1e-4), True)
            for z in fp.Zones():
                self._rule_area(z)
        for z in board.Zones():
            self._rule_area(z)
        for h in holes:
            paint(inside, h.buffer(1e-4), False)
        self.holes = unary_union(holes) if holes else None
        self.edge_dist = ndimage.distance_transform_edt(inside) * RES
        self.pad_dist = ndimage.distance_transform_edt(~padmask) * RES
        # distance to the nearest no-track rule area, so a track's full width stays outside it
        self.nt_dist = np.stack([ndimage.distance_transform_edt(~self.no_track[l]) * RES for l in (F, B)])
        self.boundary = self.outline.boundary if not holes else unary_union([self.outline.boundary] + [h.boundary for h in holes])

        for net, layer, w, pts in tracks:
            self._add_track(net, F if layer == "F" else B, w, pts)
        for net, x, y in vias:
            self._add_via(net, x, y)

    # ------------------------------------------------------------------ bookkeeping
    def nid(self, net):
        if net not in self.netid:
            self.netid[net] = len(self.netid) + 1
        return self.netid[net]

    def _rule_area(self, z):
        if not z.GetIsRuleArea():
            return
        ol = z.Outline()
        for i in range(ol.OutlineCount()):
            g = Polygon(poly_from_chain(ol.Outline(i)))
            for l, kl in ((F, pcbnew.F_Cu), (B, pcbnew.B_Cu)):
                if z.GetLayerSet().Contains(kl):
                    if z.GetDoNotAllowTracks():
                        paint(self.no_track[l], g.buffer(1e-4), True)
                    if z.GetDoNotAllowVias():
                        paint(self.no_via, g.buffer(VIA_R + 0.02), True)

    def _add_item(self, net, kind, layers, geom, anchors):
        for l in layers:
            paint(self.occ[l], geom.buffer(1e-4), self.nid(net))
            self.items[l].append((geom, net))
            self.dirty[l] = True
        self.net_items[net].append((kind, tuple(layers), geom, anchors))
        if kind == "pad":
            for l, x, y in anchors:
                self.anchor_xy[(l, y2r(y), x2c(x))] = (x, y)

    def _add_track(self, net, layer, w, pts):
        line = LineString(pts)
        self._add_item(net, "track", [layer], line.buffer(w / 2, 8), [(layer, x, y) for x, y in self._sample(pts)])

    def _add_via(self, net, x, y):
        self._add_item(net, "via", [F, B], Point(x, y).buffer(VIA_R, 16), [(F, x, y), (B, x, y)])

    @staticmethod
    def _sample(pts):
        out = []
        for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
            n = max(1, int(math.hypot(bx - ax, by - ay) / (RES * 0.9)))
            for i in range(n + 1):
                out.append((ax + (bx - ax) * i / n, ay + (by - ay) * i / n))
        return out

    def tree(self, l):
        if self.dirty[l]:
            self.trees[l] = STRtree([g for g, _ in self.items[l]])
            self.dirty[l] = False
        return self.trees[l]

    def exact_ok(self, net, layer, geom, margin=0.0):
        """geom (track or via copper) keeps CLR to other nets on this layer and EDGE_CLR to the board edge."""
        if self.boundary.distance(geom) < EDGE_CLR - 1e-6 or not self.outline.contains(geom):
            return False
        t = self.tree(layer)
        for i in t.query(geom.buffer(CLR + margin + 0.01)):
            g, n = self.items[layer][i]
            if n != net and g.distance(geom) < CLR + margin - 1e-6:
                return False
        return True

    # ------------------------------------------------------------------ connectivity
    def components(self, net):
        its = self.net_items[net]
        parent = list(range(len(its)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        geoms = [g for _, _, g, _ in its]
        t = STRtree(geoms)
        for i, (k, ls, g, _) in enumerate(its):
            for j in t.query(g):
                if j > i and set(ls) & set(its[j][1]) and g.intersects(geoms[j]):
                    parent[find(i)] = find(j)
        comps = collections.defaultdict(list)
        for i in range(len(its)):
            comps[find(i)].append(i)
        out = []
        for idx in comps.values():
            cells = set()
            has_via = False
            for i in idx:
                has_via |= its[i][0] == "via"
                for l, x, y in its[i][3]:
                    cells.add((l, y2r(y), x2c(x)))
            out.append(dict(cells=np.array(sorted(cells), dtype=np.int32), via=has_via))
        return out

    # ------------------------------------------------------------------ one Dijkstra run
    def masks(self, net, hw, win, slack):
        r0, r1, c0, c1 = win
        n = self.nid(net)
        passable, dists = [], []
        for l in (F, B):
            o = self.occ[l, r0:r1, c0:c1]
            foreign = (o != 0) & (o != n)
            d = ndimage.distance_transform_edt(~foreign) * RES
            ok = (d >= hw + CLR + slack) & (self.edge_dist[r0:r1, c0:c1] >= hw + EDGE_CLR + slack) \
                & (self.nt_dist[l, r0:r1, c0:c1] >= hw + 0.06)
            own = o == n
            if own.any():
                ok |= own & (ndimage.distance_transform_edt(own) * RES >= hw + 0.049) & (d >= hw + 0.1)
            passable.append(ok)
            dists.append(d)
        vok = np.zeros_like(passable[0])
        vok[::4, ::4] = True                                   # sparse lattice: no lateral moves in the via plane
        vok &= (dists[F] >= VIA_R + CLR + slack) & (dists[B] >= VIA_R + CLR + slack)
        vok &= self.edge_dist[r0:r1, c0:c1] >= max(VIA_R + EDGE_CLR + slack, self.via_edge)
        vok &= ~self.no_via[r0:r1, c0:c1] & (self.pad_dist[r0:r1, c0:c1] >= VIA_R + 0.15)
        vok &= passable[F] & passable[B]
        return passable, vok, dists

    via_edge = 2.0          # keep new vias this far from the board edge (front border artwork runs there)
    OFFS = [(0, dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx] + [(1, 0, 0), (-1, 0, 0)]

    def dijkstra(self, net, hw, win, starts, ends, slack, cost_f=COST_F, cost_via=COST_VIA, flood=False):
        r0, r1, c0, c1 = win
        passable, vok, dists = self.masks(net, hw, win, slack)
        cost = np.full((3,) + passable[0].shape, -1.0)
        # in the base (y > BASE_Y) the front is as good as the back and vias are cheap; elsewhere stay on the back
        base_rows = (np.arange(r0, r1) * RES + Y0 > BASE_Y)[:, None]
        for l, plane, base in ((F, 0, np.where(base_rows, COST_B, cost_f)), (B, 2, COST_B)):
            near = dists[l] < hw + CLR + slack + 0.25
            cost[plane] = np.where(passable[l], base * np.where(near, 1.6, 1.0), -1.0)
        cost[1] = np.where(vok, np.where(base_rows, min(cost_via, 40.0), cost_via), -1.0)
        pl = {F: 0, B: 2}
        s = [(pl[l], r - r0, c - c0) for l, r, c in starts]
        e = [(pl[l], r - r0, c - c0) for l, r, c in ends]
        for p in s + e:
            if cost[p] < 0:
                cost[p] = COST_B
        m = MCP_Geometric(cost, offsets=self.OFFS)
        if flood:
            cum, _ = m.find_costs(s)
            return m, cum, passable, vok
        cum, _ = m.find_costs(s, e, find_all_ends=False)
        best = min(e, key=lambda p: cum[p])
        if not np.isfinite(cum[best]):
            return None
        return m.traceback(best), passable

    # ------------------------------------------------------------------ path -> tracks
    @staticmethod
    def los(mask, a, b):
        n = max(abs(b[0] - a[0]), abs(b[1] - a[1])) * 2 + 1
        rr = np.rint(np.linspace(a[0], b[0], n)).astype(int)
        cc = np.rint(np.linspace(a[1], b[1], n)).astype(int)
        return bool(mask[rr, cc].all())

    def octi(self, mask, a, b):
        """Return [a, (corner), b] as an octilinear connection valid on mask, or None."""
        dr, dc = b[0] - a[0], b[1] - a[1]
        if dr == 0 or dc == 0 or abs(dr) == abs(dc):
            return [a, b] if self.los(mask, a, b) else None
        d = min(abs(dr), abs(dc))
        sr, sc = (1 if dr > 0 else -1), (1 if dc > 0 else -1)
        for corner in ((a[0] + sr * d, a[1] + sc * d), (b[0] - sr * d, b[1] - sc * d)):
            if self.los(mask, a, corner) and self.los(mask, corner, b):
                return [a, corner, b]
        return None

    def simplify(self, mask, cells):
        out = [cells[0]]
        i = 0
        while i < len(cells) - 1:
            best, seg, miss = i + 1, [cells[i], cells[i + 1]], 0
            j = i + 2
            while j < len(cells) and miss < 12:
                s = self.octi(mask, cells[i], cells[j])
                if s:
                    best, seg, miss = j, s, 0
                else:
                    miss += 1
                j += 1
            out += seg[1:]
            i = best
        return out

    def commit(self, net, w, path, passable, win, check=True):
        """Turn a traceback (plane,r,c) into tracks + vias. Returns False (nothing added) if an exact check fails."""
        r0, r1, c0, c1 = win
        runs, vias, cur, cur_l = [], [], [], None
        for pln, r, c in path:
            if pln == 1:
                vias.append((r + r0, c + c0))
                continue
            l = F if pln == 0 else B
            if l != cur_l:
                if cur:
                    runs.append((cur_l, cur))
                cur, cur_l = [], l
            cur.append((r, c))
        if cur:
            runs.append((cur_l, cur))
        tracks = []
        for l, cells in runs:
            if len(cells) < 2:
                continue
            simp = self.simplify(passable[l], cells)
            pts = [(c2x(c + c0), r2y(r + r0)) for r, c in simp]
            for k in (0, -1):                                   # snap ends to exact pad centres
                key = (l, simp[k][0] + r0, simp[k][1] + c0)
                if key in self.anchor_xy:
                    pts[k] = self.anchor_xy[key]
            tracks.append((l, pts))
        if check:
            for l, pts in tracks:
                if not self.exact_ok(net, l, LineString(pts).buffer(w / 2, 8)):
                    return False
            for r, c in vias:
                g = Point(c2x(c), r2y(r)).buffer(VIA_R, 16)
                if not (self.exact_ok(net, F, g) and self.exact_ok(net, B, g)):
                    return False
        for l, pts in tracks:
            self._add_track(net, l, w, pts)
            self.new_tracks.append((net, LAYER_NAME[l], w, [(round(x, 4), round(y, 4)) for x, y in pts]))
        for r, c in vias:
            self._add_via(net, c2x(c), r2y(r))
            self.new_vias.append((net, round(c2x(c), 4), round(r2y(r), 4)))
        return True

    @staticmethod
    def window(pts_rc, margin):
        rs, cs = [p[0] for p in pts_rc], [p[1] for p in pts_rc]
        m = int(margin / RES)
        return max(0, min(rs) - m), min(H, max(rs) + m + 1), max(0, min(cs) - m), min(W, max(cs) + m + 1)

    @staticmethod
    def in_win(cells, win):
        r0, r1, c0, c1 = win
        k = (cells[:, 1] >= r0) & (cells[:, 1] < r1) & (cells[:, 2] >= c0) & (cells[:, 2] < c1)
        return [tuple(int(v) for v in row) for row in cells[k]]

    # ------------------------------------------------------------------ net routing
    def route_net(self, net):
        comps = self.components(net)
        if len(comps) < 2:
            return
        w0 = NET_WIDTH.get(net, 0.2)
        comps.sort(key=lambda c: -len(c["cells"]))
        tree = comps[0]["cells"]
        rest = [c["cells"] for c in comps[1:]]
        while rest:
            kd = cKDTree(tree[:, 1:3])
            best = None
            for i, cells in enumerate(rest):
                d, j = kd.query(cells[:, 1:3])
                k = int(np.argmin(d))
                if best is None or d[k] < best[0]:
                    best = (d[k], i, tuple(cells[k][1:3]), tuple(tree[j[k]][1:3]))
            _, i, pa, pb = best
            done = False
            for w in [w0] + [x for x in (0.3, 0.2) if x < w0]:
                for margin, slack in ((4, 0.04), (10, 0.04), (10, 0.07), (25, 0.05), (60, 0.05), (60, 0.08)):
                    win = self.window([pa, pb], margin)
                    starts = self.in_win(tree, win)
                    ends = self.in_win(rest[i], win)
                    if not starts or not ends:
                        continue
                    res = self.dijkstra(net, w / 2, win, starts, ends, slack)
                    if res and self.commit(net, w, res[0], res[1], win):
                        done = True
                        break
                if done:
                    if w != w0:
                        self.log(f"   {net}: narrowed to {w} near ({c2x(pa[1]):.1f},{r2y(pa[0]):.1f})")
                    break
            if not done:
                self.failed.append((net, c2x(pa[1]), r2y(pa[0])))
                self.log(f"   FAILED {net} at ({c2x(pa[1]):.2f},{r2y(pa[0]):.2f})")
                rest.pop(i)
                continue
            comps2 = self.components(net)          # recompute: new copper may have merged several components
            comps2.sort(key=lambda c: -len(c["cells"]))
            tree = comps2[0]["cells"]
            rest = [c["cells"] for c in comps2[1:]]
            # drop components we already gave up on
            rest = [c for c in rest if not any(abs(c2x(c[0][2]) - fx) < 0.3 and abs(r2y(c[0][1]) - fy) < 0.3
                                               for n, fx, fy in self.failed if n == net)]

    def route_gnd(self):
        """Every GND pad group gets a short back track to existing via-connected GND copper or to a new via
        into the front GND pour (the pour itself is added later by finish.py)."""
        net, w = "GND", NET_WIDTH["GND"]
        while True:
            comps = self.components(net)
            plane = [c["cells"] for c in comps if c["via"]]
            todo = [c["cells"] for c in comps if not c["via"]
                    and not any(abs(c2x(c["cells"][0][2]) - fx) < 0.3 and abs(r2y(c["cells"][0][1]) - fy) < 0.3
                                for n, fx, fy in self.failed if n == net)]
            if not todo:
                return
            cells = todo[0]
            pcells = np.vstack(plane) if plane else np.zeros((0, 3), np.int32)
            done = False
            for ww in (w, 0.3, 0.2):
                for margin, slack in ((3, 0.04), (6, 0.04), (6, 0.08), (12, 0.05), (25, 0.06)):
                    win = self.window([tuple(c[1:3]) for c in cells], margin)
                    r0, r1, c0, c1 = win
                    starts = self.in_win(cells, win)
                    m, cum, passable, vok = self.dijkstra(net, ww / 2, win, starts, [], slack, cost_f=COST_F,
                                                          cost_via=40.0, flood=True)
                    cand = np.full(cum.shape, np.inf)
                    # (a) a fresh via: the front cell on top of any reachable via site with room for pour around it
                    o = self.occ[F, r0:r1, c0:c1]
                    dF = ndimage.distance_transform_edt(~((o != 0) & (o != self.nid(net)))) * RES
                    site = vok & (dF >= 0.9)
                    cand[0][site] = cum[0][site]
                    # (b) existing GND copper that already reaches the pour
                    for l, r, c in self.in_win(pcells, win) if len(pcells) else []:
                        p = (0 if l == F else 2, r - r0, c - c0)
                        cand[p] = min(cand[p], cum[p])
                    best = np.unravel_index(np.argmin(cand), cand.shape)
                    if not np.isfinite(cand[best]):
                        continue
                    path = m.traceback(best)
                    if best[0] == 0 and site[best[1], best[2]] and (len(path) < 2 or path[-2][0] != 1):
                        continue
                    if self.commit(net, ww, path, passable, win):
                        done = True
                        break
                if done:
                    break
            if not done:
                self.failed.append((net, c2x(cells[0][2]), r2y(cells[0][1])))
                self.log(f"   FAILED GND at ({c2x(cells[0][2]):.2f},{r2y(cells[0][1]):.2f})")


def route(board, tracks, vias, log=print):
    t0 = time.time()
    R = Router(board, tracks, vias, log)
    log(f"grid {W}x{H}, {sum(len(v) for v in R.net_items.values())} copper items, setup {time.time()-t0:.1f}s")
    nets = [n for n in R.net_items if not n.startswith("__nc") and n != "GND"]
    nets.sort(key=lambda n: ORDER.index(n) if n in ORDER else len(ORDER))
    for net in nets:
        t1 = time.time()
        n0 = len(R.new_tracks)
        R.route_net(net)
        if len(R.new_tracks) != n0:
            log(f"{net}: +{len(R.new_tracks)-n0} tracks  ({time.time()-t1:.1f}s)")
    t1 = time.time()
    n0 = len(R.new_vias)
    R.route_gnd()
    log(f"GND: +{len(R.new_vias)-n0} vias ({time.time()-t1:.1f}s)")
    log(f"done in {time.time()-t0:.0f}s, failed: {R.failed}")
    return R.new_tracks, R.new_vias
