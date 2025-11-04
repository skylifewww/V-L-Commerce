from django.db import models

class TikTokMetric(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    advertiser_id = models.CharField(max_length=64)
    payload = models.JSONField()

    def __str__(self) -> str:
        return f"Metric {self.advertiser_id} at {self.created_at:%Y-%m-%d %H:%M}"
