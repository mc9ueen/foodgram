from django.contrib import admin

from ingredients.models import Ingredient


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_editable = ('name', 'measurement_unit')
    list_filter = ('name', )
    empty_value_display = '--пусто--'
