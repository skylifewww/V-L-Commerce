from __future__ import annotations

from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from django.utils.http import urlencode
from django.db import transaction
from django.http import HttpRequest

from .models import TikTokCampaign, VisitorSession


class UTMMiddleware(MiddlewareMixin):
    UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign")

    def process_request(self, request: HttpRequest):
        # Ensure session exists
        if not request.session.session_key:
            request.session.save()
        session_id = request.session.session_key

        # Capture UTM params if present
        q = request.GET
        has_utm = any(k in q for k in self.UTM_KEYS)
        if has_utm:
            utm_source = q.get("utm_source", "")[:64]
            utm_medium = q.get("utm_medium", "")[:64]
            utm_campaign = q.get("utm_campaign", "")[:128]
            name = utm_campaign or utm_source or "tiktok"
            with transaction.atomic():
                campaign, _ = TikTokCampaign.objects.get_or_create(
                    utm_source=utm_source or "tiktok",
                    utm_medium=utm_medium or "paid",
                    utm_campaign=utm_campaign or "",
                    defaults={"name": name},
                )
                # persist session record (idempotent per session)
                VisitorSession.objects.get_or_create(
                    session_id=session_id,
                    defaults={
                        "campaign": campaign,
                        "landing_page": request.build_absolute_uri("/") + ("?" + urlencode({k: q[k] for k in q}) if q else ""),
                    },
                )
                # keep campaign id in session for quick access when creating orders
                request.session["campaign_id"] = campaign.id
                request.session.modified = True
        return None
