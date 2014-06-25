from django.contrib import admin

from odie import models

class CartDocumentInline(admin.TabularInline):
    model = models.CartDocument

class CartAdmin(admin.ModelAdmin):
    list_display = ('name', 'creation_time')
    inlines = [
        CartDocumentInline
    ]

admin.site.register(models.Cart, CartAdmin)
