from django.urls import path

from .views import ChangePasswordView, LoginView, ProfileView, RefreshSessionView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="account_register"),
    path("login/", LoginView.as_view(), name="account_login"),
    path("refresh/", RefreshSessionView.as_view(), name="account_refresh"),
    path("me/", ProfileView.as_view(), name="account_profile"),
    path("password/", ChangePasswordView.as_view(), name="account_change_password"),
]
