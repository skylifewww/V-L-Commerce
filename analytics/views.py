from __future__ import annotations

from django.views import View
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.utils import timezone
from django.shortcuts import render
from django.conf import settings
from django.db.models.functions import TruncDate

from .models import TikTokCampaign, Conversion, VisitorSession
from .tiktok_api import TikTokAPI
from .services import roi as roi_fn, cac as cac_fn


class CampaignDashboardView(View):
    def get(self, request):
        since = timezone.now() - timezone.timedelta(days=30)
        by_campaign = (
            Conversion.objects.filter(created_at__gte=since)
            .values("campaign__id", "campaign__name")
            .annotate(conversions=Count("id"), revenue=Sum("conversion_value"))
            .order_by("-conversions")
        )
        return JsonResponse({"campaigns": list(by_campaign)})


class ConversionReportView(View):
    def get(self, request):
        since = timezone.now() - timezone.timedelta(days=30)
        sessions = VisitorSession.objects.filter(created_at__gte=since).count()
        conversions = Conversion.objects.filter(created_at__gte=since).count()
        conv_rate = (conversions / sessions) if sessions else 0.0
        return JsonResponse({"sessions": sessions, "conversions": conversions, "conversion_rate": conv_rate})


class ROICalculatorView(View):
    def get(self, request):
        # If cost is tracked via external stats, this endpoint expects ?cost=...
        cost = float(request.GET.get("cost", 0) or 0)
        revenue = float(Conversion.objects.aggregate(total=Sum("conversion_value")).get("total") or 0)
        roi = ((revenue - cost) / cost) if cost else None
        return JsonResponse({"revenue": revenue, "cost": cost, "roi": roi})


class CampaignDashboardHTMLView(View):
    def get(self, request):
        # Filters
        def _parse_date(s: str | None):
            if not s:
                return None
            try:
                return timezone.datetime.fromisoformat(s).date()
            except Exception:
                return None

        start_s = request.GET.get("start")
        end_s = request.GET.get("end")
        camp_filter = request.GET.get("campaign") or ""
        end = _parse_date(end_s) or timezone.now().date()
        start = _parse_date(start_s) or (end - timezone.timedelta(days=30))
        since = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
        until = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))

        conv_qs = Conversion.objects.filter(created_at__gte=since, created_at__lte=until)
        if camp_filter:
            conv_qs = conv_qs.filter(campaign__name__icontains=camp_filter)

        by_campaign_base = (
            conv_qs
            .values("campaign__id", "campaign__name")
            .annotate(conversions=Count("id"), revenue=Sum("conversion_value"))
            .order_by("-conversions")
        )
        by_day_campaign = (
            conv_qs
            .annotate(day=TruncDate("created_at"))
            .values("day", "campaign__name")
            .annotate(cnt=Count("id"))
            .order_by("day")
        )
        sessions_qs = VisitorSession.objects.filter(created_at__gte=since, created_at__lte=until)
        if camp_filter:
            sessions_qs = sessions_qs.filter(campaign__name__icontains=camp_filter)
        sessions_by_utm = (
            sessions_qs
            .values("campaign__utm_source")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")
        )

        # KPIs (totals)
        total_sessions = sessions_qs.count()
        total_conversions = conv_qs.count()
        total_revenue = float(conv_qs.aggregate(total=Sum("conversion_value")).get("total") or 0)

        # Spend via Marketing API (aggregate and per-campaign)
        spend = 0.0
        spend_by_campaign_id: dict[str, float] = {}
        try:
            api = TikTokAPI()
            if getattr(api, "token", None):
                rep = api.report_stats(advertiser_id=(settings.TIKTOK_ADVERTISER_ID or ""), start_date=str(start), end_date=str(end))
                # Try common response shapes
                data = rep.get("data") or {}
                rows = data.get("list") or data.get("report_list") or []
                for row in rows:
                    v = row.get("spend") or row.get("total_spend") or 0
                    try:
                        fv = float(v)
                        spend += fv
                        cid = str(row.get("campaign_id") or "")
                        if cid:
                            spend_by_campaign_id[cid] = spend_by_campaign_id.get(cid, 0.0) + fv
                    except Exception:
                        pass
        except Exception:
            pass

        roi = roi_fn(total_revenue, spend)
        cac_val = cac_fn(spend, total_conversions)

        pixel = getattr(settings, "TIKTOK_PIXEL_CODE", "")
        currency = getattr(settings, "CURRENCY_CODE", "USD")

        # Merge per-campaign spend with names using external_campaign_id mapping
        camp_map = {
            c.external_campaign_id: c.name
            for c in TikTokCampaign.objects.exclude(external_campaign_id="")
        }
        by_campaign = []
        for row in by_campaign_base:
            name = row.get("campaign__name") or "—"
            # try map by external id
            # find campaign object once
            spend_val = 0.0
            # Load campaign to read external id
            try:
                camp_obj = TikTokCampaign.objects.filter(id=row.get("campaign__id")).only("external_campaign_id").first()
                if camp_obj and camp_obj.external_campaign_id:
                    spend_val = spend_by_campaign_id.get(str(camp_obj.external_campaign_id), 0.0)
            except Exception:
                pass
            revenue_val = float(row.get("revenue") or 0)
            conv_cnt = int(row.get("conversions") or 0)
            by_campaign.append({
                "campaign__id": row.get("campaign__id"),
                "campaign__name": name,
                "conversions": conv_cnt,
                "revenue": revenue_val,
                "spend": spend_val,
                "roi": roi_fn(revenue_val, spend_val),
                "cac": cac_fn(spend_val, conv_cnt),
            })

        return render(
            request,
            "analytics/dashboard.html",
            {
                "by_campaign": list(by_campaign),
                "by_day_campaign": list(by_day_campaign),
                "sessions_by_utm": list(sessions_by_utm),
                "tiktok_pixel_code": pixel,
                "filters": {"start": str(start), "end": str(end), "campaign": camp_filter},
                "kpis": {
                    "sessions": total_sessions,
                    "conversions": total_conversions,
                    "revenue": total_revenue,
                    "spend": spend,
                    "roi": roi,
                    "cac": cac_val,
                },
                "currency_code": currency,
            },
        )


class DashboardCSVExportView(View):
    def get(self, request):
        # Reuse logic from HTML view filters, but output CSV rows per campaign
        # Parse filters
        def _parse_date(s: str | None):
            if not s:
                return None
            try:
                return timezone.datetime.fromisoformat(s).date()
            except Exception:
                return None
        start_s = request.GET.get("start")
        end_s = request.GET.get("end")
        camp_filter = request.GET.get("campaign") or ""
        end = _parse_date(end_s) or timezone.now().date()
        start = _parse_date(start_s) or (end - timezone.timedelta(days=30))
        since = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
        until = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))

        conv_qs = Conversion.objects.filter(created_at__gte=since, created_at__lte=until)
        if camp_filter:
            conv_qs = conv_qs.filter(campaign__name__icontains=camp_filter)
        by_campaign = (
            conv_qs
            .values("campaign__id", "campaign__name")
            .annotate(conversions=Count("id"), revenue=Sum("conversion_value"))
            .order_by("-conversions")
        )
        # Compute spend per campaign via external id mapping
        spend_by_campaign_id: dict[str, float] = {}
        try:
            api = TikTokAPI()
            if getattr(api, "token", None):
                rep = api.report_stats(advertiser_id=(settings.TIKTOK_ADVERTISER_ID or ""), start_date=str(start), end_date=str(end))
                data = rep.get("data") or {}
                rows = data.get("list") or data.get("report_list") or []
                for row in rows:
                    try:
                        fv = float(row.get("spend") or row.get("total_spend") or 0)
                        cid = str(row.get("campaign_id") or "")
                        if cid:
                            spend_by_campaign_id[cid] = spend_by_campaign_id.get(cid, 0.0) + fv
                    except Exception:
                        pass
        except Exception:
            pass

        # Build CSV
        import csv
        from io import StringIO
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["campaign_id", "campaign_name", "conversions", "revenue", "spend", "roi", "cac"])
        for row in by_campaign:
            camp_obj = TikTokCampaign.objects.filter(id=row.get("campaign__id")).only("external_campaign_id").first()
            spend_val = 0.0
            if camp_obj and camp_obj.external_campaign_id:
                spend_val = spend_by_campaign_id.get(str(camp_obj.external_campaign_id), 0.0)
            revenue_val = float(row.get("revenue") or 0)
            conv_cnt = int(row.get("conversions") or 0)
            w.writerow([
                row.get("campaign__id"),
                row.get("campaign__name") or "",
                conv_cnt,
                revenue_val,
                spend_val,
                roi_fn(revenue_val, spend_val) if spend_val else "",
                cac_fn(spend_val, conv_cnt) if conv_cnt else "",
            ])

        from django.http import HttpResponse
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = "attachment; filename=analytics_dashboard.csv"
        return resp
