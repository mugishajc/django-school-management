# django-school-management

[![CI](https://github.com/mugishajc/django-school-management/actions/workflows/ci.yml/badge.svg)](https://github.com/mugishajc/django-school-management/actions/workflows/ci.yml)

A REST API for running the academic side of a secondary school: students,
teachers, classes, subjects, enrollments and grades, with term report cards
and class rankings. Built with Django 5 and Django REST Framework.

## Features

- **People** – students and teachers are profiles linked to a login account.
  One `POST` creates both the account and the profile.
- **Academic structure** – terms, subjects, class groups per year (e.g.
  *Senior 2 A, 2026*) and which teacher teaches which subject to which class.
- **Enrollments** – a student can hold only one active class per academic year.
- **Grades** – one score (0–100) per student, subject and term, with letter
  bands A–F. The API refuses grades for subjects not taught in the student's class.
- **Term reports** – per-student report card (scores, total, average, letter,
  position in class) and a class ranking with per-subject mean/high/low.
  Ties share a position (1, 2, 2, 4).
- **Role-based access**
  | Role    | Can do |
  |---------|--------|
  | admin   | everything |
  | teacher | read school data, view class rankings, record/edit grades **only for subjects they teach in that class** |
  | student | read-only; sees only their own profile, enrollments, grades and report |
- **Admin site** – search, filters, inlines for class subjects and
  enrollments, bulk actions (withdraw enrollments, deactivate students, set current term).
- Filtering, search, ordering and page-number pagination on every list endpoint.

## Stack

Python 3.11+, Django 5.1, Django REST Framework 3.15, django-filter,
SQLite by default, pytest + pytest-django, ruff.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

python manage.py migrate
python manage.py seed_demo          # optional sample data
python manage.py runserver
```

`seed_demo` creates an `admin` superuser, five teachers (`teacher1`..`teacher5`),
twelve students (`student1`..`student12`), one class and one term of grades.
Every demo account uses the password `demo-pass-123`.

Settings read from the environment:

| Variable | Default | Notes |
|----------|---------|-------|
| `DJANGO_SECRET_KEY` | dev placeholder | **set this outside development** |
| `DJANGO_DEBUG` | `1` | set to `0` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | comma-separated |
| `DJANGO_DB_PATH` | `db.sqlite3` | SQLite file location |

## Authentication

Token auth (session auth also works for the browsable API).

```bash
curl -X POST localhost:8000/api/auth/token/ \
     -d username=admin -d password=demo-pass-123
# {"token": "9b1f..."}

curl -H "Authorization: Token 9b1f..." localhost:8000/api/students/
```

## Endpoints

All under `/api/`.

| Method | Path | Notes |
|--------|------|-------|
| POST | `auth/token/` | exchange username/password for a token |
| GET/POST | `students/` | filters: `gender`, `is_active`, `school_class`, `year`; `search`, `ordering` |
| GET/PUT/PATCH/DELETE | `students/{id}/` | |
| GET | `students/{id}/report/?term={id}` | report card; defaults to the current term |
| GET/POST | `teachers/` | search by name, staff number, email |
| GET/POST | `subjects/` | |
| GET/POST | `terms/` | filters: `year`, `is_current` |
| GET/POST | `classes/` | includes subject offerings and active student count |
| GET | `classes/{id}/ranking/?term={id}` | ranking + subject statistics (admin/teacher) |
| GET/POST | `class-subjects/` | assign a teacher to a subject in a class |
| GET/POST | `enrollments/` | filters: `student`, `school_class`, `status`, `year` |
| GET/POST | `grades/` | filters: `term`, `subject`, `student`, `school_class`, `min_score`, `max_score` |

Lists are paginated (`?page=2`, `?page_size=50`, max 100).

### Example: report card

```http
GET /api/students/3/report/?term=1
```

```json
{
  "student": {"id": 3, "admission_number": "S2026003", "name": "Grace Mukamana"},
  "term": {"id": 1, "label": "Term 1 2026"},
  "school_class": {"id": 1, "label": "Senior 2 A (2026)"},
  "subjects": [
    {"subject_id": 4, "code": "BIO", "name": "Biology", "score": "81.00", "letter": "A", "remarks": ""},
    {"subject_id": 2, "code": "ENG", "name": "English", "score": "64.00", "letter": "C", "remarks": ""}
  ],
  "total": "145.00",
  "average": "72.50",
  "letter": "B",
  "position": 4,
  "class_size": 12
}
```

## Tests

```bash
pytest          # tests
ruff check .    # lint
```

The suite covers the grading bands and database constraints, report and
ranking maths (including ties and withdrawn students), the API, and the
permission rules for each role.

## Project layout

```
config/           settings and root URLs
school/
  models.py       users, profiles, classes, enrollments, grades
  grading.py      letter-grade bands
  reports.py      report cards, rankings, subject statistics
  permissions.py  role rules
  serializers.py, views.py, filters.py, urls.py
  admin.py        admin customisation
  management/commands/seed_demo.py
tests/
```

## License

MIT – see [LICENSE](LICENSE).
