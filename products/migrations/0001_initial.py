# Generated by Django 5.1.6 on 2025-03-10 17:41

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_approved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='products.category')),
            ],
            options={
                'verbose_name_plural': 'Categories',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('unit', models.CharField(choices=[('kg', 'Kilograms'), ('g', 'Grams'), ('mg', 'Milligrams'), ('lb', 'Pounds'), ('oz', 'Ounces'), ('l', 'Liters'), ('ml', 'Milliliters'), ('gal', 'Gallons'), ('pt', 'Pints'), ('qt', 'Quarts'), ('pcs', 'Pieces'), ('dozen', 'Dozen'), ('half_dozen', 'Half Dozen'), ('pair', 'Pair'), ('bundle', 'Bundle'), ('box', 'Box'), ('bag', 'Bag'), ('crate', 'Crate'), ('basket', 'Basket'), ('jar', 'Jar'), ('bottle', 'Bottle'), ('bunch', 'Bunch'), ('head', 'Head'), ('stick', 'Stick'), ('clove', 'Clove'), ('slice', 'Slice')], help_text='Select the unit used to measure the product (e.g., kilograms, liters, pieces).', max_length=15, verbose_name='Unit of Measurement')),
                ('stock_quantity', models.PositiveIntegerField(default=0)),
                ('is_organic', models.BooleanField(default=False)),
                ('is_available', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='products.category')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='product_images/')),
                ('is_primary', models.BooleanField(default=False)),
                ('alt_text', models.CharField(blank=True, max_length=100)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='products.product')),
            ],
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['price'], name='idx_product_price'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['seller'], name='idx_product_seller'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['stock_quantity'], name='idx_product_stock'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['is_available'], name='idx_product_available'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['created_at'], name='idx_product_created'),
        ),
    ]
