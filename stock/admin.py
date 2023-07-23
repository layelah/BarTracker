from django.contrib import admin
from .models import Unite, Produit, Fournisseur, Client, Achat, Vente, Inventaire
# Register your models here.

@admin.register(Unite)
class UniteAdmin(admin.ModelAdmin):
    list_display = ('titre',)
    search_fields = ('titre',)


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'unite', 'prix',)
    list_filter = ('unite',)
    search_fields = ('nom', 'prix',)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'telephone', 'email', 'adresse',)
    list_editable = ('telephone', 'email', 'adresse',)
    search_fields = ('nom', 'telephone', 'email', 'adresse',)


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'telephone', 'email', 'adresse',)
    list_editable = ('telephone', 'email', 'adresse',)
    search_fields = ('nom', 'telephone', 'email', 'adresse',)


@admin.register(Achat)
class AchatAdmin(admin.ModelAdmin):
    list_display = ('fournisseur', 'produit', 'quantite', 'montant_total',)
    list_filter = ('date_achat',)
    search_fields = ('quantite', 'montant_total',)

    def delete_queryset(self, request, queryset):
        try:
            super().delete_queryset(request, queryset)
        except ValueError:
            message = "Impossible de supprimer les achats. Des ventes sont associées à ces produits."
            self.message_user(request, message, level='error')


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ('client', 'produit', 'quantite', 'montant_total', 'date_vente',)
    list_filter = ('date_vente',)
    search_fields = ('quantite', 'montant_total',)


@admin.register(Inventaire)
class InventaireAdmin(admin.ModelAdmin):
    list_display = ('produit', 'quantite_stock',)
    search_fields = ('quantite_stock',)