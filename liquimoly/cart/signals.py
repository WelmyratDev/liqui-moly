"""Keep cached data in sync with the admin: any save/delete clears what it affects."""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Banner, Brand, Category, Place, Rating
from .services import (
    BRAND_OPTIONS_CACHE_KEY,
    CATEGORIES_FOOTER_CACHE_KEY,
    CATEGORIES_MAIN_CACHE_KEY,
    PLACES_CACHE_KEY,
    RATING_SUMMARY_CACHE_KEY,
    banners_cache_key,
    brand_children_cache_key,
)


@receiver([post_save, post_delete], sender=Place)
def clear_place_cache(sender, instance, **kwargs):
    cache.delete_many([PLACES_CACHE_KEY, banners_cache_key(instance.pk)])


@receiver([post_save, post_delete], sender=Banner)
def clear_banner_cache(sender, instance, **kwargs):
    keys = [banners_cache_key(instance.place_id)]
    # The banner may have been moved to another region.
    keys += [banners_cache_key(pk) for pk in Place.objects.values_list("pk", flat=True)]
    cache.delete_many(keys)


@receiver([post_save, post_delete], sender=Category)
def clear_category_cache(sender, instance, **kwargs):
    cache.delete_many([CATEGORIES_MAIN_CACHE_KEY, CATEGORIES_FOOTER_CACHE_KEY])


@receiver([post_save, post_delete], sender=Brand)
def clear_brand_cache(sender, instance, **kwargs):
    keys = [BRAND_OPTIONS_CACHE_KEY, "all_brands", brand_children_cache_key(instance.pk)]
    if instance.parent_id:
        keys.append(brand_children_cache_key(instance.parent_id))
    cache.delete_many(keys)


@receiver([post_save, post_delete], sender=Rating)
def clear_rating_cache(sender, instance, **kwargs):
    cache.delete(RATING_SUMMARY_CACHE_KEY)
