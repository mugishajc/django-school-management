from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

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

User = get_user_model()

USER_FIELDS = ("username", "first_name", "last_name", "email", "password")


class PersonSerializer(serializers.ModelSerializer):
    """Flattens the linked User into the profile so one request creates both."""

    username = serializers.CharField(source="user.username")
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True)
    email = serializers.EmailField(source="user.email", required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    full_name = serializers.SerializerMethodField()

    role: str = ""

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name()

    def validate_username(self, value):
        qs = User.objects.filter(username__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise serializers.ValidationError("That username is already taken.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop("user", {})
        password = validated_data.pop("password", None)
        user = User(role=self.role, **user_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return self.Meta.model.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        password = validated_data.pop("password", None)
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        if password:
            instance.user.set_password(password)
        instance.user.save()
        return super().update(instance, validated_data)


class TeacherSerializer(PersonSerializer):
    role = User.Role.TEACHER

    class Meta:
        model = Teacher
        fields = ("id", *USER_FIELDS, "full_name", "staff_number", "phone", "hire_date")


class StudentSerializer(PersonSerializer):
    role = User.Role.STUDENT

    class Meta:
        model = Student
        fields = (
            "id",
            *USER_FIELDS,
            "full_name",
            "admission_number",
            "date_of_birth",
            "gender",
            "guardian_name",
            "guardian_phone",
            "is_active",
        )


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ("id", "code", "name", "description")


class AcademicTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicTerm
        fields = ("id", "name", "year", "start_date", "end_date", "is_current")

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": "Term must end after it starts."})
        return attrs


class ClassSubjectSerializer(serializers.ModelSerializer):
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    teacher_name = serializers.CharField(source="teacher.__str__", read_only=True, default=None)

    class Meta:
        model = ClassSubject
        fields = ("id", "school_class", "subject", "subject_code", "teacher", "teacher_name")


class SchoolClassSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="__str__", read_only=True)
    student_count = serializers.IntegerField(read_only=True, default=0)
    offerings = ClassSubjectSerializer(many=True, read_only=True)

    class Meta:
        model = SchoolClass
        fields = (
            "id",
            "name",
            "stream",
            "year",
            "label",
            "class_teacher",
            "student_count",
            "offerings",
        )


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.__str__", read_only=True)
    class_label = serializers.CharField(source="school_class.__str__", read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "student",
            "student_name",
            "school_class",
            "class_label",
            "status",
            "enrolled_on",
        )
        read_only_fields = ("enrolled_on",)

    def validate(self, attrs):
        student = attrs.get("student", getattr(self.instance, "student", None))
        school_class = attrs.get("school_class", getattr(self.instance, "school_class", None))
        if student and school_class:
            # A student can only sit in one active class per academic year.
            clash = Enrollment.objects.filter(
                student=student,
                school_class__year=school_class.year,
                status=Enrollment.Status.ACTIVE,
            )
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exclude(school_class=school_class).exists():
                raise serializers.ValidationError(
                    "Student already has an active enrollment for that year."
                )
        return attrs


class GradeSerializer(serializers.ModelSerializer):
    letter = serializers.CharField(read_only=True)
    student = serializers.IntegerField(source="enrollment.student_id", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)

    class Meta:
        model = Grade
        fields = (
            "id",
            "enrollment",
            "student",
            "subject",
            "subject_code",
            "term",
            "score",
            "letter",
            "remarks",
            "recorded_by",
            "recorded_at",
        )
        read_only_fields = ("recorded_by", "recorded_at")

    def validate_score(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Score must be between 0 and 100.")
        return value

    def validate(self, attrs):
        enrollment = attrs.get("enrollment", getattr(self.instance, "enrollment", None))
        subject = attrs.get("subject", getattr(self.instance, "subject", None))
        if enrollment and subject:
            offered = ClassSubject.objects.filter(
                school_class_id=enrollment.school_class_id, subject=subject
            ).exists()
            if not offered:
                raise serializers.ValidationError(
                    {"subject": "This subject is not taught in the student's class."}
                )
        if enrollment and enrollment.status != Enrollment.Status.ACTIVE:
            raise serializers.ValidationError(
                {"enrollment": "Cannot grade a withdrawn enrollment."}
            )
        return attrs
