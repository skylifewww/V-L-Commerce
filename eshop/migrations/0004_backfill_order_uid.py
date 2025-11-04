from django.db import migrations, models
import uuid


def backfill_order_uid(apps, schema_editor):
    Order = apps.get_model('eshop', 'Order')
    for order in Order.objects.filter(uid__isnull=True):
        order.uid = uuid.uuid4()
        order.save(update_fields=["uid"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("eshop", "0003_alter_customer_phone_alter_orderitem_price"),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='uid',
            field=models.UUIDField(null=True, blank=True, unique=True, editable=False),
        ),
        migrations.RunPython(backfill_order_uid, reverse_code=noop),
        migrations.AlterField(
            model_name='order',
            name='uid',
            field=models.UUIDField(null=False, blank=False, unique=True, editable=False),
        ),
    ]
