from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Colleur, Creneau, Eleve, GroupeColle, ImportColloscope, Passage, Semaine
from .parsing import importer_tout, vider_colloscope


from django.contrib import admin, messages

from .parsing import importer_tout, vider_colloscope


@admin.register(ImportColloscope)
class ImportColloscopeAdmin(admin.ModelAdmin):
    list_display = ('libelle_annee', 'date_import')
    actions = ['action_vider']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            stats = importer_tout(
                obj.fichier_semaines,
                obj.fichier_colloscope,
                obj.fichier_eleves,
            )
        except ValidationError as erreur:
            self.message_user(
                request, f"Import annulé — {erreur.message}", level=messages.ERROR
            )
            return

        self.message_user(
            request,
            f"Import réussi : {stats['semaines']} semaines, "
            f"{stats['creneaux']} créneaux, {stats['passages']} passages, "
            f"{stats['groupes']} groupes, {stats['eleves']} élèves."
        )
        for avertissement in stats['avertissements']:
            self.message_user(request, avertissement, level=messages.WARNING)

    @admin.action(description="Vider entièrement le colloscope (fin d'année)")
    def action_vider(self, request, queryset):
        vider_colloscope()
        ImportColloscope.objects.all().delete()
        self.message_user(
            request,
            "Colloscope vidé : créneaux, passages, groupes, semaines, "
            "colleurs et élèves ont été supprimés.",
            level=messages.WARNING,
        )


@admin.register(Semaine)
class SemaineAdmin(admin.ModelAdmin):
    list_display = ('numero', 'date_debut')
    list_filter = ('numero',)


@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom')
    list_filter = ('groupes',)
    search_fields = ('nom', 'prenom')
    filter_horizontal = ('groupes',)


@admin.register(Colleur)
class ColleurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'matiere')
    list_filter = ('matiere',)
    search_fields = ('nom',)


@admin.register(GroupeColle)
class GroupeColleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'effectif')
    list_filter = ('nom',)


@admin.register(Creneau)
class CreneauAdmin(admin.ModelAdmin):
    list_display = ('jour', 'horaire', 'colleur', 'salle')
    list_filter = ('jour', 'colleur__matiere')

@admin.register(Passage)
class PassageAdmin(admin.ModelAdmin):
    list_display = ('semaine', 'groupe', 'creneau')
    list_filter = ('semaine__numero', 'groupe')