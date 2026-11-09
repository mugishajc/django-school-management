"""
Term reports: per-student report cards and class rankings.

Ranking uses standard competition ranking, so two students tied on the same
average share a position and the next student skips ahead (1, 2, 2, 4).
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg, Count, Max, Min, Q

from .grading import letter_for
from .models import AcademicTerm, Enrollment, Grade, SchoolClass, Student

TWO_PLACES = Decimal("0.01")


def _round(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class RankedStudent:
    student_id: int
    admission_number: str
    name: str
    subjects_graded: int
    average: Decimal | None
    position: int | None = None

    @property
    def letter(self) -> str:
        return letter_for(self.average)


@dataclass
class SubjectLine:
    subject_id: int
    code: str
    name: str
    score: Decimal
    letter: str
    remarks: str = ""


@dataclass
class TermReport:
    student: Student
    term: AcademicTerm
    school_class: SchoolClass | None
    subjects: list[SubjectLine] = field(default_factory=list)
    total: Decimal | None = None
    average: Decimal | None = None
    position: int | None = None
    class_size: int = 0

    @property
    def letter(self) -> str:
        return letter_for(self.average)


def enrollment_for_term(student: Student, term: AcademicTerm) -> Enrollment | None:
    """The class the student sat in during the term's academic year."""
    return (
        Enrollment.objects.select_related("school_class")
        .filter(student=student, school_class__year=term.year)
        .order_by("status")  # "active" sorts before "withdrawn"
        .first()
    )


def _term_filter(term: AcademicTerm) -> Q:
    return Q(grades__term=term)


def class_ranking(school_class: SchoolClass, term: AcademicTerm) -> list[RankedStudent]:
    rows = (
        Enrollment.objects.filter(school_class=school_class, status=Enrollment.Status.ACTIVE)
        .select_related("student__user")
        .annotate(
            subjects_graded=Count("grades", filter=_term_filter(term)),
            average=Avg("grades__score", filter=_term_filter(term)),
        )
    )

    ranked = [
        RankedStudent(
            student_id=row.student_id,
            admission_number=row.student.admission_number,
            name=row.student.user.get_full_name() or row.student.user.username,
            subjects_graded=row.subjects_graded,
            average=_round(row.average),
        )
        for row in rows
    ]
    # Students without grades go to the bottom unranked.
    ranked.sort(key=lambda r: (r.average is None, -(r.average or 0), r.admission_number))

    position = 0
    previous = None
    for index, entry in enumerate(ranked, start=1):
        if entry.average is None:
            break
        if entry.average != previous:
            position = index
            previous = entry.average
        entry.position = position
    return ranked


def subject_statistics(school_class: SchoolClass, term: AcademicTerm) -> list[dict]:
    stats = (
        Grade.objects.filter(
            enrollment__school_class=school_class,
            enrollment__status=Enrollment.Status.ACTIVE,
            term=term,
        )
        .values("subject_id", "subject__code", "subject__name")
        .annotate(mean=Avg("score"), highest=Max("score"), lowest=Min("score"), graded=Count("id"))
        .order_by("subject__code")
    )
    return [
        {
            "subject": row["subject_id"],
            "code": row["subject__code"],
            "name": row["subject__name"],
            # Decimals as strings, matching how DRF renders the other score fields.
            "mean": str(_round(row["mean"])),
            "highest": str(_round(row["highest"])),
            "lowest": str(_round(row["lowest"])),
            "graded": row["graded"],
        }
        for row in stats
    ]


def term_report(student: Student, term: AcademicTerm) -> TermReport:
    enrollment = enrollment_for_term(student, term)
    report = TermReport(student=student, term=term, school_class=None)
    if enrollment is None:
        return report

    report.school_class = enrollment.school_class
    grades = (
        Grade.objects.filter(enrollment=enrollment, term=term)
        .select_related("subject")
        .order_by("subject__code")
    )
    report.subjects = [
        SubjectLine(
            subject_id=g.subject_id,
            code=g.subject.code,
            name=g.subject.name,
            score=g.score,
            letter=letter_for(g.score),
            remarks=g.remarks,
        )
        for g in grades
    ]
    if report.subjects:
        total = sum((line.score for line in report.subjects), Decimal("0"))
        report.total = _round(total)
        report.average = _round(total / len(report.subjects))

    ranking = class_ranking(enrollment.school_class, term)
    report.class_size = len(ranking)
    for entry in ranking:
        if entry.student_id == student.pk:
            report.position = entry.position
            break
    return report
