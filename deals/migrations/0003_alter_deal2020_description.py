# Generated by Django 3.2.9 on 2021-11-12 18:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deals', '0002_alter_deal2021_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deal2020',
            name='description',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
