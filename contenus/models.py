from django.db import models
from django.utils.text import slugify

from .fichiers import CheminMedia, StockageEcrasement

stockage_ecrasement = StockageEcrasement()

## quelques fonctions utiles
# fonctionne qui retourne l'année scolaire courante
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
    slug = models.SlugField(max_length=210, unique=True, blank=True)
    description = models.TextField(blank=True)

    fichier_cours_prof = models.FileField(
        "Fiche de cours — version complète",
        upload_to=CheminMedia('cours', 'cours-prof'),
        storage=stockage_ecrasement,
        blank=True, null=True
    )
    fichier_cours_eleve = models.FileField(
        "Fiche de cours — version élève",
        upload_to=CheminMedia('cours', 'cours-eleve'),
        storage=stockage_ecrasement,
        blank=True, null=True
    )
    fichier_td_prof = models.FileField(
        "Fiche de TD — version complète",
        upload_to=CheminMedia('cours', 'td-prof'),
        storage=stockage_ecrasement,
        blank=True, null=True)
    fichier_td_eleve = models.FileField(
        "Fiche de TD — version élève",
        upload_to=CheminMedia('cours', 'td-eleve'),
        storage=stockage_ecrasement,
        blank=True, null=True)
    fichier_manip = models.FileField(
        "Manipulation de cours",
        upload_to=CheminMedia('cours', 'manip'),
        storage=stockage_ecrasement,
        blank=True, null=True)

    theme = models.ForeignKey(Theme, on_delete=models.PROTECT, related_name='cours')
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.PROTECT,
        related_name='cours', default=annee_scolaire_courante)
    tp_lies = models.ManyToManyField('TP', related_name='cours_lies', blank=True)
    devoirs_lies = models.ManyToManyField('Devoir', related_name='cours_lies', blank=True)

    date_publication = models.DateTimeField(auto_now_add=True)
    publie = models.BooleanField(default=True)

    # (nom du champ, libellé court affiché sur la vignette)
    FICHIERS = [
        ('fichier_cours_prof', "Cours prof"),
        ('fichier_cours_eleve', "Cours élève"),
        ('fichier_td_prof', "TD prof"),
        ('fichier_td_eleve', "TD élève"),
        ('fichier_manip', "Manip"),
    ]

    @property
    def fichiers_disponibles(self):
        """Liste des fichiers réellement renseignés, dans l'ordre de FICHIERS."""
        resultat = []
        for nom_champ, libelle in self.FICHIERS:
            fichier = getattr(self, nom_champ)
            if fichier:
                resultat.append({'fichier': fichier, 'libelle': libelle})
        return resultat

    class Meta:
        ordering = ['-date_publication']
        verbose_name = "Cours"
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
    fichier_sujet = models.FileField(
        upload_to=CheminMedia('tp', 'tp-eleve'),
        storage=stockage_ecrasement,
        blank=True, null=True
        )
    fichier_corrige = models.FileField(
        upload_to=CheminMedia('tp', 'tp-prof'),
        storage=stockage_ecrasement,
        blank=True, null=True
    )
    fichier_python_sujet = models.FileField(
        upload_to=CheminMedia('tp', 'tp-eleve-python'),
        storage=stockage_ecrasement,
        blank=True, null=True
        )
    fichier_python_corrige = models.FileField(
        upload_to=CheminMedia('tp', 'tp-prof-python'),
        storage=stockage_ecrasement,
        blank=True, null=True
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

    fichier_sujet = models.FileField(
        upload_to=CheminMedia('devoirs', 'sujet'),
        storage=stockage_ecrasement,
        blank=True, null=True
    )
    fichier_correction = models.FileField(
        upload_to=CheminMedia('devoirs', 'correction'),
        storage=stockage_ecrasement,
        blank=True, null=True
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
    fichier = models.FileField(
        upload_to=CheminMedia('fiches_outils', ''),
        storage=stockage_ecrasement,
    )
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
    
class ProgrammeColle(models.Model):
    semaine = models.PositiveIntegerField(
        help_text="Numéro de la semaine (1, 2, 3…)"
    )
    titre = models.CharField(
        max_length=200,
        help_text="Ex : 'Semaine 12 — Électrocinétique et mécanique'"
    )
    fichier = models.FileField(
        upload_to=CheminMedia('colles/programmes/', ''),
        storage=stockage_ecrasement,
        blank=True, null=True,
    )

    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name='programmes_colles',
        default=annee_scolaire_courante
    )
    date_publication = models.DateTimeField(auto_now_add=True)
    publie = models.BooleanField(default=True)

    class Meta:
        ordering = ['-semaine']
        verbose_name = "Programme de colle"
        verbose_name_plural = "Programmes de colles"

    def __str__(self):
        return f"S{self.semaine} — {self.titre}"
    
class CahierCalcul(models.Model):
    semaine = models.PositiveIntegerField(
        help_text="Numéro de la semaine (1, 2, 3…)"
    )
    titre = models.CharField(
        max_length=200,
        blank=True,
        help_text="Facultatif. Ex : 'Dérivées et primitives'"
    )
    fichier_sujet = models.FileField(
        upload_to=CheminMedia('cahier-calcul/', 'sujet'),
        storage=stockage_ecrasement,
        blank=True, null=True,
    )
    fichier_corrige = models.FileField(
        upload_to=CheminMedia('cahier-calcul/', 'correction'),
        blank=True,
        null=True
    )

    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name='cahiers_calcul',
        default=annee_scolaire_courante
    )
    date_publication = models.DateTimeField(auto_now_add=True)
    publie = models.BooleanField(default=True)

    class Meta:
        ordering = ['-semaine']
        verbose_name = "Cahier de calcul"
        verbose_name_plural = "Cahiers de calcul"

    def __str__(self):
        if self.titre:
            return f"S{self.semaine} — {self.titre}"
        return f"Semaine {self.semaine}"