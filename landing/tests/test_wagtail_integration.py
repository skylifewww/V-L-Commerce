from django.test import TestCase
from wagtail.models import Site
from landing.models import HomePage, ProductListingPage, ProductDetailPage
from eshop.models import Category, Product, Order, OrderItem

class TestWagtailEshopIntegration(TestCase):
    def setUp(self):
        root = Site.objects.get().root_page.specific
        self.home = HomePage(title="Home")
        root.add_child(instance=self.home)
        self.home.save_revision().publish()

        self.cat = Category.objects.create(name="Phones", slug="phones")
        self.prod = Product.objects.create(name="iPhone", sku="SKU1", price=100, stock=5, category=self.cat)

    def test_listing_and_detail_relationship(self):
        listing = ProductListingPage(title="Catalog")
        self.home.add_child(instance=listing)
        listing.save_revision().publish()

        detail = ProductDetailPage(title=self.prod.name, product=self.prod)
        listing.add_child(instance=detail)
        detail.save_revision().publish()

        self.assertEqual(detail.product_id, self.prod.id)
        self.assertEqual(self.prod.detail_pages.first().id, detail.id)

    def test_listing_filters(self):
        listing = ProductListingPage(title="Catalog")
        self.home.add_child(instance=listing)
        listing.save_revision().publish()

        request = self.client.get(listing.url + "?category=phones")
        self.assertEqual(request.status_code, 200)

        request = self.client.get(listing.url + "?q=iphone")
        self.assertEqual(request.status_code, 200)

    def test_auto_create_detail_page_and_slug_sync(self):
        # When a product is created (setUp), a detail page should be created under Home or Listing
        # Trigger signal op by committing a transaction-like behavior is tricky in tests, but Site tree exists
        # Create a listing to become preferred parent
        listing = ProductListingPage(title="Catalog")
        self.home.add_child(instance=listing)
        listing.save_revision().publish()

        p = Product.objects.create(name="Galaxy S24", sku="GAL-S24", price=200, stock=3, category=self.cat)
        # Some DB backends or timing can skip immediate page creation; ensure update triggers sync
        p.name = "Galaxy S24 Ultra"
        p.save()
        # Fetch related detail page
        page = p.detail_pages.first()
        self.assertIsNotNone(page)
        self.assertIn("galaxy-s24-ultra-gal-s24", page.slug)
        self.assertEqual(page.title, p.name)

    def test_pagination_on_listing(self):
        listing = ProductListingPage(title="Catalog")
        self.home.add_child(instance=listing)
        listing.save_revision().publish()

        # Seed 25 products to trigger 3 pages (12/12/1)
        # start from a high index to avoid sku collisions with existing ones
        for i in range(100, 125):
            Product.objects.create(name=f"Item {i}", sku=f"SKU{i}", price=10+i, stock=1, category=self.cat)

        # page 2
        resp = self.client.get(listing.url + "?page=2")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Стр.", resp.content.decode())

    def test_post_order_on_detail(self):
        listing = ProductListingPage(title="Catalog")
        self.home.add_child(instance=listing)
        listing.save_revision().publish()

        detail = ProductDetailPage(title=self.prod.name, product=self.prod)
        listing.add_child(instance=detail)
        detail.save_revision().publish()

        payload = {
            "full_name": "John Doe",
            "phone": "+380501112233",
            "email": "john@example.com",
            "quantity": 2,
            "comment": "please call"
        }
        resp = self.client.post(detail.url, payload, follow=True)
        self.assertEqual(resp.status_code, 200)
        # Check order and item created
        self.assertTrue(Order.objects.exists())
        self.assertTrue(OrderItem.objects.exists())

    def test_seo_meta_on_detail(self):
        listing = ProductListingPage(title="Catalog")
        self.home.add_child(instance=listing)
        listing.save_revision().publish()

        detail = ProductDetailPage(title=self.prod.name, product=self.prod)
        listing.add_child(instance=detail)
        detail.save_revision().publish()

        resp = self.client.get(detail.url)
        html = resp.content.decode()
        self.assertIn('<link rel="canonical"', html)
        self.assertIn('property="og:title"', html)
        self.assertIn('property="og:description"', html)
        self.assertIn('property="og:url"', html)
