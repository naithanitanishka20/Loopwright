from loopwright.output.schema import safe_stem


def test_safe_stem_distinguishes_ids_that_sanitize_to_the_same_text():
    assert safe_stem("north/east") != safe_stem("north_east")


def test_safe_stem_avoids_windows_device_names():
    assert safe_stem("CON").upper() not in {"CON", "PRN", "AUX", "NUL"}
    assert safe_stem("com1").upper() != "COM1"
