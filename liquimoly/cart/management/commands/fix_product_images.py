import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from cart.models import Product  # Укажите ваше приложение и модель товара


class Command(BaseCommand):
    help = 'Создает уникальные копии изображений для регионов на основе Ашхабада (без заглушек).'

    def handle(self, *args, **options):
        products = Product.objects.all()
        self.stdout.write(f"Всего товаров в системе: {products.count()}")

        # 1. Индексируем существующие физические файлы товаров Ашхабада
        ashgabat_images = {}
        ashgabat_products = Product.objects.filter(place_id=1)  # Укажите связку с регионом

        for p in ashgabat_products:
            # Проверяем, существует ли файл физически на сервере
            if p.image and os.path.exists(p.image.path):
                ashgabat_images[p.slug] = p.image.path

        self.stdout.write(f"Найдено реальных фото в Ашхабаде: {len(ashgabat_images)}")

        copied_count = 0
        missing_count = 0

        # 2. Обходим все товары
        for product in products:
            # Если у товара уже есть свой физический файл — пропускаем его
            if product.image and os.path.exists(product.image.path):
                continue

            # Ищем фото-исходник из Ашхабада
            source_file_path = ashgabat_images.get(product.slug)

            if source_file_path and os.path.exists(source_file_path):
                ext = os.path.splitext(source_file_path)[1]
                
                # Формируем изолированный путь: product_images/mary/atf-1200-5l.png
                region_code = str(product.place.title_tm).lower() if hasattr(product, 'place') else 'default'
                new_rel_path = f"product_images/{region_code}/{product.slug}{ext}"
                new_full_path = os.path.join(settings.MEDIA_ROOT, new_rel_path)

                # Создаем папку региона и копируем файл
                os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
                shutil.copy2(source_file_path, new_full_path)

                # Обновляем путь только при успешном копировании
                product.image.name = new_rel_path
                product.save(update_fields=['image'])
                copied_count += 1
            else:
                # Если файла нет в Ашхабаде — просто логируем и оставляем как есть
                self.stdout.write(
                    self.style.WARNING(f"Файл не найден (Товар ID: {product.id}, Slug: {product.slug})")
                )
                missing_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Готово! Скопировано уникальных фото: {copied_count}. Отсутствуют в Ашхабаде: {missing_count}"
        ))
