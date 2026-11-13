import os
import secrets
from django.core.management.base import BaseCommand
from django.conf import settings
from cart.models import Product 

class Command(BaseCommand):
    help = 'Переименовывает все существующие изображения товаров в UUID'

    def handle(self, *args, **kwargs):
        products = Product.objects.exclude(image='')
        total = products.count()

        if total == 0:
            self.stdout.write(self.style.WARNING('Нет товаров с изображениями для переименования.'))
            return

        self.stdout.write(self.style.NOTICE(f'Найдено {total} товаров. Начинаем переименование...'))

        updated_count = 0
        missing_count = 0

        for product in products:
            try:
                old_path = product.image.path
            except ValueError:
                continue

            if os.path.exists(old_path):
                ext = old_path.split('.')[-1]
                new_name = f"{secrets.token_hex(7)}.{ext}"
                new_rel_path = f"product_images/{new_name}"
                new_abs_path = os.path.join(settings.MEDIA_ROOT, 'product_images', new_name)
                
                os.makedirs(os.path.dirname(new_abs_path), exist_ok=True)
                
                os.rename(old_path, new_abs_path)
                
                product.image.name = new_rel_path
                product.save(update_fields=['image'])
                
                updated_count += 1
            else:
                missing_count += 1
                self.stdout.write(self.style.ERROR(f'Файл не найден: {old_path} (Товар ID: {product.pk})'))

        self.stdout.write(self.style.SUCCESS(f'Успешно переименовано картинок: {updated_count}'))
        if missing_count > 0:
            self.stdout.write(self.style.WARNING(f'Не найдено файлов на диске: {missing_count}'))