from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import asyncio
import io
import json
import time
import uuid
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("uvicorn.error")
import math
import re
import urllib.request
import redis.asyncio as redis
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager

## Global process pool executor
executor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global executor
    executor = ProcessPoolExecutor()
    yield
    executor.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)

# Redis Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL)

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
    for path in font_paths:
        if ("Bold" in path and bold) or ("Bold" not in path and not bold):
            try:
                return ImageFont.truetype(path, size)
            except IOError:
                pass

    font_url = "https://github.com/googlefonts/RobotoMono/raw/main/fonts/ttf/RobotoMono-Bold.ttf" if bold else "https://github.com/googlefonts/RobotoMono/raw/main/fonts/ttf/RobotoMono-Regular.ttf"
    font_filename = "RobotoMono-Bold.ttf" if bold else "RobotoMono-Regular.ttf"

    if not os.path.exists(font_filename):
        try:
            urllib.request.urlretrieve(font_url, font_filename)
        except Exception:
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
    type: str = "sim" # "sim" or "zone"
    primsHistory: Optional[List[int]] = None

class RenderableUser:
    def __init__(self, json_data, is_prev=False):
        self.json = json_data
        self.uuid = json_data.get("uuid", "")
        self.nameToDisplay = json_data.get("name", "Unknown")
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

        self.occupancyText = json_data.get("occupancyText", "0")
        try:
            self.occupancy = int(self.occupancyText)
        except:
            self.occupancy = 0

        self.dynamicText = json_data.get("dynamicText", "Static")
        self.rezStatusText = json_data.get("rezStatusText", "-")
        self.liEstText = json_data.get("liEstText", "-")

        self.prevOccupancyText = self.occupancyText
        self.prevDynamicText = self.dynamicText
        self.prevRezStatusText = self.rezStatusText
        self.prevLiEstText = self.liEstText

        # Legacy for potential compatibility
        self.rezStatus = self.rezStatusText

        if self.dynamicText in ["YES", "Ready", "Missing", "No Comms"]:
            self.isDynamic = True

        self.prevIndex = -1
        self.targetIndex = -1
        self.isNew = False
        self.isRemoved = False

        self.occupancyChanged = False
        self.dynamicChanged = False
        self.rezStatusChanged = False
        self.liEstChanged = False

def draw_crossfade_text(draw, x, y, oldText, newText, baseColor, progress, font):
    if not oldText or not newText or oldText == newText:
        draw.text((x, y), newText or "", font=font, fill=baseColor)
        return

    currentX = x
    max_len = max(len(oldText), len(newText))

    for i in range(max_len):
        oldC = oldText[i] if i < len(oldText) else ' '
        newC = newText[i] if i < len(newText) else ' '

        char_to_measure = newC if newC != ' ' else oldC
        try:
            charWidth = draw.textlength(char_to_measure, font=font)
        except AttributeError:
            charWidth = font.getsize(char_to_measure)[0]

        if oldC == newC:
            draw.text((currentX, y), newC, font=font, fill=baseColor)
        else:
            if oldC != ' ':
                old_fill = (baseColor[0], baseColor[1], baseColor[2], int(255 * (1.0 - progress)))
                draw.text((currentX, y), oldC, font=font, fill=old_fill)
            if newC != ' ':
                r = int(ACCENT_CYAN[0] + (baseColor[0] - ACCENT_CYAN[0]) * progress)
                g = int(ACCENT_CYAN[1] + (baseColor[1] - ACCENT_CYAN[1]) * progress)
                b = int(ACCENT_CYAN[2] + (baseColor[2] - ACCENT_CYAN[2]) * progress)
                new_fill = (r, g, b, int(255 * progress))
                draw.text((currentX, y), newC, font=font, fill=new_fill)

        currentX += charWidth


def get_sim_frames_count(data, prev_data):
    prevList = []
    if prev_data and "users" in prev_data:
        for u in prev_data["users"]:
            prevList.append(RenderableUser(u, True))
        prevList.sort(key=lambda u: (u.category, u.nameToDisplay.lower()))
        for i, u in enumerate(prevList):
            u.prevIndex = i

    currentList = []
    if data and "users" in data:
        for u in data["users"]:
            currentList.append(RenderableUser(u, False))
        currentList.sort(key=lambda u: (u.category, u.nameToDisplay.lower()))
        for i, u in enumerate(currentList):
            u.targetIndex = i

    for cu in currentList:
        pu = next((p for p in prevList if (p.uuid == cu.uuid and p.uuid) or (not p.uuid and p.nameToDisplay == cu.nameToDisplay)), None)
        if pu:
            if (cu.scriptsText != pu.scriptsText or
                cu.timeText != pu.timeText or
                cu.memoryText != pu.memoryText or
                cu.complexityText != pu.complexityText or
                pu.prevIndex != cu.targetIndex):
                return 8
        else:
            return 8

    for pu in prevList:
        found = any((cu.uuid == pu.uuid and pu.uuid) or (not pu.uuid and cu.nameToDisplay == pu.nameToDisplay) for cu in currentList)
        if not found:
            return 8

    return 1

def render_sim_frame(f, frames, data, prev_data, regionName):
    prevList = []
    if prev_data and "users" in prev_data:
        for u in prev_data["users"]:
            prevList.append(RenderableUser(u, True))
        prevList.sort(key=lambda u: (u.category, u.nameToDisplay.lower()))
        for i, u in enumerate(prevList):
            u.prevIndex = i

    currentList = []
    if data and "users" in data:
        for u in data["users"]:
            currentList.append(RenderableUser(u, False))
        currentList.sort(key=lambda u: (u.category, u.nameToDisplay.lower()))
        for i, u in enumerate(currentList):
            u.targetIndex = i

    renderList = []
    for cu in currentList:
        pu = next((p for p in prevList if (p.uuid == cu.uuid and p.uuid) or (not p.uuid and p.nameToDisplay == cu.nameToDisplay)), None)
        if pu:
            cu.prevIndex = pu.prevIndex
            cu.prevScriptsText = pu.scriptsText
            cu.prevTimeText = pu.timeText
            cu.prevMemoryText = pu.memoryText
            cu.prevComplexityText = pu.complexityText

            cu.scriptsChanged = cu.scriptsText != pu.scriptsText
            cu.timeChanged = cu.timeText != pu.timeText
            cu.memoryChanged = cu.memoryText != pu.memoryText
            cu.complexityChanged = cu.complexityText != pu.complexityText
        else:
            cu.isNew = True
            cu.prevIndex = cu.targetIndex
        renderList.append(cu)

    for pu in prevList:
        found = any((cu.uuid == pu.uuid and pu.uuid) or (not pu.uuid and cu.nameToDisplay == pu.nameToDisplay) for cu in currentList)
        if not found:
            pu.isRemoved = True
            pu.targetIndex = pu.prevIndex
            renderList.append(pu)

    # PRE-RENDER BASE IMAGE
    base_img = Image.new('RGBA', (WIDTH, HEIGHT), BG_COLOR)
    base_draw = ImageDraw.Draw(base_img)

    margin = 50
    headerY = 80
    statsY = 140
    tableHeaderY = 220
    rowHeight = 40
    rowStartY = 270

    if not data and not prev_data:
        msg = f"NO DATA AVAILABLE FOR {regionName.upper()}"
        try:
            tw = base_draw.textlength(msg, font=FONT_ERROR)
        except AttributeError:
            tw = FONT_ERROR.getsize(msg)[0]
        x = (WIDTH - tw) // 2
        y = HEIGHT // 2 - FONT_ERROR.getmetrics()[0]
        base_draw.text((x, y), msg, font=FONT_ERROR, fill=ACCENT_RED)
    else:
        d = data if data else prev_data

        agents = d.get("agents", 0)
        fps = d.get("fps", 0.0)
        dilation = d.get("dilation", 0.0)
        lag = d.get("lag", 0)

        base_draw.text((margin, headerY - FONT_LARGE.getmetrics()[0]), regionName.upper(), font=FONT_LARGE, fill=ACCENT_CYAN)
        base_draw.line([(margin, headerY + 15), (WIDTH - margin, headerY + 15)], fill=ACCENT_CYAN, width=2)

        labels = ["ROLEPLAYERS", "FPS", "TIME DILATION", "LAG"]
        values = [
            str(agents),
            f"{fps:.1f}",
            f"{dilation:.2f}",
            f"{lag} %"
        ]

        colWidth = (WIDTH - 2 * margin) // 4

        for i in range(4):
            x = margin + (i * colWidth)
            base_draw.text((x, statsY - FONT_LABEL.getmetrics()[0]), labels[i], font=FONT_LABEL, fill=ACCENT_YELLOW)

            v_col = TEXT_MAIN
            if i == 3 and lag > 10: v_col = ACCENT_RED
            base_draw.text((x, statsY + 40 - FONT_VAL.getmetrics()[0]), values[i], font=FONT_VAL, fill=v_col)

        base_draw.line([(margin, statsY + 55), (WIDTH - margin, statsY + 55)], fill=BORDER_COLOR, width=1)

        cols = [50, 450, 650, 770, 890]
        tableHeaders = ["USER", "SCRIPTS (T/A)", "TIME", "MEMORY", "CMPLX"]

        for i in range(len(tableHeaders)):
            base_draw.text((cols[i], tableHeaderY - FONT_TBL_HDR.getmetrics()[0] - 5), tableHeaders[i], font=FONT_TBL_HDR, fill=ACCENT_CYAN)

        base_draw.line([(margin, tableHeaderY - FONT_TBL_HDR.getmetrics()[0] +25), (WIDTH - margin, tableHeaderY - FONT_TBL_HDR.getmetrics()[0] +25)], fill=ACCENT_CYAN, width=1)

        # Borders
        base_draw.line([(0,0), (50,0)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(0,0), (0,50)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(WIDTH,0), (WIDTH-50,0)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(WIDTH,0), (WIDTH,50)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(0,HEIGHT), (50,HEIGHT)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(0,HEIGHT), (0,HEIGHT-50)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(WIDTH,HEIGHT), (WIDTH-50,HEIGHT)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(WIDTH,HEIGHT), (WIDTH,HEIGHT-50)], fill=ACCENT_CYAN, width=4)

    img = base_img.copy()
    draw = ImageDraw.Draw(img)

    if data or prev_data:
        cols = [50, 450, 650, 770, 890]
        if renderList:
            globalProgress = f / (frames - 1) if frames > 1 else 1.0
            slideProgress = min(1.0, f / 4.0) if frames > 1 else 1.0
            slideProgress = 1.0 - pow(1.0 - slideProgress, 3)

            pulseProgress = 0.0
            if frames > 1 and f >= 2:
                pulsePhase = (f - 1) / 7.0
                pulseProgress = math.sin(pulsePhase * math.pi)

            for rUser in renderList:
                prevY = rowStartY + rUser.prevIndex * rowHeight
                targetY = rowStartY + rUser.targetIndex * rowHeight
                currentY = int(prevY + (targetY - prevY) * slideProgress)

                if currentY > HEIGHT - 20 and prevY > HEIGHT - 20: continue

                alpha = 255

                row_img = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
                row_draw = ImageDraw.Draw(row_img)

                if rUser.isNew:
                    alpha = int(255 * min(1.0, max(0.0, slideProgress)))
                    if pulseProgress > 0:
                        box_alpha = int(120 * pulseProgress)
                        box_fill = (ACCENT_GREEN[0], ACCENT_GREEN[1], ACCENT_GREEN[2], box_alpha)
                        box_top = currentY - FONT_ROW.getmetrics()[0] - 13
                        box_bottom = currentY + rowHeight - FONT_ROW.getmetrics()[0] - 17
                        row_draw.rectangle([margin - 10, box_top, WIDTH - margin + 10, box_bottom], fill=box_fill)
                        outline_alpha = int(255 * pulseProgress)
                        outline_fill = (ACCENT_GREEN[0], ACCENT_GREEN[1], ACCENT_GREEN[2], outline_alpha)
                        row_draw.rectangle([margin - 10, box_top, WIDTH - margin + 10, box_bottom], outline=outline_fill)
                elif rUser.isRemoved:
                    alpha = int(255 * min(1.0, max(0.0, 1.0 - slideProgress)))

                name = rUser.nameToDisplay
                currentX = cols[0]

                textY = currentY - FONT_ROW.getmetrics()[0] - 5
                if rUser.isOOC:
                    row_draw.text((currentX, textY), "OOC:", font=FONT_ROW, fill=ACCENT_ORANGE)
                    try:
                        tw = row_draw.textlength("OOC:", font=FONT_ROW)
                    except AttributeError:
                        tw = FONT_ROW.getsize("OOC:")[0]
                    currentX += int(tw)
                    if len(name) > 21: name = name[:21] + "..."
                    row_draw.text((currentX, textY), name, font=FONT_ROW, fill=TEXT_MAIN)
                elif rUser.isChar:
                    row_draw.text((currentX, textY), "<<", font=FONT_ROW, fill=ACCENT_GREEN)
                    try:
                        tw = row_draw.textlength("<<", font=FONT_ROW)
                    except AttributeError:
                        tw = FONT_ROW.getsize("<<")[0]
                    currentX += int(tw)
                    if len(name) > 21: name = name[:21] + "..."
                    row_draw.text((currentX, textY), name, font=FONT_ROW, fill=TEXT_MAIN)
                    try:
                        tw2 = row_draw.textlength(name, font=FONT_ROW)
                    except AttributeError:
                        tw2 = FONT_ROW.getsize(name)[0]
                    currentX += int(tw2)
                    row_draw.text((currentX, textY), ">>", font=FONT_ROW, fill=ACCENT_GREEN)
                else:
                    if len(name) > 25: name = name[:25] + "..."
                    row_draw.text((currentX, textY), name, font=FONT_ROW, fill=TEXT_MAIN)

                draw_crossfade_text(row_draw, cols[1], textY, rUser.prevScriptsText, rUser.scriptsText, TEXT_MAIN, globalProgress, FONT_ROW)

                time_color = TEXT_MAIN
                try:
                    t = float(rUser.json.get("time", 0))
                    if t > 5: time_color = ACCENT_RED
                    elif t > 1: time_color = ACCENT_YELLOW
                except: pass

                draw_crossfade_text(row_draw, cols[2], textY, rUser.prevTimeText, rUser.timeText, time_color, globalProgress, FONT_ROW)
                draw_crossfade_text(row_draw, cols[3], textY, rUser.prevMemoryText, rUser.memoryText, TEXT_MAIN, globalProgress, FONT_ROW)
                draw_crossfade_text(row_draw, cols[4], textY, rUser.prevComplexityText, rUser.complexityText, TEXT_MAIN, globalProgress, FONT_ROW)

                row_draw.line([(margin, currentY + rowHeight - FONT_ROW.getmetrics()[0] - 15), (WIDTH - margin, currentY + rowHeight - FONT_ROW.getmetrics()[0] - 15)], fill=(40, 50, 60), width=1)

                if alpha < 255:
                    row_img.putalpha(row_img.split()[3].point(lambda p: p * (alpha / 255.0)))

                img.alpha_composite(row_img)

    img_byte_arr = io.BytesIO()
    img.convert('RGB').save(img_byte_arr, format='JPEG', quality=85)
    return f, img_byte_arr.getvalue()


def get_zone_frames_count(data, prev_data):
    prevList = []
    if prev_data and "zones" in prev_data:
        for z in prev_data["zones"]:
            prevList.append(RenderableZone(z))
        prevList.sort(key=lambda z: z.nameToDisplay.lower())
        for i, z in enumerate(prevList):
            z.prevIndex = i

    currentList = []
    if data and "zones" in data:
        for z in data["zones"]:
            currentList.append(RenderableZone(z))
        currentList.sort(key=lambda z: z.nameToDisplay.lower())
        for i, z in enumerate(currentList):
            z.targetIndex = i

    for cz in currentList:
        pz = next((p for p in prevList if p.nameToDisplay == cz.nameToDisplay), None)
        if pz:
            if (cz.occupancyText != pz.occupancyText or
                cz.dynamicText != pz.dynamicText or
                cz.rezStatusText != pz.rezStatusText or
                cz.liEstText != pz.liEstText or
                pz.prevIndex != cz.targetIndex):
                return 8
        else:
            return 8

    for pz in prevList:
        found = any(cz.nameToDisplay == pz.nameToDisplay for cz in currentList)
        if not found:
            return 8

    return 1

def render_zone_frame(f, frames, data, prev_data, regionName, history):
    prevList = []
    if prev_data and "zones" in prev_data:
        for z in prev_data["zones"]:
            prevList.append(RenderableZone(z))
        prevList.sort(key=lambda z: z.nameToDisplay.lower())
        for i, z in enumerate(prevList):
            z.prevIndex = i

    currentList = []
    if data and "zones" in data:
        for z in data["zones"]:
            currentList.append(RenderableZone(z))
        currentList.sort(key=lambda z: z.nameToDisplay.lower())
        for i, z in enumerate(currentList):
            z.targetIndex = i

    renderList = []
    for cz in currentList:
        pz = next((p for p in prevList if p.nameToDisplay == cz.nameToDisplay), None)
        if pz:
            cz.prevIndex = pz.prevIndex
            cz.prevOccupancyText = pz.occupancyText
            cz.prevDynamicText = pz.dynamicText
            cz.prevRezStatusText = pz.rezStatusText
            cz.prevLiEstText = pz.liEstText
            cz.occupancyChanged = cz.occupancyText != pz.occupancyText
            cz.dynamicChanged = cz.dynamicText != pz.dynamicText
            cz.rezStatusChanged = cz.rezStatusText != pz.rezStatusText
            cz.liEstChanged = cz.liEstText != pz.liEstText
        else:
            cz.isNew = True
            cz.prevIndex = cz.targetIndex
        renderList.append(cz)

    for pz in prevList:
        found = any(cz.nameToDisplay == pz.nameToDisplay for cz in currentList)
        if not found:
            pz.isRemoved = True
            pz.targetIndex = pz.prevIndex
            renderList.append(pz)

    # PRE-RENDER BASE IMAGE
    base_img = Image.new('RGBA', (WIDTH, HEIGHT), BG_COLOR)
    base_draw = ImageDraw.Draw(base_img)

    margin = 50
    headerY = 80
    statsY = 140
    tableHeaderY = 220
    rowHeight = 40
    rowStartY = 270

    if not data and not prev_data:
        msg = f"NO DATA AVAILABLE FOR {regionName.upper()}"
        try:
            tw = base_draw.textlength(msg, font=FONT_ERROR)
        except AttributeError:
            tw = FONT_ERROR.getsize(msg)[0]
        x = (WIDTH - tw) // 2
        y = HEIGHT // 2 - FONT_ERROR.getmetrics()[0]
        base_draw.text((x, y), msg, font=FONT_ERROR, fill=ACCENT_RED)
    else:
        d = data if data else prev_data

        prims = d.get("remaining_prims", 0)
        status = d.get("status", "Unknown")
        fps = d.get("fps", 0.0)
        lag = d.get("lag", 0)

        base_draw.text((margin, headerY - FONT_LARGE.getmetrics()[0]), regionName.upper(), font=FONT_LARGE, fill=ACCENT_CYAN)
        base_draw.line([(margin, headerY + 15), (WIDTH - margin, headerY + 15)], fill=ACCENT_CYAN, width=2)

        labels = ["REMAINING PRIMS"]
        values = [
            str(prims)
        ]

        colWidth = (WIDTH - 2 * margin)

        for i in range(1):
            x = margin + (i * colWidth)
            base_draw.text((x, statsY - FONT_LABEL.getmetrics()[0]), labels[i], font=FONT_LABEL, fill=ACCENT_YELLOW)

            v_col = TEXT_MAIN
            if i == 0 and prims < 100: v_col = ACCENT_RED
            base_draw.text((x, statsY + 40 - FONT_VAL.getmetrics()[0]), values[i], font=FONT_VAL, fill=v_col)

        base_draw.line([(margin, statsY + 55), (WIDTH - margin, statsY + 55)], fill=BORDER_COLOR, width=1)

        cols = [50, 420, 560, 680, 800]
        tableHeaders = ["ZONE", "OCCUPANCY", "DYNAMIC", "LI (EST)", "STATE"]

        for i in range(len(tableHeaders)):
            base_draw.text((cols[i], tableHeaderY - FONT_TBL_HDR.getmetrics()[0] - 5), tableHeaders[i], font=FONT_TBL_HDR, fill=ACCENT_CYAN)

        base_draw.line([(margin, tableHeaderY - FONT_TBL_HDR.getmetrics()[0] +25), (WIDTH - margin, tableHeaderY - FONT_TBL_HDR.getmetrics()[0] +25)], fill=ACCENT_CYAN, width=1)

        # Borders
        base_draw.line([(0,0), (50,0)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(0,0), (0,50)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(WIDTH,0), (WIDTH-50,0)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(WIDTH,0), (WIDTH,50)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(0,HEIGHT), (50,HEIGHT)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(0,HEIGHT), (0,HEIGHT-50)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(WIDTH,HEIGHT), (WIDTH-50,HEIGHT)], fill=ACCENT_CYAN, width=4)
        base_draw.line([(WIDTH,HEIGHT), (WIDTH,HEIGHT-50)], fill=ACCENT_CYAN, width=4)

    img = base_img.copy()
    draw = ImageDraw.Draw(img)

    if data or prev_data:
        # Render prim chart and animated axis
        if history and len(history) > 1:
            colWidth = (WIDTH - 2 * margin)
            x = margin + (0 * colWidth)
            chartX = x + 250
            chartY = statsY - 10
            chartW = 200
            chartH = 50

            min_val = min(history)
            max_val = max(history)
            if max_val == min_val:
                min_val -= 10
                max_val += 10

            points = []
            size = len(history)
            for j, val in enumerate(history):
                px = chartX + (j / float(max(1, size - 1))) * chartW
                py = chartY + chartH - ((val - min_val) / float(max_val - min_val)) * chartH
                points.append((px, py))

            if len(points) > 1:
                # Draw filled polygon (using cyan with 50/255 alpha ~50 out of 255)
                poly_img = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
                poly_draw = ImageDraw.Draw(poly_img)
                poly_points = [(chartX, chartY + chartH)] + points + [(points[-1][0], chartY + chartH)]
                poly_draw.polygon(poly_points, fill=(ACCENT_CYAN[0], ACCENT_CYAN[1], ACCENT_CYAN[2], 50))
                img.alpha_composite(poly_img)

                # Draw outline
                draw.line(points, fill=ACCENT_CYAN, width=2)

            # Animated Scrolling Time Axis Logic
            baseTime = time.time()
            frameProgress = f / frames if frames > 1 else 0
            timeOffset = (baseTime + frameProgress) * 20.0  # multiplier controls scroll speed

            tickSpacing = 15
            tickHeight = 5
            offset_mod = timeOffset % tickSpacing

            # Draw ticks
            for tick in range(0, chartW + tickSpacing, tickSpacing):
                tickX = chartX + tick - offset_mod
                if chartX <= tickX <= chartX + chartW:
                    draw.line([(tickX, chartY + chartH - tickHeight), (tickX, chartY + chartH)], fill=BORDER_COLOR, width=1)

            # Draw subtle scanner effect if animating
            if frames > 1:
                scanX = chartX + ((timeOffset * 2) % chartW)
                if chartX <= scanX <= chartX + chartW:
                    scan_img = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
                    scan_draw = ImageDraw.Draw(scan_img)
                    scan_draw.line([(scanX, chartY), (scanX, chartY + chartH)], fill=(ACCENT_CYAN[0], ACCENT_CYAN[1], ACCENT_CYAN[2], 100), width=1)
                    img.paste(scan_img, (0, 0), scan_img)

        cols = [50, 420, 560, 680, 800]
        if renderList:
            globalProgress = f / (frames - 1) if frames > 1 else 1.0
            slideProgress = min(1.0, f / 4.0) if frames > 1 else 1.0
            slideProgress = 1.0 - pow(1.0 - slideProgress, 3)

            for rZone in renderList:
                prevY = rowStartY + rZone.prevIndex * rowHeight
                targetY = rowStartY + rZone.targetIndex * rowHeight
                currentY = int(prevY + (targetY - prevY) * slideProgress)

                if currentY > HEIGHT - 20 and prevY > HEIGHT - 20: continue

                alpha = 255
                if rZone.isNew:
                    alpha = int(255 * min(1.0, max(0.0, slideProgress)))
                elif rZone.isRemoved:
                    alpha = int(255 * min(1.0, max(0.0, 1.0 - slideProgress)))

                name = rZone.nameToDisplay
                currentX = cols[0]

                row_img = Image.new('RGBA', (WIDTH, HEIGHT), (0,0,0,0))
                row_draw = ImageDraw.Draw(row_img)

                textY = currentY - FONT_ROW.getmetrics()[0] - 5
                if len(name) > 25: name = name[:25] + "..."
                row_draw.text((currentX, textY), name, font=FONT_ROW, fill=TEXT_MAIN)

                occColor = TEXT_MAIN
                if rZone.occupancy > 0:
                    occColor = ACCENT_GREEN
                draw_crossfade_text(row_draw, cols[1], textY, rZone.prevOccupancyText, rZone.occupancyText, occColor, globalProgress, FONT_ROW)

                dynColor = TEXT_MAIN
                if rZone.dynamicText == "Missing":
                    dynColor = ACCENT_RED
                elif rZone.dynamicText == "No Comms":
                    dynColor = ACCENT_YELLOW
                draw_crossfade_text(row_draw, cols[2], textY, rZone.prevDynamicText, rZone.dynamicText, dynColor, globalProgress, FONT_ROW)

                liColor = TEXT_MAIN
                if rZone.liEstText in ["~", "-"]:
                    liColor = BORDER_COLOR
                draw_crossfade_text(row_draw, cols[3], textY, rZone.prevLiEstText, rZone.liEstText, liColor, globalProgress, FONT_ROW)

                statusColor = TEXT_MAIN
                if rZone.isDynamic:
                    status = rZone.rezStatusText.lower()
                    if status in ["deployed", "rezzing"]:
                        statusColor = ACCENT_GREEN
                    elif status in ["idle", "derezzing"]:
                        statusColor = ACCENT_ORANGE
                else:
                    statusColor = BORDER_COLOR

                draw_crossfade_text(row_draw, cols[4], textY, rZone.prevRezStatusText, rZone.rezStatusText, statusColor, globalProgress, FONT_ROW)

                row_draw.line([(margin, currentY + rowHeight - FONT_ROW.getmetrics()[0] -15), (WIDTH - margin, currentY + rowHeight - FONT_ROW.getmetrics()[0] -15)], fill=(40, 50, 60), width=1)

                if alpha < 255:
                    row_img.putalpha(row_img.split()[3].point(lambda p: p * (alpha / 255.0)))

                img.alpha_composite(row_img)

    img_byte_arr = io.BytesIO()
    img.convert('RGB').save(img_byte_arr, format='JPEG', quality=85)
    return f, img_byte_arr.getvalue()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/")
@app.post("/render")
async def render(request: Request, payload: RenderRequest):
    data = payload.data or {}
    prev_data = payload.previousData or {}
    regionName = payload.regionName
    render_type = payload.type
    primsHistory = payload.primsHistory

    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', regionName)
    channel_name = f"region:{safe_name}:{render_type}"
    latest_key = f"latest:{safe_name}:{render_type}"

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    scheme = forwarded_proto if forwarded_proto else ("https" if request.url.scheme == "https" else "http")
    host = forwarded_host if forwarded_host else request.headers.get("host", "localhost:8000")
    base_url = f"{scheme}://{host}"

    lock_key = f"lock:{safe_name}:{render_type}"

    async def render_and_publish():
        # Generate a unique lock value so we only delete our own lock
        lock_val = uuid.uuid4().hex

        # Acquire lock to prevent race conditions during animation
        # If we can't get the lock, it means another update is actively animating.
        # Since updates are frequent (e.g., every 1s from multiple users), we simply
        # skip this render to avoid queuing up stale updates and interleaving frames.
        # Increased timeout to 5s to ensure the 1s+ animation process never exceeds it.
        lock_acquired = await redis_client.set(lock_key, lock_val, nx=True, ex=10)
        if not lock_acquired:
            return # Skip this render immediately

        try:
            start_total_time = time.time()

            # Generate the frames only after acquiring the lock to prevent blocking the
            # event loop with expensive PIL operations for updates that will be discarded.
            loop = asyncio.get_running_loop()

            start_render_time = time.time()

            if render_type == "zone":
                frames_count = get_zone_frames_count(data, prev_data)
                tasks = [
                    loop.run_in_executor(
                        executor,
                        render_zone_frame,
                        f, frames_count, data, prev_data, regionName, primsHistory
                    )
                    for f in range(frames_count)
                ]
            else:
                frames_count = get_sim_frames_count(data, prev_data)
                tasks = [
                    loop.run_in_executor(
                        executor,
                        render_sim_frame,
                        f, frames_count, data, prev_data, regionName
                    )
                    for f in range(frames_count)
                ]

            results = await asyncio.gather(*tasks)
            render_duration = time.time() - start_render_time

            # Sort the results by frame index to ensure chronological order
            results.sort(key=lambda x: x[0])

            if results:
                for f_index, img_bytes in results:
                    # Publish frame to Redis channel
                    await redis_client.publish(channel_name, img_bytes)

                    # Wait briefly between frames to match animation timing (approx 8fps like 125ms duration)
                    if frames_count > 1:
                        await asyncio.sleep(0.125)

                # Store the very last frame as the "latest" state for new connections
                latest_img_bytes = results[-1][1]
                await redis_client.set(latest_key, latest_img_bytes)

                # Send a final duplicate of the last frame to force the CEF browser to
                # immediately render the actual last frame of the animation
                if frames_count > 1:
                    await redis_client.publish(channel_name, latest_img_bytes)

            total_duration = time.time() - start_total_time
            update_type = "single frame update" if frames_count == 1 else "animation update"
            logger.info(
                f"[Performance] Render type: {render_type} | "
                f"CPU render time: {render_duration:.3f} seconds | "
                f"Total background task time: {total_duration:.3f} seconds for {update_type}."
            )

        finally:
            # Safe delete: Only delete the lock if it still belongs to this task
            current_lock_val = await redis_client.get(lock_key)
            if current_lock_val and current_lock_val.decode('utf-8') == lock_val:
                await redis_client.delete(lock_key)

    # Start the rendering/publishing in the background
    asyncio.create_task(render_and_publish())

    # Return the permanent stream URL for this region
    response_json = {"url": f"{base_url}/stream/{safe_name}/{render_type}"}
    return JSONResponse(content=response_json)

async def stream_generator(safe_name: str, render_type: str):
    channel_name = f"region:{safe_name}:{render_type}"
    latest_key = f"latest:{safe_name}:{render_type}"

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel_name)

    try:
        # First, try to send the latest cached frame immediately so the client sees something right away
        latest_frame = await redis_client.get(latest_key)
        if latest_frame:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(latest_frame)).encode() + b"\r\n\r\n" +
                latest_frame + b"\r\n"
            )
        else:
            # If no latest frame, generate a placeholder
            placeholder = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
            draw = ImageDraw.Draw(placeholder)
            msg = f"WAITING FOR DATA: {safe_name.upper()} ({render_type.upper()})"
            tw = draw.textlength(msg, font=FONT_ERROR) if hasattr(draw, 'textlength') else FONT_ERROR.getsize(msg)[0]
            draw.text(((WIDTH - tw) // 2, HEIGHT // 2), msg, font=FONT_ERROR, fill=ACCENT_CYAN)
            img_byte_arr = io.BytesIO()
            placeholder.save(img_byte_arr, format='JPEG', quality=85)
            placeholder_bytes = img_byte_arr.getvalue()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(placeholder_bytes)).encode() + b"\r\n\r\n" +
                placeholder_bytes + b"\r\n"
            )

        # Then listen for new frames published to the channel with a timeout
        # If no new frames arrive within 5 seconds, send a keep-alive frame
        # (the latest cached frame) to prevent the MoaP browser or proxy from timing out.
        while True:
            # get_message with timeout will block up to timeout seconds
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)

            if message and message['type'] == 'message':
                frame_data = message['data']
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame_data)).encode() + b"\r\n\r\n" +
                    frame_data + b"\r\n"
                )
            elif message is None:
                # Timeout reached, send a keep-alive heartbeat
                heartbeat_frame = await redis_client.get(latest_key)
                if heartbeat_frame:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(heartbeat_frame)).encode() + b"\r\n\r\n" +
                        heartbeat_frame + b"\r\n"
                    )
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()

@app.head("/stream/{region_name}/{render_type}")
async def head_stream(region_name: str, render_type: str):
    return Response(media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/stream/{region_name}/{render_type}")
async def get_stream(region_name: str, render_type: str):
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', region_name)
    safe_type = re.sub(r'[^a-zA-Z0-9_\-]', '_', render_type)
    return StreamingResponse(
        stream_generator(safe_name, safe_type),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
