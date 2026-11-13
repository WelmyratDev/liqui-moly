# Liqui Moly Turkmenistan — интернет-магазин

Django 5.2 · PostgreSQL · gunicorn + supervisor + nginx · админка jazzmin.

```
liquimoly/
  liquimoly/      настройки, urls, storage
  cart/           каталог, корзина, заказы, отзывы, баннеры
    services.py   регион (Place), владелец корзины, ключи кеша
    images.py     WebP-превью для загруженных фото
    signals.py    автоматический сброс кеша при изменениях в админке
    templates/cart/partials/   общие куски: карточка товара, модалка, баннеры…
  users/          пользователь по номеру телефона, вход и регистрация
  static/css/app.css, static/js/shop.js   стили и JS всего сайта
  config/         supervisor (gunicorn.conf), пример nginx
```

## Локальный запуск

```bash
cd liquimoly
python -m venv ../venv && source ../venv/bin/activate
pip install -r req.txt
cp .env.example .env          # DEBUG=True, POSTGRES_DB оставить пустым -> SQLite
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
python manage.py test         # 37 тестов
```

## Деплой на продакшен

> Перед деплоем сделайте бэкап базы и папки `media/`:
> `pg_dump liquimoly > ~/backup_$(date +%F).sql` и `tar czf ~/media_$(date +%F).tgz media`.

```bash
cd /home/ubuntu/liqui_moly
git pull
source venv/bin/activate
cd liquimoly
make deploy          # pip install, migrate, collectstatic, check --deploy, warm_thumbnails, restart
```

`.env` на сервере менять не нужно: используются те же переменные (`DJANGO_SECRET_KEY`, `DEBUG`,
`ALLOWED_HOSTS`, `POSTGRES_*`). Новые переменные необязательны, см. `.env.example`.

### Что важно знать при первом деплое

1. **`collectstatic` теперь обязателен.** Имена статики хешируются (`app.5e256ec06918.css`),
   поэтому nginx может кешировать её на год. Без `collectstatic` при `DEBUG=False` стили не загрузятся.
2. **Миграция `0033`** только удаляет ограничение `unique_order_product` (теперь один и тот же товар
   можно заказать для двух машин) и добавляет валидацию звёзд. Данные не меняются.
3. **Кеш** теперь файловый (`liquimoly/cache/`) и общий для всех воркеров gunicorn. Папка
   создаётся сама; у пользователя `ubuntu` должны быть права на запись (как и для `media/`).
4. **Превью картинок** создаются в `media/thumbs/` при первом показе, `make deploy` создаёт их заранее.
   Оригиналы не изменяются и не удаляются.
5. **nginx**: сравните ваш конфиг с `config/nginx.conf.example` и добавьте gzip и заголовки кеширования
   для `/static/` и `/media/`. Это даёт самый большой выигрыш для повторных визитов.
6. **supervisor**: в `config/gunicorn.conf` добавлены `--timeout 60` и `--max-requests`. Чтобы применить:
   скопируйте в `/etc/supervisor/conf.d/`, затем `sudo supervisorctl reread && sudo supervisorctl update`.

### Баннеры

Если в регионе нет баннеров, на главной показываются встроенные баннеры Liqui Moly
(`static/images/banners/`, на ru/tk). Чтобы превратить их в обычные баннеры, которые можно
редактировать в админке:

```bash
python manage.py create_default_banners            # только для регионов без баннеров
python manage.py create_default_banners --place 2  # один регион
```

Рекомендуемые размеры для своих баннеров: основной **2000×1000**, мобильный (`image_sm`) **1200×900**.
Текст лучше не «впекать» в картинку: заголовок и описание из админки выводятся поверх неё
(слева на десктопе, внизу на телефоне) и переводятся на нужный язык.

## Откат

```bash
git checkout <предыдущий-коммит>
python manage.py migrate cart 0032   # вернёт ограничение unique_order_product
python manage.py collectstatic --noinput
sudo supervisorctl restart liquimoly
```

Откат миграции не пройдёт, если уже есть заказ с одним товаром для двух машин.
