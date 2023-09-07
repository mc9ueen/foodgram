# Generated by Django 3.2.20 on 2023-09-07 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название')),
                ('color', models.CharField(max_length=7, null=True, verbose_name='Цвет в HEX')),
                ('slug', models.SlugField(max_length=200, null=True, verbose_name='Уникальный slug')),
            ],
            options={
                'verbose_name': 'Тег',
                'verbose_name_plural': 'Теги',
            },
        ),
    ]
