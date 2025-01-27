# Generated by Django 5.1.4 on 2025-01-27 08:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ('-dt',), 'verbose_name': 'Заказ', 'verbose_name_plural': 'Список заказов'},
        ),
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=models.ImageField(blank=True, default='', upload_to='avatars', verbose_name='Аватар'),
        ),
    ]
