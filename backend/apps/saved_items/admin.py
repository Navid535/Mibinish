from django.contrib import admin

from apps.saved_items.models import Category, SavedItem, SavedItemCategory


class SavedItemCategoryInline(admin.TabularInline):
    model = SavedItemCategory
    extra = 1
    autocomplete_fields = ('category',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'color')
    search_fields = ('name', 'user__email', 'user__first_name')
    list_filter = ('user',)
    ordering = ('name',)


@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'user', 'status', 'source', 'created_at', 'category_list',
    )
    search_fields = ('name', 'categories__name', 'url', 'source')
    list_filter = ('status', 'source')
    ordering = ('-created_at',)
    list_select_related = ('user',)
    inlines = (SavedItemCategoryInline,)

    def category_list(self, obj):
        return ", ".join(c.name for c in obj.categories.all())
    category_list.short_description = "Categories"


@admin.register(SavedItemCategory)
class SavedItemCategoryAdmin(admin.ModelAdmin):
    list_display = ('saved_item', 'category', 'priority')
    search_fields = ('saved_item__name', 'category__name')
    list_filter = ('category', 'priority')
    list_select_related = ('saved_item', 'category')