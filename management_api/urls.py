from django.urls import path

from .views import CategoryDetailView, CategoryListView, FaydaReviewView, OverviewView, StartupReviewView, UserDetailView, UserListView, CampaignMonitorView, WithdrawalManagementView

urlpatterns = [
    path("overview/", OverviewView.as_view(), name="management_overview"),
    path("categories/", CategoryListView.as_view(), name="management_categories"),
    path("categories/<uuid:category_id>/", CategoryDetailView.as_view(), name="management_category_detail"),
    path("fayda/", FaydaReviewView.as_view(), name="management_fayda"),
    path("fayda/<uuid:startup_id>/", FaydaReviewView.as_view(), name="management_fayda_review"),
    path("startups/", StartupReviewView.as_view(), name="management_startups"),
    path("startups/<uuid:startup_id>/", StartupReviewView.as_view(), name="management_startup_review"),
    path("withdrawals/", WithdrawalManagementView.as_view(), name="management_withdrawals"),
    path("withdrawals/<uuid:withdrawal_id>/", WithdrawalManagementView.as_view(), name="management_withdrawal_detail"),
    path("users/", UserListView.as_view(), name="management_users"),
    path("users/<uuid:user_id>/", UserDetailView.as_view(), name="management_user_detail"),
    path("campaigns/", CampaignMonitorView.as_view(), name="management_campaigns"),
    path("campaigns/<uuid:campaign_id>/", CampaignMonitorView.as_view(), name="management_campaign_detail"),
]
