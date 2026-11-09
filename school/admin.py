from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
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

admin.site.site_header = "School Management"
admin.site.site_title = "School Management"
admin.site.index_title = "Administration"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (("School", {"fields": ("role",)}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("School", {"fields": ("role",)}),)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("staff_number", "full_name", "phone", "hire_date")
    search_fields = ("staff_number", "user__first_name", "user__last_name", "user__email")
    list_select_related = ("user",)
    autocomplete_fields = ("user",)

    @admin.display(description="Name", ordering="user__last_name")
    def full_name(self, obj):
        return obj.user.get_full_name()


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    autocomplete_fields = ("student",)
    fields = ("student", "status", "enrolled_on")
    readonly_fields = ("enrolled_on",)


class ClassSubjectInline(admin.TabularInline):
    model = ClassSubject
    extra = 0
    autocomplete_fields = ("subject", "teacher")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("admission_number", "full_name", "gender", "guardian_phone", "is_active")
    list_filter = ("is_active", "gender")
    search_fields = ("admission_number", "user__first_name", "user__last_name", "guardian_name")
    list_select_related = ("user",)
    autocomplete_fields = ("user",)
    actions = ("deactivate",)

    @admin.display(description="Name", ordering="user__last_name")
    def full_name(self, obj):
        return obj.user.get_full_name()

    @admin.action(description="Mark selected students as inactive")
    def deactivate(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} student(s) marked inactive.")


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("__str__", "year", "class_teacher", "student_count")
    list_filter = ("year",)
    search_fields = ("name", "stream")
    autocomplete_fields = ("class_teacher",)
    inlines = (ClassSubjectInline, EnrollmentInline)

    @admin.display(description="Students")
    def student_count(self, obj):
        return obj.enrollments.filter(status=Enrollment.Status.ACTIVE).count()


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ("name", "year", "start_date", "end_date", "is_current")
    list_filter = ("year", "is_current")
    actions = ("make_current",)

    @admin.action(description="Set as the current term")
    def make_current(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Pick exactly one term.", level="error")
            return
        AcademicTerm.objects.update(is_current=False)
        queryset.update(is_current=True)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "school_class", "status", "enrolled_on")
    list_filter = ("status", "school_class__year", "school_class")
    search_fields = ("student__admission_number", "student__user__last_name")
    autocomplete_fields = ("student", "school_class")
    list_select_related = ("student__user", "school_class")
    actions = ("withdraw",)

    @admin.action(description="Withdraw selected enrollments")
    def withdraw(self, request, queryset):
        queryset.update(status=Enrollment.Status.WITHDRAWN)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "subject", "term", "score", "letter", "recorded_by")
    list_filter = ("term", "subject", "enrollment__school_class")
    search_fields = ("enrollment__student__admission_number", "enrollment__student__user__last_name")
    autocomplete_fields = ("enrollment", "subject", "recorded_by")
    list_select_related = ("enrollment__student__user", "enrollment__school_class", "subject", "term")
