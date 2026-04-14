"""
SCTY Poster - Design & Technology Studio

Professional poster highlighting SCTY's AI-native design studio and recent recognition.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

import drawBot as db
from drawbot_grid import Grid
from drawbot_design_system import (
    POSTER_SCALE,
    get_output_path,
    draw_wrapped_text,
    setup_poster_page
)

# ==================== SETUP ====================

WIDTH, HEIGHT, MARGIN = setup_poster_page("letter", margin_ratio=1/12)

grid = Grid.from_margins(
    (-MARGIN, -MARGIN, -MARGIN, -MARGIN),
    column_subdivisions=12,
    row_subdivisions=16,
    column_gutter=12,
    row_gutter=8
)

scale = POSTER_SCALE

# Colors - Professional tech palette
DARK_BG = (0.02, 0.02, 0.05)       # Near black
ACCENT = (0.2, 0.6, 1.0)           # Bright blue
TEXT = (0.95, 0.95, 0.97)          # Off white
SUBTLE = (0.5, 0.5, 0.55)          # Gray

# ==================== BACKGROUND ====================

db.fill(*DARK_BG)
db.rect(0, 0, WIDTH, HEIGHT)

# Subtle gradient overlay
db.blendMode("screen")
gradient_texture = Path(__file__).parent.parent / "assets/gradient/001.jpg"
if gradient_texture.exists():
    db.image(str(gradient_texture), (0, 0), width=WIDTH, height=HEIGHT, alpha=0.05)
db.blendMode("normal")

# ==================== LOGO ====================

logo_path = Path(__file__).parent.parent / "assets/logos/scty-logo.svg"
if logo_path.exists():
    logo_size = 80
    logo_x = MARGIN
    logo_y = grid[(0, 15)][1] + 10
    # Note: drawbot-skia may have limited SVG support, using fallback text if needed
    try:
        db.image(str(logo_path), (logo_x, logo_y), width=logo_size)
    except:
        # Fallback: SCTY text logo
        db.font("Helvetica-Bold")
        db.fontSize(scale.h1)
        db.fill(*ACCENT)
        db.text("SCTY", (logo_x, logo_y))
else:
    # Fallback: SCTY text logo
    db.font("Helvetica-Bold")
    db.fontSize(scale.h1)
    db.fill(*ACCENT)
    db.text("SCTY", (MARGIN, grid[(0, 15)][1] + 10))

# ==================== HEADLINE ====================

headline_box = (*grid[(0, 12)], *grid*(12, 2))

db.font("Helvetica-Bold")
db.fontSize(scale.h1 * 1.1)
db.fill(*TEXT)
db.text("Designing Desirable", (MARGIN, headline_box[1] + headline_box[3] - 15))

db.fill(*ACCENT)
db.text("Futures", (MARGIN, headline_box[1] + headline_box[3] - 65))

# ==================== TAGLINE ====================

tagline_box = (*grid[(0, 11)], *grid*(12, 1))

db.font("Helvetica")
db.fontSize(scale.h3)
db.fill(*SUBTLE)
db.text("Augmenting Human Creativity with AI Native Intelligence",
        (MARGIN, tagline_box[1] + 5))

# ==================== FEATURED NEWS ====================

news_box = (*grid[(0, 9)], *grid*(12, 1.5))

db.font("Helvetica-Bold")
db.fontSize(scale.body)
db.fill(*ACCENT)
db.text("FEATURED", (MARGIN, news_box[1] + news_box[3] - 10))

db.font("Helvetica")
db.fontSize(scale.h3 * 0.85)
db.fill(*TEXT)
news_text = "Ali's Brand OS & synthetic personas featured in Brands in the Age of AI by SVA"
draw_wrapped_text(
    news_text,
    MARGIN,
    news_box[1] + news_box[3] - 35,
    (grid * (12, 1))[0] - MARGIN * 2,
    news_box[3] - 45,
    "Helvetica",
    scale.h3 * 0.85,
    leading_ratio=1.4
)

# ==================== SERVICES ====================

# Service 1: Vision Sprint
service1_box = (*grid[(0, 7)], *grid*(5, 2))

db.font("Helvetica-Bold")
db.fontSize(scale.h3)
db.fill(*ACCENT)
db.text("Vision Sprint", (service1_box[0] + 10, service1_box[1] + service1_box[3] - 20))

db.font("Helvetica")
db.fontSize(scale.body)
db.fill(*TEXT)
db.text('"Where should we play?"', (service1_box[0] + 10, service1_box[1] + service1_box[3] - 50))

db.fontSize(scale.body * 0.9)
db.fill(*SUBTLE)
vision_desc = "Cut through the hype and develop a focused AI strategy with clear priorities."
draw_wrapped_text(
    vision_desc,
    service1_box[0] + 10,
    service1_box[1] + service1_box[3] - 75,
    service1_box[2] - 20,
    80,
    "Helvetica",
    scale.body * 0.9,
    leading_ratio=1.5
)

# Service 2: Maker Lab
service2_box = (*grid[(7, 7)], *grid*(5, 2))

db.font("Helvetica-Bold")
db.fontSize(scale.h3)
db.fill(*ACCENT)
db.text("Maker Lab", (service2_box[0] + 10, service2_box[1] + service2_box[3] - 20))

db.font("Helvetica")
db.fontSize(scale.body)
db.fill(*TEXT)
db.text('"How do we start today?"', (service2_box[0] + 10, service2_box[1] + service2_box[3] - 50))

db.fontSize(scale.body * 0.9)
db.fill(*SUBTLE)
maker_desc = "Break through analysis paralysis with hands-on experimentation."
draw_wrapped_text(
    maker_desc,
    service2_box[0] + 10,
    service2_box[1] + service2_box[3] - 75,
    service2_box[2] - 20,
    80,
    "Helvetica",
    scale.body * 0.9,
    leading_ratio=1.5
)

# Service 3: Transformation
service3_box = (*grid[(0, 4)], *grid*(5, 2))

db.font("Helvetica-Bold")
db.fontSize(scale.h3)
db.fill(*ACCENT)
db.text("Transformation", (service3_box[0] + 10, service3_box[1] + service3_box[3] - 20))

db.font("Helvetica")
db.fontSize(scale.body)
db.fill(*TEXT)
db.text('"Embed AI into the org."', (service3_box[0] + 10, service3_box[1] + service3_box[3] - 50))

db.fontSize(scale.body * 0.9)
db.fill(*SUBTLE)
transform_desc = "Transform disconnected AI efforts into cohesive organizational change."
draw_wrapped_text(
    transform_desc,
    service3_box[0] + 10,
    service3_box[1] + service3_box[3] - 75,
    service3_box[2] - 20,
    80,
    "Helvetica",
    scale.body * 0.9,
    leading_ratio=1.5
)

# Service 4: Product Incubator
service4_box = (*grid[(7, 4)], *grid*(5, 2))

db.font("Helvetica-Bold")
db.fontSize(scale.h3)
db.fill(*ACCENT)
db.text("Product Incubator", (service4_box[0] + 10, service4_box[1] + service4_box[3] - 20))

db.font("Helvetica")
db.fontSize(scale.body)
db.fill(*TEXT)
db.text('"Ship an AI product."', (service4_box[0] + 10, service4_box[1] + service4_box[3] - 50))

db.fontSize(scale.body * 0.9)
db.fill(*SUBTLE)
product_desc = "Navigate complexity to launch AI products users love."
draw_wrapped_text(
    product_desc,
    service4_box[0] + 10,
    service4_box[1] + service4_box[3] - 75,
    service4_box[2] - 20,
    80,
    "Helvetica",
    scale.body * 0.9,
    leading_ratio=1.5
)

# ==================== APPROACH ====================

approach_box = (*grid[(0, 2)], *grid*(12, 1))

db.font("Helvetica-Bold")
db.fontSize(scale.body * 1.1)
db.fill(*TEXT)
db.text("We help teams use AI to solve real problems and grow faster",
        (MARGIN, approach_box[1] + 15))

# ==================== FOOTER ====================

footer_box = (*grid[(0, 0)], *grid*(12, 1))

db.font("Helvetica")
db.fontSize(scale.body)
db.fill(*ACCENT)
db.text("Design & Technology Studio", (MARGIN, footer_box[1] + footer_box[3] - 20))

db.fontSize(scale.caption)
db.fill(*SUBTLE)
db.text("scty.io", (MARGIN, footer_box[1] + footer_box[3] - 45))

# Accent line
db.fill(*ACCENT)
db.rect(MARGIN, footer_box[1] + 5, 60, 2)

# ==================== DEBUG (optional) ====================

# Uncomment to visualize grid:
# grid.draw(show_index=True)

# ==================== SAVE ====================

output = get_output_path("scty_poster.pdf")
db.saveImage(str(output))
print(f"✓ Saved to {output}")
