from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
# from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import io
from fastapi.responses import Response
import uuid
from PIL import Image, ImageDraw, ImageFont
import math
from urllib.parse import urlparse
import re
import urllib.request

app = FastAPI()

# Ensure static directory exists
# Removed static directory creation
# Removed static mount

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


def render_sim(data, prev_data, regionName):
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

    anyChanges = any(ru.isNew or ru.isRemoved or ru.scriptsChanged or ru.timeChanged or ru.memoryChanged or ru.complexityChanged or ru.prevIndex != ru.targetIndex for ru in renderList)

    frames = 32 if anyChanges else 1

    images = []

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

    for f in range(frames):
        img = base_img.copy()
        draw = ImageDraw.Draw(img)

        if data or prev_data:
            cols = [50, 450, 650, 770, 890]
            if renderList:
                globalProgress = f / (frames - 1) if frames > 1 else 1.0
                slideProgress = min(1.0, f / 16.0) if frames > 1 else 1.0
                slideProgress = 1.0 - pow(1.0 - slideProgress, 3)

                pulseProgress = 0.0
                if frames > 1 and f >= 16:
                    pulsePhase = (f - 16) / 15.0
                    pulseProgress = abs(math.sin(pulsePhase * 3.0 * math.pi))

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
                            box_alpha = int(60 * pulseProgress)
                            box_fill = (ACCENT_GREEN[0], ACCENT_GREEN[1], ACCENT_GREEN[2], box_alpha)
                            box_top = currentY - FONT_ROW.getmetrics()[0] - 13
                            box_bottom = currentY + rowHeight - FONT_ROW.getmetrics()[0] - 17
                            row_draw.rectangle([margin - 10, box_top, WIDTH - margin + 10, box_bottom], fill=box_fill)
                            outline_alpha = int(180 * pulseProgress)
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

        images.append(img.convert('RGB'))
    return images


def render_zone(data, prev_data, regionName, history):
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

    anyChanges = any(rz.isNew or rz.isRemoved or rz.occupancyChanged or rz.dynamicChanged or rz.rezStatusChanged or rz.liEstChanged or rz.prevIndex != rz.targetIndex for rz in renderList)

    frames = 32 if anyChanges else 1

    images = []

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

            # Render prim chart
            if i == 0 and history and len(history) > 1:
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
                    base_img.alpha_composite(poly_img)

                    # Draw outline
                    base_draw.line(points, fill=ACCENT_CYAN, width=2)

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

    for f in range(frames):
        img = base_img.copy()
        draw = ImageDraw.Draw(img)

        if data or prev_data:
            cols = [50, 420, 560, 680, 800]
            if renderList:
                globalProgress = f / (frames - 1) if frames > 1 else 1.0
                slideProgress = min(1.0, f / 16.0) if frames > 1 else 1.0
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
                        elif status in ["not deployed", "derezzing"]:
                            statusColor = ACCENT_ORANGE
                    else:
                        statusColor = BORDER_COLOR

                    draw_crossfade_text(row_draw, cols[4], textY, rZone.prevRezStatusText, rZone.rezStatusText, statusColor, globalProgress, FONT_ROW)

                    row_draw.line([(margin, currentY + rowHeight - FONT_ROW.getmetrics()[0] -15), (WIDTH - margin, currentY + rowHeight - FONT_ROW.getmetrics()[0] -15)], fill=(40, 50, 60), width=1)

                    if alpha < 255:
                        row_img.putalpha(row_img.split()[3].point(lambda p: p * (alpha / 255.0)))

                    img.alpha_composite(row_img)

        images.append(img.convert('RGB'))
    return images

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

    if render_type == "zone":
        images = render_zone(data, prev_data, regionName, primsHistory)
    else:
        images = render_sim(data, prev_data, regionName)

    if not images:
        return JSONResponse(status_code=500, content={"detail": "Failed to generate image."})

    img_io = io.BytesIO()
    if len(images) > 1:
        images[0].save(img_io, format='GIF', save_all=True, append_images=images[1:], duration=125, loop=0)
    else:
        images[0].save(img_io, format='GIF')

    img_io.seek(0)

    return Response(content=img_io.getvalue(), media_type="image/gif")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
