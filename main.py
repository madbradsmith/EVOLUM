"""Reverie — scene-driven self-insert experiential fiction product.

v1 placeholder. The real app lands incrementally as the build progresses.
For now this serves a single landing page so the Render service has
something to deploy and so the private URL responds 200 while we wire
the rest.
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

HERE = Path(__file__).parent

app = FastAPI(title="Reverie")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/healthz")
async def healthz():
    return {"ok": True}
