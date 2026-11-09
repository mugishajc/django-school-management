import pytest

from school.models import Grade


@pytest.fixture
def setup(make_student, math, english, term, grade):
    alice = make_student("S001", "Alice")
    bob = make_student("S002", "Bob")
    grade(alice, math, 70)
    grade(bob, math, 50)
    return {"alice": alice, "bob": bob}


def grade_payload(student, subject, term, score="75"):
    return {
        "enrollment": student.enrollments.get().pk,
        "subject": subject.pk,
        "term": term.pk,
        "score": score,
    }


class TestStudentRole:
    def test_sees_only_own_profile_and_grades(self, api, setup):
        api.force_authenticate(setup["alice"].user)

        students = api.get("/api/students/").data["results"]
        grades = api.get("/api/grades/").data["results"]

        assert [s["admission_number"] for s in students] == ["S001"]
        assert {g["student"] for g in grades} == {setup["alice"].pk}

    def test_cannot_read_another_students_report(self, api, setup):
        api.force_authenticate(setup["alice"].user)
        response = api.get(f"/api/students/{setup['bob'].pk}/report/")
        assert response.status_code == 404

    def test_can_read_own_report(self, api, setup):
        api.force_authenticate(setup["alice"].user)
        response = api.get(f"/api/students/{setup['alice'].pk}/report/")
        assert response.status_code == 200
        assert response.data["position"] == 1

    def test_cannot_write_grades(self, api, setup, english, term):
        api.force_authenticate(setup["alice"].user)
        response = api.post(
            "/api/grades/", grade_payload(setup["alice"], english, term, "100"), format="json"
        )
        assert response.status_code == 403

    def test_cannot_see_class_ranking(self, api, setup, school_class):
        api.force_authenticate(setup["alice"].user)
        assert api.get(f"/api/classes/{school_class.pk}/ranking/").status_code == 403

    def test_cannot_create_subjects(self, api, setup):
        api.force_authenticate(setup["alice"].user)
        response = api.post("/api/subjects/", {"code": "X", "name": "X"})
        assert response.status_code == 403


class TestTeacherRole:
    def test_records_grade_for_own_subject(self, api, setup, english_teacher, english, term):
        api.force_authenticate(english_teacher.user)

        response = api.post(
            "/api/grades/", grade_payload(setup["alice"], english, term), format="json"
        )

        assert response.status_code == 201, response.data
        assert response.data["recorded_by"] == english_teacher.pk

    def test_cannot_grade_subject_they_do_not_teach(self, api, setup, math_teacher, english, term):
        api.force_authenticate(math_teacher.user)
        response = api.post(
            "/api/grades/", grade_payload(setup["alice"], english, term), format="json"
        )
        assert response.status_code == 403

    def test_can_update_grade_in_own_subject(self, api, setup, math_teacher, math):
        api.force_authenticate(math_teacher.user)
        existing = Grade.objects.get(enrollment__student=setup["bob"], subject=math)

        response = api.patch(f"/api/grades/{existing.pk}/", {"score": "58"}, format="json")

        assert response.status_code == 200
        existing.refresh_from_db()
        assert str(existing.score) == "58.00"
        assert existing.recorded_by == math_teacher

    def test_cannot_update_grade_in_other_subject(self, api, setup, english_teacher, math):
        api.force_authenticate(english_teacher.user)
        existing = Grade.objects.get(enrollment__student=setup["bob"], subject=math)
        response = api.patch(f"/api/grades/{existing.pk}/", {"score": "99"}, format="json")
        assert response.status_code == 403

    def test_can_read_ranking_but_not_edit_students(self, api, setup, math_teacher, school_class):
        api.force_authenticate(math_teacher.user)
        assert api.get(f"/api/classes/{school_class.pk}/ranking/").status_code == 200
        response = api.patch(
            f"/api/students/{setup['bob'].pk}/", {"guardian_name": "X"}, format="json"
        )
        assert response.status_code == 403
