from django.db import models
from django import forms
from django.utils.functional import cached_property
from django.shortcuts import redirect, render
from django.core.cache import cache
from django.core.mail import mail_admins
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.text import slugify
from django.conf import settings
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail import blocks
from wagtail.blocks import RichTextBlock
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


class HeroBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True)
    subtitle = blocks.TextBlock(required=False)
    price = blocks.DecimalBlock(required=False, max_digits=10, decimal_places=2)
    old_price = blocks.DecimalBlock(required=False, max_digits=10, decimal_places=2)
    image = ImageChooserBlock(required=False)
    cta_text = blocks.CharBlock(required=False, default="Замовити зараз")
    cta_anchor = blocks.CharBlock(required=False, default="#form", help_text="Якорь ссылки, например #form")
    use_product_image = blocks.BooleanBlock(required=False, default=True, help_text="Если задан product у страницы — использовать его изображение")
    use_product_price = blocks.BooleanBlock(required=False, default=True, help_text="Если задан product у страницы — использовать его цену")

    class Meta:
        icon = "pick"
        label = "Hero"


class GalleryBlock(blocks.StructBlock):
    images = blocks.ListBlock(ImageChooserBlock())

    class Meta:
        icon = "image"
        label = "Gallery"


class SimpleImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True)
    alt = blocks.CharBlock(required=False, help_text="Alt-текст (опционально)")

    class Meta:
        icon = "image"
        label = "Banner"

class TitleBannerBlock(blocks.StructBlock):
    top_text = blocks.CharBlock(required=False, help_text="Верхняя надпись (опционально)")
    image = ImageChooserBlock(required=True, help_text="Изображение на всю ширину блока")
    bottom_text = blocks.CharBlock(required=False, help_text="Нижняя надпись (опционально)")
    text_color = blocks.CharBlock(required=False, default="#cc5a12", help_text="Цвет надписей: например #ff5500 или rgb(255,85,0)")

    class Meta:
        icon = "title"
        label = "Title Banner"


class VideoBlock(blocks.StructBlock):
    youtube_id = blocks.CharBlock(required=True, help_text="YouTube ID, например wKj3LlQ89IA")
    height = blocks.IntegerBlock(required=False, default=540)

    class Meta:
        icon = "media"
        label = "YouTube Video"


class AnimatedImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True, help_text="Загрузите GIF для анимации")
    alt = blocks.CharBlock(required=False, help_text="Alt-текст (опционально)")
    alignment = blocks.ChoiceBlock(
        required=False,
        choices=(
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ),
        default="center",
        help_text="Выравнивание блока на странице",
    )

    class Meta:
        icon = "image"
        label = "Animated Image (GIF)"


class TextSectionBlock(blocks.StructBlock):
    html = RichTextBlock(features=["h2", "h3", "bold", "italic", "link", "ol", "ul", "hr"]) 

    class Meta:
        icon = "doc-full"
        label = "Text Section"


class BenefitItemBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    description = blocks.TextBlock()
    icon = ImageChooserBlock(required=False)


class BenefitsBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, default="Головні переваги")
    items = blocks.ListBlock(BenefitItemBlock())

    class Meta:
        icon = "tick"
        label = "Benefits"


class StepItemBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    description = blocks.TextBlock()


class StepsBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, default="Як замовити?")
    items = blocks.ListBlock(StepItemBlock())

    class Meta:
        icon = "list-ol"
        label = "Steps"


class PromoBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True)
    text = blocks.TextBlock(required=True)
    price = blocks.DecimalBlock(required=False, max_digits=10, decimal_places=2)
    old_price = blocks.DecimalBlock(required=False, max_digits=10, decimal_places=2)
    cta_text = blocks.CharBlock(required=False, default="Замовити зараз")
    cta_anchor = blocks.CharBlock(required=False, default="#form", help_text="Якорь ссылки, например #form")
    use_product_price = blocks.BooleanBlock(required=False, default=True)

    class Meta:
        icon = "pick"
        label = "Promo Text + Price"

class FormBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, default="ЗАЛИШИТИ ЗАЯВКУ")
    subtitle = blocks.TextBlock(required=False)
    submit_text = blocks.CharBlock(required=False, default="Залишити заявку")
    show_full_name = blocks.BooleanBlock(required=False, default=True, label="Показать ФИО")
    show_country = blocks.BooleanBlock(required=False, default=False, label="Показать страну")
    show_phone = blocks.BooleanBlock(required=False, default=True, label="Показать телефон")
    show_email = blocks.BooleanBlock(required=False, default=False, label="Показать Email")
    show_quantity = blocks.BooleanBlock(required=False, default=False, label="Показать количество")
    show_comment = blocks.BooleanBlock(required=False, default=False, label="Показать комментарий")

    class Meta:
        icon = "form"
        label = "Order Form"

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

    subpage_types = [
        "landing.ProductLandingPage",
        "landing.ProductListingPage",
        "landing.ProductDetailPage",
    ]

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
    COUNTRY_CHOICES = (
        ("UA", "Ukraine"),
        ("PL", "Poland"),
        ("DE", "Germany"),
        ("CZ", "Czechia"),
        ("SK", "Slovakia"),
        ("RO", "Romania"),
        ("HU", "Hungary"),
        ("LT", "Lithuania"),
        ("LV", "Latvia"),
        ("EE", "Estonia"),
    )
    full_name = forms.CharField(max_length=255)
    phone = forms.CharField(max_length=32)
    email = forms.EmailField(required=False)
    quantity = forms.IntegerField(min_value=1, initial=1, required=False)
    comment = forms.CharField(widget=forms.Textarea, required=False)
    country = forms.ChoiceField(choices=COUNTRY_CHOICES, initial="UA")

    def clean_phone(self):
        import re
        phone = self.cleaned_data.get("phone", "").strip()
        country = self.cleaned_data.get("country", "UA")
        patterns = {
            "UA": r"^\+?380\s?\(?\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}$",
            "PL": r"^\+?48\s?\d{3}[\s-]?\d{3}[\s-]?\d{3}$",
        }
        pat = patterns.get(country)
        if pat and not re.match(pat, phone):
            raise forms.ValidationError("Enter a valid phone for selected country.")
        return phone

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
            # Render directly to avoid binding StreamField from POST data
            return render(request, self.get_template(request), ctx)
        return super().serve(request)


class ProductLandingPage(Page):
    """Template-driven product landing page editors can fill."""

    icon = "form"
    template = "landing/product_landing_page.html"  # Основной шаблон
    
    product = models.ForeignKey("eshop.Product", on_delete=models.PROTECT, related_name="landing_pages", null=True, blank=True)
    theme = models.CharField(
        max_length=10,
        choices=(
            ("light", "Light"),
            ("dark", "Dark"),
        ),
        default="light",
    )
    font_family = models.CharField(
        max_length=20,
        choices=(
            ("system", "System Default"),
            ("inter", "Inter"),
            ("roboto", "Roboto"),
            ("montserrat", "Montserrat"),
        ),
        default="system",
    )
    # Typography controls
    heading_weight = models.CharField(
        max_length=3,
        choices=(("300","300"),("400","400"),("500","500"),("600","600"),("700","700"),("800","800")),
        default="600",
    )
    heading_line_height = models.DecimalField(max_digits=3, decimal_places=2, default=1.25)
    title_weight = models.CharField(
        max_length=3,
        choices=(("300","300"),("400","400"),("500","500"),("600","600")),
        default="400",
    )
    title_line_height = models.DecimalField(max_digits=3, decimal_places=2, default=1.30)
    body_weight = models.CharField(
        max_length=3,
        choices=(("300","300"),("400","400"),("500","500")),
        default="300",
    )
    body_line_height = models.DecimalField(max_digits=3, decimal_places=2, default=1.30)
    success_page = models.ForeignKey("landing.OrderSuccessPage", on_delete=models.SET_NULL, null=True, blank=True)
    
    # Динамический выбор шаблона
    def get_template(self, request):
        if self.product:  # Если привязан товар
            return "landing/product_landing_page.html" 
        return "landing/general_landing_page.html"  # Шаблон без привязки к товару
    
    content_panels = Page.content_panels + [
        FieldPanel("product"),
        FieldPanel("theme"),
        FieldPanel("font_family"),
        FieldPanel("heading_weight"),
        FieldPanel("heading_line_height"),
        FieldPanel("title_weight"),
        FieldPanel("title_line_height"),
        FieldPanel("body_weight"),
        FieldPanel("body_line_height"),
        FieldPanel("success_page"),
        FieldPanel("body"),
    ]

    # Use Wagtail's default page form
    base_form_class = WagtailAdminPageForm
    
    class Meta:
        verbose_name = "Product Landing Page"
        verbose_name_plural = "Product Landing Pages"
    body = StreamField(
        [
            ("hero", HeroBlock()),
            ("gallery", GalleryBlock()),
            ("image", SimpleImageBlock()),
            ("title_banner", TitleBannerBlock()),
            ("video", VideoBlock()),
            ("animated", AnimatedImageBlock()),
            ("text", TextSectionBlock()),
            ("promo", PromoBlock()),
            ("benefits", BenefitsBlock()),
            ("steps", StepsBlock()),
            ("form", FormBlock()),
        ],
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("product"),
        FieldPanel("theme"),
        FieldPanel("font_family"),
        FieldPanel("heading_weight"),
        FieldPanel("heading_line_height"),
        FieldPanel("title_weight"),
        FieldPanel("title_line_height"),
        FieldPanel("body_weight"),
        FieldPanel("body_line_height"),
        FieldPanel("success_page"),
        FieldPanel("body"),
    ]

    parent_page_types = ["landing.HomePage", "landing.ProductListingPage"]
    subpage_types = []

    @cached_property
    def product_obj(self) -> Product | None:
        if not self.product_id:
            return None
        return Product.objects.select_related("category").filter(pk=self.product_id).first()

    def get_context(self, request):
        ctx = super().get_context(request)
        ctx["site_name"] = getattr(settings, "WAGTAIL_SITE_NAME", "")
        # Всегда добавляем product в контекст (даже если None)
        ctx["product"] = self.product_obj
        ctx["theme"] = self.theme
        ctx["font_family"] = self.font_family
        ctx["heading_weight"] = self.heading_weight
        ctx["heading_line_height"] = float(self.heading_line_height)
        ctx["title_weight"] = self.title_weight
        ctx["title_line_height"] = float(self.title_line_height)
        ctx["body_weight"] = self.body_weight
        ctx["body_line_height"] = float(self.body_line_height)
        # Simple order form (same fields as ProductDetailPage)
        ctx["order_form"] = OrderRequestForm()
        return ctx

    def serve(self, request):
        if request.method == "POST":
            form = OrderRequestForm(request.POST)
            if form.is_valid() and self.product_obj:
                customer, _ = Customer.objects.get_or_create(
                    full_name=form.cleaned_data["full_name"],
                    phone=form.cleaned_data["phone"],
                    defaults={"email": form.cleaned_data.get("email", "")},
                )
                order = Order.objects.create(customer=customer)
                OrderItem.objects.create(
                    order=order,
                    product=self.product_obj,
                    quantity=form.cleaned_data.get("quantity", 1),
                )
                try:
                    mail_admins(
                        subject=f"New order #{order.id}",
                        message=f"Product: {self.product_obj.name}\nQty: {form.cleaned_data.get('quantity', 1)}\nCustomer: {customer.full_name} / {customer.phone}",
                        fail_silently=True,
                    )
                except Exception:
                    pass
                if self.success_page_id:
                    return redirect(self.success_page.url)
                return redirect(self.url)
            ctx = self.get_context(request)
            ctx["order_form"] = form
            return self.render(request, context_overrides=ctx)
        return super().serve(request)


class OrderSuccessPage(Page):
    icon = "tick"  # Changed to match Wagtail's icon set
    template = "landing/order_success_page.html"
    parent_page_types = ["landing.HomePage", "landing.ProductListingPage", "landing.ProductLandingPage"]
    subpage_types = []
    
    # Ensure it's available in the add page menu
    class Meta:
        verbose_name = "Order Success Page"
        verbose_name_plural = "Order Success Pages"
