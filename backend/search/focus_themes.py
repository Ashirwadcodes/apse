"""Editorially curated search rules for APTG focus themes.

Focus themes are intentionally separate from the ISO ICS taxonomy. A theme can
span several sectors and is matched against the record title, provider
keywords/category, description, and normalized ISO sector classification.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from backend.taxonomy.iso_ics import SectorClassification


@dataclass(frozen=True)
class FocusTheme:
    id: str
    label: str
    short_label: str
    sector_codes: tuple[str, ...]
    terms: tuple[str, ...]
    excluded_terms: tuple[str, ...] = ()
    required_context_terms: tuple[str, ...] = ()
    minimum_score: int = 6


FOCUS_THEMES: dict[str, FocusTheme] = {
    "energy-transition": FocusTheme(
        id="energy-transition",
        label="Energy transition and renewable technologies",
        short_label="Energy transition",
        sector_codes=("27", "29", "31"),
        terms=(
            "renewable energy",
            "clean energy",
            "energy transition",
            "solar",
            "photovoltaic",
            "wind energy",
            "wind turbine",
            "geothermal",
            "hydropower",
            "hydroelectric",
            "green hydrogen",
            "bioenergy",
            "biofuel",
            "biogas",
            "biomass",
            "battery",
            "energy storage",
            "smart grid",
            "microgrid",
            "energy efficiency",
            "heat pump",
            "decarbonization",
            "decarbonisation",
        ),
        excluded_terms=("petroleum exploration", "coal mining"),
    ),
    "climate-resilient-cities": FocusTheme(
        id="climate-resilient-cities",
        label="Climate-resilient infrastructure in cities",
        short_label="Climate-resilient cities",
        sector_codes=("13", "23", "27", "91", "93"),
        terms=(
            "climate resilience",
            "climate resilient",
            "climate adaptation",
            "urban resilience",
            "resilient infrastructure",
            "sustainable city",
            "sustainable cities",
            "smart city",
            "urban infrastructure",
            "urban planning",
            "flood resilience",
            "flood control",
            "stormwater",
            "urban drainage",
            "heat island",
            "urban cooling",
            "disaster risk reduction",
            "disaster resilient",
            "resilient building",
            "green building",
            "nature based solution",
        ),
        excluded_terms=("military infrastructure",),
        required_context_terms=(
            "city",
            "cities",
            "urban",
            "infrastructure",
            "building",
            "housing",
            "flood",
            "stormwater",
            "drainage",
            "heat island",
            "urban cooling",
            "disaster",
            "seismic",
        ),
    ),
    "digital-4ir": FocusTheme(
        id="digital-4ir",
        label="Digital and Fourth Industrial Revolution technologies",
        short_label="Digital & 4IR",
        sector_codes=("25", "31", "33", "35", "37"),
        terms=(
            "fourth industrial revolution",
            "4ir",
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "internet of things",
            "iot",
            "robotics",
            "robotic",
            "automation",
            "digital twin",
            "blockchain",
            "cloud computing",
            "edge computing",
            "cybersecurity",
            "cyber security",
            "big data",
            "computer vision",
            "additive manufacturing",
            "3d printing",
            "smart manufacturing",
            "industry 4.0",
            "remote sensing",
            "sensor network",
        ),
        excluded_terms=("digital printing ink",),
    ),
    "pollution-control": FocusTheme(
        id="pollution-control",
        label="Pollution prevention and control technologies",
        short_label="Pollution control",
        sector_codes=("13", "23", "71", "83"),
        terms=(
            "pollution prevention",
            "pollution control",
            "air pollution",
            "water pollution",
            "soil pollution",
            "emission control",
            "emissions reduction",
            "air quality",
            "wastewater",
            "waste water",
            "effluent treatment",
            "waste treatment",
            "waste management",
            "recycling",
            "plastic waste",
            "remediation",
            "bioremediation",
            "filtration",
            "scrubber",
            "carbon capture",
            "particulate removal",
            "oil spill",
            "hazardous waste",
        ),
        excluded_terms=("noise cancelling entertainment",),
    ),
}


def get_focus_theme(theme_id: str | None) -> FocusTheme | None:
    return FOCUS_THEMES.get((theme_id or "").strip().lower())


def focus_theme_options() -> list[dict[str, str]]:
    return [
        {"id": theme.id, "label": theme.label, "short_label": theme.short_label}
        for theme in FOCUS_THEMES.values()
    ]


def score_focus_record(
    record: dict,
    classification: SectorClassification,
    theme: FocusTheme,
) -> tuple[bool, int]:
    """Return whether a record belongs to a focus theme and its rank score.

    Scoring is deliberately reviewable and deterministic:
    title +8, provider keywords/category +6, ISO sector +4, description +2,
    and explicit negative evidence -6. A score of six is required, which
    prevents a broad sector or a lone description mention from qualifying by
    itself while allowing sector + description evidence to combine.
    """

    title = _normalize(record.get("title", ""))
    summary = _normalize(record.get("summary", ""))
    keywords = _normalize(" ".join(str(value) for value in record.get("keywords", [])))
    category = _normalize(
        " ".join(
            str(record.get(key, ""))
            for key in ("sector", "category", "source_sector", "programme")
        )
        + " "
        + classification.source_sector
    )

    sector_match = any(
        _sector_matches(code, theme.sector_codes) for code in classification.codes
    )
    score = 0
    if _matches_any(title, theme.terms):
        score += 8
    if _matches_any(keywords, theme.terms):
        score += 6
    if _matches_any(category, theme.terms):
        score += 6
    if sector_match:
        score += 4
    if _matches_any(summary, theme.terms):
        score += 2

    combined = " ".join((title, summary, keywords, category))
    if _matches_any(combined, theme.excluded_terms):
        score -= 6

    if theme.required_context_terms:
        has_required_context = sector_match or _matches_any(
            combined, theme.required_context_terms
        )
        if not has_required_context:
            return False, score

    return score >= theme.minimum_score, score


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _matches_any(text: str, terms: tuple[str, ...]) -> bool:
    if not text or not terms:
        return False
    padded = f" {text} "
    return any(f" {_normalize(term)} " in padded for term in terms)


def _sector_matches(record_code: str, theme_codes: tuple[str, ...]) -> bool:
    return any(
        record_code == theme_code or record_code.startswith(f"{theme_code}.")
        for theme_code in theme_codes
    )
