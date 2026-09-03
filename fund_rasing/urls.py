from django.urls import path

from .views import CampaignContributionListView, CampaignCreateView, CampaignDetailView, CampaignLikeView, CampaignListView, CampaignManageView, CampaignPitchDeckView, CampaignReportView, ChapaPaymentCallbackView, ChapaPaymentInitializeView, ChapaPaymentOptionsView, ChapaPaymentStatusView, MyCampaignListView, WithdrawalRequestView

urlpatterns = [
    path("", CampaignListView.as_view(), name="campaign_list"),
    path("create/", CampaignCreateView.as_view(), name="campaign_create"),
    path("mine/", MyCampaignListView.as_view(), name="my_campaigns"),
    path("withdrawals/", WithdrawalRequestView.as_view(), name="withdrawal_requests"),
    path("<uuid:campaign_id>/pitch-deck/", CampaignPitchDeckView.as_view(), name="campaign_pitch_deck"),
    path("<uuid:campaign_id>/", CampaignDetailView.as_view(), name="campaign_detail"),
    path("<uuid:campaign_id>/manage/", CampaignManageView.as_view(), name="campaign_manage"),
    path("<uuid:campaign_id>/contributions/", CampaignContributionListView.as_view(), name="campaign_contributions"),
    path("<uuid:campaign_id>/like/", CampaignLikeView.as_view(), name="campaign_like"),
    path("<uuid:campaign_id>/report/", CampaignReportView.as_view(), name="campaign_report"),
    path("<uuid:campaign_id>/payments/chapa/initialize/", ChapaPaymentInitializeView.as_view(), name="chapa_payment_initialize"),
    path("payments/chapa/callback/", ChapaPaymentCallbackView.as_view(), name="chapa_payment_callback"),
    path("payments/chapa/options/", ChapaPaymentOptionsView.as_view(), name="chapa_payment_options"),
    path("payments/chapa/<str:tx_ref>/", ChapaPaymentStatusView.as_view(), name="chapa_payment_status"),
]
