"""Local server for the demo app: solve, edit, validate and import plans over HTTP.

It binds to 127.0.0.1 by default and refuses requests addressed to any other
host, so a web page can't reach it through DNS rebinding. Uploads are size
limited and parsed only as images, PDFs or DXF; ResPlan plans load only from the
configured file, never from an upload.
"""
import contextlib
import json
import math
import mimetypes
import pathlib
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from shapely.errors import ShapelyError

from loopwright.config import DEFAULT
from loopwright.io.edits import apply_edits, door_parts
from loopwright.io.sketch import build_plan
from loopwright.output.app_page import render_app
from loopwright.output.explain import explain_hubs
from loopwright.output.installer import installer_data, render_installer
from loopwright.output.overlay import render_svg
from loopwright.output.resilience import cut_analysis
from loopwright.output.viewer import viewer_data
from loopwright.solve import solve

IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp")
MAX_ROOMS = 80
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                               "style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


class Source(BaseModel):
    plan_id: int | str | None = None
    sketch: dict | None = None


class SolveRequest(BaseModel):
    source: Source
    edits: list[dict] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)


class ValidateRequest(SolveRequest):
    design: dict


@contextlib.contextmanager
def _bad_input(*kinds):
    """Turn input errors into a 400 carrying the reason."""
    try:
        yield
    except HTTPException:
        raise
    except kinds or (ValueError, TypeError, IndexError, KeyError, ShapelyError) as exc:
        raise HTTPException(400, str(exc).strip("'\"")) from exc


def create_app(data_path=None, *, max_upload_mb=20, allowed_hosts=("127.0.0.1", "localhost"), site_dir=None):
    if (isinstance(max_upload_mb, bool) or not isinstance(max_upload_mb, (int, float))
            or not math.isfinite(max_upload_mb) or max_upload_mb <= 0):
        raise ValueError("max_upload_mb must be a finite positive number")
    app = FastAPI(title="Loopwright", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts))
    data = pathlib.Path(data_path) if data_path else None
    limit = int(max_upload_mb * 1024 * 1024)
    cache = {}

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    def resplan():
        if data is None or not data.exists():
            raise HTTPException(404, "no ResPlan dataset configured; start with --data")
        if "plans" not in cache:
            from loopwright.io.resplan import load_plans

            cache["plans"] = {str(p.get("id")): p for p in load_plans(data)}
        return cache["plans"]

    def plan_for(req):
        src = req.source
        if src.sketch is not None:
            rooms = src.sketch.get("rooms")
            if not isinstance(rooms, list) or not 1 <= len(rooms) <= MAX_ROOMS:
                raise ValueError(f"a sketch needs 1 to {MAX_ROOMS} rooms")
            doors = src.sketch.get("doors", [])
            if not isinstance(doors, list):
                raise ValueError("doors must be a list of room-index pairs")
            for door in doors:
                if (not isinstance(door, (list, tuple)) or len(door) != 2
                        or any(type(index) is not int for index in door)):
                    raise ValueError("door room indices must be two integers")
                if any(not 0 <= index < len(rooms) for index in door):
                    raise ValueError("a door names a room the sketch doesn't have")
            plan = build_plan(rooms, doors, wall_m=src.sketch.get("wall_m", 0.1))
        elif src.plan_id is not None:
            plan = resplan().get(str(src.plan_id))
            if plan is None:
                raise HTTPException(404, f"plan {src.plan_id} not found")
        else:
            raise ValueError("source needs a plan_id or a sketch")
        settings = DEFAULT.with_overrides(**req.settings)
        return apply_edits(plan, req.edits, settings), settings

    @app.get("/app/" if site_dir else "/", response_class=HTMLResponse)
    def index():
        return render_app()

    @app.get("/api/plans")
    def plans():
        if data is None or not data.exists():
            return {"available": False, "test": []}
        split = data.with_name("split.json")
        return {"available": True, "test": json.loads(split.read_text(encoding="utf-8"))["test"] if split.exists() else []}

    @app.post("/api/solve")
    def api_solve(req: SolveRequest):
        with _bad_input():
            plan, settings = plan_for(req)
            out, model = solve(plan, settings)
        body = viewer_data(model, out)
        body.update(svg=render_svg(model, out), explain=explain_hubs(out), cuts=cut_analysis(out),
                    installer=installer_data(out, door_parts(plan)))
        return body

    @app.post("/api/validate")
    def api_validate(req: ValidateRequest):
        from loopwright.validate.rules import validate
        from loopwright.validate.structure import validate_design

        issues = validate_design(req.design)
        if issues:
            return {"valid": False, "structure": issues, "checks": []}
        with _bad_input():
            plan, settings = plan_for(req)
            result = validate(plan, req.design, settings)
        return {"valid": result["valid"], "structure": [], "checks": result["checks"]}

    @app.post("/api/installer", response_class=HTMLResponse)
    def api_installer(req: SolveRequest):
        with _bad_input():
            plan, settings = plan_for(req)
            out, model = solve(plan, settings)
        return render_installer(model, out, door_parts(plan))

    @app.post("/api/import")
    async def api_import(file: UploadFile = File(...), m_per_px: float | None = Form(None),
                         area_m2: float | None = Form(None), scale: float | None = Form(None),
                         page: int = Form(0), dpi: int = Form(150)):
        raw = await file.read(limit + 1)
        if len(raw) > limit:
            raise HTTPException(413, f"upload is over the {max_upload_mb:g} MB limit")
        name = (file.filename or "").lower()
        # Parsers of untrusted files can raise almost anything; every failure is the file's fault here.
        with _bad_input(Exception):
            if name.endswith(".dxf"):
                from loopwright.io.dxf import read_dxf

                with tempfile.TemporaryDirectory() as tmp:
                    path = pathlib.Path(tmp) / "upload.dxf"
                    path.write_bytes(raw)
                    return read_dxf(path)
            if name.endswith(".pdf"):
                from loopwright.io.image import read_pdf

                return read_pdf(raw, page=page, dpi=min(max(dpi, 50), 300), scale=scale, m_per_px=m_per_px, area_m2=area_m2)
            if name.endswith(IMAGE_TYPES):
                from loopwright.io.image import read_image

                return read_image(raw, m_per_px=m_per_px, area_m2=area_m2)  # refuses an image too big to process
        raise HTTPException(400, "upload a PNG, JPEG, PDF or DXF file")

    if site_dir:  # the product site in front and the app behind /app/, as on a hosted copy
        site = pathlib.Path(site_dir)
        front = (site / "index.html").read_text(encoding="utf-8").replace(
            "</head>", '<meta name="loopwright:app" content="/app/">\n</head>', 1)

        @app.get("/", response_class=HTMLResponse)
        def front_page():
            return front

        @app.get("/app", include_in_schema=False)
        def to_app():
            return RedirectResponse("/app/")

        mimetypes.add_type("font/woff2", ".woff2")  # not every platform's table knows it
        app.mount("/", StaticFiles(directory=site), name="site")

    return app
