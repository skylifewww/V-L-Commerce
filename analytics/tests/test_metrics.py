from django.test import SimpleTestCase
from analytics.services import ctr, conversion_rate, roi, cac, ltv


class MetricsTests(SimpleTestCase):
    def test_ctr(self):
        self.assertEqual(ctr(0, 0), 0.0)
        self.assertEqual(ctr(50, 100), 0.5)

    def test_conversion_rate(self):
        self.assertEqual(conversion_rate(10, 0), 0.0)
        self.assertEqual(conversion_rate(25, 100), 0.25)

    def test_roi(self):
        self.assertIsNone(roi(100.0, 0.0))
        self.assertAlmostEqual(roi(200.0, 100.0), 1.0)

    def test_cac(self):
        self.assertIsNone(cac(100.0, 0))
        self.assertEqual(cac(200.0, 10), 20.0)

    def test_ltv(self):
        self.assertEqual(ltv(50.0, 2.0, 0.5), 50.0)
