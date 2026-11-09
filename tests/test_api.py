import pytest
from rest_framework.authtoken.models import Token

from school.models import Enrollment, Student, User


@pytest.fixture
def as_admin(api, admin_user):
    api.force_authenticate(admin_user)
    return api


def test_token_login(api, admin_user):
    response = api.post("/api/auth/token/", {"username": "head", "password": "pass-12345"})
    assert response.status_code == 200
    assert response.data["token"] == Token.objects.get(user=admin_user).key


def test_anonymous_requests_are_rejected(api, db):
    assert api.get("/api/students/").status_code == 401


def test_admin_creates_student_with_login(as_admin, db):
    payload = {
        "username": "aline",
        "first_name": "Aline",
        "last_name": "Uwase",
        "password": "a-strong-pass",
        "admission_number": "S2026001",
        "gender": "F",
    }
    response = as_admin.post("/api/students/", payload, format="json")

    assert response.status_code == 201, response.data
    assert "password" not in response.data
    student = Student.objects.get(admission_number="S2026001")
    assert student.user.role == User.Role.STUDENT
    assert student.user.check_password("a-strong-pass")


def test_duplicate_username_is_rejected(as_admin, make_user):
    make_user("taken", User.Role.STUDENT)
    response = as_admin.post(
        "/api/students/", {"username": "taken", "admission_number": "S1"}, format="json"
    )
    assert response.status_code == 400
    assert "username" in response.data


def test_list_is_paginated(as_admin, make_student):
    for n in range(25):
        make_student(f"S{n:03d}")
    response = as_admin.get("/api/students/")
    assert response.data["count"] == 25
    assert len(response.data["results"]) == 20
    assert response.data["next"] is not None


def test_search_and_filter_students(as_admin, make_student):
    make_student("S001", "Aline")
    make_student("S002", "Eric")
    make_student("S003", "Grace", enrol=False)

    found = as_admin.get("/api/students/", {"search": "eric"}).data["results"]
    assert [s["admission_number"] for s in found] == ["S002"]

    klass = Enrollment.objects.first().school_class_id
    in_class = as_admin.get("/api/students/", {"school_class": klass}).data
    assert in_class["count"] == 2


def test_class_lists_offerings_and_size(as_admin, school_class, make_student):
    make_student("S001")
    data = as_admin.get(f"/api/classes/{school_class.pk}/").data
    assert data["student_count"] == 1
    assert {o["subject_code"] for o in data["offerings"]} == {"MATH", "ENG"}


def test_second_active_enrollment_in_same_year_is_rejected(as_admin, make_student, db):
    from school.models import SchoolClass

    student = make_student("S001")
    other = SchoolClass.objects.create(name="Senior 2", stream="B", year=2026)
    response = as_admin.post(
        "/api/enrollments/", {"student": student.pk, "school_class": other.pk}, format="json"
    )
    assert response.status_code == 400


def test_grade_rejects_subject_not_taught_in_class(as_admin, make_student, term, db):
    from school.models import Subject

    student = make_student("S001")
    art = Subject.objects.create(code="ART", name="Art")
    response = as_admin.post(
        "/api/grades/",
        {
            "enrollment": student.enrollments.get().pk,
            "subject": art.pk,
            "term": term.pk,
            "score": "70",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "subject" in response.data


def test_grade_filters(as_admin, make_student, math, english, grade):
    s1 = make_student("S001")
    s2 = make_student("S002")
    grade(s1, math, 45)
    grade(s1, english, 85)
    grade(s2, math, 75)

    data = as_admin.get("/api/grades/", {"subject": math.pk, "min_score": 50}).data
    assert [g["student"] for g in data["results"]] == [s2.pk]


def test_student_report_endpoint(as_admin, make_student, math, english, term, grade):
    student = make_student("S001", "Aline")
    grade(student, math, 90)
    grade(student, english, 70)

    data = as_admin.get(f"/api/students/{student.pk}/report/", {"term": term.pk}).data

    assert data["average"] == "80.00"
    assert data["letter"] == "A"
    assert data["position"] == 1
    assert data["school_class"]["label"] == "Senior 2 A (2026)"
    assert len(data["subjects"]) == 2


def test_report_defaults_to_current_term(as_admin, make_student, term):
    student = make_student("S001")
    data = as_admin.get(f"/api/students/{student.pk}/report/").data
    assert data["term"]["id"] == term.pk


def test_report_with_unknown_term(as_admin, make_student, term):
    student = make_student("S001")
    response = as_admin.get(f"/api/students/{student.pk}/report/", {"term": 999})
    assert response.status_code == 400


def test_class_ranking_endpoint(as_admin, school_class, make_student, math, term, grade):
    grade(make_student("S001"), math, 60)
    grade(make_student("S002"), math, 80)

    data = as_admin.get(f"/api/classes/{school_class.pk}/ranking/", {"term": term.pk}).data

    assert [row["admission_number"] for row in data["ranking"]] == ["S002", "S001"]
    assert data["subjects"][0]["mean"] == "70.00"
