"""Shared bounds for lossless upright crops of normalized reviewed xywh boxes."""
import math


ROUNDING = 'floor left/top, ceil right/bottom; exclusive right/bottom'


def crop_bounds(box, size):
    if (not isinstance(box, (list, tuple)) or len(box) != 4 or
            any(type(n) not in (int, float) or not math.isfinite(n) for n in box)):
        raise ValueError('Crop box must contain four finite normalized xywh numbers')
    x, y, width, height = box
    if not (0 < width <= 1 and 0 < height <= 1 and
            0 <= x - width / 2 <= x + width / 2 <= 1 and
            0 <= y - height / 2 <= y + height / 2 <= 1):
        raise ValueError('Crop box must stay inside the upright source image')
    w, h = size
    return (max(0, math.floor((x - width / 2) * w)),
            max(0, math.floor((y - height / 2) * h)),
            min(w, math.ceil((x + width / 2) * w)),
            min(h, math.ceil((y + height / 2) * h)))
