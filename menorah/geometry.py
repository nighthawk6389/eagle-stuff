"""Menorah board geometry (mm). Front view, origin top-left, +y down (KiCad).

Single source of truth for outline, LED/sensor positions and mechanical
features. All parts are soldered on the BACK; coordinates here are as seen
from the FRONT.
"""
from shapely.geometry import Point, box
from shapely.ops import unary_union

CX = 100.0
CANDLE_DX = [25, 47, 69, 91]    # candle offsets from centre (each side)
CANDLE_W = 12.0
SHAMASH_W = 14.0
NECK_W = 5.5                    # wick neck (carries 4 traces on the back)
NECK_H = 4.0
FLAME_R = 5.0
FLAME_H = 18.0                  # tip to bulb bottom
TIP_R = 1.0

BAR_TOP, BAR_BOT = 70.0, 84.0
CANDLE_TOP = 38.0
SHAMASH_TOP = 24.0
STEM_X0, STEM_X1 = 88.0, 112.0
BASE_X0, BASE_X1 = 45.0, 155.0
BASE_TOP, BASE_BOT = 118.0, 152.0

FOOT_SLOT_X = [55.0, 145.0]
FOOT_SLOT_W = 1.75              # for a 1.6 mm foot board
FOOT_SLOT_DEPTH = 15.5

LED_Y_BOTTOM = 67.0
LED_PITCH = 7.0
HALL_DY = 2.0                   # hall sensor centre below candle top

MIC = (CX, 96.0)
TEXT_BOX = (62.0, 139.5, 138.0, 149.5)      # Hebrew lettering block (front)
BATTERY_ZONE = (108.0, 120.0, 144.0, 151.0)  # keep parts out (back)
ANT_KEEPOUT = (55.0, 117.0, 85.0, 124.6)     # no copper, both layers
U1_POS = (70.0, 130.75)


def flame(cx, body_top):
    neck = box(cx - NECK_W / 2, body_top - NECK_H - 0.5, cx + NECK_W / 2, body_top + 0.5)
    bulb_cy = body_top - NECK_H - FLAME_R + 0.8
    tip = Point(cx, bulb_cy + FLAME_R - FLAME_H + TIP_R)
    drop = unary_union([Point(cx, bulb_cy).buffer(FLAME_R, 48), tip.buffer(TIP_R, 24)]).convex_hull
    return drop, neck, (cx, bulb_cy)


def _candle(cid, x, top, w):
    drop, neck, fc = flame(x, top)
    ys = []
    y = LED_Y_BOTTOM
    while y >= top + 7.9:
        ys.append(y)
        y -= LED_PITCH
    return dict(id=cid, x=x, top=top, w=w, drop=drop, neck=neck,
                flame_led=fc, body_leds=[(x, yy) for yy in ys],   # bottom -> top
                hall=(x, top + HALL_DY))


def candles():
    """C1..C8 left->right as seen from the front, then SH. Night N lights C(9-N)..C8."""
    xs = [CX - d for d in reversed(CANDLE_DX)] + [CX + d for d in CANDLE_DX]
    out = [_candle(f"C{i+1}", x, CANDLE_TOP, CANDLE_W) for i, x in enumerate(xs)]
    out.append(_candle("SH", CX, SHAMASH_TOP, SHAMASH_W))
    return out


def chain_order():
    """LED data chain, left to right: C1..C4, SH, C5..C8; inside a candle bottom->top, flame last.

    Left-to-right order lets every candle-to-candle data link be a short hop along the
    crossbar (the level shifter sits under C1), so the whole chain routes on the back.
    """
    cs = {c["id"]: c for c in candles()}
    order = ["C1", "C2", "C3", "C4", "SH", "C5", "C6", "C7", "C8"]
    leds = []
    for cid in order:
        c = cs[cid]
        for i, p in enumerate(c["body_leds"]):
            leds.append(dict(candle=cid, kind="body", idx=i, pos=p))
        leds.append(dict(candle=cid, kind="flame", idx=len(c["body_leds"]), pos=c["flame_led"]))
    return leds


def slot(fx):
    w = FOOT_SLOT_W
    top = BASE_BOT - FOOT_SLOT_DEPTH
    return unary_union([box(fx - w / 2, top, fx + w / 2, BASE_BOT + 1), Point(fx, top).buffer(w / 2, 16)])


def outline():
    e = CANDLE_DX[-1]
    parts = [
        box(CX - e, BAR_TOP, CX + e, BAR_BOT),
        Point(CX - e, (BAR_TOP + BAR_BOT) / 2).buffer(7, 48),
        Point(CX + e, (BAR_TOP + BAR_BOT) / 2).buffer(7, 48),
        box(STEM_X0, BAR_BOT - 1, STEM_X1, BASE_TOP + 1),
        box(BASE_X0, BASE_TOP, BASE_X1, BASE_BOT).buffer(-3).buffer(3, 16),
    ]
    for c in candles():
        parts.append(box(c["x"] - c["w"] / 2, c["top"], c["x"] + c["w"] / 2, BAR_TOP + 1))
        parts += [c["drop"], c["neck"]]
    shape = unary_union(parts)
    shape = shape.buffer(1.2, 12).buffer(-1.2, 12)     # fillet inside corners
    shape = shape.buffer(-0.8, 12).buffer(0.8, 12)     # round outside corners
    for fx in FOOT_SLOT_X:
        shape = shape.difference(slot(fx))
    return shape.simplify(0.01)


if __name__ == "__main__":
    o = outline()
    print("bounds", [round(v, 1) for v in o.bounds], "LEDs", len(chain_order()),
          o.geom_type, "verts", len(o.exterior.coords), "holes", len(o.interiors))
