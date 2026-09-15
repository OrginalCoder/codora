from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_sellerprofile_bank_name_sellerprofile_card_holder_and_more'),
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='buyer_note',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='order',
            name='receipt_image',
            field=models.ImageField(blank=True, null=True, upload_to='receipts/'),
        ),
        migrations.AddField(
            model_name='order',
            name='receipt_uploaded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='rejection_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='order',
            name='seller',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='seller_direct_orders', to='accounts.sellerprofile'),
        ),
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(default='direct_card', max_length=50),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending_verification', 'Chek tekshirilmoqda'), ('paid', 'Tasdiqlangan'), ('rejected', 'Rad etilgan'), ('cancelled', 'Bekor qilindi')], default='pending_verification', max_length=25),
        ),
    ]
