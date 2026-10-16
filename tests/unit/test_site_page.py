"""The product site's hand-written pages: self-contained, sized to their drawings, and honest without scripts."""
import json
import pathlib
import re
import struct
from dataclasses import asdict
from html.parser import HTMLParser

import pytest

from loopwright.config import DEFAULT

SITE = pathlib.Path(__file__).resolve().parents[2] / "site"
DATA = json.loads((SITE / "data.js").read_text(encoding="utf-8")[len("window.LOOPWRIGHT = "):].rstrip().rstrip(";"))


class Page(HTMLParser):
    """Collects references, images and the text of every element the script fills in."""

    def __init__(self):
        super().__init__()
        self.refs, self.images, self.filled, self.open, self.settings = [], [], [], [], {}
        self.figures = None
        self.setting = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("src", "href"):
            if key in a and tag in ("script", "link", "img"):
                self.refs.append((tag, a[key]))
        if tag == "img":
            self.images.append(a)
        if "data-figures" in a:
            self.figures = a["data-figures"]
        for key in ("data-num", "data-fig", "data-key"):
            if key in a:
                name = f"{self.figures}.{a[key]}" if key == "data-key" else a[key]
                self.open.append([key, name, ""])
        if "data-setting" in a:
            self.setting = a["data-setting"]
            self.settings[self.setting] = ""

    def handle_data(self, data):
        for item in self.open:
            item[2] += data
        if self.setting:
            self.settings[self.setting] += data

    def handle_endtag(self, tag):
        if self.open and tag in ("span", "strong", "dd"):
            self.filled.append(tuple(self.open.pop()))
        if tag == "span":
            self.setting = None


def page(name="index.html"):
    p = Page()
    p.feed((SITE / name).read_text(encoding="utf-8"))
    return p


@pytest.mark.parametrize("name", ["index.html", "settings.html"])
def test_the_pages_load_nothing_from_another_site(name):
    refs = page(name).refs
    assert refs, "no references found"
    for tag, ref in refs:
        assert not re.match(r"(https?:)?//", ref), ref
        assert (SITE / ref).exists(), ref
    css = (SITE / "styles.css").read_text(encoding="utf-8")
    assert "@import" not in css
    for url in re.findall(r"url\(\"?([^\")]+)\"?\)", css):
        assert not re.match(r"(https?:)?//", url) and (SITE / url).exists(), url
    assert "@import" not in (SITE / "figure.css").read_text(encoding="utf-8")


def size_of(path):
    if path.suffix == ".svg":
        w, h = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', path.read_text(encoding="utf-8")).groups()
        return int(float(w)), int(float(h))
    head = path.read_bytes()[:30]
    assert head[:4] == b"RIFF" and head[8:12] == b"WEBP" and head[12:16] == b"VP8 ", "expected a lossy WebP"
    w, h = struct.unpack("<HH", head[26:30])
    return w & 0x3FFF, h & 0x3FFF


def test_every_image_states_the_size_of_its_file_so_nothing_shifts_on_load():
    images = page().images
    assert len(images) >= 8
    for img in images:
        assert (int(img["width"]), int(img["height"])) == size_of(SITE / img["src"]), img["src"]
        assert img.get("alt"), img["src"]


def expected(name, kind):
    n = DATA["numbers"]
    if kind == "data-num":
        derived = {"infeasible": n["plans"] - n["feasible"], "J_per_plan": n["J"] / n["valid"]}
        v = derived.get(name, n.get(name, DATA.get(name)))
        if name in ("p50_s", "p95_s"):
            return f"{v:.2f}"
        if name == "J_per_plan":
            return f"{v:.1f}"
        return v if isinstance(v, str) else f"{round(v):,}"
    drawing, key = name.split(".")
    v = DATA["drawings"][drawing][key]
    return f"{v:.1f}" if key in ("length_m", "overlap_m", "J") else str(v)


def test_without_scripts_the_page_shows_the_same_numbers_as_the_data_file():
    filled = page().filled
    assert len(filled) >= 28
    for kind, name, text in filled:
        assert text.strip() == expected(name, kind), (kind, name)


def shown(value):
    """A setting the way the page's script prints it."""
    if isinstance(value, (list, tuple)):
        return ", ".join(value)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(int(value)) if float(value).is_integer() else str(value)
    return value


def test_the_settings_page_shows_every_setting_with_its_default():
    settings = page("settings.html").settings
    defaults = asdict(DEFAULT)
    assert set(settings) == set(defaults)
    assert {k: v.strip() for k, v in settings.items()} == {k: shown(v) for k, v in defaults.items()}
    assert DATA["settings"] == json.loads(json.dumps(defaults))
