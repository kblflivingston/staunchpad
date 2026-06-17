import pytest

from staunchpad import color
from staunchpad.color import Color, palette, rgb


def test_named_palette_indices_match_prm_examples():
    # Indices taken straight from the Launchpad MK2 PRM worked examples.
    assert color.RED.index == 5
    assert color.ORANGE.index == 9
    assert color.YELLOW.index == 13
    assert color.GREEN.index == 21
    assert color.BLUE.index == 45
    assert color.PINK.index == 53
    assert color.PURPLE.index == 81
    assert color.OFF.index == 0


def test_palette_velocity():
    assert palette(45).velocity() == 45
    assert not palette(0)          # off is falsy
    assert palette(5)


def test_rgb_mode():
    c = rgb(63, 0, 0)
    assert c.is_rgb and c.rgb == (63, 0, 0)
    with pytest.raises(ValueError):
        c.velocity()               # RGB has no palette velocity


def test_validation():
    with pytest.raises(ValueError):
        Color()                    # neither index nor rgb
    with pytest.raises(ValueError):
        Color(index=5, rgb=(1, 1, 1))   # both
    with pytest.raises(ValueError):
        palette(200)               # index out of range
    with pytest.raises(ValueError):
        rgb(64, 0, 0)              # element out of range


def test_parse():
    assert color.parse("red") is color.RED
    assert color.parse(45) == palette(45)
    assert color.parse([63, 0, 0]) == rgb(63, 0, 0)
    assert color.parse(color.GREEN) is color.GREEN
    assert color.parse("#ff0000") == rgb(63, 0, 0)   # 255>>2 == 63
    with pytest.raises(ValueError):
        color.parse(True)          # bool guarded
