import re

with open('app.py', 'r') as f:
    content = f.read()

# We need to replace the `render_zone` function to pre-render the static parts.

render_zone_code = """
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
"""

# Find the start and end of `render_zone`
start_idx = content.find("def render_zone(data, prev_data, regionName, history):")
end_idx = content.find("@app.get(\"/health\")", start_idx)

# Replace the content
new_content = content[:start_idx] + render_zone_code + "\n" + content[end_idx:]

with open('app.py', 'w') as f:
    f.write(new_content)
