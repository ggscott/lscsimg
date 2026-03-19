import re

with open('app.py', 'r') as f:
    content = f.read()

# We need to replace the `render_sim` function to pre-render the static parts.

render_sim_code = """
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
"""

# Find the start and end of `render_sim`
start_idx = content.find("def render_sim(data, prev_data, regionName):")
end_idx = content.find("def render_zone(", start_idx)

# Replace the content
new_content = content[:start_idx] + render_sim_code + "\n" + content[end_idx:]

with open('app.py', 'w') as f:
    f.write(new_content)
