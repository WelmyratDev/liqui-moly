import os

from django.db.models.signals import post_delete, pre_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from cart.models import Product, Category, CartItem, Banner



@receiver(post_delete, sender=Category)
def delete_category_image(sender, instance, **kwargs):

    if instance.image:

        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)


@receiver(pre_save, sender=Category)
def delete_old_image_category_when_change(sender, instance, **kwargs):

    if not instance.pk:
        return

    try:
        old_image = Category.objects.get(pk=instance.pk).image
    except Category.DoesNotExist:
        return

    new_image = instance.image

    if not old_image:
        return

    if old_image != new_image:

        if os.path.isfile(old_image.path):
            os.remove(old_image.path)


@receiver(post_delete, sender=Product)
def delete_product_image(sender, instance, **kwargs):

    if instance.image:

        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)


@receiver(pre_save, sender=Product)
def delete_old_image_when_change(sender, instance, **kwargs):

    if not instance.pk:
        return

    try:
        old_image = Product.objects.get(pk=instance.pk).image
    except Product.DoesNotExist:
        return

    new_image = instance.image

    if not old_image:
        return

    if old_image != new_image:

        if os.path.isfile(old_image.path):
            os.remove(old_image.path)


@receiver(user_logged_in)
def merge_cart_after_login(sender, request, user, **kwargs):
    device_id = getattr(request, "device_id", None)

    if not device_id:
        return

    CartItem.objects.filter(
        device_id=device_id,
        user__isnull=True,
    ).update(user=user)




@receiver(post_delete, sender=Banner)
def delete_banner_image(sender, instance, **kwargs):

    if instance.image:

        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)

    if instance.image_sm:

        if os.path.isfile(instance.image_sm.path):
            os.remove(instance.image_sm.path)