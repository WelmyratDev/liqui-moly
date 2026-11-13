from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)

from django.core.validators import RegexValidator
import re

MIN_PASSWORD_LENGTH = 6

MANAGER_PERMISSIONS = frozenset(
    [
        # products of their region
        "cart.view_product", "cart.add_product", "cart.change_product", "cart.delete_product",
        "cart.view_specification", "cart.add_specification",
        "cart.change_specification", "cart.delete_specification",
        # orders of their region
        "cart.view_order", "cart.change_order", "cart.delete_order",
        "cart.view_orderitem", "cart.change_orderitem",
        # banners of their region
        "cart.view_banner", "cart.add_banner", "cart.change_banner", "cart.delete_banner",
        # read-only
        "cart.view_cartitem",
        "cart.view_category",
        # customers of their region
        "users.view_user", "users.change_user",
    ]
)

phone_validator = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be in format: +999999999. Up to 15 digits."
)


class UserManager(BaseUserManager):

    def create_user(self, phone_number=None, password=None, **extra_fields):

        if not phone_number:
            raise ValueError("Phone number is required")

        user = self.model(
            phone_number=phone_number,
            **extra_fields
        )

        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(self, phone_number=None, password=None, **extra_fields):

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(
            phone_number=phone_number,
            password=password,
            **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin):

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        validators=[phone_validator]
    )

    name = models.CharField(max_length=200, blank=True, null=True)

    place = models.ForeignKey(
        "cart.Place",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    is_manager = models.BooleanField(
        default=False
    )

    USERNAME_FIELD = 'phone_number'

    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.phone_number

    # ------------------------------------------------------------------
    # Permissions
    #   Superusers: everything (Django default).
    #   Managers (is_manager + is_staff): only what a regional manager needs.
    #   Previously managers got *every* permission, including deleting
    #   regions/categories (CASCADE-deletes products of all regions),
    #   groups and user rights.
    # ------------------------------------------------------------------
    def has_perm(self, perm, obj=None):
        if super().has_perm(perm, obj):
            return True
        return bool(self.is_active and self.is_manager and perm in MANAGER_PERMISSIONS)

    def has_module_perms(self, app_label):
        if super().has_module_perms(app_label):
            return True
        return bool(
            self.is_active
            and self.is_manager
            and any(p.startswith(app_label + ".") for p in MANAGER_PERMISSIONS)
        )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    @staticmethod
    def normalize_phone(phone_number: str):
        """Clean a phone number typed on the site.

        The login form shows a fixed "+993" prefix, so customers are stored
        with the 8 local digits.  "+993 61 23-45-67" -> "61234567".
        Returns None for anything that is not a plausible number.
        """
        if not phone_number:
            return None

        cleaned = re.sub(r"[\s\-().]", "", str(phone_number))
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]

        if not cleaned.isdigit():
            return None

        if User.objects.filter(phone_number=cleaned).exists():
            return cleaned  # existing account in whatever format it was saved

        if cleaned.startswith("993") and len(cleaned) == 11:
            cleaned = cleaned[3:]

        if len(cleaned) != 8:
            return None

        return cleaned

    @staticmethod
    def create_user_if_not_exists(place_id: object, fullname: str, phone_number: str, password: str):
        """Return the account for this phone, creating it on first login.

        Returns None for an invalid phone or password.
        """
        phone_number = User.normalize_phone(phone_number)

        if not phone_number or not password:
            return None

        user = User.objects.filter(phone_number=phone_number).first()
        if user is not None:
            return user

        if len(password) < MIN_PASSWORD_LENGTH:
            return None

        user = User(phone_number=phone_number, name=(fullname or "").strip()[:200] or None)
        user.place = place_id if place_id else None
        user.set_password(password)
        user.save()
        return user
