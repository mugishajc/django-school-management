from decimal import Decimal

from school.reports import class_ranking, subject_statistics, term_report


def test_term_report_totals_and_average(make_student, math, english, term, grade):
    student = make_student("S001", "Aline")
    grade(student, math, 82)
    grade(student, english, 67.5)

    report = term_report(student, term)

    assert [line.code for line in report.subjects] == ["ENG", "MATH"]
    assert report.total == Decimal("149.50")
    assert report.average == Decimal("74.75")
    assert report.letter == "B"
    assert report.position == 1
    assert report.class_size == 1


def test_ranking_shares_position_on_ties(make_student, math, english, term, grade, school_class):
    a = make_student("S001")
    b = make_student("S002")
    c = make_student("S003")
    d = make_student("S004")
    for student, scores in [(a, (90, 80)), (b, (70, 70)), (c, (60, 80)), (d, (50, 40))]:
        grade(student, math, scores[0])
        grade(student, english, scores[1])

    ranking = class_ranking(school_class, term)

    assert [(r.admission_number, r.position) for r in ranking] == [
        ("S001", 1),
        ("S002", 2),
        ("S003", 2),
        ("S004", 4),
    ]


def test_students_without_grades_are_unranked(make_student, math, term, grade, school_class):
    graded = make_student("S001")
    make_student("S002")
    grade(graded, math, 55)

    ranking = class_ranking(school_class, term)

    assert ranking[0].position == 1
    assert ranking[1].admission_number == "S002"
    assert ranking[1].position is None
    assert ranking[1].average is None


def test_withdrawn_students_are_left_out_of_ranking(make_student, math, term, grade, school_class):
    stays = make_student("S001")
    leaves = make_student("S002")
    grade(stays, math, 50)
    grade(leaves, math, 99)
    leaves.enrollments.update(status="withdrawn")

    ranking = class_ranking(school_class, term)

    assert [r.admission_number for r in ranking] == ["S001"]


def test_report_for_student_with_no_class(make_student, term):
    student = make_student("S009", enrol=False)
    report = term_report(student, term)
    assert report.school_class is None
    assert report.subjects == []
    assert report.average is None


def test_subject_statistics(make_student, math, term, grade, school_class):
    grade(make_student("S001"), math, 40)
    grade(make_student("S002"), math, 90)

    stats = subject_statistics(school_class, term)

    assert stats == [
        {
            "subject": math.pk,
            "code": "MATH",
            "name": "Mathematics",
            "mean": "65.00",
            "highest": "90.00",
            "lowest": "40.00",
            "graded": 2,
        }
    ]
