from staunchpad import layout as L


def test_grid_corners_session_layout():
    # PRM: top-left grid LED is note 81 (0x51); bottom-left is 11.
    assert L.xy_to_midi(0, 1) == ("note", 81)    # top-left
    assert L.xy_to_midi(7, 1) == ("note", 88)    # top-right
    assert L.xy_to_midi(0, 8) == ("note", 11)    # bottom-left
    assert L.xy_to_midi(7, 8) == ("note", 18)    # bottom-right


def test_scene_and_top_buttons():
    assert L.xy_to_midi(8, 1) == ("note", 89)    # top scene button
    assert L.xy_to_midi(8, 8) == ("note", 19)    # bottom scene button
    assert L.xy_to_midi(0, 0) == ("cc", 104)     # first top button
    assert L.xy_to_midi(7, 0) == ("cc", 111)     # last top button


def test_round_trip():
    for x, y in L.all_coords():
        kind, num = L.xy_to_midi(x, y)
        assert L.midi_to_xy(kind, num) == (x, y)


def test_invalid_coords():
    assert not L.is_valid(8, 0)    # top-right corner does not exist
    assert not L.is_valid(9, 1)
    assert not L.is_valid(0, 9)


def test_column_and_row_indices():
    assert L.column_index(0) == 0 and L.column_index(8) == 8
    # row 0 = top buttons, row 8 (bottom-to-top SysEx) ; our y inverts.
    assert L.row_index(0) == 8     # top buttons row
    assert L.row_index(8) == 0     # bottom grid row
    assert L.row_index(1) == 7     # top grid row


def test_all_coords_count():
    assert len(L.all_coords()) == 80
    assert len(set(L.all_coords())) == 80
