"""Generate architecture diagram - minimal, reference-style (GIBMS/SLG)."""
from PIL import Image, ImageDraw, ImageFont
import math

W, H = 1000, 420
img = Image.new('RGB', (W, H), color=(255, 255, 255))
draw = ImageDraw.Draw(img)

# Colors (reference style: light blue, orange, grey, green)
C_P = (230, 240, 250)      # problems - light blue
C_S = (255, 245, 230)      # solutions - light orange
C_R = (235, 250, 235)      # results - light green
C_BORDER = (120, 120, 120)
C_DASH = (180, 180, 180)
C_TEXT = (60, 60, 60)

def rounded_rect(d, xy, fill, outline=C_BORDER, r=8):
    x1, y1, x2, y2 = xy
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=1)

def dashed_rect(d, xy, color=C_DASH):
    x1, y1, x2, y2 = xy
    dash = 6
    for i in range(x1, x2, dash*2):
        d.line([(i, y1), (min(i+dash, x2), y1)], fill=color)
    for i in range(x1, x2, dash*2):
        d.line([(i, y2), (min(i+dash, x2), y2)], fill=color)
    for i in range(y1, y2, dash*2):
        d.line([(x1, i), (x1, min(i+dash, y2))], fill=color)
    for i in range(y1, y2, dash*2):
        d.line([(x2, i), (x2, min(i+dash, y2))], fill=color)

def arrow(dr, x1, y1, x2, y2, color=C_BORDER):
    dr.line([(x1, y1), (x2, y2)], fill=color, width=2)
    ang = math.atan2(y2 - y1, x2 - x1)
    size = 8
    dr.polygon([
        (x2, y2),
        (x2 - size * math.cos(ang - 0.35), y2 - size * math.sin(ang - 0.35)),
        (x2 - size * math.cos(ang + 0.35), y2 - size * math.sin(ang + 0.35))
    ], fill=color)

try:
    f_sm = ImageFont.truetype("arial.ttf", 9)
    f_md = ImageFont.truetype("arial.ttf", 11)
    f_hd = ImageFont.truetype("arial.ttf", 12)
except Exception:
    f_sm = f_md = f_hd = ImageFont.load_default()

# Stage 1: Problems (compact)
stage1 = (25, 50, 180, 360)
dashed_rect(draw, stage1)
draw.text((55, 25), "(a) Problems", fill=C_TEXT, font=f_hd)

rounded_rect(draw, (45, 55, 160, 115), C_P)
draw.text((55, 68), "P1", fill=C_TEXT, font=f_md)
draw.text((55, 85), "Calibration", fill=C_TEXT, font=f_sm)

rounded_rect(draw, (45, 130, 160, 190), C_P)
draw.text((55, 143), "P2", fill=C_TEXT, font=f_md)
draw.text((55, 160), "Selection", fill=C_TEXT, font=f_sm)

rounded_rect(draw, (45, 205, 160, 265), C_P)
draw.text((55, 218), "P3", fill=C_TEXT, font=f_md)
draw.text((55, 235), "Evaluation", fill=C_TEXT, font=f_sm)

# Stage 2: Modules (compact, icon-like)
stage2 = (200, 50, 520, 360)
dashed_rect(draw, stage2)
draw.text((320, 25), "(b) Our Solutions", fill=C_TEXT, font=f_hd)

rounded_rect(draw, (215, 55, 505, 115), C_S)
draw.text((230, 68), "RQ1", fill=C_TEXT, font=f_md)
draw.text((230, 85), "Window | Target", fill=C_TEXT, font=f_sm)

rounded_rect(draw, (215, 130, 505, 190), C_S)
draw.text((230, 143), "RQ2", fill=C_TEXT, font=f_md)
draw.text((230, 160), "P1/P2/P3 | IRT+UCB", fill=C_TEXT, font=f_sm)

rounded_rect(draw, (215, 205, 505, 265), C_S)
draw.text((230, 218), "RQ3", fill=C_TEXT, font=f_md)
draw.text((230, 235), "Rule+LLM | Fallback", fill=C_TEXT, font=f_sm)

# Stage 3: Results (minimal, symbolic bars)
stage3 = (540, 50, 970, 360)
dashed_rect(draw, stage3)
draw.text((700, 25), "(c) Results", fill=C_TEXT, font=f_hd)

rounded_rect(draw, (555, 55, 955, 115), C_R)
# Mini bar chart
for i, (x, w) in enumerate([(570, 35), (620, 55), (690, 25)]):
    draw.rectangle([x, 95, x + w, 105], fill=(100, 150, 100))
draw.text((570, 68), "Calibration", fill=C_TEXT, font=f_sm)
draw.text((570, 82), "Convergence", fill=C_TEXT, font=f_sm)

rounded_rect(draw, (555, 130, 955, 190), C_R)
for i, (x, w) in enumerate([(570, 45), (630, 50), (695, 40)]):
    draw.rectangle([x, 170, x + w, 180], fill=(100, 150, 100))
draw.text((570, 143), "Gap | Coverage", fill=C_TEXT, font=f_sm)
draw.text((570, 157), "Personalization", fill=C_TEXT, font=f_sm)

rounded_rect(draw, (555, 205, 955, 265), C_R)
for i, (x, w) in enumerate([(570, 50), (635, 45), (695, 55)]):
    draw.rectangle([x, 245, x + w, 255], fill=(100, 150, 100))
draw.text((570, 218), "Agreement", fill=C_TEXT, font=f_sm)
draw.text((570, 232), "Uptime", fill=C_TEXT, font=f_sm)

# Arrows
arrow(draw, 160, 85, 213, 85)
arrow(draw, 160, 160, 213, 160)
arrow(draw, 160, 235, 213, 235)
arrow(draw, 505, 85, 553, 85)
arrow(draw, 505, 160, 553, 160)
arrow(draw, 505, 235, 553, 235)

img.save('architecture.png')
print('Saved architecture.png')
