from django.db import models
from datetime import date, timedelta

class Colleur(models.Model):
    nom = models.CharField(max_length=100)
    matiere = models.CharField(max_length=50)

    class Meta:
        ordering = ['matiere', 'nom']
        constraints = [
            models.UniqueConstraint(
                fields=['nom', 'matiere'],
                name='colleur_unique_par_matiere'
            )
        ]

    def __str__(self):
        return f"{self.nom} ({self.matiere})"

class Semaine(models.Model):
    numero = models.PositiveIntegerField(unique=True)
    date_debut = models.DateField(help_text="Lundi de la semaine.")

    class Meta:
        ordering = ['numero']

    def __str__(self):
        return f"S{self.numero} — {self.date_debut:%d/%m/%Y}"

    @property
    def est_en_cours(self):
        """Vrai uniquement pendant les sept jours de la semaine."""
        return self.date_debut <= date.today() <= self.date_debut + timedelta(days=6)


class GroupeColle(models.Model):
    nom = models.CharField(max_length=10, unique=True, help_text="Ex : T1, B3")

    class Meta:
        ordering = ['nom']
        verbose_name = "Groupe de colle"
        verbose_name_plural = "Groupes de colle"

    def __str__(self):
        return self.nom

    @property
    def effectif(self):
        return {'T': 'Trinôme', 'B': 'Binôme'}.get(self.nom[:1].upper(), '')

class Eleve(models.Model):
    prenom = models.CharField(max_length=100)
    nom = models.CharField(max_length=100)
    groupes = models.ManyToManyField(GroupeColle, related_name='eleves')

    class Meta:
        ordering = ['nom', 'prenom']
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class Creneau(models.Model):
    class Jour(models.IntegerChoices):
        LUNDI = 1, 'Lundi'
        MARDI = 2, 'Mardi'
        MERCREDI = 3, 'Mercredi'
        JEUDI = 4, 'Jeudi'
        VENDREDI = 5, 'Vendredi'
        SAMEDI = 6, 'Samedi'

    colleur = models.ForeignKey(Colleur, on_delete=models.CASCADE, related_name='creneaux')
    jour = models.IntegerField(choices=Jour.choices)
    horaire = models.CharField(max_length=20, help_text="Ex : 12h, 17h30")
    salle = models.CharField(max_length=50, blank=True)
    class Meta:
        ordering = ['jour', 'horaire', 'colleur__nom']
        verbose_name = "Créneau"
        verbose_name_plural = "Créneaux"

    def __str__(self):
        return f"{self.get_jour_display()} {self.horaire} — {self.colleur}"


class Passage(models.Model):
    creneau = models.ForeignKey(Creneau, on_delete=models.CASCADE, related_name='passages')
    semaine = models.ForeignKey(Semaine, on_delete=models.CASCADE, related_name='passages')
    groupe = models.ForeignKey(GroupeColle, on_delete=models.CASCADE, related_name='passages')

    class Meta:
        ordering = ['semaine__numero', 'creneau__jour', 'creneau__horaire']
        constraints = [
            models.UniqueConstraint(
                fields=['creneau', 'semaine'],
                name='un_seul_groupe_par_creneau_et_semaine'
            )
        ]

    def __str__(self):
        return f"{self.semaine} — {self.groupe} — {self.creneau}"


class ImportColloscope(models.Model):
    libelle_annee = models.CharField(
        max_length=20,
        help_text="Affiché en tête du colloscope. Ex : 2025-2026"
    )
    fichier_semaines = models.FileField(upload_to='colloscope/imports/')
    fichier_colloscope = models.FileField(upload_to='colloscope/imports/')
    fichier_eleves = models.FileField(upload_to='colloscope/imports/')
    date_import = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_import']
        verbose_name = "Import de colloscope"
        verbose_name_plural = "Imports de colloscope"

    def __str__(self):
        return f"{self.libelle_annee} — {self.date_import:%d/%m/%Y %H:%M}"
