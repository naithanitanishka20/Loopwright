import copy
import io

import pytest

pytest.importorskip("fastapi", reason="install the serve extra")
from fastapi.testclient import TestClient  # noqa: E402

from loopwright.api.app import create_app  # noqa: E402

SQ = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
SKETCH = {"rooms": [{"type": "living", "polygon": SQ(0, 0, 6, 6)}, {"type": "bedroom", "polygon": SQ(0, 6, 6, 12)}],
          "doors": [[0, 1]]}


@pytest.fixture
def client():
    return TestClient(create_app(data_path=None), base_url="http://127.0.0.1")


def test_solving_a_sketch_returns_design_drawing_and_explanations(client):
    r = client.post("/api/solve", json={"source": {"sketch": SKETCH}})
    assert r.status_code == 200
    body = r.json()
    assert (body["design"]["metrics"]["hubs"], body["design"]["validation"]["valid"]) == (1, True)
    assert body["svg"].startswith("<svg")
    assert body["explain"]["binding"] == "one zone"
    assert [c["leg"] for c in body["cuts"]["H1"]] == [1, 2, 3]
    assert body["installer"]["bom"]["devices"] == 2
    assert [room["id"] for room in body["rooms"]] == ["living_0", "bedroom_0"]


def test_edits_and_settings_apply_before_solving(client):
    r = client.post("/api/solve", json={"source": {"sketch": SKETCH}, "edits": [{"op": "remove_door", "door": 0}],
                                        "settings": {"max_nodes": 1}})
    assert r.status_code == 200
    assert r.json()["design"]["metrics"]["hubs"] == 2


@pytest.mark.parametrize("payload, message", [
    ({"source": {"sketch": {"rooms": [{"type": "ballroom", "polygon": SQ(0, 0, 6, 6)}], "doors": []}}}, "room type"),
    ({"source": {"sketch": SKETCH}, "settings": {"zone_link": "sideways"}}, "zone_link"),
    ({"source": {"sketch": SKETCH}, "edits": [{"op": "paint_walls"}]}, "unknown edit"),
    ({"source": {}}, "plan_id or a sketch"),
    ({"source": {"sketch": {**SKETCH, "doors": [[0, -1]]}}}, "doesn't have"),
    ({"source": {"sketch": {**SKETCH, "doors": [[True, 1]]}}}, "door room indices"),
])
def test_bad_requests_get_a_400_with_the_reason(client, payload, message):
    r = client.post("/api/solve", json=payload)
    assert r.status_code == 400
    assert message in r.json()["detail"]


def test_a_plan_in_the_wrong_units_is_refused_not_routed(client):
    huge = {"rooms": [{"type": "living", "polygon": SQ(0, 0, 5000, 4000)}], "doors": []}
    r = client.post("/api/solve", json={"source": {"sketch": huge}})
    assert r.status_code == 400 and "check its units" in r.json()["detail"]


def test_validate_catches_a_leg_bent_diagonally(client):
    design = client.post("/api/solve", json={"source": {"sketch": SKETCH}}).json()["design"]
    bent = copy.deepcopy(design)
    path = bent["rings"][0]["legs"][1]["path"]
    path[-1] = [path[-1][0] + 0.7, path[-1][1] + 0.7]  # diagonal whichever way the segment ran
    r = client.post("/api/validate", json={"source": {"sketch": SKETCH}, "design": bent})
    failed = [c["id"] for c in r.json()["checks"] if c["pass"] is False]
    assert r.json()["valid"] is False and "V14" in failed


def test_validate_reports_structure_problems_before_rules(client):
    r = client.post("/api/validate", json={"source": {"sketch": SKETCH}, "design": {"schema": "loopwright/2"}})
    assert r.json()["valid"] is False and r.json()["structure"]


def test_importing_a_plan_image_returns_a_sketch(client):
    from tests.unit.test_import_image import M_PER_PX, plan_image

    r = client.post("/api/import", files={"file": ("plan.png", plan_image(), "image/png")}, data={"m_per_px": M_PER_PX})
    assert r.status_code == 200
    assert (len(r.json()["rooms"]), r.json()["doors"]) == (2, [[0, 1]])


def test_importing_a_dxf_returns_a_sketch(client, tmp_path):
    from tests.unit.test_import_dxf import drawing

    path = drawing(tmp_path / "flat.dxf")
    r = client.post("/api/import", files={"file": ("flat.dxf", path.read_bytes(), "application/dxf")})
    assert r.status_code == 200
    assert [room["type"] for room in r.json()["rooms"]] == ["living", "bedroom"]


def test_unsupported_and_oversized_uploads_are_refused(tmp_path):
    client = TestClient(create_app(data_path=None, max_upload_mb=0.01), base_url="http://127.0.0.1")
    assert client.post("/api/import", files={"file": ("notes.txt", b"hello", "text/plain")}).status_code == 400
    assert client.post("/api/import", files={"file": ("big.png", b"x" * 20_000, "image/png")},
                       data={"m_per_px": 0.02}).status_code == 413


@pytest.mark.parametrize("limit", [0, -1, float("nan"), float("inf"), True])
def test_invalid_upload_limits_are_rejected(limit):
    with pytest.raises(ValueError, match="max_upload_mb must be a finite positive number"):
        create_app(data_path=None, max_upload_mb=limit)


def test_an_image_claiming_huge_dimensions_is_refused_before_decoding(client):
    import struct
    import zlib

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    # A 60-byte PNG whose header claims 8000 x 8000 grey pixels (64 megapixels).
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 8000, 8000, 8, 0, 0, 0, 0)) + chunk(b"IEND", b"")
    r = client.post("/api/import", files={"file": ("bomb.png", png, "image/png")}, data={"m_per_px": 0.02})
    assert r.status_code == 400 and "scale it down" in r.json()["detail"]


def test_requests_naming_another_host_are_refused(client):
    assert client.get("/", headers={"host": "evil.example"}).status_code == 400


def test_the_app_page_and_dataset_status(client):
    page = client.get("/")
    assert page.status_code == 200 and 'id="app"' in page.text
    assert page.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert client.get("/api/plans").json() == {"available": False, "test": []}


def test_installer_pack_page(client):
    r = client.post("/api/installer", json={"source": {"sketch": SKETCH}})
    assert r.status_code == 200 and "Commissioning sheet" in r.text


@pytest.mark.dataset
def test_resplan_plans_by_id_under_both_zone_rules():
    from tests.conftest import DATA

    split = DATA.with_name("split.json")
    if not split.exists():
        pytest.skip(f"dataset split not found at {split}")

    client = TestClient(create_app(data_path=str(DATA)), base_url="http://127.0.0.1")
    strict = client.post("/api/solve", json={"source": {"plan_id": 16448}}).json()["design"]["metrics"]["hubs"]
    loose = client.post("/api/solve", json={"source": {"plan_id": 16448},
                                            "settings": {"zone_link": "through_rooms"}}).json()["design"]["metrics"]["hubs"]
    assert (strict, loose) == (4, 2)
    assert client.post("/api/solve", json={"source": {"plan_id": 999999999}}).status_code == 404
    listing = client.get("/api/plans").json()
    assert listing["available"] is True and len(listing["test"]) == 1632


def a_site(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<!doctype html><html><head><title>Loopwright</title></head><body>the site</body></html>",
                                     encoding="utf-8")
    (site / "styles.css").write_text("body{}", encoding="utf-8")
    return site


def test_with_a_site_folder_the_site_is_the_front_page_and_the_app_moves_to_app(tmp_path):
    client = TestClient(create_app(data_path=None, site_dir=a_site(tmp_path)), base_url="http://127.0.0.1")
    front = client.get("/")
    assert front.status_code == 200 and "the site" in front.text
    assert '<meta name="loopwright:app" content="/app/">' in front.text  # the site's feature buttons open this app
    assert "default-src 'self'" in front.headers["content-security-policy"]
    assert client.get("/styles.css").text == "body{}"
    assert 'id="app"' in client.get("/app/").text
    moved = client.get("/app", follow_redirects=False)
    assert moved.status_code in (307, 308) and moved.headers["location"].endswith("/app/")
    assert client.get("/api/plans").json() == {"available": False, "test": []}
    assert client.get("/missing.html").status_code == 404


def test_serve_can_put_the_site_in_front_and_answer_to_a_public_host(tmp_path, monkeypatch):
    import uvicorn

    from loopwright.cli import main

    served = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: served.update(app=app, **options))
    assert main(["serve", "--site", str(a_site(tmp_path)), "--host", "0.0.0.0", "--port", "8080",
                 "--allow-host", "loopwright.example"]) == 0
    assert (served["host"], served["port"]) == ("0.0.0.0", 8080)
    client = TestClient(served["app"], base_url="http://loopwright.example")
    assert "the site" in client.get("/").text and 'id="app"' in client.get("/app/").text
    assert client.get("/", headers={"host": "evil.example"}).status_code == 400
