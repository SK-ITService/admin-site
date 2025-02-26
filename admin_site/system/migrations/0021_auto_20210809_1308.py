# Generated by Django 3.1.9 on 2021-08-09 13:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0020_image_version_updates'),
    ]

    operations = [
        migrations.AlterField(
            model_name='script',
            name='author',
            field=models.CharField(blank=True, max_length=255, verbose_name='author'),
        ),
        migrations.AlterField(
            model_name='script',
            name='author_email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='author email'),
        ),
    ]
