from launchpad import layout as L


def test_grid_corners():
    assert L.xy_to_midi(0, 1) == ("note", 0x00)   # top-left grid
    assert L.xy_to_midi(7, 1) == ("note", 0x07)   # top-right grid
    assert L.xy_to_midi(0, 8) == ("note", 0x70)   # bottom-left grid
    assert L.xy_to_midi(7, 8) == ("note", 0x77)   # bottom-right grid


def test_scene_and_top_buttons():
    assert L.xy_to_midi(8, 1) == ("note", 0x08)   # first scene button
    assert L.xy_to_midi(8, 8) == ("note", 0x78)   # last scene button
    assert L.xy_to_midi(0, 0) == ("cc", 104)      # first top button
    assert L.xy_to_midi(7, 0) == ("cc", 111)      # last top button


def test_round_trip():
    for x, y in L.all_coords():
        kind, num = L.xy_to_midi(x, y)
        assert L.midi_to_xy(kind, num) == (x, y)


def test_invalid_coords():
    assert not L.is_valid(8, 0)   # top-right corner does not exist
    assert not L.is_valid(9, 1)
    assert not L.is_valid(0, 9)


def test_rapid_order_is_80_unique_in_spec_order():
    order = L.rapid_order()
    assert len(order) == 80
    assert len(set(order)) == 80
    assert order[0] == (0, 1)     # grid first, top-left
    assert order[63] == (7, 8)    # ...through bottom-right
    assert order[64] == (8, 1)    # then scene buttons
    assert order[72] == (0, 0)    # then top mode buttons
