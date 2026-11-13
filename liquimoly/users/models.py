from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)

from django.core.validators import RegexValidator
import cart

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

    def has_perm(self, perm, obj=None):
        return self.is_manager or self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_manager or self.is_superuser
    
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    @staticmethod
    def normalize_phone(phone_number: str):
        if not phone_number:
            return None

        phone_number = phone_number.strip()

        if phone_number.startswith("+993") or phone_number.startswith("993"):
            return None

        return phone_number

    @staticmethod
    def create_user_if_not_exists(place_id: object, fullname: str, phone_number: str, password: str):
        phone_number = User.normalize_phone(phone_number)

        if not phone_number or not password:
            return None

        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={"name": fullname}
        )

        if created:
            user.place = place_id if place_id else None
            user.set_password(password)
            user.save() 

        return user
