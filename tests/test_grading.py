from decimal import Decimal

import pytest
from django.db import IntegrityError

from school.grading import letter_for
from school.models import Grade


@pytest.mark.parametrize(
    "score,letter",
    [(100, "A"), (80, "A"), (79.99, "B"), (70, "B"), (65, "C"), (50, "D"), (40, "E"), (0, "F")],
)
def test_letter_bands(score, letter):
    assert letter_for(score) == letter


def test_letter_for_none_is_blank():
    assert letter_for(None) == ""


def test_score_must_be_within_range(make_student, math, term):
    student = make_student("S001")
    with pytest.raises(IntegrityError):
        Grade.objects.create(
            enrollment=student.enrollments.get(), subject=math, term=term, score=Decimal("101")
        )


def test_one_grade_per_subject_per_term(make_student, math, grade):
    student = make_student("S001")
    grade(student, math, 60)
    with pytest.raises(IntegrityError):
        grade(student, math, 70)
