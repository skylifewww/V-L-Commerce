from celery import shared_task

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def fetch_tiktok_metrics(self, advertiser_id: str) -> dict:
    # TODO: integrate with TikTok API client
    return {"advertiser_id": advertiser_id, "status": "ok"}
