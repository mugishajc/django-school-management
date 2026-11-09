from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from school.models import (
    AcademicTerm,
    ClassSubject,
    Enrollment,
    Grade,
    SchoolClass,
    Student,
    Subject,
    Teacher,
    User,
)


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(username, role, **extra):
        return User.objects.create_user(
            username=username, password="pass-12345", role=role, **extra
        )

    return _make


@pytest.fixture
def admin_user(make_user):
    return make_user("head", User.Role.ADMIN)


@pytest.fixture
def term(db):
    return AcademicTerm.objects.create(
        name="Term 1",
        year=2026,
        start_date=date(2026, 1, 8),
        end_date=date(2026, 4, 4),
        is_current=True,
    )


@pytest.fixture
def math(db):
    return Subject.objects.create(code="MATH", name="Mathematics")


@pytest.fixture
def english(db):
    return Subject.objects.create(code="ENG", name="English")


@pytest.fixture
def math_teacher(make_user):
    user = make_user("mteacher", User.Role.TEACHER, first_name="Eric", last_name="Habimana")
    return Teacher.objects.create(user=user, staff_number="T001")


@pytest.fixture
def english_teacher(make_user):
    user = make_user("eteacher", User.Role.TEACHER, first_name="Grace", last_name="Uwase")
    return Teacher.objects.create(user=user, staff_number="T002")


@pytest.fixture
def school_class(db, math, english, math_teacher, english_teacher):
    klass = SchoolClass.objects.create(name="Senior 2", stream="A", year=2026)
    ClassSubject.objects.create(school_class=klass, subject=math, teacher=math_teacher)
    ClassSubject.objects.create(school_class=klass, subject=english, teacher=english_teacher)
    return klass


@pytest.fixture
def make_student(make_user, school_class):
    def _make(admission_number, first_name="", enrol=True):
        user = make_user(
            admission_number.lower(), User.Role.STUDENT, first_name=first_name, last_name="Test"
        )
        student = Student.objects.create(user=user, admission_number=admission_number)
        if enrol:
            Enrollment.objects.create(student=student, school_class=school_class)
        return student

    return _make


@pytest.fixture
def grade(term):
    def _grade(student, subject, score):
        enrollment = student.enrollments.get()
        return Grade.objects.create(
            enrollment=enrollment, subject=subject, term=term, score=Decimal(str(score))
        )

    return _grade
