"""One EXIF orientation contract for reviewed images, model input and boxes."""
import hashlib

from PIL import Image, ImageOps


def orientation_of(image):
    orientation = image.getexif().get(274, 1)
    if type(orientation) is not int or orientation not in range(1, 9):
        raise ValueError('Invalid EXIF orientation; resolve metadata before annotation')
    return orientation


def upright_rgb(image):
    orientation_of(image)
    return ImageOps.exif_transpose(image).convert('RGB')


def load_upright_rgb(path):
    with Image.open(path) as image:
        return upright_rgb(image)


def upright_digest(image):
    pixels = upright_rgb(image)
    header = f'RGB:{pixels.width}:{pixels.height}:'.encode('ascii')
    return hashlib.sha256(header + pixels.tobytes()).hexdigest()


def orient_box(box, orientation):
    """Convert a validated raw-pixel normalized xywh box into upright space."""
    x, y, width, height = box
    mappings = {
        1: (x, y, width, height),
        2: (1 - x, y, width, height),
        3: (1 - x, 1 - y, width, height),
        4: (x, 1 - y, width, height),
        5: (y, x, height, width),
        6: (1 - y, x, height, width),
        7: (1 - y, 1 - x, height, width),
        8: (y, 1 - x, height, width),
    }
    if type(orientation) is not int or orientation not in mappings:
        raise ValueError('Invalid EXIF orientation')
    return list(mappings[orientation])
