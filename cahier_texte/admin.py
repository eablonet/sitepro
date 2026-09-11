"""
Cahier de texte — `cahier_texte/admin.py`.

Deux surfaces de saisie complémentaires :

  * `SemaineCahierAdmin`  — vue « une semaine », pour relire ou compléter
    une ligne du tableau. L'inline reste volontairement léger.
  * `EntreeCahierAdmin`   — vue « toutes les entrées », filtrable par rubrique.
    C'est là qu'on remplit vite (tous les TP d'affilée, puis tous les cours…).
"""

from django.contrib import admin
from django.db.models import Count
from django.utils.text import Truncator

from .models import EntreeCahier, SemaineCahier



class EntreeCahierInline(admin.TabularInline):
    model = EntreeCahier
    extra = 1
    # Les six FK de liaison ne sont PAS ici : six colonnes de <select> rendent
    # l'inline illisible. On saisit le squelette de la semaine ici, et on
    # rattache les documents depuis la fiche de l'entrée (lien « Modifier »).
    fields = ("rubrique", "jour", "ordre", "statut", "titre", "texte")
    show_change_link = True


@admin.register(SemaineCahier)
class SemaineCahierAdmin(admin.ModelAdmin):
    list_display = ("__str__", "annee", "date_lundi", "numero", "statut", "nb_entrees")
    list_filter = ("annee", "statut")
    list_editable = ("numero", "statut")
    date_hierarchy = "date_lundi"
    ordering = ("-date_lundi",)
    inlines = (EntreeCahierInline,)

    fieldsets = (
        (None, {"fields": ("annee", "date_lundi", "numero")}),
        ("Semaine particulière", {
            "fields": ("statut", "libelle"),
            "description": "Pour les vacances. Un jour férié isolé se marque "
                           "sur l'entrée concernée, pas ici.",
        }),
    )

    @admin.display(description="entrées", ordering="_nb_entrees")
    def nb_entrees(self, obj):
        return obj._nb_entrees

    def get_queryset(self, request):
        # L'annotation sert deux fins : rendre la colonne triable, et éviter
        # une requête COUNT par ligne affichée.
        return (
            super().get_queryset(request)
            .select_related("annee")
            .annotate(_nb_entrees=Count("entrees"))
        )


@admin.register(EntreeCahier)
class EntreeCahierAdmin(admin.ModelAdmin):
    list_display = ("semaine", "rubrique", "jour", "resume", "statut")

    list_filter = ("rubrique", "statut", "semaine__annee")
    list_select_related = ("semaine",)
    search_fields = ("titre", "texte",)
    ordering = ("-semaine__date_lundi", "jour", "ordre")


    fieldsets = (
        (None, {"fields": ("semaine", "rubrique", "jour", "ordre", "statut")}),
        ("Contenu", {"fields": ("titre", "texte",)}),
        ("Document lié", {
            "fields": EntreeCahier.CHAMPS_LIAISON,
            "description": "Un seul champ, cohérent avec la rubrique choisie. "
            "Laisser vide si aucun document ne correspond.",
        }),
    )

    @admin.display(description="libellé")
    def libelle(self, obj):
        return obj.libelle
    
    @admin.display(description="contenu")
    def resume(self, obj):
        return Truncator(obj.titre).chars(60)