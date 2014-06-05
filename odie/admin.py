from django.contrib import admin

from odie import models

class CartDocumentInline(admin.TabularInline):
    model = models.CartDocument

class CartAdmin(admin.ModelAdmin):
    list_display = ('name', 'date')
    inlines = [
        CartDocumentInline
    ]

admin.site.register(models.Cart, CartAdmin)
