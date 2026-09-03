from django.urls import path

from .views import StartupApplicationView, StartupStatusView

urlpatterns = [
    path("apply/", StartupApplicationView.as_view(), name="startup_apply"),
    path("status/", StartupStatusView.as_view(), name="startup_status"),
]
