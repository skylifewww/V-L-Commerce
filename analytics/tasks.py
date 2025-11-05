from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .tiktok_api import TikTokAPI
from .models import TikTokMetric, Conversion
from django.db.models import Sum
import os
import requests
from django.core.mail import send_mail

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def fetch_tiktok_metrics(self, advertiser_id: str) -> dict:
    api = TikTokAPI()
    end = timezone.now().date()
    start = end - timedelta(days=1)
    try:
        stats = api.report_stats(advertiser_id=advertiser_id, start_date=str(start), end_date=str(end))
        TikTokMetric.objects.create(advertiser_id=advertiser_id, payload=stats)
        return {"advertiser_id": advertiser_id, "status": "ok"}
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True)
def alert_on_conversion_drop(self) -> dict:
    now = timezone.now()
    last7 = now - timedelta(days=7)
    prev7 = now - timedelta(days=14)
    conv_last = Conversion.objects.filter(created_at__gte=last7).count()
    conv_prev = Conversion.objects.filter(created_at__lt=last7, created_at__gte=prev7).count()
    drop = None
    if conv_prev > 0:
        drop = (conv_prev - conv_last) / conv_prev
    # Simplified alert: log/return payload; integrate with email/slack as needed
    payload = {"last7": conv_last, "prev7": conv_prev, "drop": drop}

    try:
        threshold = float(os.getenv("CONVERSION_DROP_THRESHOLD", "0.3"))
        if drop is not None and drop >= threshold:
            # Slack
            webhook = os.getenv("SLACK_WEBHOOK_URL", "")
            if webhook:
                text = f":warning: Conversion drop alert: last7={conv_last}, prev7={conv_prev}, drop={drop:.2%}"
                try:
                    requests.post(webhook, json={"text": text}, timeout=5)
                except Exception:
                    pass
            # Email
            recipients = [e.strip() for e in os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",") if e.strip()]
            if recipients:
                subject = "Conversion drop alert"
                body = f"Conversions last7={conv_last}, prev7={conv_prev}, drop={drop:.2%}"
                try:
                    send_mail(subject, body, os.getenv("ALERT_EMAIL_FROM", "alerts@example.com"), recipients, fail_silently=True)
                except Exception:
                    pass
    except Exception:
        pass

    return payload


@shared_task(bind=True)
def alert_on_kpi_breach(self) -> dict:
    """Alert when CR or ROI dip below thresholds over the last 7 days."""
    now = timezone.now()
    start = (now - timedelta(days=7)).date()
    end = now.date()

    # Metrics
    from .models import VisitorSession
    sessions = VisitorSession.objects.filter(created_at__date__gte=start, created_at__date__lte=end).count()
    conversions = Conversion.objects.filter(created_at__date__gte=start, created_at__date__lte=end).count()
    revenue = float(Conversion.objects.filter(created_at__date__gte=start, created_at__date__lte=end).aggregate(total=Sum("conversion_value")).get("total") or 0)

    spend = 0.0
    try:
        api = TikTokAPI()
        if getattr(api, "token", None):
            rep = api.report_stats(advertiser_id=(getattr(settings, "TIKTOK_ADVERTISER_ID", "") or ""), start_date=str(start), end_date=str(end))
            data = rep.get("data") or {}
            rows = data.get("list") or data.get("report_list") or []
            for row in rows:
                try:
                    spend += float(row.get("spend") or row.get("total_spend") or 0)
                except Exception:
                    pass
    except Exception:
        pass

    cr = (conversions / sessions) if sessions else 0.0
    roi_val = ((revenue - spend) / spend) if spend else None

    result = {"sessions": sessions, "conversions": conversions, "revenue": revenue, "spend": spend, "cr": cr, "roi": roi_val}

    # Thresholds
    try:
        cr_thr = float(os.getenv("CR_ALERT_THRESHOLD", "0.02"))
        roi_thr = float(os.getenv("ROI_ALERT_THRESHOLD", "0.2"))
        breach_msgs = []
        if cr < cr_thr:
            breach_msgs.append(f"CR below threshold: cr={cr:.2%} < {cr_thr:.2%}")
        if roi_val is not None and roi_val < roi_thr:
            breach_msgs.append(f"ROI below threshold: roi={roi_val:.2f} < {roi_thr:.2f}")
        if breach_msgs:
            text = "; ".join(breach_msgs) + f" | sessions={sessions}, conv={conversions}, revenue={revenue:.2f}, spend={spend:.2f}"
            # Slack
            webhook = os.getenv("SLACK_WEBHOOK_URL", "")
            if webhook:
                try:
                    requests.post(webhook, json={"text": ":rotating_light: KPI Alert: " + text}, timeout=5)
                except Exception:
                    pass
            # Email
            recipients = [e.strip() for e in os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",") if e.strip()]
            if recipients:
                try:
                    send_mail("KPI Alert", text, os.getenv("ALERT_EMAIL_FROM", "alerts@example.com"), recipients, fail_silently=True)
                except Exception:
                    pass
    except Exception:
        pass

    return result
