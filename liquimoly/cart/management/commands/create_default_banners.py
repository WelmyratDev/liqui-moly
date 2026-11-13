from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from cart.default_banners import DEFAULT_BANNERS
from cart.models import Banner, Place

BANNER_DIR = Path(settings.BASE_DIR) / "static" / "images" / "banners"


class Command(BaseCommand):
    help = (
        "Create the built-in Liqui Moly banners for regions that have no banners yet. "
        "They are normal Banner rows afterwards: edit or delete them in the admin."
    )

    def add_arguments(self, parser):
        parser.add_argument("--place", type=int, help="Only this place id")
        parser.add_argument(
            "--force", action="store_true", help="Also add them to regions that already have banners"
        )

    def handle(self, *args, **options):
        places = Place.objects.all()
        if options["place"]:
            places = places.filter(pk=options["place"])

        created = 0
        for place in places:
            if Banner.objects.filter(place=place).exists() and not options["force"]:
                self.stdout.write(f"skip {place}: already has banners")
                continue
            # reversed: the newest banner is shown first, keep the list order
            for spec in reversed(DEFAULT_BANNERS):
                banner = Banner(
                    place=place,
                    title_tm=spec["title_tm"],
                    title_ru=spec["title_ru"],
                    description_tm=spec["description_tm"],
                    description_ru=spec["description_ru"],
                )
                with open(BANNER_DIR / f"{spec['key']}-desktop.jpg", "rb") as big, open(
                    BANNER_DIR / f"{spec['key']}-mobile.jpg", "rb"
                ) as small:
                    banner.image.save(f"{spec['key']}.jpg", File(big), save=False)
                    banner.image_sm.save(f"{spec['key']}-sm.jpg", File(small), save=False)
                    banner.save()
                created += 1
            self.stdout.write(f"{place}: banners created")

        self.stdout.write(self.style.SUCCESS(f"Done, {created} banners created."))
