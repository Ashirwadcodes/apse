import unittest

from backend.search.focus_themes import (
    FOCUS_THEMES,
    get_focus_theme,
    score_focus_record,
)
from backend.taxonomy.iso_ics import SectorClassification


def classification(*codes: str, source_sector: str = "") -> SectorClassification:
    return SectorClassification(
        source_sector=source_sector,
        codes=tuple(codes),
        labels=tuple(codes),
        method="test",
        confidence="high",
    )


class FocusThemeTests(unittest.TestCase):
    def test_four_editorial_themes_have_stable_ids(self):
        self.assertEqual(
            tuple(FOCUS_THEMES),
            (
                "energy-transition",
                "climate-resilient-cities",
                "digital-4ir",
                "pollution-control",
            ),
        )

    def test_title_keyword_is_sufficient(self):
        match, score = score_focus_record(
            {
                "title": "Low-cost solar dryer for farmer cooperatives",
                "summary": "",
                "keywords": [],
            },
            classification("65"),
            get_focus_theme("energy-transition"),
        )

        self.assertTrue(match)
        self.assertGreaterEqual(score, 8)

    def test_broad_sector_alone_is_not_sufficient(self):
        match, score = score_focus_record(
            {
                "title": "General electrical connector",
                "summary": "Industrial component",
                "keywords": [],
            },
            classification("29"),
            get_focus_theme("energy-transition"),
        )

        self.assertFalse(match)
        self.assertEqual(score, 4)

    def test_sector_and_description_evidence_combine(self):
        match, score = score_focus_record(
            {
                "title": "Modular municipal treatment unit",
                "summary": "A compact wastewater solution for dense communities.",
                "keywords": [],
            },
            classification("23"),
            get_focus_theme("pollution-control"),
        )

        self.assertTrue(match)
        self.assertEqual(score, 6)

    def test_short_terms_match_words_not_substrings(self):
        match, _ = score_focus_record(
            {
                "title": "Painting system for small manufacturers",
                "summary": "A conventional coating process.",
                "keywords": [],
            },
            classification("87"),
            get_focus_theme("digital-4ir"),
        )

        self.assertFalse(match)

    def test_climate_resilient_agriculture_is_not_city_infrastructure(self):
        match, _ = score_focus_record(
            {
                "title": "Climate-resilient rice variety",
                "summary": "A drought tolerant crop for farmers.",
                "keywords": ["climate resilience"],
            },
            classification("65"),
            get_focus_theme("climate-resilient-cities"),
        )

        self.assertFalse(match)


if __name__ == "__main__":
    unittest.main()
