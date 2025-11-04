from django.db import models
from django import forms
from django.utils.functional import cached_property
from django.shortcuts import redirect
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.text import slugify
from django.conf import settings

from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from eshop.models import Product, Category, Customer, Order, OrderItem

class FeaturedProductsBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False)
    max_items = blocks.IntegerBlock(required=False, default=8, min_value=1, max_value=24)

    class Meta:
        icon = "star"
        label = "Featured Products"

class ProductGridBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False)
    category_slug = blocks.CharBlock(required=False, help_text="Slug категории для фильтрации (опционально)")
    show_prices = blocks.BooleanBlock(required=False, default=True)

    class Meta:
        icon = "table"
        label = "Product Grid"

class CallToActionBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    subtitle = blocks.TextBlock(required=False)
    button_text = blocks.CharBlock(default="Заказать")

    class Meta:
        icon = "placeholder"
        label = "Call To Action"

class TestimonialsBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False)
    items = blocks.ListBlock(
        blocks.StructBlock(
            [
                ("quote", blocks.TextBlock()),
                ("author", blocks.CharBlock(required=False)),
                ("avatar", ImageChooserBlock(required=False)),
            ]
        )
    )

    class Meta:
        icon = "openquote"
        label = "Testimonials"

class HomePage(Page):
    icon = "home"
    body = StreamField(
        [
            ("featured", FeaturedProductsBlock()),
            ("grid", ProductGridBlock()),
            ("testimonials", TestimonialsBlock()),
            ("cta", CallToActionBlock()),
        ],
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [FieldPanel("body")]

    subpage_types = ["landing.ProductListingPage", "landing.ProductDetailPage"]

    def get_context(self, request):
        ctx = super().get_context(request)
        cache_key = "homepage_featured_products"
        featured = cache.get(cache_key)
        if featured is None:
            featured = list(Product.objects.filter(is_active=True).order_by("-created_at")[:12])
            cache.set(cache_key, featured, 300)
        ctx["featured_products"] = featured
        return ctx

class ProductListingPage(Page):
    icon = "list-ul"
    intro = models.TextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro")]

    parent_page_types = ["landing.HomePage"]
    subpage_types = ["landing.ProductDetailPage"]

    def get_queryset(self, request):
        key = f"plist:{self.id}:q={request.GET.get('q','')}|c={request.GET.get('category','')}|pmin={request.GET.get('price_min','')}|pmax={request.GET.get('price_max','')}"
        cached_ids = cache.get(key)
        if cached_ids is not None:
            return Product.objects.filter(pk__in=cached_ids).select_related("category")

        qs = Product.objects.filter(is_active=True)
        q = request.GET.get("q")
        if q:
            qs = qs.filter(models.Q(name__icontains=q) | models.Q(description__icontains=q) | models.Q(sku__icontains=q))
        cat = request.GET.get("category")
        if cat:
            qs = qs.filter(category__slug=cat)
        price_min = request.GET.get("price_min")
        price_max = request.GET.get("price_max")
        if price_min:
            qs = qs.filter(price__gte=price_min)
        if price_max:
            qs = qs.filter(price__lte=price_max)
        qs = qs.order_by("-created_at", "-id")
        ids = list(qs.values_list("id", flat=True))
        cache.set(key, ids, 300)
        return Product.objects.filter(pk__in=ids).select_related("category")

    def get_context(self, request):
        ctx = super().get_context(request)
        qs = self.get_queryset(request)
        paginator = Paginator(qs, 24)
        page_param = request.GET.get("page")
        try:
            page_obj = paginator.page(page_param)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        ctx["page_obj"] = page_obj
        ctx["products"] = page_obj.object_list
        ctx["categories"] = Category.objects.all()
        ctx["q"] = request.GET.get("q", "")
        ctx["selected_category"] = request.GET.get("category")
        ctx["price_min"] = request.GET.get("price_min", "")
        ctx["price_max"] = request.GET.get("price_max", "")
        return ctx

class OrderRequestForm(forms.Form):
    full_name = forms.CharField(max_length=255)
    phone = forms.CharField(max_length=32)
    email = forms.EmailField(required=False)
    quantity = forms.IntegerField(min_value=1, initial=1)
    comment = forms.CharField(widget=forms.Textarea, required=False)

class ProductDetailPage(Page):
    icon = "tag"
    product = models.ForeignKey("eshop.Product", on_delete=models.PROTECT, related_name="detail_pages")

    content_panels = Page.content_panels + [FieldPanel("product")]

    parent_page_types = ["landing.HomePage", "landing.ProductListingPage"]
    subpage_types = []

    @cached_property
    def product_obj(self) -> Product:
        return Product.objects.select_related("category").get(pk=self.product_id)

    def clean(self):
        # Auto-sync title, slug, seo_title from product
        super().clean()
        if self.product_id:
            base = self.product_obj.name
            suffix = self.product_obj.sku or str(self.product_id)
            combined = f"{base}-{suffix}"
            self.title = self.product_obj.name
            self.seo_title = self.product_obj.name
            self.slug = slugify(combined)[:255]

    def get_context(self, request):
        ctx = super().get_context(request)
        ctx["product"] = self.product_obj
        rel_key = f"rel:{self.product_id}:{self.product_obj.category_id}"
        rel_ids = cache.get(rel_key)
        if rel_ids is None:
            rel_qs = Product.objects.filter(is_active=True, category=self.product_obj.category).exclude(pk=self.product_id)[:8]
            rel_ids = list(rel_qs.values_list("id", flat=True))
            cache.set(rel_key, rel_ids, 900)
        related = Product.objects.filter(pk__in=rel_ids)
        ctx["related_products"] = related
        ctx["order_form"] = OrderRequestForm()
        ctx["site_name"] = getattr(settings, "WAGTAIL_SITE_NAME", "")
        return ctx

    def serve(self, request):
        if request.method == "POST":
            form = OrderRequestForm(request.POST)
            if form.is_valid():
                customer, _ = Customer.objects.get_or_create(
                    full_name=form.cleaned_data["full_name"],
                    phone=form.cleaned_data["phone"],
                    defaults={"email": form.cleaned_data.get("email", "")},
                )
                order = Order.objects.create(customer=customer)
                OrderItem.objects.create(
                    order=order,
                    product=self.product_obj,
                    quantity=form.cleaned_data["quantity"],
                )
                return redirect(self.url)
            ctx = self.get_context(request)
            ctx["order_form"] = form
            return self.render(request, context_overrides=ctx)
        return super().serve(request)

