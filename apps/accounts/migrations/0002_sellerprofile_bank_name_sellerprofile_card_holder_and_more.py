from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sellerprofile',
            name='bank_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='sellerprofile',
            name='card_holder',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='sellerprofile',
            name='card_number',
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
