from unittest.mock import patch, MagicMock
from django.test import TestCase
from analytics.tiktok_api import TikTokAPI


class TikTokAPITests(TestCase):
    @patch('analytics.tiktok_api.requests.post')
    def test_list_campaigns_and_report_stats(self, mpost):
        mresp = MagicMock()
        mresp.json.return_value = {"code": 0, "data": {"list": []}}
        mresp.raise_for_status.return_value = None
        mpost.return_value = mresp

        api = TikTokAPI(access_token="dummy")
        r1 = api.list_campaigns(advertiser_id="123")
        r2 = api.report_stats(advertiser_id="123", start_date="2025-01-01", end_date="2025-01-02")
        self.assertEqual(r1["code"], 0)
        self.assertEqual(r2["code"], 0)
        self.assertGreaterEqual(mpost.call_count, 2)

    @patch('analytics.tiktok_api.requests.post')
    def test_send_conversion(self, mpost):
        mresp = MagicMock()
        mresp.json.return_value = {"code": 0, "data": {"success": 1}}
        mresp.raise_for_status.return_value = None
        mpost.return_value = mresp

        api = TikTokAPI(access_token="dummy")
        api.pixel_code = "PIXEL123"
        out = api.send_conversion("CompletePayment", {"value": 10, "currency": "USD", "order_id": "abc"})
        self.assertEqual(out.get("code"), 0)
        self.assertTrue(mpost.called)
