from django.test import TestCase, Client
from django.urls import reverse
from analytics.models import VisitorSession, TikTokCampaign


class UTMMiddlewareTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_utm_capture_creates_session_and_campaign(self):
        # Hit any page with UTM to trigger middleware
        resp = self.client.get(
            "/eshop/products/",
            {
                "utm_source": "tiktok",
                "utm_medium": "paid",
                "utm_campaign": "bf2025",
            },
        )
        self.assertEqual(resp.status_code, 200)
        session_key = self.client.session.session_key
        self.assertTrue(session_key)
        vs = VisitorSession.objects.filter(session_id=session_key).first()
        self.assertIsNotNone(vs)
        self.assertIsNotNone(vs.campaign)
        self.assertEqual(vs.campaign.utm_source, "tiktok")
        self.assertEqual(vs.campaign.utm_campaign, "bf2025")
        # Ensure campaign_id stored in session
        self.assertIn("campaign_id", self.client.session)
