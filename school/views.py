from django.db.models import Count, Q
from rest_framework import viewsets

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


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.select_related("user")
    serializer_class = TeacherSerializer


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.select_related("user")
    serializer_class = StudentSerializer


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class AcademicTermViewSet(viewsets.ModelViewSet):
    queryset = AcademicTerm.objects.all()
    serializer_class = AcademicTermSerializer


class SchoolClassViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolClassSerializer

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


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related("student__user", "school_class")
    serializer_class = EnrollmentSerializer


class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.select_related("enrollment", "subject", "term")
    serializer_class = GradeSerializer
