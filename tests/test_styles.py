import re
import unittest
from pathlib import Path


class StyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        css_path = Path(__file__).resolve().parent.parent / 'foosbam' / 'static' / 'css' / 'foosbam.css'
        cls.css = css_path.read_text(encoding='utf-8')
        templates_dir = Path(__file__).resolve().parent.parent / 'foosbam' / 'templates' / 'core'
        cls.result_templates = (
            (templates_dir / 'show_results.html').read_text(encoding='utf-8'),
            (templates_dir / 'user.html').read_text(encoding='utf-8'),
        )

    def test_light_mode_keeps_original_bulma_highlight(self):
        light_mode_css = self.css.split('@media (prefers-color-scheme: dark)', maxsplit=1)[0]
        self.assertNotIn('.kruipen-row', light_mode_css)
        for template in self.result_templates:
            self.assertIn('class="has-background-danger-light kruipen-row"', template)

    def test_dark_mode_styles_filter_and_table_links(self):
        self.assertIn('@media (prefers-color-scheme: dark)', self.css)
        dark_mode_css = self.css.split('@media (prefers-color-scheme: dark)', maxsplit=1)[1]

        self.assertRegex(
            dark_mode_css,
            r'\.kruipen-filter\s*\{[^}]*background:\s*#363636;[^}]*color:\s*#fff;',
        )
        self.assertRegex(
            dark_mode_css,
            r'\.table a,[^{]*\{[^}]*color:\s*#a8c7fa;',
        )
        self.assertRegex(
            dark_mode_css,
            r'\.kruipen-row\s*\{[^}]*background:\s*#4a2630\s*!important;[^}]*color:\s*#f5e9ec\s*!important;',
        )
        self.assertRegex(
            dark_mode_css,
            r'\.table \.kruipen-row a:link,\s*\.table \.kruipen-row a:visited\s*\{[^}]*color:\s*#a8c7fa\s*!important;[^}]*font-weight:\s*600;',
        )
        self.assertRegex(
            dark_mode_css,
            r'\.table \.kruipen-row a:focus-visible\s*\{[^}]*outline:\s*2px solid currentColor;',
        )
        self.assertNotIn('text-decoration: underline;', dark_mode_css)
