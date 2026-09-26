from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("rating/", views.rating, name="rating"),
    path("login/", views.login_page, name="login"),
    path("admin/", views.admin_page, name="admin-panel"),
    path("admin-login/", views.admin_login, name="admin-login"),
    path("profile/", views.profile_page, name="profile"),
    path("archive/", views.archive_page, name="archive"),
]