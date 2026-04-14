"""
DrawBot Design System - Enforces professional design principles.

This module provides:
1. Typography scales (poster, book, magazine, report)
2. Point-based text wrapping (real measurements, not character heuristics)
3. Layout validation (overlap detection, boundary checks)
4. Portable path handling

Based on principles from:
- Hochuli: Detail in Typography
- Bringhurst: Elements of Typographic Style
- Müller-Brockmann: Grid Systems

Usage:
    from drawbot_design_system import (
        POSTER_SCALE, setup_poster_page, draw_wrapped_text, get_output_path
    )
"""

from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass

from drawbot_backend import db

__all__ = [
    # Path management
    'REPO_ROOT', 'OUTPUT_DIR', 'get_output_path',
    # Typography scales
    'TypographyScale', 'POSTER_SCALE', 'MAGAZINE_SCALE', 'BOOK_SCALE', 'REPORT_SCALE',
    'create_typography_scale',
    # Scale ratios
    'MINOR_SECOND', 'MAJOR_SECOND', 'MINOR_THIRD', 'MAJOR_THIRD',
    'PERFECT_FOURTH', 'PERFECT_FIFTH', 'GOLDEN_RATIO',
    # Text functions
    'get_text_metrics', 'wrap_text_to_width', 'draw_wrapped_text',
    # Layout
    'validate_layout_fit', 'setup_poster_page',
    # Helpers
    'get_spacing_for_context', 'get_color_palette',
    # Color harmony
    'generate_color_palette', 'hex_to_rgb', 'rgb_to_hex', 'check_contrast_ratio',
    'get_accessible_text_color', 'adjust_lightness',
    # OpenType & Variable Fonts
    'set_opentype_features', 'get_available_opentype_features',
    'set_font_variation', 'get_font_variation_axes',
    # Print production
    'setup_print_page', 'validate_print_ready', 'PRINT_PRESETS',
]

# ==================== PATH MANAGEMENT ====================

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"

def _ensure_output_dir():
    """Create output directory on first use (not at import time)."""
    OUTPUT_DIR.mkdir(exist_ok=True)

def get_output_path(filename: str) -> Path:
    """Get absolute path for output file (works on any machine)."""
    _ensure_output_dir()
    return OUTPUT_DIR / filename

# ==================== TYPOGRAPHY SCALES ====================

@dataclass
class TypographyScale:
    """Typography scale with proper ratios"""
    caption: float
    body: float
    h3: float
    h2: float
    h1: float
    title: float
    ratio: float

    def leading(self, size: float, ratio: float = 1.5) -> float:
        """Calculate proper leading (line spacing)"""
        return size * ratio

# Common scale ratios (from docs/layout-design-principles.md:95-103)
MINOR_SECOND = 1.067
MAJOR_SECOND = 1.125
MINOR_THIRD = 1.2
MAJOR_THIRD = 1.25
PERFECT_FOURTH = 1.333
PERFECT_FIFTH = 1.5
GOLDEN_RATIO = 1.618

def create_typography_scale(base: float, ratio: float) -> TypographyScale:
    """Create a modular typography scale"""
    return TypographyScale(
        caption=base / ratio,
        body=base,
        h3=base * ratio,
        h2=base * (ratio ** 2),
        h1=base * (ratio ** 3),
        title=base * (ratio ** 4),
        ratio=ratio
    )

# Pre-defined scales (from docs/layout-design-principles.md:486-503)
POSTER_SCALE = create_typography_scale(18, PERFECT_FIFTH)      # Base 18pt, ratio 1.5
MAGAZINE_SCALE = create_typography_scale(11, MAJOR_THIRD)      # Base 11pt, ratio 1.25
BOOK_SCALE = create_typography_scale(11, MINOR_THIRD)          # Base 11pt, ratio 1.2
REPORT_SCALE = create_typography_scale(12, MAJOR_THIRD)        # Base 12pt, ratio 1.25

# ==================== TEXT METRICS ====================

def get_text_metrics(text: str, font: str, size: float) -> dict:
    """Get real text metrics from DrawBot (not approximations)"""
    db.font(font)
    db.fontSize(size)

    # Get actual dimensions
    width, height = db.textSize(text)

    # Get font metrics
    try:
        ascender = db.fontAscender()
        descender = db.fontDescender()  # Should be negative
        line_height = db.fontLineHeight()
        x_height = db.fontXHeight()
        cap_height = db.fontCapHeight()
    except Exception as e:
        # Fallback if metrics not available
        # Log warning so issues don't go unnoticed
        import warnings
        warnings.warn(f"Could not get font metrics for '{font}' at {size}pt: {e}")
        ascender = size * 0.8
        descender = -size * 0.2  # Descender should be negative (below baseline)
        line_height = size * 1.2
        x_height = size * 0.5
        cap_height = size * 0.7

    return {
        'width': width,
        'height': height,
        'ascender': ascender,
        'descender': descender,
        'line_height': line_height,
        'x_height': x_height,
        'cap_height': cap_height
    }

def calculate_chars_per_line(width_in_points: float, font: str, size: float) -> int:
    """
    Calculate character count based on ACTUAL width in points.

    From docs/typography-style-guide.md:171-179:
    - Optimal: 60-70 characters per line
    - Ideal: 60-65 characters
    """
    db.font(font)
    db.fontSize(size)

    # Use 'm' as average character width
    avg_char_width, _ = db.textSize("m")

    # Calculate how many fit
    chars_per_line = int(width_in_points / avg_char_width)

    return chars_per_line

# ==================== TEXT WRAPPING ====================

def wrap_text_to_width(
    text: str,
    width_in_points: float,
    font: str,
    size: float
) -> List[str]:
    """
    Wrap text based on ACTUAL visual width in points.

    Measures each word with DrawBot to ensure accurate line breaks.
    Handles variable-width fonts correctly (unlike character-count methods).

    Args:
        text: Text to wrap
        width_in_points: Maximum line width in points
        font: Font name
        size: Font size in points

    Returns:
        List of wrapped lines
    """
    db.font(font)
    db.fontSize(size)

    words = text.split()
    if not words:
        return []

    lines = []
    current_line_words = []
    current_line_width = 0.0
    space_width, _ = db.textSize(" ")

    for word in words:
        word_width, _ = db.textSize(word)

        # Calculate width if we add this word
        if current_line_words:
            test_width = current_line_width + space_width + word_width
        else:
            test_width = word_width

        if test_width <= width_in_points:
            # Word fits on current line
            current_line_words.append(word)
            current_line_width = test_width
        else:
            # Word doesn't fit - start new line
            if current_line_words:
                lines.append(" ".join(current_line_words))

            # Handle words wider than the box (long URLs, etc.)
            if word_width > width_in_points:
                # Break the word into multiple chunks
                chunks = _break_long_word(word, width_in_points, font, size)
                # Add all but the last chunk as separate lines
                for chunk in chunks[:-1]:
                    lines.append(chunk)
                # Start new line with final chunk (may continue with more words)
                if chunks:
                    last_chunk = chunks[-1]
                    last_width, _ = db.textSize(last_chunk)
                    current_line_words = [last_chunk]
                    current_line_width = last_width
                else:
                    current_line_words = []
                    current_line_width = 0.0
            else:
                current_line_words = [word]
                current_line_width = word_width

    # Don't forget the last line
    if current_line_words:
        lines.append(" ".join(current_line_words))

    return lines


def _break_long_word(word: str, max_width: float, font: str, size: float) -> List[str]:
    """
    Break a word that's too wide for the column into multiple chunks.

    Returns a list of chunks, each fitting within max_width (with hyphens added
    to all but the last chunk).
    """
    db.font(font)
    db.fontSize(size)

    hyphen_width, _ = db.textSize("-")
    available = max_width - hyphen_width

    chunks = []
    remaining = word

    while remaining:
        # Check if remainder fits without hyphen
        remaining_width, _ = db.textSize(remaining)
        if remaining_width <= max_width:
            chunks.append(remaining)
            break

        # Find how many characters fit with hyphen
        found_break = False
        for i in range(len(remaining), 0, -1):
            part_width, _ = db.textSize(remaining[:i])
            if part_width <= available:
                chunks.append(remaining[:i] + "-")
                remaining = remaining[i:]
                found_break = True
                break

        # Fallback: take at least one character to avoid infinite loop
        if not found_break:
            if remaining:
                chunks.append(remaining[0] + "-")
                remaining = remaining[1:]
            else:
                break

    return chunks if chunks else [""]

def draw_wrapped_text(
    text: str,
    x: float,
    y: float,
    width: float,
    height: float,
    font: str,
    size: float,
    leading_ratio: float = 1.5,
    align: str = "left"
) -> float:
    """
    Draw wrapped text with proper metrics and return final y position.

    Args:
        text: Text to draw
        x, y: Top-left corner of text box
        width, height: Box dimensions
        font, size: Typography settings
        leading_ratio: Line spacing ratio (default 1.5x from docs)
        align: "left", "right", "center"

    Returns:
        Final y position (baseline of last line drawn)
    """
    db.font(font)
    db.fontSize(size)

    # Get real metrics
    metrics = get_text_metrics("M", font, size)  # Use cap height as reference
    line_spacing = size * leading_ratio

    # Wrap text to width
    lines = wrap_text_to_width(text, width, font, size)

    # Start from top, move down
    current_y = y - metrics['ascender']  # Position first baseline
    
    # Bottom boundary of text box
    bottom_boundary = y - height

    for line in lines:
        # Check if we have room (descender is negative, so + moves down)
        line_bottom = current_y + metrics['descender']
        if line_bottom < bottom_boundary:
            break  # Stop if we'd overflow

        # Calculate x position based on alignment
        if align == "center":
            line_width, _ = db.textSize(line)
            line_x = x + (width - line_width) / 2
        elif align == "right":
            line_width, _ = db.textSize(line)
            line_x = x + width - line_width
        else:  # left
            line_x = x

        db.text(line, (line_x, current_y))
        current_y -= line_spacing

    return current_y

# ==================== LAYOUT VALIDATION ====================

def validate_layout_fit(
    elements: List[Dict[str, Any]],
    page_height: float,
    page_width: Optional[float] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all elements fit on page without overlapping.

    Coordinate system: DrawBot uses bottom-left origin.
    - y is the TOP of the element
    - Element extends from y down to (y - height)

    Args:
        elements: List of dicts with:
            - 'y': float - Top Y coordinate
            - 'height': float - Element height
            - 'name': str - Element name for error messages
            - 'x': float (optional) - Left X coordinate
            - 'width': float (optional) - Element width
        page_height: Total page height
        page_width: Total page width (optional, for horizontal checks)

    Returns:
        (fits: bool, error_message: Optional[str])
    """
    if not elements:
        return True, None

    # Sort by y position (top to bottom, highest y first)
    sorted_elements = sorted(elements, key=lambda e: e['y'], reverse=True)

    for i, elem in enumerate(sorted_elements):
        elem_top = elem['y']
        elem_bottom = elem['y'] - elem['height']
        elem_name = elem.get('name', f'Element {i}')

        # Check if element extends above page
        if elem_top > page_height:
            overhang = elem_top - page_height
            return False, f"{elem_name} extends {overhang:.1f}pt above page top"

        # Check if element extends below page
        if elem_bottom < 0:
            return False, f"{elem_name} extends {abs(elem_bottom):.1f}pt below page bottom"

        # Check horizontal bounds if provided
        if page_width and 'x' in elem and 'width' in elem:
            if elem['x'] < 0:
                return False, f"{elem_name} extends {abs(elem['x']):.1f}pt past left edge"
            if elem['x'] + elem['width'] > page_width:
                overhang = (elem['x'] + elem['width']) - page_width
                return False, f"{elem_name} extends {overhang:.1f}pt past right edge"

        # Check for overlaps with elements below
        if i < len(sorted_elements) - 1:
            next_elem = sorted_elements[i + 1]
            next_top = next_elem['y']
            next_name = next_elem.get('name', f'Element {i+1}')

            # Overlap occurs if current bottom is below next top
            if elem_bottom < next_top:
                overlap = next_top - elem_bottom
                return False, f"{elem_name} overlaps {next_name} by {overlap:.1f}pt"

    return True, None

# ==================== SPACING HELPERS ====================

def get_spacing_for_context(context: str = "poster") -> dict:
    """
    Get spacing values based on context.

    From docs/layout-design-principles.md:506-512
    """
    spacing_map = {
        "tight": {
            "letter_spacing": -0.02,  # -2%
            "word_spacing": 0.2,      # 0.2em
            "line_spacing": 1.2,      # 1.2x
            "paragraph_spacing": 0.5   # 0.5em
        },
        "normal": {
            "letter_spacing": 0.0,
            "word_spacing": 0.25,
            "line_spacing": 1.5,
            "paragraph_spacing": 1.0
        },
        "generous": {
            "letter_spacing": 0.05,   # +5%
            "word_spacing": 0.3,      # 0.3em
            "line_spacing": 1.8,      # 1.8x
            "paragraph_spacing": 1.5   # 1.5em
        }
    }

    context_spacing = {
        "poster": "normal",      # Posters use normal spacing with larger type
        "book": "normal",
        "magazine": "tight",
        "report": "normal"
    }

    style = context_spacing.get(context, "normal")
    return spacing_map[style]

# ==================== COLOR HELPERS ====================

def get_color_palette(name: str = "professional") -> dict:
    """Get pre-defined color palettes following 70-20-10 rule"""
    palettes = {
        "professional": {
            "background": (0.98, 0.98, 0.97),  # Off-white (70%)
            "text": (0.1, 0.1, 0.1),           # Near black (20%)
            "accent": (0.2, 0.45, 0.7)         # Blue (10%)
        },
        "warm": {
            "background": (0.98, 0.96, 0.94),
            "text": (0.2, 0.15, 0.1),
            "accent": (0.8, 0.4, 0.2)
        },
        "cool": {
            "background": (0.96, 0.97, 0.98),
            "text": (0.1, 0.15, 0.2),
            "accent": (0.2, 0.5, 0.7)
        },
        "high_contrast": {
            "background": (1, 1, 1),
            "text": (0, 0, 0),
            "accent": (0.9, 0.2, 0.2)
        }
    }

    return palettes.get(name, palettes["professional"])

# ==================== QUICK START HELPERS ====================

def setup_poster_page(
    size: str = "letter",
    margin_ratio: float = 1/10,
    orientation: str = "portrait"
) -> Tuple[float, float, float]:
    """
    Set up a poster page with proper dimensions.

    Returns: (width, height, margin)
    """
    sizes = {
        "letter": (612, 792),      # 8.5 x 11 inches
        "tabloid": (792, 1224),    # 11 x 17 inches
        "a4": (595, 842),          # 210 x 297 mm
        "a3": (842, 1191),         # 297 x 420 mm
        "square": (792, 792)       # 11 x 11 inches
    }

    w, h = sizes.get(size, sizes["letter"])

    if orientation == "landscape":
        w, h = h, w

    db.newPage(w, h)
    margin = min(w, h) * margin_ratio

    return w, h, margin

# ==================== COLOR HARMONY ====================

import colorsys
import math

def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
    """Convert hex color (#RRGGBB or RRGGBB) to RGB (0-1 range)."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    return tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))

def rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convert RGB (0-1 range) to hex color (#RRGGBB)."""
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

def adjust_lightness(r: float, g: float, b: float, factor: float) -> Tuple[float, float, float]:
    """
    Adjust lightness of RGB color.

    Args:
        r, g, b: RGB values (0-1 range)
        factor: Lightness adjustment (-1 to 1). Positive = lighter, negative = darker.

    Returns:
        Adjusted RGB tuple (0-1 range)
    """
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    # Adjust lightness, clamping to valid range
    new_l = max(0, min(1, l + factor * (1 - l if factor > 0 else l)))
    return colorsys.hls_to_rgb(h, new_l, s)

def _rotate_hue(r: float, g: float, b: float, degrees: float) -> Tuple[float, float, float]:
    """Rotate hue by given degrees."""
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + degrees / 360) % 1.0
    return colorsys.hls_to_rgb(h, l, s)

def generate_color_palette(
    base_color: Tuple[float, float, float],
    harmony: str = "complementary",
    as_dict: bool = True
) -> Any:
    """
    Generate a color palette based on color harmony theory.

    Args:
        base_color: RGB tuple (0-1 range) as the primary color
        harmony: Type of harmony:
            - "complementary": Base + opposite on color wheel
            - "analogous": Base + adjacent colors (30 degrees apart)
            - "triadic": Base + two colors 120 degrees apart
            - "split_complementary": Base + two colors adjacent to complement
            - "tetradic": Base + 3 colors forming rectangle on wheel
            - "monochromatic": Base + lighter/darker variations
        as_dict: If True, return dict with semantic names. If False, return list.

    Returns:
        Dict with 'background', 'text', 'accent', 'accent2' (and sometimes 'accent3')
        or list of RGB tuples
    """
    r, g, b = base_color

    if harmony == "complementary":
        complement = _rotate_hue(r, g, b, 180)
        colors = [
            adjust_lightness(r, g, b, 0.7),      # Light background from base
            adjust_lightness(r, g, b, -0.6),     # Dark text from base
            base_color,                           # Primary accent
            complement                            # Complementary accent
        ]

    elif harmony == "analogous":
        analog1 = _rotate_hue(r, g, b, 30)
        analog2 = _rotate_hue(r, g, b, -30)
        colors = [
            adjust_lightness(r, g, b, 0.7),
            adjust_lightness(r, g, b, -0.6),
            base_color,
            analog1,
            analog2
        ]

    elif harmony == "triadic":
        triad1 = _rotate_hue(r, g, b, 120)
        triad2 = _rotate_hue(r, g, b, 240)
        colors = [
            adjust_lightness(r, g, b, 0.7),
            adjust_lightness(r, g, b, -0.6),
            base_color,
            triad1,
            triad2
        ]

    elif harmony == "split_complementary":
        split1 = _rotate_hue(r, g, b, 150)
        split2 = _rotate_hue(r, g, b, 210)
        colors = [
            adjust_lightness(r, g, b, 0.7),
            adjust_lightness(r, g, b, -0.6),
            base_color,
            split1,
            split2
        ]

    elif harmony == "tetradic":
        color2 = _rotate_hue(r, g, b, 90)
        color3 = _rotate_hue(r, g, b, 180)
        color4 = _rotate_hue(r, g, b, 270)
        colors = [
            adjust_lightness(r, g, b, 0.7),
            adjust_lightness(r, g, b, -0.6),
            base_color,
            color2,
            color3,
            color4
        ]

    elif harmony == "monochromatic":
        colors = [
            adjust_lightness(r, g, b, 0.7),      # Very light
            adjust_lightness(r, g, b, -0.7),     # Very dark
            base_color,                           # Base
            adjust_lightness(r, g, b, 0.3),      # Light variation
            adjust_lightness(r, g, b, -0.3)      # Dark variation
        ]

    else:
        raise ValueError(f"Unknown harmony type: {harmony}. Use: complementary, analogous, triadic, split_complementary, tetradic, monochromatic")

    if not as_dict:
        return colors

    result = {
        "background": colors[0],
        "text": colors[1],
        "accent": colors[2]
    }
    if len(colors) > 3:
        result["accent2"] = colors[3]
    if len(colors) > 4:
        result["accent3"] = colors[4]
    if len(colors) > 5:
        result["accent4"] = colors[5]

    return result

def _relative_luminance(r: float, g: float, b: float) -> float:
    """Calculate relative luminance per WCAG 2.1."""
    def adjust(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

def check_contrast_ratio(
    foreground: Tuple[float, float, float],
    background: Tuple[float, float, float]
) -> Tuple[float, str]:
    """
    Check WCAG contrast ratio between two colors.

    Args:
        foreground: RGB tuple (0-1 range)
        background: RGB tuple (0-1 range)

    Returns:
        Tuple of (ratio, level) where level is:
        - "AAA" (7:1+): Enhanced contrast, all text sizes
        - "AA" (4.5:1+): Minimum for normal text
        - "AA-large" (3:1+): Minimum for large text (18pt+ or 14pt+ bold)
        - "fail": Does not meet WCAG requirements
    """
    lum1 = _relative_luminance(*foreground)
    lum2 = _relative_luminance(*background)

    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)

    ratio = (lighter + 0.05) / (darker + 0.05)

    if ratio >= 7:
        level = "AAA"
    elif ratio >= 4.5:
        level = "AA"
    elif ratio >= 3:
        level = "AA-large"
    else:
        level = "fail"

    return ratio, level

def get_accessible_text_color(
    background: Tuple[float, float, float],
    prefer_dark: bool = True
) -> Tuple[float, float, float]:
    """
    Get an accessible text color for a given background.

    Args:
        background: RGB tuple (0-1 range)
        prefer_dark: If True, prefer dark text when contrast is similar

    Returns:
        RGB tuple that meets at least WCAG AA contrast
    """
    dark = (0.1, 0.1, 0.1)
    light = (0.98, 0.98, 0.98)

    dark_ratio, _ = check_contrast_ratio(dark, background)
    light_ratio, _ = check_contrast_ratio(light, background)

    if prefer_dark:
        return dark if dark_ratio >= 4.5 else light
    else:
        return light if light_ratio >= 4.5 else dark

# ==================== OPENTYPE & VARIABLE FONTS ====================

# Common OpenType features with descriptions
OPENTYPE_FEATURES = {
    # Ligatures
    'liga': 'Standard ligatures (fi, fl, ff)',
    'dlig': 'Discretionary ligatures',
    'clig': 'Contextual ligatures',
    'rlig': 'Required ligatures',

    # Capitals
    'smcp': 'Small capitals (lowercase to small caps)',
    'c2sc': 'Capitals to small caps',
    'pcap': 'Petite capitals',
    'titl': 'Titling alternates (display caps)',

    # Numbers
    'lnum': 'Lining figures (uppercase-height numerals)',
    'onum': 'Oldstyle figures (varying heights)',
    'pnum': 'Proportional figures',
    'tnum': 'Tabular figures (monospaced numerals)',
    'frac': 'Fractions (1/2 → ½)',
    'ordn': 'Ordinals (1st → 1ˢᵗ)',
    'sups': 'Superscripts',
    'subs': 'Subscripts',

    # Stylistic
    'salt': 'Stylistic alternates',
    'ss01': 'Stylistic set 1',
    'ss02': 'Stylistic set 2',
    'ss03': 'Stylistic set 3',
    'swsh': 'Swash',
    'cswh': 'Contextual swash',

    # Kerning and spacing
    'kern': 'Kerning',
    'cpsp': 'Capital spacing',
    'case': 'Case-sensitive forms',
}

def set_opentype_features(features: List[str], enable: bool = True) -> None:
    """
    Enable or disable OpenType features for subsequent text.

    Args:
        features: List of feature tags, e.g., ['smcp', 'liga', 'onum']
        enable: True to enable, False to disable

    Example:
        set_opentype_features(['smcp', 'onum'])  # Enable small caps + oldstyle figures
        db.text("The Quick Brown Fox 1234", (x, y))

    Common features:
        - 'liga': Standard ligatures (fi, fl)
        - 'smcp': Small capitals
        - 'onum': Oldstyle figures
        - 'tnum': Tabular (monospace) figures
        - 'frac': Automatic fractions (1/2 → ½)
        - 'ss01'-'ss20': Stylistic sets
    """
    for feature in features:
        db.openTypeFeatures(**{feature: enable})

def get_available_opentype_features(font_name: str = None) -> Dict[str, str]:
    """
    Get available OpenType features for current or specified font.

    Args:
        font_name: Font to query (uses current font if None)

    Returns:
        Dict of {feature_tag: description}
    """
    if font_name:
        db.font(font_name)

    try:
        available = db.listOpenTypeFeatures()
        return {f: OPENTYPE_FEATURES.get(f, 'Custom feature') for f in available}
    except Exception:
        return {}

def set_font_variation(axes: Dict[str, float] = None, **kwargs) -> None:
    """
    Set variable font axis values.

    Args:
        axes: Dict of {axis_tag: value}, e.g., {'wght': 700, 'wdth': 75}
        **kwargs: Alternative axis specification, e.g., wght=700, wdth=75

    Example:
        set_font_variation(wght=600, wdth=85)  # Semi-bold, slightly condensed
        db.text("Variable Font Text", (x, y))

    Common axes:
        - wght: Weight (100-900, where 400=regular, 700=bold)
        - wdth: Width (50-200, where 100=normal)
        - slnt: Slant (-90 to 90 degrees)
        - ital: Italic (0=upright, 1=italic)
        - opsz: Optical size (point size for optimization)
    """
    if axes is None:
        axes = {}
    axes.update(kwargs)
    db.fontVariations(**axes)

def get_font_variation_axes(font_name: str = None) -> Dict[str, Dict[str, float]]:
    """
    Get available variable font axes for current or specified font.

    Args:
        font_name: Font to query (uses current font if None)

    Returns:
        Dict of {axis_tag: {'minValue': x, 'defaultValue': y, 'maxValue': z}}
    """
    if font_name:
        db.font(font_name)

    try:
        return db.listFontVariations()
    except Exception:
        return {}

# ==================== PRINT PRODUCTION ====================

# Standard print presets with bleed
PRINT_PRESETS = {
    "letter": {
        "width": 612,       # 8.5 inches
        "height": 792,      # 11 inches
        "bleed": 9,         # 0.125 inches (standard bleed)
        "safe_margin": 36,  # 0.5 inches from trim
    },
    "tabloid": {
        "width": 792,       # 11 inches
        "height": 1224,     # 17 inches
        "bleed": 9,
        "safe_margin": 36,
    },
    "a4": {
        "width": 595,       # 210 mm
        "height": 842,      # 297 mm
        "bleed": 8.5,       # 3 mm (standard metric bleed)
        "safe_margin": 28,  # 10 mm from trim
    },
    "a3": {
        "width": 842,       # 297 mm
        "height": 1191,     # 420 mm
        "bleed": 8.5,
        "safe_margin": 28,
    },
    "poster_24x36": {
        "width": 1728,      # 24 inches
        "height": 2592,     # 36 inches
        "bleed": 18,        # 0.25 inches
        "safe_margin": 72,  # 1 inch
    },
}

def setup_print_page(
    size: str = "letter",
    orientation: str = "portrait",
    include_bleed: bool = True,
    custom_bleed: float = None
) -> Dict[str, float]:
    """
    Set up a print-ready page with bleed area.

    Args:
        size: Paper size from PRINT_PRESETS or custom (width, height) tuple
        orientation: "portrait" or "landscape"
        include_bleed: Whether to extend canvas for bleed
        custom_bleed: Override default bleed (in points)

    Returns:
        Dict with 'width', 'height', 'bleed', 'safe_margin',
        'trim_x', 'trim_y' (offset to trim edge from canvas edge)

    Example:
        specs = setup_print_page("letter", include_bleed=True)
        # Draw background to full canvas (includes bleed)
        db.fill(0.2, 0.4, 0.8)
        db.rect(0, 0, specs['canvas_width'], specs['canvas_height'])
        # Position content relative to trim edge
        x = specs['trim_x'] + specs['safe_margin']
    """
    if isinstance(size, tuple):
        preset = {
            "width": size[0],
            "height": size[1],
            "bleed": custom_bleed or 9,
            "safe_margin": 36
        }
    else:
        preset = PRINT_PRESETS.get(size, PRINT_PRESETS["letter"]).copy()

    if custom_bleed is not None:
        preset["bleed"] = custom_bleed

    width = preset["width"]
    height = preset["height"]
    bleed = preset["bleed"] if include_bleed else 0

    if orientation == "landscape":
        width, height = height, width

    canvas_width = width + (bleed * 2)
    canvas_height = height + (bleed * 2)

    db.newPage(canvas_width, canvas_height)

    return {
        "width": width,              # Trim width
        "height": height,            # Trim height
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
        "bleed": bleed,
        "safe_margin": preset["safe_margin"],
        "trim_x": bleed,             # X offset from canvas to trim
        "trim_y": bleed,             # Y offset from canvas to trim
    }

def validate_print_ready(
    filepath: str = None,
    check_bleed: bool = True,
    check_resolution: bool = True,
    min_dpi: int = 300
) -> Tuple[bool, List[str]]:
    """
    Validate a design for print production.

    Args:
        filepath: Path to check (uses current document if None)
        check_bleed: Verify bleed area is utilized
        check_resolution: Check image resolution
        min_dpi: Minimum acceptable DPI for images

    Returns:
        Tuple of (is_valid, list of warnings/errors)

    Note: This performs basic checks. For full preflight,
    use professional tools like Adobe Acrobat Pro.
    """
    warnings = []

    # Check page dimensions
    try:
        w = db.width()
        h = db.height()

        # Check for reasonable print dimensions
        if w < 72 or h < 72:
            warnings.append(f"Page too small for print: {w:.0f}x{h:.0f}pt")

        if w > 5184 or h > 5184:  # 72 inches
            warnings.append(f"Page very large: {w:.0f}x{h:.0f}pt - verify print capability")
    except Exception:
        warnings.append("Could not read page dimensions")

    # Check color space (CMYK recommended for print)
    # Note: DrawBot defaults to RGB, CMYK requires explicit setup
    warnings.append("Reminder: Use cmykFill()/cmykStroke() for print production")

    # General print recommendations
    recommendations = [
        "Verify fonts are embedded or outlined",
        "Check images are 300+ DPI at final size",
        "Ensure important content is within safe margin",
        "Background elements should extend to bleed edge",
    ]

    is_valid = len([w for w in warnings if "too small" in w or "Could not" in w]) == 0

    return is_valid, warnings + recommendations

# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    # Example: Create a poster with proper system
    width, height, margin = setup_poster_page("letter", margin_ratio=1/10)

    # Get typography scale
    scale = POSTER_SCALE

    # Get spacing
    spacing = get_spacing_for_context("poster")

    # Get colors
    colors = get_color_palette("professional")

    print(f"Page: {width} x {height}pt")
    print(f"Margin: {margin}pt")
    print(f"Typography scale: {scale}")
    print(f"Spacing: {spacing}")
    print(f"Colors: {colors}")

    # Example: Validate layout
    elements = [
        {'y': height - margin, 'height': 100, 'name': 'Header'},
        {'y': height - margin - 120, 'height': 300, 'name': 'Hero Section'},
        {'y': 200, 'height': 150, 'name': 'Footer'}
    ]

    fits, error = validate_layout_fit(elements, height)
    print(f"Layout fits: {fits}")
    if error:
        print(f"Error: {error}")
