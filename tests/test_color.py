from launchpad import color
from launchpad.color import Color, FLAG_COPY, FLAG_CLEAR, FLAG_IGNORE


def test_palette_velocities_match_novation_reference():
    # Values straight out of the Launchpad S PRM (copy mode, +0x0C).
    assert color.RED.velocity() == 0x0F     # 15
    assert color.GREEN.velocity() == 0x3C   # 60
    assert color.AMBER.velocity() == 0x3F   # 63
    assert color.OFF.velocity() == 0x0C     # 12 (copy-mode "off")


def test_flag_arithmetic():
    # PRM: flashing = copy value minus 4 (clear bit 2); ignore = minus 12.
    assert color.AMBER.velocity(FLAG_COPY) == 63
    assert color.AMBER.velocity(FLAG_CLEAR) == 59
    assert color.AMBER.velocity(FLAG_IGNORE) == 51


def test_velocity_round_trip():
    for r in range(4):
        for g in range(4):
            v = Color(r, g).velocity()
            assert Color.from_velocity(v) == Color(r, g)


def test_bounds():
    for bad in [(-1, 0), (4, 0), (0, 9)]:
        try:
            Color(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Color{bad} should have raised")


def test_parse():
    assert color.parse("red") is color.RED
    assert color.parse([3, 3]) == color.AMBER
    assert color.parse(color.GREEN) is color.GREEN


def test_scaled_and_bool():
    assert color.RED.scaled(0) == color.OFF
    assert not color.OFF
    assert color.RED
