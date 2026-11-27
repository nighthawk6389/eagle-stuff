"""Write KiCad 9 schematic files from Python.

Only what this project needs: symbols, wires, labels, power symbols, no-connects,
junctions (placed automatically), text, and sheets on the root page.
Coordinates are millimetres on the sheet (y grows downwards), on a 1.27 mm grid.
"""
import copy
import os
import uuid as _uuid

from sexp import Q, dump, find, findall, parse

KICAD_SYMBOLS = "/usr/share/kicad/symbols"
PROJECT = "emg-pod"
NS = _uuid.UUID("5b0f2d2e-3f0a-4c58-9a35-0d1f6c1e7a11")


def uid(*key):
    """Stable UUID so regenerating does not churn the files."""
    return Q(str(_uuid.uuid5(NS, "/".join(str(k) for k in key))))


def r(v):
    return round(float(v), 4)


def on_grid(v):
    k = v / 1.27
    return abs(k - round(k)) < 1e-6


# ---------------------------------------------------------------- symbol library
_lib_text = {}
_sym_cache = {}
CUSTOM = {}          # name -> s-expression of project-library symbols ("emgpod:NAME")


def _block(text, name):
    key = f'\n\t(symbol "{name}"'
    i = text.find(key)
    if i < 0:
        raise KeyError(name)
    i += 1
    depth = 0
    j = i
    in_str = False
    while True:
        c = text[j]
        if in_str:
            if c == "\\":
                j += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return parse(text[i:j + 1])


def lib_symbol(lib_id):
    """Return the flattened symbol under the project library name "emgpod:NAME".

    Symbols taken from KiCad's standard libraries are copied into the project
    library, so the schematic does not depend on the library version installed.
    """
    lib, name = lib_id.split(":")
    key = "emgpod:" + name
    if key in _sym_cache:
        return _sym_cache[key]
    if name not in CUSTOM:
        if lib not in _lib_text:
            _lib_text[lib] = open(os.path.join(KICAD_SYMBOLS, lib + ".kicad_sym"), encoding="utf8").read()
        sym = _block(_lib_text[lib], name)
        ext = find(sym, "extends")
        if ext:
            parent = _block(_lib_text[lib], ext[1])
            child_props = {p[1]: p for p in findall(sym, "property")}
            merged = [parent[0], Q(name)]
            for x in parent[2:]:
                if isinstance(x, list) and x[0] == "property":
                    merged.append(child_props.get(x[1], x))
                elif isinstance(x, list) and x[0] == "symbol":
                    x = copy.deepcopy(x)
                    x[1] = Q(name + x[1][len(ext[1]):])
                    merged.append(x)
                else:
                    merged.append(x)
            sym = merged
        CUSTOM[name] = sym
    sym = copy.deepcopy(CUSTOM[name])
    sym[1] = Q(key)
    _sym_cache[key] = sym
    return sym


def sym_pins(sym):
    """[(number, name, x, y, angle, length)] in library coordinates (y up)."""
    out = []
    for unit in findall(sym, "symbol"):
        for p in findall(unit, "pin"):
            at = find(p, "at")
            out.append((str(find(p, "number")[1]), str(find(p, "name")[1]),
                        float(at[1]), float(at[2]), int(float(at[3])), float(find(p, "length")[1])))
    return out


def xform(x, y, rot):
    """Library offset (y up) -> sheet offset (y down) for a symbol rotation."""
    return {0: (x, -y), 90: (-y, -x), 180: (-x, y), 270: (y, x)}[rot]


def font(size=1.27, justify=None, hide=False, bold=False):
    f = ["font", ["size", size, size]]
    if bold:
        f.append(["bold", "yes"])
    e = ["effects", f]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append(["hide", "yes"])
    return e


def box_symbol(name, ref, left=(), right=(), top=(), bottom=(), pitch=2.54, width=None, footprint="",
               datasheet="", description="", left_pitch=None, pin_len=2.54, tb_pitch=None):
    """Rectangle symbol. Each side is a list of (number, name, electrical_type) or None for a gap."""
    lp = left_pitch or pitch
    tp = tb_pitch or pitch
    h = max(len(left) * lp, len(right) * pitch, 2 * pitch)
    w = width or max(len(top), len(bottom), 4) * tp + 2 * tp
    w = round(w / 2.54) * 2.54
    h = round(h / 2.54 + 0.499) * 2.54
    x0, y0 = -w / 2, h / 2                       # top-left corner, library coords
    pins = []

    def pin(p, x, y, ang):
        if p is None:
            return
        num, pname, etype = p
        pins.append(["pin", etype, "line", ["at", r(x), r(y), ang], ["length", pin_len],
                     ["name", Q(pname), font(1.016)], ["number", Q(str(num)), font(1.016)]])

    def snap(v):
        return round(v / 1.27) * 1.27

    for i, p in enumerate(left):
        pin(p, x0 - pin_len, snap(y0 - lp / 2 - i * lp), 0)
    for i, p in enumerate(right):
        pin(p, -x0 + pin_len, snap(y0 - pitch / 2 - i * pitch), 180)
    tx = snap(-(len(top) - 1) * tp / 2)
    for i, p in enumerate(top):
        pin(p, tx + i * tp, y0 + pin_len, 270)
    bx = snap(-(len(bottom) - 1) * tp / 2)
    for i, p in enumerate(bottom):
        pin(p, bx + i * tp, -y0 - pin_len, 90)
    sym = ["symbol", Q(name), ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"],
           ["property", Q("Reference"), Q(ref), ["at", r(x0), r(y0 + 1.27), 0], font(justify="left bottom")],
           ["property", Q("Value"), Q(name), ["at", r(x0), r(-y0 - 1.27), 0], font(justify="left top")],
           ["property", Q("Footprint"), Q(footprint), ["at", 0, 0, 0], font(hide=True)],
           ["property", Q("Datasheet"), Q(datasheet), ["at", 0, 0, 0], font(hide=True)],
           ["property", Q("Description"), Q(description), ["at", 0, 0, 0], font(hide=True)],
           ["symbol", Q(name + "_0_1"),
            ["rectangle", ["start", r(x0), r(y0)], ["end", r(-x0), r(-y0)],
             ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]]],
           ["symbol", Q(name + "_1_1")] + pins,
           ["embedded_fonts", "no"]]
    CUSTOM[name] = sym
    return sym


def power_symbol(name):
    """A power-rail symbol that looks like +3V3 but carries another net name."""
    base = copy.deepcopy(lib_symbol("power:+3V3"))
    old = "+3V3"

    def walk(n):
        for i, x in enumerate(n):
            if isinstance(x, list):
                walk(x)
            elif isinstance(x, Q) and x == old:
                n[i] = Q(name)
            elif isinstance(x, Q) and x.startswith(old + "_"):
                n[i] = Q(name + x[len(old):])
            elif isinstance(x, Q) and x == "emgpod:+3V3":
                n[i] = Q(name)
    walk(base)
    base[1] = Q(name)
    for p in findall(base, "property"):
        if p[1] == "Description":
            p[2] = Q(f'Power symbol creates a global label with name "{name}"')
    CUSTOM[name] = base
    return base


def write_custom_library(path):
    lib = ["kicad_symbol_lib", ["version", 20241209], ["generator", Q("emg_pod_gen")],
           ["generator_version", Q("9.0")]]
    for name in sorted(CUSTOM):
        s = copy.deepcopy(CUSTOM[name])
        s[1] = Q(name)
        lib.append(s)
    with open(path, "w", encoding="utf8") as f:
        f.write(dump(lib) + "\n")


# ---------------------------------------------------------------- placed parts
class Part:
    def __init__(self, lib_id, ref, x, y, rot):
        self.lib_id, self.ref, self.x, self.y, self.rot = lib_id, ref, x, y, rot
        self.pins = {}
        self.names = {}
        for num, name, px, py, ang, length in sym_pins(lib_symbol(lib_id)):
            dx, dy = xform(px, py, rot)
            # unit vector pointing away from the symbol body
            ox, oy = xform(*{0: (-1, 0), 180: (1, 0), 90: (0, -1), 270: (0, 1)}[ang], rot)
            self.pins[num] = (r(x + dx), r(y + dy), int(round(ox)), int(round(oy)))
            self.names.setdefault(name, []).append(num)

    def p(self, pin):
        """Sheet position of a pin given by number or by unique name."""
        pin = str(pin)
        if pin not in self.pins:
            nums = self.names[pin]
            assert len(nums) == 1, (self.ref, pin, nums)
            pin = nums[0]
        return self.pins[pin][:2]

    def out(self, pin):
        pin = str(pin)
        if pin not in self.pins:
            pin = self.names[pin][0]
        return self.pins[pin][2:]


class Sheet:
    def __init__(self, filename, title, paper="A4", page=1, root_uuid=None, sheet_uuid=None, rev="A",
                 date="", comments=()):
        self.filename, self.title, self.paper, self.page = filename, title, paper, page
        self.uuid = uid("sheet-file", filename)
        self.path = f"/{root_uuid}" if sheet_uuid is None else f"/{root_uuid}/{sheet_uuid}"
        self.rev, self.date, self.comments = rev, date, comments
        self.items = []
        self.used = {}
        self.parts = {}
        self.wires = []
        self.endpoints = []       # label anchors: wires are split there
        self.pinpts = []          # pin positions
        self.pwr = 0
        self.n = 0

    def _id(self, kind):
        self.n += 1
        return uid(self.filename, kind, self.n)

    # ---- symbols
    def place(self, lib_id, ref, value, x, y, rot=0, footprint="", fields=None, ref_at=None, val_at=None,
              in_bom=True, on_board=True, dnp=False, show_value=True, show_ref=True, datasheet=""):
        assert on_grid(x) and on_grid(y), (ref, x, y)
        sym = lib_symbol(lib_id)
        lib_id = str(sym[1])
        self.used[lib_id] = sym
        part = Part(lib_id, ref, r(x), r(y), rot)
        assert ref not in self.parts, ref
        self.parts[ref] = part
        fa = 90 if rot in (90, 270) else 0          # stored angle that renders horizontally
        rx, ry, rj = ref_at or (x, y - 3.0, "")
        vx, vy, vj = val_at or (x, y + 3.0, "")

        def just(j):
            # left/right swap when the symbol transform mirrors the text direction
            if rot in (90, 180):      # found by rendering: these two rotations mirror the text anchor
                j = j.replace("left", "@").replace("right", "left").replace("@", "right")
            return j or None

        node = ["symbol", ["lib_id", Q(lib_id)], ["at", r(x), r(y), rot], ["unit", 1],
                ["exclude_from_sim", "no"], ["in_bom", "yes" if in_bom else "no"],
                ["on_board", "yes" if on_board else "no"], ["dnp", "yes" if dnp else "no"],
                ["uuid", uid(self.filename, "sym", ref)],
                ["property", Q("Reference"), Q(ref), ["at", r(rx), r(ry), fa],
                 font(justify=just(rj), hide=not show_ref)],
                ["property", Q("Value"), Q(value), ["at", r(vx), r(vy), fa],
                 font(justify=just(vj), hide=not show_value)],
                ["property", Q("Footprint"), Q(footprint), ["at", r(x), r(y), 0], font(hide=True)],
                ["property", Q("Datasheet"), Q(datasheet), ["at", r(x), r(y), 0], font(hide=True)],
                ["property", Q("Description"), Q(""), ["at", r(x), r(y), 0], font(hide=True)]]
        for k, v in (fields or {}).items():
            node.append(["property", Q(k), Q(v), ["at", r(x), r(y), 0], font(hide=True)])
        for num in part.pins:
            node.append(["pin", Q(num), ["uuid", uid(self.filename, "pin", ref, num)]])
        node.append(["instances", ["project", Q(PROJECT),
                                   ["path", Q(self.path), ["reference", Q(ref)], ["unit", 1]]]])
        self.items.append(node)
        for num, (px, py, _, _) in part.pins.items():
            self.pinpts.append((px, py))
        return part

    def power(self, net, pt, rot=0):
        """Power symbol with its pin at pt. rot 0 = rail symbols point up, GND points down."""
        self.pwr += 1
        lib_id = {"GND": "power:GND", "+3V3": "power:+3V3", "PWR_FLAG": "power:PWR_FLAG"}.get(net, "emgpod:" + net)
        ref = f"#PWR{self.page:02d}{self.pwr:02d}" if net != "PWR_FLAG" else f"#FLG{self.page:02d}{self.pwr:02d}"
        x, y = pt
        bx, by = xform(0, -1 if net == "GND" else 1, rot)      # direction the symbol body points
        if bx == 0:
            vx, vy, vj = x, y + by * 3.6, ""
        else:
            vx, vy, vj = x + bx * 3.3, y, ("left" if bx > 0 else "right")
        return self.place(lib_id, ref, net, x, y, rot, in_bom=False, show_ref=False,
                          val_at=(vx, vy, vj), ref_at=(x, y, ""), show_value=(net != "PWR_FLAG"))

    # ---- connectivity
    def wire(self, *pts):
        pts = [(r(x), r(y)) for x, y in pts]
        for a, b in zip(pts[:-1], pts[1:]):
            if a == b:
                continue
            assert a[0] == b[0] or a[1] == b[1], ("diagonal wire", a, b)
            assert all(on_grid(v) for v in a + b), ("off grid", a, b)
            self.wires.append((a, b))
        return pts[-1]

    def label(self, net, pt, rot=0):
        x, y = pt
        j = {0: "left bottom", 180: "right bottom", 90: "left bottom", 270: "right bottom"}[rot]
        self.items.append(["label", Q(net), ["at", r(x), r(y), rot], font(justify=j), ["uuid", self._id("label")]])
        self.endpoints.append((r(x), r(y)))
        return pt

    def glabel(self, net, pt, shape="passive", rot=0):
        x, y = pt
        j = "left" if rot in (0, 90) else "right"
        self.items.append(["global_label", Q(net), ["shape", shape], ["at", r(x), r(y), rot],
                           font(justify=j), ["uuid", self._id("glabel")],
                           ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", r(x), r(y), 0],
                            font(hide=True)]])
        self.endpoints.append((r(x), r(y)))
        return pt

    def nc(self, pt):
        self.items.append(["no_connect", ["at", r(pt[0]), r(pt[1])], ["uuid", self._id("nc")]])

    def text(self, s, pt, size=1.27, bold=False, justify="left bottom"):
        self.items.append(["text", Q(s), ["exclude_from_sim", "no"], ["at", r(pt[0]), r(pt[1]), 0],
                           font(size, justify, bold=bold), ["uuid", self._id("text")]])

    def box(self, x0, y0, x1, y1):
        self.items.append(["rectangle", ["start", r(x0), r(y0)], ["end", r(x1), r(y1)],
                           ["stroke", ["width", 0], ["type", "dash"]], ["fill", ["type", "none"]],
                           ["uuid", self._id("rect")]])

    def subsheet(self, name, filename, x, y, w, h, page):
        su = uid("sheet-symbol", filename)
        self.items.append(
            ["sheet", ["at", r(x), r(y)], ["size", r(w), r(h)], ["exclude_from_sim", "no"], ["in_bom", "yes"],
             ["on_board", "yes"], ["dnp", "no"], ["fields_autoplaced", "yes"],
             ["stroke", ["width", 0.1524], ["type", "solid"]], ["fill", ["color", 0, 0, 0, 0.0]], ["uuid", su],
             ["property", Q("Sheetname"), Q(name), ["at", r(x), r(y - 0.7), 0], font(1.5, "left bottom", bold=True)],
             ["property", Q("Sheetfile"), Q(filename), ["at", r(x), r(y + h + 0.6), 0], font(1.27, "left top")],
             ["instances", ["project", Q(PROJECT), ["path", Q(self.path), ["page", Q(str(page))]]]]])
        return su

    # ---- output
    def _split_wires(self):
        """Cut every wire where a pin, a label or another wire's end lies on it.

        KiCad only connects things at wire ends, so a wire drawn across a pin would
        otherwise pass it by.
        """
        pts = set(self.endpoints) | set(self.pinpts)
        for a, b in self.wires:
            pts.add(a)
            pts.add(b)
        out = []
        for a, b in self.wires:
            if a[0] == b[0]:
                inner = sorted(p for p in pts if p[0] == a[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1]))
            else:
                inner = sorted(p for p in pts if p[1] == a[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0]))
            chain = sorted([a, b] + inner)
            out += list(zip(chain[:-1], chain[1:]))
        self.wires = sorted(set(out))

    def _junctions(self):
        count = {}
        for a, b in self.wires:
            for p in (a, b):
                count[p] = count.get(p, 0) + 1
        for p in self.pinpts:
            if p in count:
                count[p] += 1
        return sorted(p for p, c in count.items() if c >= 3)

    def write(self, directory):
        tb = ["title_block", ["title", Q(self.title)], ["date", Q(self.date)], ["rev", Q(self.rev)],
              ["company", Q("EMG wristband, main pod")]]
        for i, c in enumerate(self.comments, 1):
            tb.append(["comment", i, Q(c)])
        doc = ["kicad_sch", ["version", 20250114], ["generator", Q("eeschema")], ["generator_version", Q("9.0")],
               ["uuid", self.uuid], ["paper", Q(self.paper)], tb,
               ["lib_symbols"] + [self.used[k] for k in sorted(self.used)]]
        self._split_wires()
        for p in self._junctions():
            doc.append(["junction", ["at", p[0], p[1]], ["diameter", 0], ["color", 0, 0, 0, 0],
                        ["uuid", uid(self.filename, "junction", p)]])
        for i, (a, b) in enumerate(self.wires):
            doc.append(["wire", ["pts", ["xy", a[0], a[1]], ["xy", b[0], b[1]]],
                        ["stroke", ["width", 0], ["type", "default"]], ["uuid", uid(self.filename, "wire", i)]])
        doc += self.items
        if self.page == 1:
            doc.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
        doc.append(["embedded_fonts", "no"])
        with open(os.path.join(directory, self.filename), "w", encoding="utf8") as f:
            f.write(dump(doc) + "\n")
