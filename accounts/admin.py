from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile

admin.site.site_header = "LMS Platform Administration"
admin.site.site_title = "LMS Admin"
admin.site.index_title = "Boshqaruv paneli"


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil'
    fk_name = 'user'


class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = [
        'username', 'email', 'first_name', 'last_name', 'is_staff',
        'get_is_teacher', 'get_is_supervisor',
    ]
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'profile__is_teacher', 'profile__is_supervisor']

    def get_is_teacher(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.is_teacher
        return False

    get_is_teacher.short_description = "O'qituvchi"
    get_is_teacher.boolean = True

    def get_is_supervisor(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.is_supervisor
        return False

    get_is_supervisor.short_description = "Nazoratchi"
    get_is_supervisor.boolean = True

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


# Standart User admin ni o'chirish va yangi bilan almashtirish
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'is_teacher', 'is_supervisor', 'is_verified', 'created_at']
    list_filter = ['is_teacher', 'is_supervisor', 'is_verified']
    search_fields = ['user__username', 'user__email', 'phone']
    list_editable = ['is_teacher', 'is_supervisor', 'is_verified']
    readonly_fields = ['created_at', 'updated_at']
