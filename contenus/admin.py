from django.contrib import admin
from .models import (
    AnneeScolaire,
    Theme,
    Cours,
    TP, 
    Devoir,
    FicheOutil,
    FichierOutil,
    ProgrammeColle,
    CahierCalcul
)

# Register your models here.
@admin.register(AnneeScolaire)
class AnneScolaireAdmin(admin.ModelAdmin):
    list_display = ('nom', 'date_debut', 'date_fin', 'est_courante')
    list_filter = ('est_courante',)
    
    def save_model(self, request, obj, form, change):
        if obj.est_courante:
            AnneeScolaire.objects.exclude(pk=obj.pk).update(est_courante=False)
        super().save_model(request, obj, form, change)
            
@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'ordre')
    prepopulated_fields = {'slug': ('nom',)}
    ordering = ('ordre',)
    
@admin.register(Cours)
class CoursAdmin(admin.ModelAdmin):
    list_display = ('titre', 'theme', 'annee_scolaire', 'date_publication', 'publie')
    list_filter = ('theme', 'annee_scolaire', 'publie')
    search_fields = ('titre', 'description')
    filter_horizontal = ('tp_lies', 'devoirs_lies')
    fieldsets = (
        (None, {
            'fields': ('titre', 'slug', 'description', 'theme', 'annee_scolaire', 'publie')
        }),
        ("Documents du chapitre", {
            'fields': ('fichier_cours_prof', 'fichier_cours_eleve',
                'fichier_td_prof', 'fichier_td_eleve', 'fichier_manip'),
            'description': "Tous les fichiers sont facultatifs."
        }),
        ("Documents liés", {
            'fields': ('tp_lies', 'devoirs_lies')
        }),
    )

@admin.register(TP)
class TPAdmin(admin.ModelAdmin):
    list_display = ('titre', 'annee_scolaire', 'date_publication', 'publie')
    list_filter = ('themes', 'annee_scolaire', 'publie')
    search_fields = ('titre', 'description')
    filter_horizontal = ('themes',)

@admin.register(Devoir)
class DevoirAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type', 'annee_scolaire', 'date_publication', 'publie')
    list_filter = ('type', 'themes', 'annee_scolaire', 'publie')
    search_fields = ('titre',)
    filter_horizontal = ('themes',)

class FichierOutilInline(admin.TabularInline):
    model = FichierOutil
    extra = 1
    
@admin.register(FicheOutil)
class FicheOutilAdmin(admin.ModelAdmin):
    list_display = ('titre', 'annee_scolaire', 'date_publication', 'publie')
    list_filter = ('annee_scolaire', 'publie')
    search_fields = ('titre', 'description')
    inlines = [FichierOutilInline]
    
from .models import (
    AnneeScolaire, Theme, Cours, TP, Devoir,
    FicheOutil, FichierOutil, ProgrammeColle
)

@admin.register(ProgrammeColle)
class ProgrammeColleAdmin(admin.ModelAdmin):
    list_display = ('semaine', 'titre', 'annee_scolaire', 'date_publication', 'publie')
    list_filter = ('annee_scolaire', 'publie')
    search_fields = ('titre',)
    
    
@admin.register(CahierCalcul)
class CahierCalculAdmin(admin.ModelAdmin):
    list_display = ('semaine', 'titre', 'annee_scolaire', 'date_publication', 'publie')
    list_filter = ('annee_scolaire', 'publie')
    search_fields = ('titre',)