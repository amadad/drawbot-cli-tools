"""
Minimal Poster Example - Using Design System

This demonstrates the absolute minimum code needed to create
a well-designed poster using the design system.

Compare to manual approach - this is:
- ✅ Simpler (30 lines vs 200+)
- ✅ Correct (follows your docs automatically)
- ✅ Portable (works on any machine)
- ✅ Maintainable (semantic, not magic numbers)
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

import drawBot as db
from drawbot_grid import Grid
from drawbot_design_system import (
    POSTER_SCALE,
    get_output_path,
    get_color_palette,
    draw_wrapped_text,
    setup_poster_page
)

# ==================== SETUP ====================

# Setup (one line creates canvas and returns dimensions)
WIDTH, HEIGHT, MARGIN = setup_poster_page("letter", margin_ratio=1/10)

# Grid (automatically reads canvas size)
grid = Grid.from_margins(
    (-MARGIN, -MARGIN, -MARGIN, -MARGIN),
    column_subdivisions=12,
    row_subdivisions=8
)

# Typography (pre-defined scale following your docs)
scale = POSTER_SCALE

# Colors (70-20-10 rule)
colors = get_color_palette("professional")

# ==================== DRAW ====================

# Background
db.fill(*colors["background"])
db.rect(0, 0, WIDTH, HEIGHT)

# Header area (top 2 rows, full width)
header = (*grid[(0, 6)], *grid*(12, 2))

db.font("Helvetica-Bold")
db.fontSize(scale.title)
db.fill(*colors["text"])
db.text("Poster Title", (grid[(0, 7)][0] + 10, grid[(0, 7)][1] + 20))

# Subtitle
db.fontSize(scale.h2)
db.fill(*colors["accent"])
db.text("Subtitle Here", (grid[(0, 6)][0] + 10, grid[(0, 6)][1] + 10))

# Body area (rows 1-5, full width)
body = (*grid[(0, 1)], *grid*(12, 5))

# Draw wrapped text (automatically fits to box)
body_text = """
This is body text that will automatically wrap to fit the available
width. No manual calculation needed. The design system measures the
actual character widths and wraps accordingly. It also uses real font
metrics for line spacing, not approximations.
""".strip()

db.font("Helvetica")
db.fontSize(scale.body)
db.fill(*colors["text"])

draw_wrapped_text(
    body_text,
    grid[(0, 1)][0] + 10,
    grid[(0, 5)][1] - 10,
    (grid * (12, 1))[0] - 20,  # Need parentheses for multiplication
    (grid * (4, 1))[1],
    "Helvetica",
    scale.body,
    leading_ratio=1.5,
    align="left"
)

# Footer (row 0)
db.fontSize(scale.caption)
db.fill(0.5, 0.5, 0.5)  # Gray for footer
db.text("Footer Info", (grid[(0, 0)][0] + 10, grid[(0, 0)][1] + 10))

# ==================== DEBUG (optional) ====================

# Uncomment to see grid during development:
# grid.draw(show_index=True)

# ==================== SAVE ====================

# Save (portable path, works on any machine)
output = get_output_path("minimal_poster.pdf")
db.saveImage(str(output))
print(f"✓ Saved: {output}")

print(f"\nStats:")
print(f"  Page: {WIDTH} × {HEIGHT}pt")
print(f"  Grid: {grid.columns.columns} cols × {grid.rows.rows} rows")
print(f"  Scale: base {scale.body}pt, ratio {scale.ratio}")
print(f"  Lines of code: ~80 (vs 200+ manual approach)")
