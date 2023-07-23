from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from phonenumber_field.modelfields import PhoneNumberField
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files import File
import random
import string



class Unite(models.Model):
    titre = models.CharField(max_length=50, null=True)

    def __str__(self):
        return self.titre


class Produit(models.Model):
    nom = models.CharField(max_length=200)  # Champ pour le nom du produit
    code_barre = models.ImageField(upload_to='images/', blank=True)  # Champ pour l'image du code-barres
    unite = models.ForeignKey(Unite, on_delete=models.CASCADE, null=True)
    prix = models.FloatField(null=True)
    produit_id = models.CharField(max_length=4, unique=True, null=True, editable=False)  # Champ pour l'identifiant unique du produit

    def __str__(self):
        return str(self.nom)

    def save(self, *args, **kwargs):
        if not self.produit_id:
            self.code_pays = '604'  # Code du pays attribué (exemple)
            self.code_fabricant = '32450'  # Code du fabricant attribué (exemple)
            
            # Générer un produit_id unique de 4 chiffres
            while True:
                id_unique = str(random.randint(1000, 9999))
                if not Produit.objects.filter(produit_id=id_unique).exists():
                    self.produit_id = id_unique
                    break
            
            EAN = barcode.get_barcode_class('ean13')
            ean = EAN(f'{self.code_pays}{self.code_fabricant}{self.produit_id}', writer=ImageWriter())
            buffer = BytesIO()
            ean.write(buffer)
            self.code_barre.save(f'{self.nom}.png', File(buffer), save=False)
        return super().save(*args, **kwargs)
    

class Fournisseur(models.Model):
    nom = models.CharField(max_length=100, null=True)
    telephone = PhoneNumberField(null=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    adresse = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.nom


class Client(models.Model):
    nom = models.CharField(max_length=200, null=True)
    telephone = PhoneNumberField(null=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    adresse = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.nom
    


class Achat(models.Model):
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.CASCADE, null=True)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, null=True)
    quantite = models.PositiveIntegerField(null=True)
    montant_total = models.FloatField(editable=False, null=True)
    date_achat = models.DateField(auto_now_add=True, null=True)
    is_modified = models.BooleanField(default=False, editable=False)

    def save(self, *args, **kwargs):
        if self.pk:  # Vérifie si l'achat existe déjà (modification)
            raise ValueError("[La modification d'un achat existant n'est pas autorisée.]")

        self.montant_total = self.quantite * self.produit.prix
        super().save(*args, **kwargs)

        # Mettre à jour l'inventaire
        inventaire, created = Inventaire.objects.get_or_create(produit=self.produit)
        if inventaire:
            inventaire.quantite_stock += self.quantite
            inventaire.save()
        else:
            raise Exception("L'inventaire n'a pas été créé pour le produit associé à l'achat.")


class Vente(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, null=True)
    quantite = models.PositiveIntegerField(null=True)
    montant_total = models.FloatField(editable=False, null=True)
    date_vente = models.DateField(auto_now_add=True, null=True)
    is_modified = models.BooleanField(default=False, editable=False)

    def save(self, *args, **kwargs):
        if self.pk:  # Vérifie si la vente existe déjà (modification)
            raise ValueError("[La modification d'une vente existante n'est pas autorisée.]")

        self.montant_total = self.quantite * self.produit.prix

        # Vérifier si la quantité en stock est suffisante
        inventaire = Inventaire.objects.get(produit=self.produit)
        if self.quantite > inventaire.quantite_stock:
            raise ValidationError("Stock insuffisant pour effectuer la vente.")

        super().save(*args, **kwargs)

        # Mettre à jour l'inventaire
        inventaire.quantite_stock -= self.quantite
        inventaire.save()


class Inventaire(models.Model):
    produit = models.OneToOneField(Produit, on_delete=models.CASCADE)
    quantite_stock = models.PositiveIntegerField(default=0)


@receiver(post_save, sender=Produit)
def update_inventaire(sender, instance, created, **kwargs):
    if created:
        Inventaire.objects.create(produit=instance)
    else:
        inventaire = Inventaire.objects.get(produit=instance)
        inventaire.save()


@receiver(pre_save, sender=Achat)
def update_inventaire_pre_save_achat(sender, instance, **kwargs):
    if instance.pk:  # Vérifie si l'achat existe déjà (modification)
        old_instance = Achat.objects.get(pk=instance.pk)
        diff = instance.quantite - old_instance.quantite

        # Mettre à jour l'inventaire en tenant compte de la différence de quantité
        inventaire, created = Inventaire.objects.get_or_create(produit=instance.produit)
        inventaire.quantite_stock -= old_instance.quantite  # Soustraire l'ancienne quantité de l'inventaire
        inventaire.quantite_stock += diff  # Ajouter la différence de quantité à l'inventaire
        inventaire.save()


@receiver(pre_save, sender=Vente)
def update_inventaire_pre_save_vente(sender, instance, **kwargs):
    if instance.pk:  # Vérifie si la vente existe déjà (modification)
        old_instance = Vente.objects.get(pk=instance.pk)
        diff = instance.quantite - old_instance.quantite

        # Mettre à jour l'inventaire en tenant compte de la différence de quantité
        inventaire, created = Inventaire.objects.get_or_create(produit=instance.produit)
        inventaire.quantite_stock += old_instance.quantite  # Ajouter l'ancienne quantité à l'inventaire
        inventaire.quantite_stock -= diff  # Soustraire la différence de quantité de l'inventaire
        inventaire.save()


@receiver(pre_delete, sender=Achat)
def update_inventaire_pre_delete(sender, instance, **kwargs):
    # Mettre à jour l'inventaire en soustrayant la quantité de l'achat supprimé
    inventaire = instance.produit.inventaire
    inventaire.quantite_stock -= instance.quantite

    # Vérifier si la quantité stockée est suffisante après la suppression
    if inventaire.quantite_stock < 0:
        raise ValueError("[Si cette suppression est validé il y aura plus de produit vendu pour cet article que de produit stocké]")
    inventaire.save()


@receiver(pre_delete, sender=Vente)
def update_inventaire_pre_delete_vente(sender, instance, **kwargs):
    # Mettre à jour l'inventaire en ajoutant la quantité de la vente supprimée
    inventaire = instance.produit.inventaire
    inventaire.quantite_stock += instance.quantite
    inventaire.save()

