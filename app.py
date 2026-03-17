from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
from PIL import Image, ImageDraw, ImageFont
import math
from urllib.parse import urlparse
import re

app = FastAPI()

# Ensure static directory exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

WIDTH = 1024
HEIGHT = 1024

# Colors
BG_COLOR = (16, 24, 32)
TEXT_MAIN = (229, 229, 229)
ACCENT_CYAN = (0, 255, 209)
ACCENT_ORANGE = (255, 149, 0)
ACCENT_GREEN = (0, 255, 64)
ACCENT_YELLOW = (248, 231, 28)
ACCENT_RED = (255, 59, 48)
BORDER_COLOR = (60, 70, 80)

import urllib.request

font_paths = [
    "DejaVuSansMono-Bold.ttf",
    "DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
]

def load_font(size, bold=False):
    # Try to find a local font first
    for path in font_paths:
        if ("Bold" in path and bold) or ("Bold" not in path and not bold):
            try:
                return ImageFont.truetype(path, size)
            except IOError:
                pass

    # If no local font found, download a reliable one (Roboto Mono)
    font_url = "https://github.com/googlefonts/RobotoMono/raw/main/fonts/ttf/RobotoMono-Bold.ttf" if bold else "https://github.com/googlefonts/RobotoMono/raw/main/fonts/ttf/RobotoMono-Regular.ttf"
    font_filename = "RobotoMono-Bold.ttf" if bold else "RobotoMono-Regular.ttf"

    if not os.path.exists(font_filename):
        try:
            print(f"Downloading fallback font {font_filename}...")
            urllib.request.urlretrieve(font_url, font_filename)
        except Exception as e:
            print(f"Failed to download font: {e}")
            return ImageFont.load_default()

    try:
        return ImageFont.truetype(font_filename, size)
    except IOError:
        return ImageFont.load_default()

FONT_LARGE = load_font(48, bold=True)
FONT_ERROR = load_font(40, bold=True)
FONT_SUB = load_font(24, bold=False)
FONT_LABEL = load_font(18, bold=True)
FONT_VAL = load_font(36, bold=True)
FONT_TBL_HDR = load_font(20, bold=True)
FONT_ROW = load_font(20, bold=False)

class RenderRequest(BaseModel):
    data: Optional[Dict[str, Any]] = None
    previousData: Optional[Dict[str, Any]] = None
    regionName: str = "Unknown Region"
    type: str = "sim"
    primsHistory: Optional[List[int]] = None
    type: str = "sim" # "sim" or "zone"
    primsHistory: Optional[List[int]] = None

class RenderableUser:
    def __init__(self, json_data, is_prev=False):
        self.json = json_data
        self.uuid = json_data.get("uuid", "")
        self.nameToDisplay = json_data.get("name", "Unknown")
        self.category = 2

        self.category = json_data.get("category", 2)
        self.isOOC = json_data.get("isOOC", False)
        self.isChar = json_data.get("isChar", False)
        if self.isOOC:
            self.nameToDisplay = json_data.get("display_name", self.nameToDisplay)

        total = json_data.get("total", 0)
        active = json_data.get("active", 0)
        self.scriptsText = f"{total} / {active}"

        time = json_data.get("time", 0.0)
        self.timeText = f"{time:.2f} ms"

        mem = json_data.get("memory", 0)
        if mem < 1024 * 1024:
            self.memoryText = f"{mem // 1024} kB"
        else:
            self.memoryText = f"{mem / (1024.0 * 1024.0):.1f} MB"

        self.complexityText = str(json_data.get("complexity", 0))

        self.prevScriptsText = self.scriptsText
        self.prevTimeText = self.timeText
        self.prevMemoryText = self.memoryText
        self.prevComplexityText = self.complexityText

        self.prevIndex = -1
        self.targetIndex = -1
        self.isNew = False
        self.isRemoved = False
        self.scriptsChanged = False
        self.timeChanged = False
        self.memoryChanged = False
        self.complexityChanged = False

class RenderableZone:
    def __init__(self, json_data):
        self.json = json_data
        self.uuid = json_data.get("uuid", "")
        self.nameToDisplay = json_data.get("name", "Unknown Zone")

        self.isDynamic = json_data.get("isDynamic", False)

        self.rezStatus = json_data.get("rezStatus", "Not deployed")
        self.rezStatusText = self.rezStatus

        self.liEstText = json_data.get("liEstText", "-")

        self.prevRezStatusText = self.rezStatusText
        self.prevLiEstText = self.liEstText

        self.prevIndex = -1
        self.targetIndex = -1

        self.isNew = False
        self.isRemoved = False

        self.rezStatusChanged = False
        self.liEstChanged = False

def render_zone(data, prev_data, regionName, history, frames_count):
    if payload.type == 'zone':
        images = render_zone(data, prev_data, regionName, payload.primsHistory)
    else:
        images = render_sim(data, prev_data, regionName)

    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', regionName)
    filename = f"{safe_name}.gif"
    filepath = os.path.join("static", filename)

    if images:
        if len(images) > 1:
            images[0].save(filepath, save_all=True, append_images=images[1:], duration=125, loop=1)
        else:
            images[0].save(filepath)

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    scheme = forwarded_proto if forwarded_proto else ("https" if request.url.scheme == "https" else "http")
    host = forwarded_host if forwarded_host else request.headers.get("host", "localhost:8000")
    base_url = f"{scheme}://{host}"

    return JSONResponse(content={"url": f"{base_url}/static/{filename}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
