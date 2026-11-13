from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import PermissionDenied

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    list_select_related = ('place',)

    ordering = ['id']

    list_display = (
        'name',
        'phone_number',
        'place',
        'is_staff',
        'is_manager',
        'is_active',
        'is_superuser',
        'created_at',
    )

    list_filter = (
        'is_staff',
        'is_active',
        'is_manager',
        'is_superuser',
        'created_at',
    )

    search_fields = (
        'phone_number',
        'name',
    )

    readonly_fields = (
        'last_login',
        'created_at',
        'updated_at',
    )

    filter_horizontal = (
        'groups',
        'user_permissions',
    )

    fieldsets = (
        (
            'User Info',
            {
                'fields': (
                    'phone_number',
                    'name',
                    'place',
                    'password',
                    'is_manager',
                )
            }
        ),
        (
            'Permissions',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            }
        ),
        (
            'Important dates',
            {
                'fields': (
                    'last_login',
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'phone_number',
                    'name',
                    'place',
                    'is_manager',
                    'password1',
                    'password2',
                    'is_staff',
                    'is_active',
                ),
            },
        ),
    )

    raw_id_fields = ('place',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if not request.user.place:
            return qs.none()

        # Managers see customers of their region, never superusers or other staff.
        return qs.filter(place=request.user.place, is_superuser=False, is_staff=False)
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)

        if not request.user.is_superuser:
            readonly.extend([
                'is_superuser',
                'is_staff',
                'groups',
                'user_permissions',
                'is_manager',
            ])
            readonly.append('place')

        return readonly
    
    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            old_obj = User.objects.get(pk=obj.pk) if obj.pk else None

            if old_obj and old_obj.is_superuser != obj.is_superuser:
                raise PermissionDenied(
                    "Вы не можете изменять статус суперпользователя."
                )

        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "place" and not request.user.is_superuser and request.user.place_id:
            kwargs["queryset"] = request.user.place.__class__.objects.filter(
                pk=request.user.place.pk
            )

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )
