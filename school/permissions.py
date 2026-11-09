from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import ClassSubject


def teacher_profile(user):
    return getattr(user, "teacher_profile", None) if user.is_authenticated else None


def student_profile(user):
    return getattr(user, "student_profile", None) if user.is_authenticated else None


def teaches(teacher, school_class_id, subject_id) -> bool:
    if teacher is None:
        return False
    return ClassSubject.objects.filter(
        teacher=teacher, school_class_id=school_class_id, subject_id=subject_id
    ).exists()


class IsSchoolAdmin(BasePermission):
    message = "Only school administrators can do that."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_school_admin)


class IsSchoolAdminOrReadOnly(BasePermission):
    """Anyone signed in can read; only administrators can change data."""

    message = "Only school administrators can change this resource."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or request.user.is_school_admin


class IsStaffMember(BasePermission):
    """Administrators and teachers. Students are kept out of staff-only data."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_school_admin or user.is_teacher))


class GradePermission(BasePermission):
    """
    Admins can do anything with grades. Teachers can record and edit grades
    only for subjects they teach in that class. Students can only read.
    """

    message = "You can only manage grades for subjects you teach in that class."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_school_admin or user.is_teacher

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in SAFE_METHODS or user.is_school_admin:
            return True
        return teaches(teacher_profile(user), obj.enrollment.school_class_id, obj.subject_id)
