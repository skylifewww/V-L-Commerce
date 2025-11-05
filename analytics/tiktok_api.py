from __future__ import annotations

import os
import json
import time
from typing import Any, Dict, Optional

import requests
from django.conf import settings

DEFAULT_BASE = "https://business-api.tiktok.com/open_api"


class TikTokAPI:
    def __init__(self, access_token: Optional[str] = None, base_url: str = DEFAULT_BASE):
        self.base_url = base_url.rstrip("/")
        self.token = access_token or getattr(settings, "TIKTOK_ACCESS_TOKEN", None) or os.getenv("TIKTOK_ACCESS_TOKEN")
        self.pixel_code = getattr(settings, "TIKTOK_PIXEL_CODE", None) or os.getenv("TIKTOK_PIXEL_CODE")
        self.timeout = 15

    # ---- Marketing API examples ----
    def _headers(self) -> Dict[str, str]:
        return {"Access-Token": self.token, "Content-Type": "application/json"}

    def list_campaigns(self, advertiser_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/v1.3/campaign/get/"
        payload = {"advertiser_id": advertiser_id}
        r = requests.post(url, headers=self._headers(), data=json.dumps(payload), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def report_stats(self, advertiser_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        url = f"{self.base_url}/v1.3/report/integrated/get/"
        payload = {
            "advertiser_id": advertiser_id,
            "report_type": "BASIC",
            "dimensions": ["campaign_id", "stat_time_day"],
            "metrics": ["spend", "impressions", "clicks", "conversions"],
            "start_date": start_date,
            "end_date": end_date,
        }
        r = requests.post(url, headers=self._headers(), data=json.dumps(payload), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ---- Events API conversion tracking ----
    def send_conversion(self, event: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        if not self.pixel_code:
            return {"status": "skipped", "reason": "no_pixel"}
        url = f"{self.base_url}/v1.3/pixel/track/"
        payload = {"pixel_code": self.pixel_code, "event": event, "event_id": properties.get("event_id", str(int(time.time()*1000))), "properties": properties}
        r = requests.post(url, headers=self._headers(), data=json.dumps(payload), timeout=self.timeout)
        r.raise_for_status()
        return r.json()
