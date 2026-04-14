"""
Tests for drawbot_design_system.py

Uses a mock DrawBot to test wrapping and layout validation without requiring
the actual DrawBot package (macOS only).
"""

import sys
from pathlib import Path

import pytest

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

import drawbot_backend as backend


# ==================== MOCK DRAWBOT ====================

class MockDrawBot:
    """Mock DrawBot for testing without macOS dependency."""

    def __init__(self):
        self._font = "Helvetica"
        self._size = 12
        # Approximate character widths (monospace-ish for predictability)
        self._char_width_ratio = 0.6  # width = size * ratio per char

    def font(self, name):
        self._font = name

    def fontSize(self, size):
        self._size = size

    def textSize(self, text):
        """Return (width, height) based on character count."""
        width = len(text) * self._size * self._char_width_ratio
        height = self._size
        return (width, height)

    def fontAscender(self):
        return self._size * 0.8

    def fontDescender(self):
        return -self._size * 0.2  # Negative, as it should be

    def fontLineHeight(self):
        return self._size * 1.2

    def fontXHeight(self):
        return self._size * 0.5

    def fontCapHeight(self):
        return self._size * 0.7

    def newPage(self, w, h):
        pass

    def text(self, txt, pos):
        pass


@pytest.fixture
def mock_db():
    """Provide a mock DrawBot instance."""
    return MockDrawBot()


@pytest.fixture(autouse=True)
def reset_backend_state(monkeypatch):
    backend._backend_cache.clear()
    backend._resolved_backend_cache = None
    monkeypatch.delenv(backend.DRAWBOT_BACKEND_ENV_VAR, raising=False)


@pytest.fixture
def patched_design_system(mock_db):
    """Import design system with mocked DrawBot backend."""
    backend._backend_cache[backend.NATIVE_BACKEND] = mock_db
    backend._resolved_backend_cache = None

    if 'drawbot_design_system' in sys.modules:
        del sys.modules['drawbot_design_system']

    import drawbot_design_system as ds
    yield ds


# ==================== TYPOGRAPHY SCALE TESTS ====================

def test_typography_scale_creation(patched_design_system):
    """Test that typography scales are created correctly."""
    ds = patched_design_system

    scale = ds.create_typography_scale(base=12, ratio=1.5)

    assert scale.body == 12
    assert scale.caption == 12 / 1.5
    assert scale.h3 == 12 * 1.5
    assert scale.h2 == 12 * 1.5 ** 2
    assert scale.h1 == 12 * 1.5 ** 3
    assert scale.title == 12 * 1.5 ** 4


def test_predefined_scales_exist(patched_design_system):
    """Test that predefined scales are available."""
    ds = patched_design_system

    assert ds.POSTER_SCALE.body == 18
    assert ds.MAGAZINE_SCALE.body == 11
    assert ds.BOOK_SCALE.body == 11
    assert ds.REPORT_SCALE.body == 12


# ==================== TEXT WRAPPING TESTS ====================

def test_wrap_text_simple(patched_design_system, mock_db):
    """Test basic text wrapping."""
    ds = patched_design_system

    # With size=12 and ratio=0.6, each char is 7.2pt wide
    # "hello world" = 11 chars = 79.2pt
    # Width of 50pt should force a break

    lines = ds.wrap_text_to_width("hello world", 50, "Helvetica", 12)

    assert len(lines) == 2
    assert lines[0] == "hello"
    assert lines[1] == "world"


def test_wrap_text_no_break_needed(patched_design_system, mock_db):
    """Test that short text doesn't break unnecessarily."""
    ds = patched_design_system

    # "hi" = 2 chars = 14.4pt, fits in 100pt easily
    lines = ds.wrap_text_to_width("hi", 100, "Helvetica", 12)

    assert len(lines) == 1
    assert lines[0] == "hi"


def test_wrap_empty_text(patched_design_system, mock_db):
    """Test wrapping empty string."""
    ds = patched_design_system

    lines = ds.wrap_text_to_width("", 100, "Helvetica", 12)

    assert lines == []


def test_break_long_word_returns_all_chunks(patched_design_system, mock_db):
    """Test that _break_long_word doesn't discard the tail."""
    ds = patched_design_system

    # Long word that needs multiple breaks
    # Each char is 7.2pt at size 12
    # "abcdefghij" = 10 chars = 72pt
    # With max_width=30pt, should break into chunks

    chunks = ds._break_long_word("abcdefghij", 30, "Helvetica", 12)

    # Should get multiple chunks
    assert len(chunks) > 1

    # Reconstruct original (removing hyphens)
    reconstructed = "".join(c.rstrip("-") for c in chunks)
    assert reconstructed == "abcdefghij", "Long word tail was discarded!"


def test_long_url_preserved(patched_design_system, mock_db):
    """Test that long URLs are fully preserved across line breaks."""
    ds = patched_design_system

    url = "https://example.com/very/long/path/to/resource"

    # Wrap with narrow width to force breaks
    lines = ds.wrap_text_to_width(url, 50, "Helvetica", 12)

    # Reconstruct and verify nothing was lost
    reconstructed = "".join(line.rstrip("-") for line in lines)
    assert reconstructed == url, f"URL was truncated! Got: {reconstructed}"


# ==================== LAYOUT VALIDATION TESTS ====================

def test_validate_layout_fit_success(patched_design_system):
    """Test layout validation with valid non-overlapping elements."""
    ds = patched_design_system

    elements = [
        {'y': 700, 'height': 100, 'name': 'Header'},
        {'y': 500, 'height': 150, 'name': 'Content'},
        {'y': 200, 'height': 100, 'name': 'Footer'}
    ]

    fits, error = ds.validate_layout_fit(elements, page_height=800)

    assert fits is True
    assert error is None


def test_validate_layout_overlap_detected(patched_design_system):
    """Test that overlapping elements are detected."""
    ds = patched_design_system

    elements = [
        {'y': 700, 'height': 250, 'name': 'Header'},  # Extends to 450
        {'y': 500, 'height': 100, 'name': 'Content'}  # Starts at 500, overlaps!
    ]

    fits, error = ds.validate_layout_fit(elements, page_height=800)

    assert fits is False
    assert "overlaps" in error.lower()


def test_validate_layout_extends_above_page(patched_design_system):
    """Test detection of elements above page bounds."""
    ds = patched_design_system

    elements = [
        {'y': 900, 'height': 100, 'name': 'Header'}  # y > page_height
    ]

    fits, error = ds.validate_layout_fit(elements, page_height=800)

    assert fits is False
    assert "above" in error.lower()


def test_validate_layout_extends_below_page(patched_design_system):
    """Test detection of elements below page bounds."""
    ds = patched_design_system

    elements = [
        {'y': 50, 'height': 100, 'name': 'Footer'}  # Extends to -50
    ]

    fits, error = ds.validate_layout_fit(elements, page_height=800)

    assert fits is False
    assert "below" in error.lower()


def test_validate_empty_layout(patched_design_system):
    """Test that empty layout is valid."""
    ds = patched_design_system

    fits, error = ds.validate_layout_fit([], page_height=800)

    assert fits is True
    assert error is None


# ==================== METRICS TESTS ====================

def test_descender_is_negative(patched_design_system, mock_db):
    """Test that descender values are negative (below baseline)."""
    ds = patched_design_system

    metrics = ds.get_text_metrics("test", "Helvetica", 12)

    assert metrics['descender'] < 0, "Descender should be negative"


def test_get_text_metrics_structure(patched_design_system, mock_db):
    """Test that get_text_metrics returns all expected keys."""
    ds = patched_design_system

    metrics = ds.get_text_metrics("test", "Helvetica", 12)

    expected_keys = ['width', 'height', 'ascender', 'descender',
                     'line_height', 'x_height', 'cap_height']
    for key in expected_keys:
        assert key in metrics, f"Missing key: {key}"


# ==================== PATH TESTS ====================

def test_output_path_is_absolute(patched_design_system):
    """Test that get_output_path returns absolute paths."""
    ds = patched_design_system

    path = ds.get_output_path("test.pdf")

    assert path.is_absolute()
    assert path.name == "test.pdf"


def test_repo_root_exists(patched_design_system):
    """Test that REPO_ROOT points to actual directory."""
    ds = patched_design_system

    assert ds.REPO_ROOT.exists()
    assert ds.REPO_ROOT.is_dir()
