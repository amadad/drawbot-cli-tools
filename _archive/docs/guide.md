# DrawBot Design System - Usage Guide

**The design system enforces principles from your documentation automatically.**

## Quick Start

```python
from drawbot_backend import db
from drawbot_grid import Grid
from drawbot_design_system import (
    POSTER_SCALE,
    get_output_path,
    get_color_palette,
    draw_wrapped_text,
    setup_poster_page
)

# 1. Setup page (automatically creates canvas)
WIDTH, HEIGHT, MARGIN = setup_poster_page("letter", margin_ratio=1/10)

# 2. Define grid FIRST (reads active canvas automatically)
grid = Grid.from_margins(
    (-MARGIN, -MARGIN, -MARGIN, -MARGIN),
    column_subdivisions=12,
    row_subdivisions=16
)

# 3. Use pre-defined typography scale (poster: base 18pt, ratio 1.5)
scale = POSTER_SCALE

# 4. Use semantic grid coordinates (no manual math!)
header_area = (*grid[(0, 14)], *grid*(12, 2))  # Full width, top 2 rows

# 5. Draw with proper text wrapping
draw_wrapped_text(
    "Your text here",
    x, y, width, height,
    "Helvetica", scale.body
)

# 6. Save with portable paths (works on any machine)
db.saveImage(str(get_output_path("output.pdf")))
```

## Backend Selection

Install one of the supported backends:

```bash
# Native DrawBot on macOS
uv sync --extra cli --extra drawbot

# Cross-platform backend
uv sync --extra cli --extra drawbot-skia
```

Backend resolution order for CLI-owned flows and wrapper-aware scripts:

1. `--backend`
2. `DRAWBOT_BACKEND`
3. auto-detect, preferring native `drawBot` first and `drawbot-skia` second

Examples:

```bash
drawbot from-spec poster.yaml --backend drawbot-skia
DRAWBOT_BACKEND=drawbot-skia drawbot render poster.py
```

Phase 1 is intentionally incremental:

- repo-owned library and spec-rendering flows are backend-aware
- newly generated scaffolds use `from drawbot_backend import db`
- existing DrawBot workflows remain supported for scripts that still do `import drawBot as db`
- arbitrary legacy scripts are not rewritten automatically

## What's Fixed

### ✅ Grid System Now Reads Active Canvas

**Before** (hardcoded):
```python
# drawbot_grid.py - OLD
page_width = 612   # Always letter size!
page_height = 792
```

**After** (dynamic):
```python
# drawbot_grid.py - NEW
try:
    page_width = db.width()   # Reads actual canvas
    page_height = db.height()
except:
    page_width = 612          # Fallback
    page_height = 792
```

**Impact**: Grid now works with A4, tabloid, square, any size.

### ✅ Typography Scales Follow Your Docs

**Your docs say** (`layout-design-principles.md:486-503`):

| Purpose | Base Size | Scale Ratio |
|---------|-----------|-------------|
| Poster  | 16-24pt   | 1.5-1.618   |
| Magazine| 10-11pt   | 1.25-1.333  |
| Book    | 10-12pt   | 1.2-1.25    |

**Now enforced** (`drawbot_design_system.py`):
```python
POSTER_SCALE = create_typography_scale(18, PERFECT_FIFTH)    # 18pt base, 1.5 ratio
MAGAZINE_SCALE = create_typography_scale(11, MAJOR_THIRD)    # 11pt base, 1.25 ratio
BOOK_SCALE = create_typography_scale(11, MINOR_THIRD)        # 11pt base, 1.2 ratio
```

Use like:
```python
scale = POSTER_SCALE
db.fontSize(scale.body)    # 18pt
db.fontSize(scale.h1)      # 60.75pt
db.fontSize(scale.title)   # 91.125pt
```

### ✅ Text Wrapping Based on Points (Not Characters)

**Before** (broken):
```python
# Wraps based on CHARACTER COUNT (ignores actual width!)
wrapped = textwrap.wrap(text, width=70)
```

**After** (correct):
```python
# Measures actual character width in points
from drawbot_design_system import wrap_text_to_width

wrapped = wrap_text_to_width(
    text,
    width_in_points=400,  # Actual visual width
    font="Helvetica",
    size=16
)
```

**Impact**: Text no longer overflows boxes.

### ✅ Real Text Metrics (Not Approximations)

**Before** (wrong):
```python
# Assumes line height = fontSize (WRONG!)
line_y -= font_size
```

**After** (correct):
```python
from drawbot_design_system import get_text_metrics

metrics = get_text_metrics("Sample", "Helvetica", 16)
# Returns: ascender, descender, line_height, x_height, cap_height
line_y -= metrics['line_height']  # Real measurement!
```

### ✅ Portable Paths (Works on Any Machine)

**Before** (breaks on other machines):
```python
# Hardcoded to YOUR home directory
output = "/Users/amadad/Projects/tools/drawbot-redux/output/file.pdf"
```

**After** (portable):
```python
from drawbot_design_system import get_output_path

output = get_output_path("file.pdf")
# Resolves to: <repo_root>/output/file.pdf
# Works on ANY machine
```

## Pre-defined Components

### Typography Scales

```python
from drawbot_design_system import (
    POSTER_SCALE,    # Base 18pt, ratio 1.5
    MAGAZINE_SCALE,  # Base 11pt, ratio 1.25
    BOOK_SCALE,      # Base 11pt, ratio 1.2
    REPORT_SCALE     # Base 12pt, ratio 1.25
)

# Access sizes:
scale = POSTER_SCALE
scale.caption  # 12pt
scale.body     # 18pt
scale.h3       # 27pt
scale.h2       # 40.5pt
scale.h1       # 60.75pt
scale.title    # 91.125pt
scale.ratio    # 1.5

# Get proper leading:
leading = scale.leading(scale.body, ratio=1.5)  # 27pt (18pt * 1.5)
```

### Color Palettes

```python
from drawbot_design_system import get_color_palette

colors = get_color_palette("professional")
# Returns: {'background': (0.98, 0.98, 0.97),
#           'text': (0.1, 0.1, 0.1),
#           'accent': (0.2, 0.45, 0.7)}

# Available palettes:
# - "professional" (default)
# - "warm"
# - "cool"
# - "high_contrast"
```

Follows **70-20-10 rule** from your docs (`layout-design-principles.md:353-363`).

### Page Setup

```python
from drawbot_design_system import setup_poster_page

# Creates canvas and returns dimensions
width, height, margin = setup_poster_page(
    size="letter",           # "letter", "tabloid", "a4", "a3", "square"
    margin_ratio=1/10,       # Margin as fraction of page
    orientation="portrait"   # or "landscape"
)

# Automatically calls db.newPage(width, height)
```

### Advanced Text Drawing

```python
from drawbot_design_system import draw_wrapped_text

# Draws text with proper wrapping and metrics
final_y = draw_wrapped_text(
    text="Your long text here...",
    x=100,              # Top-left corner
    y=500,
    width=300,          # Box width
    height=200,         # Box height
    font="Helvetica",
    size=16,
    leading_ratio=1.5,  # Line spacing (default 1.5x)
    align="left"        # "left", "right", "center"
)

# Returns final y position (for stacking content)
```

**Automatically**:
- Wraps based on actual width in points
- Uses real font metrics (not approximations)
- Stops when out of vertical space
- Returns final baseline position

### Layout Validation

```python
from drawbot_design_system import validate_layout_fit

# Define your elements
elements = [
    {'y': 700, 'height': 100, 'name': 'Header'},
    {'y': 580, 'height': 200, 'name': 'Hero', 'margin_top': 20},
    {'y': 200, 'height': 150, 'name': 'Footer'}
]

# Validate BEFORE drawing
fits, error = validate_layout_fit(elements, page_height=792)

if not fits:
    print(f"Layout error: {error}")
    # Example: "Hero overlaps Footer by 30pt"
```

**Checks**:
- Elements fit within page bounds
- No overlaps between elements
- Respects margin_top spacing

## Grid System Best Practices

### 1. Always Define Grid FIRST

```python
# ✅ CORRECT order:
db.newPage(612, 792)

grid = Grid.from_margins(...)  # Grid reads active canvas

db.rect(*grid[(0, 0)], *grid*(3, 2))  # Use grid

# ❌ WRONG order:
grid = Grid.from_margins(...)  # No canvas yet!
db.newPage(612, 792)
```

### 2. Use Semantic Coordinates

```python
# ✅ GOOD (semantic, clear intent)
header = (*grid[(0, 14)], *grid*(12, 2))  # "Full width, top 2 rows"
left_col = (*grid[(0, 0)], *grid*(5, 10)) # "Left 5 cols, 10 rows"

# ❌ BAD (manual math, error-prone)
header = (MARGIN, HEIGHT - 200, WIDTH - MARGIN*2, 150)
```

### 3. Allocate Rows Before Drawing

```python
# Calculate space needed:
HEADER_ROWS = 2
CONTENT_ROWS = 12
FOOTER_ROWS = 2
# Total: 16 rows

assert HEADER_ROWS + CONTENT_ROWS + FOOTER_ROWS == 16, "Mismatch!"

# Then map to grid
```

### 4. Debug with Visual Grid

```python
# During development, visualize the grid:
grid.draw(show_index=True)  # Shows grid lines + indices

# Remove for final output
```

## Common Patterns

### Poster Layout

```python
from drawbot_backend import db
from drawbot_grid import Grid
from drawbot_design_system import (
    POSTER_SCALE,
    get_output_path,
    get_color_palette,
    setup_poster_page
)

# Setup
WIDTH, HEIGHT, MARGIN = setup_poster_page("letter", margin_ratio=1/10)
grid = Grid.from_margins((-MARGIN, -MARGIN, -MARGIN, -MARGIN),
                         column_subdivisions=12, row_subdivisions=16)
scale = POSTER_SCALE
colors = get_color_palette("professional")

# Background
db.fill(*colors["background"])
db.rect(0, 0, WIDTH, HEIGHT)

# Header (top 2 rows)
db.font("Helvetica-Bold")
db.fontSize(scale.title)
db.fill(*colors["text"])
db.text("Title", (MARGIN, grid[(0, 15)][1]))

# Content (rows 1-13)
content_area = (*grid[(0, 1)], *grid*(12, 13))

# Footer (row 0)
db.fontSize(scale.caption)
db.fill(*colors["text"])
db.text("Footer", (MARGIN, grid[(0, 0)][1] + 10))

# Save
db.saveImage(str(get_output_path("poster.pdf")))
```

### Two-Column Layout

```python
# Define columns with gutter
left_col = (*grid[(0, 1)], *grid*(5, 14))   # Cols 0-4
right_col = (*grid[(7, 1)], *grid*(5, 14))  # Cols 7-11
# Column 5-6 is automatic gutter (from grid definition)

# Draw in columns
db.rect(*left_col)   # Left content area
db.rect(*right_col)  # Right content area
```

### Multi-Row Content

```python
# Stack elements using row indices
row_1 = (*grid[(0, 15)], *grid*(12, 1))
row_2 = (*grid[(0, 14)], *grid*(12, 1))
row_3 = (*grid[(0, 13)], *grid*(12, 1))

# Gutters are automatic (from row_gutter in grid definition)
```

## Troubleshooting

### "Grid doesn't match my page!"

**Cause**: Grid defined before `newPage()` or page size changed after grid creation.

**Fix**:
```python
# ✅ Correct order:
db.newPage(WIDTH, HEIGHT)              # 1. Create page
grid = Grid.from_margins(...)          # 2. Create grid (reads page)

# OR use setup helper:
WIDTH, HEIGHT, MARGIN = setup_poster_page("letter")  # Does both
grid = Grid.from_margins((-MARGIN, -MARGIN, -MARGIN, -MARGIN))
```

### "Text overflows my box!"

**Cause**: Using character-count wrapping instead of point-based wrapping.

**Fix**:
```python
# ❌ Wrong:
wrapped = textwrap.wrap(text, width=70)  # Character count

# ✅ Right:
from drawbot_design_system import wrap_text_to_width
wrapped = wrap_text_to_width(text, width_in_points=400, font="Helvetica", size=16)
```

### "Content doesn't fit on page!"

**Cause**: Not allocating space before drawing.

**Fix**:
```python
# Use layout validation:
from drawbot_design_system import validate_layout_fit

elements = [
    {'y': 700, 'height': 100, 'name': 'Header'},
    {'y': 580, 'height': 200, 'name': 'Body'},
    {'y': 50, 'height': 50, 'name': 'Footer'}
]

fits, error = validate_layout_fit(elements, HEIGHT)
if not fits:
    print(f"ERROR: {error}")
    # Adjust heights or positions
```

### "Paths don't work on other machines!"

**Cause**: Hardcoded absolute paths.

**Fix**:
```python
# ❌ Wrong:
output = "/Users/amadad/Projects/tools/drawbot-redux/output/file.pdf"

# ✅ Right:
from drawbot_design_system import get_output_path
output = get_output_path("file.pdf")
```

## Migration Guide

### For New Scripts

Prefer the backend wrapper in new repo-owned scripts and scaffolds:

```python
from drawbot_backend import db
```

This keeps the same drawing API while allowing backend selection through the CLI or `DRAWBOT_BACKEND`.

### For Existing DrawBot Scripts

Existing DrawBot-first scripts still work unchanged when native DrawBot is installed:

```python
import drawBot as db
```

Keep using that form if you rely on native DrawBot directly. Phase 1 does not force a repo-wide rewrite.


### Updating Old Scripts

1. **Replace page setup**:
```python
# OLD:
WIDTH = 612
HEIGHT = 792
db.newPage(WIDTH, HEIGHT)
MARGIN = 60

# NEW:
from drawbot_design_system import setup_poster_page
WIDTH, HEIGHT, MARGIN = setup_poster_page("letter", margin_ratio=1/10)
```

2. **Add grid system**:
```python
# Add after page setup:
from drawbot_grid import Grid
grid = Grid.from_margins((-MARGIN, -MARGIN, -MARGIN, -MARGIN),
                         column_subdivisions=12, row_subdivisions=16)
```

3. **Replace manual calculations**:
```python
# OLD:
header_x = MARGIN
header_y = HEIGHT - MARGIN - 100
header_w = WIDTH - MARGIN*2
header_h = 100

# NEW:
header_area = (*grid[(0, 14)], *grid*(12, 2))
# Unpack: header_x, header_y, header_w, header_h = header_area
```

4. **Use typography scales**:
```python
# OLD:
SIZE_TITLE = 76
SIZE_H1 = 47
SIZE_BODY = 11

# NEW:
from drawbot_design_system import POSTER_SCALE
scale = POSTER_SCALE
db.fontSize(scale.title)  # 91.125pt (better for posters)
db.fontSize(scale.h1)     # 60.75pt
db.fontSize(scale.body)   # 18pt
```

5. **Fix text wrapping**:
```python
# OLD:
import textwrap
wrapped = textwrap.wrap(text, width=70)
for line in wrapped[:2]:  # Truncates!
    db.text(line, (x, y))
    y -= 14

# NEW:
from drawbot_design_system import draw_wrapped_text
final_y = draw_wrapped_text(text, x, y, width, height,
                             "Helvetica", scale.body)
```

6. **Fix paths**:
```python
# OLD:
output = "/Users/amadad/Projects/tools/drawbot-redux/output/file.pdf"

# NEW:
from drawbot_design_system import get_output_path
output = get_output_path("file.pdf")
db.saveImage(str(output))
```

7. **Optional backend wrapper for new scripts**:
```python
# NEW scaffold style:
from drawbot_backend import db
```

## See Also

- `lib/drawbot_grid.py` - Grid system implementation
- `lib/drawbot_design_system.py` - Design system source
- `docs/api.md` - DrawBot API reference
- `examples/` - Example scripts
