#!/usr/bin/env python3
"""Tests for serve.py security features.

Validates the URL-decode-aware extension deny list (C-1 fix).
"""
import sys
import unittest
from pathlib import Path

# Ensure serve.py's directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from serve import _is_denied_path  # noqa: E402


class TestIsDeniedPath(unittest.TestCase):
    """Test _is_denied_path handles URL-encoded bypass attempts."""

    # --- Baseline: plain extensions ---

    def test_pem_denied(self) -> None:
        self.assertTrue(_is_denied_path('/key.pem'))

    def test_py_denied(self) -> None:
        self.assertTrue(_is_denied_path('/serve.py'))

    def test_html_allowed(self) -> None:
        self.assertFalse(_is_denied_path('/qr-generator.html'))

    def test_root_allowed(self) -> None:
        self.assertFalse(_is_denied_path('/'))

    def test_no_extension_allowed(self) -> None:
        self.assertFalse(_is_denied_path('/README'))

    # --- C-1: URL-encoded dot bypass ---

    def test_url_encoded_dot_uppercase(self) -> None:
        """C-1: %2E (uppercase) must be decoded before check."""
        self.assertTrue(_is_denied_path('/key%2Epem'))

    def test_url_encoded_dot_lowercase(self) -> None:
        """C-1: %2e (lowercase) must be decoded before check."""
        self.assertTrue(_is_denied_path('/key%2epem'))

    def test_url_encoded_py(self) -> None:
        """C-1: serve%2Epy must be denied."""
        self.assertTrue(_is_denied_path('/serve%2Epy'))

    def test_url_encoded_full_extension(self) -> None:
        """Entire .pem encoded as %2E%70%65%6D."""
        self.assertTrue(_is_denied_path('/key%2E%70%65%6D'))

    # --- Path normalization bypass ---

    def test_trailing_dot_slash(self) -> None:
        """Path /key.pem/. normalizes to /key.pem — must be denied."""
        self.assertTrue(_is_denied_path('/key.pem/.'))

    def test_trailing_dot_slash_dir(self) -> None:
        """Path /key.pem/./ normalizes to /key.pem — must be denied."""
        self.assertTrue(_is_denied_path('/key.pem/./'))

    def test_parent_traversal_to_pem(self) -> None:
        """Path /subdir/../key.pem normalizes to /key.pem — must be denied."""
        self.assertTrue(_is_denied_path('/subdir/../key.pem'))

    # --- Query string and fragment stripping ---

    def test_query_string_stripped(self) -> None:
        self.assertTrue(_is_denied_path('/key.pem?foo=bar'))

    def test_fragment_stripped(self) -> None:
        self.assertTrue(_is_denied_path('/key.pem#section'))

    def test_query_and_fragment(self) -> None:
        self.assertTrue(_is_denied_path('/key.pem?a=1#top'))

    # --- Case insensitivity ---

    def test_uppercase_extension(self) -> None:
        self.assertTrue(_is_denied_path('/key.PEM'))

    def test_mixed_case(self) -> None:
        self.assertTrue(_is_denied_path('/serve.Py'))

    # --- Path components ---

    def test_subdirectory_denied(self) -> None:
        self.assertTrue(_is_denied_path('/subdir/key.pem'))

    def test_traversal_denied(self) -> None:
        self.assertTrue(_is_denied_path('/../key.pem'))

    # --- Double encoding (should NOT match — not a bypass) ---

    def test_double_encoded_not_denied(self) -> None:
        """Double encoding (%252E) decodes to literal '%2E', not a dot.

        SimpleHTTPRequestHandler also only decodes once, so looking up
        a file named 'key%2Epem' which does not exist.
        """
        self.assertFalse(_is_denied_path('/key%252Epem'))


if __name__ == '__main__':
    unittest.main()
