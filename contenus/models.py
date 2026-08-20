from django.db import models
from django.utils.text import slugify

# Create your models here.

## quelques fonctions utiles
# foncitonne qui retorune l'année scolaire courante
def annee_scolaire_courante():
    """Retourne l'id de l'année scolaire marquée comme courante (ou None)."""
    annee = AnneeScolaire.objects.filter(est_courante=True).first()
    return annee.pk if annee else None

# pour générer un slug unique avec l'année scolaire;
def slug_avec_annee(titre, annee_scolaire):
    """Génère un slug incluant une version courte de l'année scolaire.
    Ex: 'Électronique 1' + '2024-2025' -> 'electronique-1-24-25'
    """
    base = slugify(titre)
    if not annee_scolaire:
        return base
    try:
        parties = annee_scolaire.nom.split('-')
        suffixe = '-'.join(p.strip()[-2:] for p in parties if p.strip())
        return f"{base}-{suffixe}"
    except (AttributeError, IndexError):
        return base


## Gestion des années scolaires
class AnneeScolaire(models.Model):
    nom = models.CharField(
        max_length=20,
        unique=True,
        help_text="ex : 2025-2026"
    )
    date_debut = models.DateField()
    date_fin = models.DateField()
    est_courante = models.BooleanField(
        default=False,
        help_text="Une seule année doit être marqué courante."
    )
    
    class Meta:
        ordering = ['-date_debut']
        verbose_name = "Année scolaire"
        verbose_name_plural = "Années scolaires"
        
    def __str__(self):
        return self.nom




## Gestion des thèmes
class Theme(models.Model):
    nom = models.CharField(
        max_length=100
    )
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)
    ordre = models.PositiveIntegerField(
        default=0,
        help_text="Ordre d'affichage, 0 en premier"
    )
    
    class Meta:
        ordering  = ['ordre', 'nom']
        
        
    def __str__(self):
        return self.nom
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)
    
    
    
## Gestion des cours
class Cours(models.Model):
    titre = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=200, unique=True, blank=True,
        help_text="Si vide sera complété automatiquement. Ex 'E1_24-25' pour le E1 de l'année 2024-2025"
        )
    description = models.TextField(
        blank=True,
        help_text='Peut contenir des url en txt simple, pas de format enrichi pour le moment'
    )
    fichier_accompagnement = models.FileField(upload_to='cours/fichier_accompagnement/')
    fichier_td = models.FileField(upload_to='cours/td/')
    
    theme = models.ForeignKey(Theme, on_delete=models.PROTECT, related_name='cours')
    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name='cours',
        default=annee_scolaire_courante
    )
    
    tp_lies = models.ManyToManyField(
        'TP',
        related_name='cours_lies',
        blank=True
    )
    devoirs_lies = models.ManyToManyField(
        'Devoir',
        related_name='cours_lies',
        blank=True
    )
    
    date_publication = models.DateTimeField(auto_now=True)
    publie = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-date_publication']
        verbose_name_plural = "Cours"
        
    def __str__(self):
        return self.titre
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_avec_annee(self.titre, self.annee_scolaire)
        super().save(*args, **kwargs)
    
    
## Les TP
class TP(models.Model):
    titre = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=210, unique=True, blank=True,
        help_text="Si vide sera complété automatiquement. Ex 'TP1_24-25' pour le TP 1 de l'année 2024-2025"
    )
    description = models.TextField(blank=True)
    fichier_sujet = models.FileField(upload_to='tp/sujets/')
    fichier_corrige = models.FileField(
        upload_to='tp/corriges/',
        blank=True,
        null=True
    )

    themes = models.ManyToManyField(
        Theme,
        related_name='tp',
        blank=True
    )

    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name='tp',
        default=annee_scolaire_courante
    )

    date_publication = models.DateTimeField(auto_now_add=True)
    publie = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_publication']
        verbose_name = "TP"
        verbose_name_plural = "TP"

    def __str__(self):
        return self.titre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_avec_annee(self.titre, self.annee_scolaire)
        super().save(*args, **kwargs)
        



### les devoirs
class Devoir(models.Model):
    class TypeDevoir(models.TextChoices):
        DM = 'DM', 'Devoir maison'
        DS = 'DS', 'Devoir surveillé'
        IR = 'IC', 'Interrogation de cours'

    type = models.CharField(
        max_length=2,
        choices=TypeDevoir.choices
    )
    titre = models.CharField(
        max_length=200,
        help_text="Ex : 'DS n°3' ou 'DM — Fonctions dérivées'"
    )
    slug = models.SlugField(
        max_length=210, unique=True, blank=True,
        help_text="Si vide sera complété automatiquement. Ex 'DM-3_24-25' pour le DM 3 de l'année 2024-2025"
    )

    fichier_sujet = models.FileField(upload_to='devoirs/sujets/')
    fichier_correction = models.FileField(
        upload_to='devoirs/corrections/',
        blank=True,
        null=True
    )

    themes = models.ManyToManyField(
        Theme,
        related_name='devoirs',
        blank=True
    )
    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name='devoirs',
        default=annee_scolaire_courante
    )

    date_publication = models.DateTimeField(auto_now_add=True)
    publie = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_publication']

    def __str__(self):
        return f"{self.get_type_display()} — {self.titre}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_avec_annee(f"{self.type}-{self.titre}", self.annee_scolaire)
        super().save(*args, **kwargs)
        
        
## les fiches outils
class FicheOutil(models.Model):
    titre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=210, unique=True, blank=True)
    description = models.TextField(blank=True)

    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name='fiches_outils',
        default=annee_scolaire_courante
    )

    date_publication = models.DateTimeField(auto_now_add=True)
    publie = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_publication']
        verbose_name = "Fiche outil"
        verbose_name_plural = "Fiches outils"

    def __str__(self):
        return self.titre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_avec_annee(self.titre, self.annee_scolaire)
        super().save(*args, **kwargs)


class FichierOutil(models.Model):
    fiche_outil = models.ForeignKey(
        FicheOutil,
        on_delete=models.CASCADE,
        related_name='fichiers'
    )
    fichier = models.FileField(upload_to='fiches_outils/')
    legende = models.CharField(
        max_length=150,
        blank=True,
        help_text="Ex : 'Formulaire' ou 'Annexe 1' — optionnel."
    )
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'id']

    def __str__(self):
        return self.legende or self.fichier.name