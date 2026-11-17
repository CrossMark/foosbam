import re
import unittest
from pathlib import Path


class StyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        css_path = Path(__file__).resolve().parent.parent / 'foosbam' / 'static' / 'css' / 'foosbam.css'
        cls.css = css_path.read_text(encoding='utf-8')

    def test_kruipen_rows_keep_light_red_background_and_black_text(self):
        self.assertRegex(self.css, r'\.kruipen-row\s*\{[^}]*background:\s*#feecf0\s*!important;')
        self.assertRegex(self.css, r'\.kruipen-row th,[^{]*\{[^}]*color:\s*#000\s*!important;')

    def test_dark_mode_styles_filter_and_table_links(self):
        self.assertIn('@media (prefers-color-scheme: dark)', self.css)
        dark_mode_css = self.css.split('@media (prefers-color-scheme: dark)', maxsplit=1)[1]

        self.assertRegex(
            dark_mode_css,
            r'\.kruipen-filter\s*\{[^}]*background:\s*#363636;[^}]*color:\s*#fff;',
        )
        self.assertRegex(
            dark_mode_css,
            r'\.table a,[^{]*\{[^}]*color:\s*#8ab4ff;',
        )
        self.assertRegex(
            dark_mode_css,
            r'\.kruipen-row a\s*\{[^}]*color:\s*#000\s*!important;',
        )
