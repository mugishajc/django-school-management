"""Grading scale shared by the models, serializers and reports."""

from decimal import Decimal

# (minimum score, letter), checked from the top down.
GRADE_BANDS: list[tuple[Decimal, str]] = [
    (Decimal("80"), "A"),
    (Decimal("70"), "B"),
    (Decimal("60"), "C"),
    (Decimal("50"), "D"),
    (Decimal("40"), "E"),
    (Decimal("0"), "F"),
]


def letter_for(score) -> str:
    if score is None:
        return ""
    value = Decimal(str(score))
    for minimum, letter in GRADE_BANDS:
        if value >= minimum:
            return letter
    return "F"
