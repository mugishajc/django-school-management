import random
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

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

DEMO_PASSWORD = "demo-pass-123"

FIRST_NAMES = ["Aline", "Eric", "Grace", "Patrick", "Diane", "Kevin", "Sandrine", "Olivier"]
LAST_NAMES = ["Uwase", "Habimana", "Mukamana", "Niyonzima", "Ingabire", "Mugabo", "Keza"]
SUBJECTS = [
    ("MATH", "Mathematics"),
    ("ENG", "English"),
    ("PHY", "Physics"),
    ("BIO", "Biology"),
    ("HIST", "History"),
]


class Command(BaseCommand):
    help = "Create a small, repeatable demo dataset (users, classes, grades)."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=12)
        parser.add_argument("--seed", type=int, default=42)

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        year = date.today().year

        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"role": User.Role.ADMIN, "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password(DEMO_PASSWORD)
            admin.save()

        term, _ = AcademicTerm.objects.get_or_create(
            name="Term 1",
            year=year,
            defaults={
                "start_date": date(year, 1, 8),
                "end_date": date(year, 4, 4),
                "is_current": True,
            },
        )

        subjects = [
            Subject.objects.get_or_create(code=code, defaults={"name": name})[0]
            for code, name in SUBJECTS
        ]

        teachers = []
        for index, subject in enumerate(subjects, start=1):
            user, created = User.objects.get_or_create(
                username=f"teacher{index}",
                defaults={
                    "role": User.Role.TEACHER,
                    "first_name": rng.choice(FIRST_NAMES),
                    "last_name": rng.choice(LAST_NAMES),
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            teacher, _ = Teacher.objects.get_or_create(
                user=user, defaults={"staff_number": f"T{index:03d}"}
            )
            teachers.append((teacher, subject))

        school_class, _ = SchoolClass.objects.get_or_create(
            name="Senior 2", stream="A", year=year, defaults={"class_teacher": teachers[0][0]}
        )
        for teacher, subject in teachers:
            ClassSubject.objects.get_or_create(
                school_class=school_class, subject=subject, defaults={"teacher": teacher}
            )

        for index in range(1, options["students"] + 1):
            user, created = User.objects.get_or_create(
                username=f"student{index}",
                defaults={
                    "role": User.Role.STUDENT,
                    "first_name": rng.choice(FIRST_NAMES),
                    "last_name": rng.choice(LAST_NAMES),
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            student, _ = Student.objects.get_or_create(
                user=user,
                defaults={"admission_number": f"S{year}{index:03d}", "gender": rng.choice("FM")},
            )
            enrollment, _ = Enrollment.objects.get_or_create(
                student=student, school_class=school_class
            )
            for teacher, subject in teachers:
                Grade.objects.get_or_create(
                    enrollment=enrollment,
                    subject=subject,
                    term=term,
                    defaults={
                        "score": Decimal(rng.randint(35, 98)),
                        "recorded_by": teacher,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: class {school_class}, term {term}, "
                f"{options['students']} students. Password for every demo user: {DEMO_PASSWORD}"
            )
        )
