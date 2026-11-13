"""Built-in hero banners (static/images/banners/).

Shown on the home page when a region has no banners in the admin, and used by
``manage.py create_default_banners`` to create real, editable Banner rows.
"""
DEFAULT_BANNERS = [
    {
        "key": "motor-oils",
        "title_tm": "Nemes hilli motor ýaglary",
        "title_ru": "Моторные масла немецкого качества",
        "description_tm": "Liqui Moly — Germaniýada öndürilen, iň ýokary standartlara laýyk sintetiki ýaglar.",
        "description_ru": "Синтетические масла Liqui Moly, произведённые в Германии по самым высоким стандартам.",
    },
    {
        "key": "additives",
        "title_tm": "Hereketlendirijiňiz üçin goşundylar",
        "title_ru": "Присадки для вашего двигателя",
        "description_tm": "Ýangyç ulgamyny arassalaýar, güýji we tygşytlylygy ýokarlandyrýar.",
        "description_ru": "Очищают топливную систему, возвращают мощность и снижают расход.",
    },
    {
        "key": "transmission",
        "title_tm": "Transmissiýa we ATF ýaglary",
        "title_ru": "Трансмиссионные масла и ATF",
        "description_tm": "Awtomat we mehaniki tizlik gutulary üçin ygtybarly gorag.",
        "description_ru": "Надёжная защита автоматических и механических коробок передач.",
    },
]
