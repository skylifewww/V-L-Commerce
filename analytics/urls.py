from django.urls import path
from .views import CampaignDashboardView, ConversionReportView, ROICalculatorView, CampaignDashboardHTMLView, DashboardCSVExportView

app_name = "analytics"

urlpatterns = [
    path("dashboard/", CampaignDashboardView.as_view(), name="dashboard"),
    path("dashboard/ui/", CampaignDashboardHTMLView.as_view(), name="dashboard_ui"),
    path("dashboard/export.csv", DashboardCSVExportView.as_view(), name="dashboard_export_csv"),
    path("conversions/", ConversionReportView.as_view(), name="conversions"),
    path("roi/", ROICalculatorView.as_view(), name="roi"),
]
