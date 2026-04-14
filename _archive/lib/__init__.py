"""
DrawBot Design System - Professional typography and layout enforcement.

Usage:
    from lib.drawbot_design_system import (
        POSTER_SCALE, setup_poster_page, draw_wrapped_text, get_output_path
    )
    from lib.drawbot_grid import Grid
"""

from .drawbot_design_system import (
    # Path management
    REPO_ROOT,
    OUTPUT_DIR,
    get_output_path,
    # Typography scales
    TypographyScale,
    POSTER_SCALE,
    MAGAZINE_SCALE,
    BOOK_SCALE,
    REPORT_SCALE,
    create_typography_scale,
    # Scale ratios
    MINOR_SECOND,
    MAJOR_SECOND,
    MINOR_THIRD,
    MAJOR_THIRD,
    PERFECT_FOURTH,
    PERFECT_FIFTH,
    GOLDEN_RATIO,
    # Text functions
    get_text_metrics,
    wrap_text_to_width,
    draw_wrapped_text,
    # Layout
    validate_layout_fit,
    setup_poster_page,
    # Helpers
    get_spacing_for_context,
    get_color_palette,
)

from .drawbot_grid import (
    Grid,
    ColumnGrid,
    RowGrid,
    BaselineGrid,
    create_page_grid,
)

__all__ = [
    # Design system
    'REPO_ROOT', 'OUTPUT_DIR', 'get_output_path',
    'TypographyScale', 'POSTER_SCALE', 'MAGAZINE_SCALE', 'BOOK_SCALE', 'REPORT_SCALE',
    'create_typography_scale',
    'MINOR_SECOND', 'MAJOR_SECOND', 'MINOR_THIRD', 'MAJOR_THIRD',
    'PERFECT_FOURTH', 'PERFECT_FIFTH', 'GOLDEN_RATIO',
    'get_text_metrics', 'wrap_text_to_width', 'draw_wrapped_text',
    'validate_layout_fit', 'setup_poster_page',
    'get_spacing_for_context', 'get_color_palette',
    # Grid
    'Grid', 'ColumnGrid', 'RowGrid', 'BaselineGrid', 'create_page_grid',
]
