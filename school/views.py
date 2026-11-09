from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from .models import (
    AcademicTerm,
    ClassSubject,
    Enrollment,
    Grade,
    SchoolClass,
    Student,
    Subject,
    Teacher,
)
from .permissions import (
    GradePermission,
    IsSchoolAdminOrReadOnly,
    student_profile,
    teacher_profile,
    teaches,
)
from .serializers import (
    AcademicTermSerializer,
    ClassSubjectSerializer,
    EnrollmentSerializer,
    GradeSerializer,
    SchoolClassSerializer,
    StudentSerializer,
    SubjectSerializer,
    TeacherSerializer,
)


class StudentScopedMixin:
    """
    Narrows the queryset to the requesting student's own rows.
    `student_field` is the ORM path from the model to Student.
    """

    student_field = "student"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_student:
            profile = student_profile(user)
            if profile is None:
                return qs.none()
            return qs.filter(**{self.student_field: profile})
        return qs


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.select_related("user")
    serializer_class = TeacherSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.select_related("user")
    serializer_class = StudentSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_student:
            profile = student_profile(user)
            return qs.filter(pk=profile.pk) if profile else qs.none()
        return qs


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]


class AcademicTermViewSet(viewsets.ModelViewSet):
    queryset = AcademicTerm.objects.all()
    serializer_class = AcademicTermSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]


class SchoolClassViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolClassSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]

    def get_queryset(self):
        return (
            SchoolClass.objects.select_related("class_teacher__user")
            .prefetch_related("offerings__subject", "offerings__teacher__user")
            .annotate(
                student_count=Count(
                    "enrollments", filter=Q(enrollments__status=Enrollment.Status.ACTIVE)
                )
            )
        )


class ClassSubjectViewSet(viewsets.ModelViewSet):
    queryset = ClassSubject.objects.select_related("subject", "teacher__user", "school_class")
    serializer_class = ClassSubjectSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]


class EnrollmentViewSet(StudentScopedMixin, viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related("student__user", "school_class")
    serializer_class = EnrollmentSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]


class GradeViewSet(StudentScopedMixin, viewsets.ModelViewSet):
    queryset = Grade.objects.select_related("enrollment", "subject", "term")
    serializer_class = GradeSerializer
    permission_classes = [GradePermission]
    student_field = "enrollment__student"

    def _check_teacher_can_grade(self, serializer):
        user = self.request.user
        if user.is_school_admin:
            return None
        teacher = teacher_profile(user)
        enrollment = serializer.validated_data.get(
            "enrollment", getattr(serializer.instance, "enrollment", None)
        )
        subject = serializer.validated_data.get(
            "subject", getattr(serializer.instance, "subject", None)
        )
        if not teaches(teacher, enrollment.school_class_id, subject.pk):
            raise PermissionDenied(GradePermission.message)
        return teacher

    def perform_create(self, serializer):
        teacher = self._check_teacher_can_grade(serializer)
        serializer.save(recorded_by=teacher)

    def perform_update(self, serializer):
        teacher = self._check_teacher_can_grade(serializer)
        if teacher is not None:
            serializer.save(recorded_by=teacher)
        else:
            serializer.save()
