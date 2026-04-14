# DrawBot API Quick Reference

Essential DrawBot functions for the drawbot-designer subagent.

## Canvas & Pages

```python
db.newPage(width, height)          # Create new page with dimensions
db.width()                          # Get page width
db.height()                         # Get page height
db.saveImage("path/to/file.pdf")   # Save as PDF, PNG, SVG, etc.
```

## Drawing Context

```python
db.save()      # Save current graphics state
db.restore()   # Restore previous graphics state
db.translate(x, y)    # Move origin
db.rotate(degrees)    # Rotate coordinate system
db.scale(x, y=None)   # Scale coordinate system
```

## Colors & Fills

```python
# RGB Colors (0-1 range)
db.fill(r, g, b, alpha=1)          # Set fill color
db.stroke(r, g, b, alpha=1)        # Set stroke color
db.strokeWidth(width)              # Set stroke width
db.lineDash(dash1, gap1, ...)     # Set line dash pattern
db.noFill()                        # Disable fill
db.noStroke()                      # Disable stroke

# CMYK Colors (for print) - values 0-1
db.cmykFill(c, m, y, k, alpha=1)   # CMYK fill color
db.cmykStroke(c, m, y, k, alpha=1) # CMYK stroke color

# Color modes
db.colorSpace("RGB")               # RGB color space (default)
db.colorSpace("CMYK")              # CMYK for print
```

## Basic Shapes

```python
db.rect(x, y, width, height)       # Rectangle
db.oval(x, y, width, height)       # Oval/circle
db.line((x1, y1), (x2, y2))       # Straight line
db.polygon((x1,y1), (x2,y2), ...) # Polygon from points
```

## Bezier Paths

```python
# Drawing paths
db.newPath()                       # Start new path
db.moveTo((x, y))                 # Move to point without drawing
db.lineTo((x, y))                 # Draw line to point
db.curveTo((cp1x, cp1y), (cp2x, cp2y), (x, y))  # Bezier curve
db.closePath()                     # Close current path
db.drawPath()                      # Draw the path
db.clipPath()                      # Use path as clipping mask

# BezierPath object (for complex operations)
path = db.BezierPath()            # Create path object
path.rect(x, y, w, h)             # Add rectangle to path
path.oval(x, y, w, h)             # Add oval to path
path.polygon((x1,y1), (x2,y2)...) # Add polygon to path
path.text("Hello", font="Helvetica", fontSize=50)  # Text as path

# Boolean operations (combine paths)
union = path1.union(path2)         # Combine paths (OR)
intersection = path1.intersection(path2)  # Overlap only (AND)
difference = path1.difference(path2)      # Subtract path2 from path1
xor = path1.xor(path2)            # Non-overlapping areas

# Path utilities
path.removeOverlap()               # Remove overlapping contours
path.expandStroke(width)           # Convert stroke to filled path
path.optimizePath()                # Simplify path points
db.drawPath(path)                  # Draw BezierPath object
```

## Typography

```python
# Font setup
db.font("Helvetica")               # Set font by name
db.font("path/to/font.otf")       # Set font by path
db.fontSize(size)                  # Set font size
db.lineHeight(height)              # Set line height
db.language("en")                  # Set language for hyphenation

# Text styling
db.tracking(value)                 # Letter spacing (em units)
db.baselineShift(value)            # Shift baseline up/down
db.strikethrough(True/False)       # Strikethrough text
db.underline(True/False)           # Underline text

# Variable fonts
db.fontVariations(wght=700, wdth=100)  # Set variation axes
db.fontVariations(resetVariations=True)  # Reset to defaults
axes = db.listFontVariations()     # Get available axes
db.fontNamedInstance("Bold")       # Use predefined instance

# OpenType features
db.openTypeFeatures(liga=True, smcp=True)  # Enable features
features = db.listOpenTypeFeatures()        # Get available features

# Drawing text
db.text("Hello", (x, y))          # Draw text at position
db.textBox("Long text...", (x, y, w, h))  # Text in box
overflow = db.textOverflow("text", (x,y,w,h))  # Check if text fits

# Text measurements
w, h = db.textSize("Hello")        # Returns (width, height)
baselines = db.textBoxBaselines("text", (x,y,w,h))  # Get line positions
bounds = db.textBoxCharacterBounds("text", (x,y,w,h))  # Get char positions

# Layout control
db.hyphenation(True/False)         # Enable/disable hyphenation
```

## FormattedString (Rich Text)

```python
# Create and style text runs
txt = db.FormattedString()
txt.append("Bold", font="Helvetica-Bold", fontSize=24)
txt.append(" and ", fontSize=16)
txt.append("italic", font="Helvetica-Oblique")
txt.append("Red text", fill=(1, 0, 0))

# Styling methods (apply to all text)
txt.font("Helvetica")
txt.fontSize(16)
txt.fill(0, 0, 0)
txt.cmykFill(0, 0, 0, 1)          # CMYK fill
txt.stroke(1, 0, 0)
txt.strokeWidth(2)
txt.tracking(10)                   # Letter spacing
txt.baselineShift(5)               # Shift baseline
txt.lineHeight(20)                 # Line height
txt.align("left")                  # "left", "center", "right", "justified"

# Paragraph spacing
txt.firstLineIndent(20)            # Indent first line
txt.indent(10)                     # Left indent
txt.tailIndent(10)                 # Right indent
txt.paragraphTopSpacing(10)        # Space before paragraph
txt.paragraphBottomSpacing(10)     # Space after paragraph

# Tab stops
txt.tabs((100, "left"), (200, "center"), (300, "right"))

# Advanced features
txt.fontVariations(wght=700)       # Variable font
txt.openTypeFeatures(liga=True)    # OpenType features
txt.hyphenation(True)              # Enable hyphenation
txt.language("en")                 # Set language
txt.strikethrough(True)            # Strikethrough
txt.underline(True)                # Underline
txt.url("https://example.com")     # Hyperlink (PDF)

# Add glyphs by name
txt.appendGlyph("heart.fill", font="SF Symbols", fontSize=20)

# Draw it
db.text(txt, (x, y))
db.textBox(txt, (x, y, w, h))
```

## Images

```python
db.image("path/to/image.png", (x, y))              # Draw image
db.image("path/to/image.png", (x, y, w, h))       # Draw with size
db.imageSize("path/to/image.png")                  # Get image dimensions
```

## Gradients

```python
# Linear gradient (RGB)
db.linearGradient(
    (startX, startY),              # Start point
    (endX, endY),                  # End point
    [(color1, 0), (color2, 1)]     # Color stops (color, position 0-1)
)

# Radial gradient (RGB)
db.radialGradient(
    (centerX, centerY),            # Center
    (endX, endY),                  # Outer edge
    [(color1, 0), (color2, 1)],    # Color stops
    startRadius=0                  # Inner radius (default 0)
)

# CMYK gradients (for print)
db.cmykLinearGradient(
    (startX, startY),
    (endX, endY),
    [((c,m,y,k), 0), ((c,m,y,k), 1)]
)

db.cmykRadialGradient(
    (centerX, centerY),
    (endX, endY),
    [((c,m,y,k), 0), ((c,m,y,k), 1)],
    startRadius=0
)
```

## Blending & Effects

```python
db.blendMode("multiply")           # Blend mode: multiply, overlay, screen, etc.
db.opacity(value)                  # Global opacity (0-1)

# Shadow (RGB)
db.shadow((offsetX, offsetY), blur, color)

# Shadow (CMYK)
db.cmykShadow((offsetX, offsetY), blur, (c, m, y, k))

# Blend modes available:
# "normal", "multiply", "screen", "overlay", "darken", "lighten",
# "colorDodge", "colorBurn", "softLight", "hardLight", "difference",
# "exclusion", "hue", "saturation", "color", "luminosity"
```

## Grid & Layout Helpers (Custom)

These are patterns to use, not built-in functions:

```python
def grid_positions(cols, rows, x, y, cell_w, cell_h, gutter_x=0, gutter_y=0):
    """Generate grid positions"""
    positions = []
    for row in range(rows):
        for col in range(cols):
            px = x + col * (cell_w + gutter_x)
            py = y + row * (cell_h + gutter_y)
            positions.append((px, py))
    return positions

def margin_box(margin):
    """Get content box with margins"""
    return (
        margin,
        margin,
        db.width() - margin * 2,
        db.height() - margin * 2
    )
```

## Common Patterns

### Centered text
```python
text = "Centered"
w, h = db.textSize(text)
x = (db.width() - w) / 2
y = (db.height() - h) / 2
db.text(text, (x, y))
```

### Grid layout
```python
margin = 50
gutter = 20
cols = 3

content_width = db.width() - margin * 2
cell_width = (content_width - gutter * (cols - 1)) / cols

for i in range(cols):
    x = margin + i * (cell_width + gutter)
    db.rect(x, margin, cell_width, 100)
```

### Typography scale
```python
# Modular scale (1.5 ratio)
base = 16
scale = 1.5

sizes = {
    'body': base,
    'h3': base * scale,
    'h2': base * scale ** 2,
    'h1': base * scale ** 3,
}
```

## Color Palettes

```python
# Grayscale
white = (1, 1, 1)
light_gray = (0.9, 0.9, 0.9)
mid_gray = (0.5, 0.5, 0.5)
dark_gray = (0.2, 0.2, 0.2)
black = (0, 0, 0)

# Opacity variants
semi_transparent = (0, 0, 0, 0.5)
barely_visible = (1, 1, 1, 0.1)
```

## Drawing Order (Z-Index)

DrawBot draws in order - last drawn is on top:
```python
# Background (drawn first)
db.fill(1, 1, 1)
db.rect(0, 0, db.width(), db.height())

# Middle layer
db.fill(0.8, 0.8, 0.8)
db.rect(100, 100, 200, 200)

# Foreground (drawn last, appears on top)
db.fill(0, 0, 0)
db.text("On Top", (150, 150))
```

## Coordinate System

- Origin (0, 0) is at **bottom-left**
- X increases to the right
- Y increases upward
- Use `db.translate()` to reposition origin

## PDF Interactive Features

```python
# Hyperlinks
db.linkURL("https://example.com", (x, y, w, h))  # Clickable link
db.linkRect((x, y, w, h), "DestinationName")     # Internal page link
db.linkDestination("DestinationName", (x, y))    # Link destination marker

# FormattedString links
txt = db.FormattedString()
txt.append("Click here", url="https://example.com")
```

## Animation & Multi-Page

```python
# Multi-page documents
db.newPage(width, height)          # Add new page
db.frameDuration(seconds)          # Set duration for this page (animations)

# Page info
pages = db.pages()                 # List of all page objects
count = db.pageCount()             # Number of pages
num = db.numberOfPages()           # Alias for pageCount()

# Example animation
for frame in range(30):
    db.newPage(500, 500)
    db.frameDuration(1/30)         # 30 fps
    # ... draw frame
db.saveImage("animation.gif")      # Animated GIF
db.saveImage("animation.mp4")      # MP4 video
```

## File Formats

```python
db.saveImage("output.pdf")    # Vector PDF
db.saveImage("output.svg")    # Vector SVG
db.saveImage("output.png")    # Raster PNG
db.saveImage("output.jpg")    # Raster JPEG
db.saveImage("output.gif")    # Animated GIF (multi-page)
db.saveImage("output.mp4")    # MP4 video (multi-page)
db.saveImage("output.tiff")   # TIFF image

# Save options
db.saveImage("output.png", imageResolution=144)  # High-res PNG
```

## Best Practices

1. **Always use 'db.' prefix** for all DrawBot functions
2. **Define design system first**: margins, colors, typography before drawing
3. **Save/restore context**: Use `db.save()` and `db.restore()` for transformations
4. **Bottom-up coordinates**: Remember Y increases upward from bottom
5. **Colors in 0-1 range**: Not 0-255
6. **Create reusable functions**: For grids, repeated elements, layouts
7. **Comment design intent**: Why you chose spacing, colors, hierarchy

## Resources

- Full documentation: http://www.drawbot.com
- Forum: http://forum.drawbot.com
- This is a quick reference - check docs for advanced features
