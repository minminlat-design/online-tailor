from django.db import models
from django.urls import reverse


class MainCategory(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    name_order = models.IntegerField(default=0)
    image = models.ImageField(upload_to='main_categories/%Y/%m/%d/', null=True, blank=True)
    
    class Meta:
        ordering = ['name_order', 'name']
        indexes = [
            models.Index(fields=['name']),
        ]
        verbose_name = 'main category'
        verbose_name_plural = 'main categories'
        
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('store:store_main', args=[self.slug])
    
    
class Category(models.Model):
    main_category = models.ForeignKey(MainCategory, on_delete=models.PROTECT, related_name='categories')
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    image = models.ImageField(upload_to='category/%Y/%m/%d', blank=True)
    name_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='categories/%Y/%m/%d/', null=True, blank=True)
    
    class Meta:
        ordering = ['name_order', 'name']
        indexes = [
            models.Index(fields=['name']),
        ]
        verbose_name = 'category'
        verbose_name_plural = 'categories'
        
    def __str__(self):
        return f'{self.main_category.name} - {self.name}'
    
    def get_absolute_url(self):
        return reverse('store:store_category', args=[self.main_category.slug, self.slug])
    
    
class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    name_order = models.IntegerField(default=0)
    image = models.ImageField(upload_to='sub_categories/%Y/%m/%d/', null=True, blank=True)
    
    class Meta:
        ordering = ['name_order', 'name']
        indexes = [
            models.Index(fields=['name']),
        ]
        verbose_name = 'sub category'
        verbose_name_plural = 'sub categories'
        
    def __str__(self):
        if self.category:
            return f'{self.category.name} - {self.name}'
        return self.name # fallback if no category assigned
    
    def get_absolute_url(self):
        return reverse(
            'store:store_subcategory', args=[self.category.main_category.slug, self.category.slug, self.slug]
        )
    