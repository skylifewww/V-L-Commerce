from django.db import models

class TikTokMetric(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    advertiser_id = models.CharField(max_length=64)
    payload = models.JSONField()

    def __str__(self) -> str:
        return f"Metric {self.advertiser_id} at {self.created_at:%Y-%m-%d %H:%M}"


class TikTokCampaign(models.Model):
    name = models.CharField(max_length=255)
    utm_source = models.CharField(max_length=64, db_index=True)
    utm_medium = models.CharField(max_length=64, blank=True)
    utm_campaign = models.CharField(max_length=128, blank=True, db_index=True)
    external_campaign_id = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("utm_source", "utm_medium", "utm_campaign")

    def __str__(self) -> str:
        return f"{self.name} ({self.utm_source}/{self.utm_medium}/{self.utm_campaign})"


class VisitorSession(models.Model):
    session_id = models.CharField(max_length=64, db_index=True)
    campaign = models.ForeignKey("TikTokCampaign", null=True, blank=True, on_delete=models.SET_NULL, related_name="sessions")
    landing_page = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Session {self.session_id}"


class Conversion(models.Model):
    order = models.OneToOneField("eshop.Order", on_delete=models.CASCADE, related_name="conversion")
    campaign = models.ForeignKey("TikTokCampaign", null=True, blank=True, on_delete=models.SET_NULL, related_name="conversions")
    conversion_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Conversion for Order #{self.order_id}"
