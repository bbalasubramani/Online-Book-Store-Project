# Generated by Django 2.2 on 2024-11-16 10:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0002_auto_20241116_1616'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='transaction_id',
        ),
    ]
