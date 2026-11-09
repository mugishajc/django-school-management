from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Login account. The role decides what the API lets the user do."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STUDENT)

    @property
    def is_school_admin(self) -> bool:
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_teacher(self) -> bool:
        return self.role == self.Role.TEACHER

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT


class Teacher(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_profile"
    )
    staff_number = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    hire_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self) -> str:
        return self.user.get_full_name() or self.user.username


class Student(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "F", "Female"
        MALE = "M", "Male"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile"
    )
    admission_number = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    guardian_name = models.CharField(max_length=120, blank=True)
    guardian_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["admission_number"]

    def __str__(self) -> str:
        name = self.user.get_full_name() or self.user.username
        return f"{name} ({self.admission_number})"


class AcademicTerm(models.Model):
    name = models.CharField(max_length=40, help_text="e.g. Term 1")
    year = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-year", "start_date"]
        constraints = [
            models.UniqueConstraint(fields=["year", "name"], name="unique_term_per_year"),
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F("start_date")),
                name="term_ends_after_start",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} {self.year}"


class Subject(models.Model):
    code = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class SchoolClass(models.Model):
    """A class group for one academic year, e.g. Senior 2 stream B, 2026."""

    name = models.CharField(max_length=40)
    stream = models.CharField(max_length=10, blank=True)
    year = models.PositiveSmallIntegerField()
    class_teacher = models.ForeignKey(
        Teacher, null=True, blank=True, on_delete=models.SET_NULL, related_name="homerooms"
    )
    subjects = models.ManyToManyField(Subject, through="ClassSubject", related_name="classes")

    class Meta:
        ordering = ["-year", "name", "stream"]
        verbose_name = "class"
        verbose_name_plural = "classes"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "stream", "year"], name="unique_class_stream_year"
            )
        ]

    def __str__(self) -> str:
        label = f"{self.name} {self.stream}".strip()
        return f"{label} ({self.year})"


class ClassSubject(models.Model):
    """Which teacher teaches which subject to which class."""

    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="offerings"
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="offerings")
    teacher = models.ForeignKey(
        Teacher, null=True, blank=True, on_delete=models.SET_NULL, related_name="offerings"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school_class", "subject"], name="unique_class_subject")
        ]

    def __str__(self) -> str:
        return f"{self.school_class} / {self.subject.code}"


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WITHDRAWN = "withdrawn", "Withdrawn"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_on = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["school_class", "student"]
        constraints = [
            models.UniqueConstraint(fields=["student", "school_class"], name="unique_enrollment")
        ]

    def __str__(self) -> str:
        return f"{self.student} in {self.school_class}"


class Grade(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="grades")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="grades")
    term = models.ForeignKey(AcademicTerm, on_delete=models.PROTECT, related_name="grades")
    score = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(
        Teacher, null=True, blank=True, on_delete=models.SET_NULL, related_name="recorded_grades"
    )
    recorded_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["term", "enrollment", "subject"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "subject", "term"], name="one_grade_per_subject_term"
            ),
            models.CheckConstraint(
                condition=models.Q(score__gte=0) & models.Q(score__lte=100),
                name="score_between_0_and_100",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.enrollment.student} {self.subject.code} {self.term}: {self.score}"

    @property
    def letter(self) -> str:
        from .grading import letter_for

        return letter_for(self.score)
