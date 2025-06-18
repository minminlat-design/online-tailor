from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account

@admin.register(Account)
class AccountAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'last_login', 'date_joined', 'is_active')
    list_display_links = ('email', 'first_name', 'last_name', 'username')
    readonly_fields = ('last_login', 'date_joined')
    ordering = ('-date_joined',)
    search_fields = ('email', 'username', 'first_name', 'last_name')
    list_filter = ('is_admin', 'is_staff', 'is_superadmin', 'is_active') # it is a must
    filter_horizontal = () # it is a must
    fieldsets = () # it is a must
    show_facets = admin.ShowFacets.ALWAYS
