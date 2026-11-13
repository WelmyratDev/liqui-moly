import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from cart.models import Product  # Укажите ваше приложение и модель товара


class Command(BaseCommand):
    help = 'Переносит файлы из корня product_images в ashgabat и распределяет уникальные копии по регионам.'

    def handle(self, *args, **options):
        base_dir = os.path.join(settings.MEDIA_ROOT, 'product_images')
        ashgabat_dir = os.path.join(base_dir, 'ashgabat')
        os.makedirs(ashgabat_dir, exist_ok=True)

        # 1. Перемещаем все разбросанные файлы из корня product_images в папку ashgabat
        moved_count = 0
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            # Переносу подлежат только файлы (папки ahal, dasoguz и т.д. не трогаем)
            if os.path.isfile(item_path):
                target_path = os.path.join(ashgabat_dir, item)
                shutil.move(item_path, target_path)
                moved_count += 1

        self.stdout.write(f"Перемещено файлов в папку ashgabat: {moved_count}")

        # 2. Индексируем файлы в папки ashgabat
        ashgabat_files = os.listdir(ashgabat_dir)

        # 3. Обновляем товары в базе данных и копируем уникальные файлы в папки других регионов
        products = Product.objects.select_related('place').all()
        updated_count = 0

        for product in products:
            if not product.place or not product.slug:
                continue

            region_slug = str(product.place.title_tm).lower()  # slug региона (ashgabat, mary, lebap, dasoguz, ahal)

            # Ищем файл в ashgabat, у которого имя совпадает со slug товара
            matched_file = None
            for fname in ashgabat_files:
                fname_without_ext = os.path.splitext(fname)[0]
                if fname_without_ext == product.slug:
                    matched_file = fname
                    break

            if matched_file:
                source_path = os.path.join(ashgabat_dir, matched_file)
                ext = os.path.splitext(matched_file)[1].lower()

                if region_slug == 'ashgabat':
                    # Для Ашхабада привязываем путь к папке ashgabat
                    new_rel_path = f"product_images/ashgabat/{matched_file}"
                    product.image.name = new_rel_path
                    product.save(update_fields=['image'])
                    updated_count += 1
                else:
                    # Для других регионов создаем их папку и копируем изолированный файл
                    region_dir = os.path.join(base_dir, region_slug)
                    os.makedirs(region_dir, exist_ok=True)

                    new_filename = f"{product.slug}{ext}"
                    dest_path = os.path.join(region_dir, new_filename)

                    # Физически копируем файл
                    shutil.copy2(source_path, dest_path)

                    # Записываем в БД индивидуальный путь
                    new_rel_path = f"product_images/{region_slug}/{new_filename}"
                    product.image.name = new_rel_path
                    product.save(update_fields=['image'])
                    updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Готово! Обработано и обновлено товаров: {updated_count}"
        ))
