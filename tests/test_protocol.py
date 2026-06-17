import pytest

from staunchpad import protocol as P

H = [0xF0, 0x00, 0x20, 0x29, 0x02, 0x18]   # MK2 SysEx header
END = 0xF7


def test_sysex_framing():
    assert P.sysex(0x0E, 0x00) == H + [0x0E, 0x00, END]


def test_layout_and_clear():
    assert P.layout_msg(P.LAYOUT_SESSION) == H + [0x22, 0x00, END]
    assert P.set_all_msg(0) == H + [0x0E, 0x00, END]


def test_channel_messages_static_flash_pulse():
    # PRM: light top-left grid LED blue -> 90 51 2D (note 81, palette 45, ch1).
    assert P.note_msg(81, 45, P.CH_STATIC) == [0x90, 81, 45]
    # PRM: flash bottom-left between red and current -> 91 0B 05 (ch2).
    assert P.note_msg(11, 5, P.CH_FLASH) == [0x91, 11, 5]
    # PRM: pulse top-right purple -> 92 58 51 (note 88, palette 81, ch3).
    assert P.note_msg(88, 81, P.CH_PULSE) == [0x92, 88, 81]
    # PRM: light cursor-left LED pink -> B0 6A 35 (CC 106, palette 53).
    assert P.cc_msg(106, 53, P.CH_STATIC) == [0xB0, 106, 53]


def test_set_led_sysex_palette_and_rgb():
    assert P.set_led_msg(81, 45) == H + [0x0A, 81, 45, END]
    assert P.set_led_rgb_msg(81, 0, 0, 63) == H + [0x0B, 81, 0, 0, 63, END]


def test_set_many_leds_one_message():
    msg = P.set_leds_msg([(11, 5), (12, 9), (13, 13)])
    assert msg == H + [0x0A, 11, 5, 12, 9, 13, 13, END]
    assert len(P.set_leds_rgb_msg([(11, 1, 2, 3)])) == len(H) + 1 + 4 + 1


def test_set_leds_limits():
    with pytest.raises(ValueError):
        P.set_leds_msg([(0, 0)] * 81)
    with pytest.raises(ValueError):
        P.set_led_rgb_msg(11, 64, 0, 0)   # element out of range


def test_column_row_all():
    assert P.set_column_msg(0, 5) == H + [0x0C, 0, 5, END]
    assert P.set_row_msg(8, 5) == H + [0x0D, 8, 5, END]
    with pytest.raises(ValueError):
        P.set_column_msg(9, 5)


def test_flash_pulse_sysex_have_unused_mode_byte():
    assert P.flash_led_sysex(11, 5) == H + [0x23, 0x00, 11, 5, END]
    assert P.pulse_led_sysex(88, 81) == H + [0x28, 0x00, 88, 81, END]


def test_text_scroll():
    # PRM "Hello world" header: 14 <colour> <loop> <text...>
    msg = P.scroll_text_msg("Hi", 124, loop=True)
    assert msg[:6] == H
    assert msg[6:9] == [0x14, 124, 1]
    assert msg[9:11] == [ord("H"), ord("i")]
    assert msg[-1] == END
    assert P.scroll_stop_msg() == H + [0x14, END]


def test_device_inquiry():
    assert P.device_inquiry_msg() == [0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]
