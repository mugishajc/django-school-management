from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .filters import EnrollmentFilter, GradeFilter, SchoolClassFilter, StudentFilter
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
    IsStaffMember,
    student_profile,
    teacher_profile,
    teaches,
)
from .reports import class_ranking, subject_statistics, term_report
from .serializers import (
    AcademicTermSerializer,
    ClassSubjectSerializer,
    EnrollmentSerializer,
    GradeSerializer,
    RankedStudentSerializer,
    SchoolClassSerializer,
    StudentSerializer,
    SubjectSerializer,
    TeacherSerializer,
    TermReportSerializer,
)


def resolve_term(request) -> AcademicTerm:
    """Use ?term=<id> if given, otherwise fall back to the current term."""
    term_id = request.query_params.get("term")
    if term_id:
        try:
            return AcademicTerm.objects.get(pk=int(term_id))
        except (ValueError, AcademicTerm.DoesNotExist) as exc:
            raise ValidationError({"term": "Unknown term."}) from exc
    term = AcademicTerm.objects.filter(is_current=True).first()
    if term is None:
        raise ValidationError({"term": "No current term is set; pass ?term=<id>."})
    return term


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
    search_fields = ["staff_number", "user__first_name", "user__last_name", "user__email"]
    ordering_fields = ["staff_number", "user__last_name", "hire_date"]


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.select_related("user")
    serializer_class = StudentSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]
    filterset_class = StudentFilter
    search_fields = ["admission_number", "user__first_name", "user__last_name", "guardian_name"]
    ordering_fields = ["admission_number", "user__last_name", "date_of_birth"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_student:
            profile = student_profile(user)
            return qs.filter(pk=profile.pk) if profile else qs.none()
        # The class/year filters join through enrollments, so guard against duplicates.
        return qs.distinct()

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        """Report card for one term: scores per subject, average and class position."""
        student = self.get_object()
        report = term_report(student, resolve_term(request))
        return Response(TermReportSerializer(report).data)


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]
    search_fields = ["code", "name"]


class AcademicTermViewSet(viewsets.ModelViewSet):
    queryset = AcademicTerm.objects.all()
    serializer_class = AcademicTermSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]
    filterset_fields = ["year", "is_current"]


class SchoolClassViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolClassSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]
    filterset_class = SchoolClassFilter
    search_fields = ["name", "stream"]
    ordering_fields = ["name", "year", "student_count"]

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

    @action(detail=True, methods=["get"], permission_classes=[IsStaffMember])
    def ranking(self, request, pk=None):
        """Class ranking for a term plus per-subject statistics. Staff only."""
        school_class = self.get_object()
        term = resolve_term(request)
        ranking = class_ranking(school_class, term)
        return Response(
            {
                "school_class": {"id": school_class.pk, "label": str(school_class)},
                "term": {"id": term.pk, "label": str(term)},
                "ranking": RankedStudentSerializer(ranking, many=True).data,
                "subjects": subject_statistics(school_class, term),
            }
        )


class ClassSubjectViewSet(viewsets.ModelViewSet):
    queryset = ClassSubject.objects.select_related("subject", "teacher__user", "school_class")
    serializer_class = ClassSubjectSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]
    filterset_fields = ["school_class", "subject", "teacher"]


class EnrollmentViewSet(StudentScopedMixin, viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related("student__user", "school_class")
    serializer_class = EnrollmentSerializer
    permission_classes = [IsSchoolAdminOrReadOnly]
    filterset_class = EnrollmentFilter
    search_fields = ["student__admission_number", "student__user__last_name"]


class GradeViewSet(StudentScopedMixin, viewsets.ModelViewSet):
    queryset = Grade.objects.select_related("enrollment", "subject", "term")
    serializer_class = GradeSerializer
    permission_classes = [GradePermission]
    filterset_class = GradeFilter
    ordering_fields = ["score", "recorded_at"]
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
