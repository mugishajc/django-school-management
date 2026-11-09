import django_filters

from .models import Enrollment, Grade, SchoolClass, Student


class StudentFilter(django_filters.FilterSet):
    school_class = django_filters.NumberFilter(
        field_name="enrollments__school_class", label="Class id"
    )
    year = django_filters.NumberFilter(field_name="enrollments__school_class__year")

    class Meta:
        model = Student
        fields = ["gender", "is_active", "school_class", "year"]


class SchoolClassFilter(django_filters.FilterSet):
    class Meta:
        model = SchoolClass
        fields = ["year", "name", "class_teacher"]


class EnrollmentFilter(django_filters.FilterSet):
    year = django_filters.NumberFilter(field_name="school_class__year")

    class Meta:
        model = Enrollment
        fields = ["student", "school_class", "status", "year"]


class GradeFilter(django_filters.FilterSet):
    student = django_filters.NumberFilter(field_name="enrollment__student")
    school_class = django_filters.NumberFilter(field_name="enrollment__school_class")
    min_score = django_filters.NumberFilter(field_name="score", lookup_expr="gte")
    max_score = django_filters.NumberFilter(field_name="score", lookup_expr="lte")

    class Meta:
        model = Grade
        fields = ["term", "subject", "student", "school_class", "min_score", "max_score"]
