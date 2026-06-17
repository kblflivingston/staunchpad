from launchpad import protocol as P
from launchpad.color import AMBER, RED


def test_basic_commands():
    assert P.reset_msg() == [0xB0, 0x00, 0x00]
    assert P.layout_msg(P.LAYOUT_XY) == [0xB0, 0x00, 0x01]
    assert P.layout_msg(P.LAYOUT_DRUM) == [0xB0, 0x00, 0x02]
    assert P.all_leds_on_msg(0) == [0xB0, 0x00, 0x7D]
    assert P.all_leds_on_msg(2) == [0xB0, 0x00, 0x7F]


def test_brightness_examples_from_prm():
    # Pre-baked examples in the PRM (p.11).
    assert P.brightness_msg(1, 16) == [0xB0, 0x1E, 0x0D]
    assert P.brightness_msg(1, 11) == [0xB0, 0x1E, 0x08]
    assert P.brightness_msg(1, 7) == [0xB0, 0x1E, 0x04]
    assert P.brightness_msg(1, 5) == [0xB0, 0x1E, 0x02]   # default
    assert P.brightness_msg(1, 3) == [0xB0, 0x1E, 0x00]


def test_led_messages():
    # PRM example: light second-from-bottom-left grid LED red -> 90 60 0F.
    assert P.led_note_msg(0x60, RED.velocity()) == [0x90, 0x60, 0x0F]
    assert P.led_cc_msg(0x6A, 0x3C) == [0xB0, 0x6A, 0x3C]


def test_rapid_pairs():
    vels = list(range(80))
    msgs = P.rapid_msgs(vels)
    assert len(msgs) == 40
    assert msgs[0] == [0x92, 0, 1]
    assert msgs[-1] == [0x92, 78, 79]


def test_rapid_pairs_rejects_odd():
    try:
        P.rapid_msgs([1, 2, 3])
    except ValueError:
        pass
    else:
        raise AssertionError("odd-length rapid update should raise")


def test_text_scroll_sysex():
    # PRM "Hello world" header bytes: F0 00 20 29 09 <colour> ...
    msg = P.text_scroll_msg("Hi", AMBER.velocity(), loop=True)
    assert msg[:5] == [0xF0, 0x00, 0x20, 0x29, 0x09]
    assert msg[5] == AMBER.velocity() | P.TEXT_LOOP_BIT
    assert msg[6:8] == [ord("H"), ord("i")]
    assert msg[-1] == 0xF7
    assert P.text_stop_msg() == [0xF0, 0x00, 0x20, 0x29, 0x09, 0x00, 0xF7]
