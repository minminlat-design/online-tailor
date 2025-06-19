from django.contrib import admin
from django import forms
from ckeditor.widgets import CKEditorWidget
from .models import Post, PostImage       
from easy_thumbnails.files import get_thumbnailer
from django.utils.html import format_html



class PostAdminForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = Post
        fields = '__all__'
        


class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 3
    fields = ('order', 'image', 'thumbnail_preview', 'caption')  # add thumbnail_preview here
    readonly_fields = ('thumbnail_preview',)  # make it readonly so it's not editable
    ordering = ('order',)

    def thumbnail_preview(self, obj):
        if obj.image:
            thumbnail_url = get_thumbnailer(obj.image).get_thumbnail({'size': (100, 100), 'crop': True}).url
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', thumbnail_url)
        return "(No image)"

    thumbnail_preview.short_description = 'Preview'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    list_display = ('title', 'slug', 'author', 'status', 'publish', 'created')
    list_filter = ('status', 'created', 'publish', 'author')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    date_hierarchy = 'publish'
    ordering = ('status', 'publish',)
    inlines = [PostImageInline]
