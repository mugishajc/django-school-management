from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("teachers", views.TeacherViewSet)
router.register("students", views.StudentViewSet)
router.register("subjects", views.SubjectViewSet)
router.register("terms", views.AcademicTermViewSet)
router.register("classes", views.SchoolClassViewSet, basename="schoolclass")
router.register("class-subjects", views.ClassSubjectViewSet)
router.register("enrollments", views.EnrollmentViewSet)
router.register("grades", views.GradeViewSet)

urlpatterns = router.urls
