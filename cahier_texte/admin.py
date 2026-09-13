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
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from .forms_admin import GenerationSemainesForm, ReinitialisationForm
from .services import generer_semaines, reinitialiser_annee

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
        
    change_list_template = "admin/cahier_texte/semainecahier/change_list.html"
 
    def get_urls(self):
        # Nos routes passent AVANT celles de l'admin : la route par défaut
        # `<path:object_id>/change/` capturerait sinon "generer/" comme un
        # identifiant d'objet et renverrait un 404 déroutant.
        perso = [
            path(
                "generer/",
                self.admin_site.admin_view(self.vue_generer),
                name="cahier_texte_semainecahier_generer",
            ),
            path(
                "reinitialiser/",
                self.admin_site.admin_view(self.vue_reinitialiser),
                name="cahier_texte_semainecahier_reinitialiser",
            ),
        ]
        return perso + super().get_urls()
 
    def _retour_liste(self):
        return HttpResponseRedirect(
            reverse("admin:cahier_texte_semainecahier_changelist")
        )
 
    # --- Génération ------------------------------------------------------
 
    def vue_generer(self, request):
        if not self.has_add_permission(request):
            messages.error(request, "Permission insuffisante.")
            return self._retour_liste()
 
        if request.method == "POST":
            formulaire = GenerationSemainesForm(request.POST)
            if formulaire.is_valid():
                donnees = formulaire.cleaned_data
                creees, existantes = generer_semaines(
                    annee=donnees["annee"],
                    debut=donnees["debut"],
                    fin=donnees["fin"],
                    numeroter=donnees["numeroter"],
                )
                message = f"{creees} semaine(s) créée(s)."
                if existantes:
                    message += f" {existantes} déjà présente(s), laissée(s) intacte(s)."
                messages.success(request, message)
                return self._retour_liste()
        else:
            formulaire = GenerationSemainesForm()
 
        return render(request, "admin/cahier_texte/formulaire.html", {
            **self.admin_site.each_context(request),
            "titre": "Générer les semaines",
            "introduction": "Crée les semaines manquantes sur la période choisie. "
                            "Les semaines déjà saisies ne sont pas modifiées.",
            "form": formulaire,
            "libelle_bouton": "Générer",
            "destructif": False,
            "opts": self.model._meta,
        })
 
    # --- Réinitialisation ------------------------------------------------
 
    def vue_reinitialiser(self, request):
        if not self.has_delete_permission(request):
            messages.error(request, "Permission insuffisante.")
            return self._retour_liste()
 
        if request.method == "POST":
            formulaire = ReinitialisationForm(request.POST)
            if formulaire.is_valid():
                donnees = formulaire.cleaned_data
                nb_entrees, nb_semaines = reinitialiser_annee(
                    annee=donnees["annee"],
                    supprimer_semaines=(
                        donnees["portee"] == ReinitialisationForm.PORTEE_TOUT
                    ),
                )
                messages.warning(
                    request,
                    f"{nb_entrees} entrée(s) et {nb_semaines} semaine(s) supprimées.",
                )
                return self._retour_liste()
        else:
            formulaire = ReinitialisationForm()
 
        return render(request, "admin/cahier_texte/formulaire.html", {
            **self.admin_site.each_context(request),
            "titre": "Réinitialiser le calendrier",
            "introduction": "Cette opération est irréversible et ne peut pas être "
                            "annulée depuis l'historique de l'admin.",
            "form": formulaire,
            "libelle_bouton": "Supprimer définitivement",
            "destructif": True,
            "opts": self.model._meta,
        })


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