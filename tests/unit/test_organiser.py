import pytest

from loopwright.io.organiser import from_dict


def test_aliases_and_geometry_encodings_map_onto_resplan_keys():
    plan = from_dict({
        "id": 3,
        "area": 12.0,
        "Boundary": "POLYGON ((0 0, 4 0, 4 3, 0 3, 0 0))",
        "Store": [[0, 0], [1, 0], [1, 1], [0, 1]],
        "Bedrooms": [[[1, 0], [4, 0], [4, 3], [1, 3]]],
        "Bath": {"type": "Polygon", "coordinates": [[[0, 1], [1, 1], [1, 3], [0, 3], [0, 1]]]},
    })
    assert plan["inner"].area == 12
    assert plan["storage"].area == 1
    assert plan["bedroom"].geom_type == "MultiPolygon"
    assert plan["bathroom"].area == 2


def test_missing_boundary_is_named():
    with pytest.raises(ValueError, match="boundary"):
        from_dict({"area": 10, "living": "POLYGON ((0 0, 1 0, 1 1, 0 0))"})
