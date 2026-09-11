from PIL import Image

from pipeline.images import _border_whiteness_score, _pad_to_square


def test_border_whiteness_score_all_white():
    img = Image.new("RGB", (50, 50), (255, 255, 255))
    assert _border_whiteness_score(img) == 1.0


def test_border_whiteness_score_all_black():
    img = Image.new("RGB", (50, 50), (0, 0, 0))
    assert _border_whiteness_score(img) == 0.0


def test_pad_to_square_centers_and_pads():
    img = Image.new("RGB", (10, 20), (0, 0, 0))
    squared = _pad_to_square(img, (255, 255, 255))
    assert squared.size == (20, 20)
    assert squared.getpixel((0, 0)) == (255, 255, 255)
    assert squared.getpixel((10, 10)) == (0, 0, 0)
