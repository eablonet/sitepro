"""
Cahier de texte — `cahier_texte/models.py`.

App dédiée, dépendant de `contenus` dans un seul sens : `cahier_texte` référence
les documents de `contenus`, jamais l'inverse.

Les cibles des clés étrangères sont données sous forme de chaîne
("contenus.Cours") : pas d'import de `contenus.models`, donc aucun risque
d'import circulaire, et la dépendance de migration est détectée toute seule.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models


class SemaineCahier(models.Model):
    """Une ligne du tableau : la semaine calendaire, du lundi au dimanche."""

    class Statut(models.TextChoices):
        NORMALE = "NORMALE", "Semaine de cours"
        VACANCES = "VACANCES", "Vacances"

    annee = models.ForeignKey(
        "contenus.AnneeScolaire",
        on_delete=models.CASCADE,
        related_name="semaines_cahier",
        verbose_name="année scolaire",
    )
    date_lundi = models.DateField("lundi de la semaine")
    numero = models.PositiveSmallIntegerField(
        "n° de semaine pédagogique",
        null=True,
        blank=True,
        help_text="À laisser vide pour les semaines de vacances.",
    )
    statut = models.CharField(
        max_length=10, choices=Statut.choices, default=Statut.NORMALE
    )
    libelle = models.CharField(
        "libellé",
        max_length=100,
        blank=True,
        help_text="Ex. « Vacances de la Toussaint ».",
    )

    class Meta:
        verbose_name = "semaine du cahier de texte"
        verbose_name_plural = "semaines du cahier de texte"
        ordering = ["date_lundi"]
        constraints = [
            models.UniqueConstraint(
                fields=["annee", "date_lundi"],
                name="cahier_semaine_unique_par_annee",
            ),
        ]

    def __str__(self):
        if self.numero:
            return f"S{self.numero} — semaine du {self.date_lundi:%d/%m/%Y}"
        return f"{self.libelle or 'Semaine'} du {self.date_lundi:%d/%m/%Y}"

    @property
    def date_dimanche(self):
        return self.date_lundi + timedelta(days=6)


class EntreeCahier(models.Model):
    """Une case du tableau : une séance, ou une rubrique hebdomadaire (CC, PC)."""

    class Rubrique(models.TextChoices):
        COURS = "COURS", "Cours"
        IC = "IC", "Interrogation de cours"
        TD = "TD", "TD"
        TP = "TP", "TP"
        AP = "AP", "Accompagnement personnalisé"
        DS = "DS", "Devoir surveillé"
        DM = "DM", "Devoir maison"
        CC = "CC", "Cahier de calcul"
        PC = "PC", "Programme de colle"

    class Jour(models.IntegerChoices):
        LUNDI = 0, "lundi"
        MARDI = 1, "mardi"
        MERCREDI = 2, "mercredi"
        JEUDI = 3, "jeudi"
        VENDREDI = 4, "vendredi"

    class Statut(models.TextChoices):
        NORMALE = "NORMALE", "Séance normale"
        FERIE = "FERIE", "Férié"
        ANNULEE = "ANNULEE", "Annulée"

    # Rubrique -> nom du champ de liaison autorisé. `None` = aucune liaison
    # possible pour l'instant (pas de modèle correspondant).
    LIAISONS = {
        Rubrique.COURS: "cours",
        Rubrique.IC: "devoir",
        Rubrique.TD: "cours",
        Rubrique.TP: "tp",
        Rubrique.AP: "fiche_outil",
        Rubrique.DS: "devoir",
        Rubrique.DM: "devoir",
        Rubrique.CC: "cahier_calcul",
        Rubrique.PC: "programme_colle",
    }
    
    FICHIERS_ELEVE = {
        "COURS": ("cours", "fichier_cours_eleve"),
        "TD": ("cours", "fichier_td_eleve"),
    }

    CHAMPS_LIAISON = (
        "cours",
        "tp",
        "devoir",
        "fiche_outil",
        "cahier_calcul",
        "programme_colle",
    )

    semaine = models.ForeignKey(
        SemaineCahier, on_delete=models.CASCADE, related_name="entrees"
    )
    rubrique = models.CharField(max_length=10, choices=Rubrique.choices)
    jour = models.IntegerField(
        choices=Jour.choices,
        null=True,
        blank=True,
        help_text="À laisser vide pour une rubrique hebdomadaire (CC, programme de colle).",
    )
    ordre = models.PositiveSmallIntegerField(
        default=0, help_text="Pour ordonner plusieurs entrées dans la même case."
    )
    statut = models.CharField(
        max_length=10, choices=Statut.choices, default=Statut.NORMALE
    )
    
    titre = models.CharField(
        "titre",
        max_length=200,
        blank=True,
        help_text="Laisser vide pour reprendre le titre du document lié. "
                "Rempli, il s'affiche à sa place.",
    )
    texte = models.TextField(
        "détail",
        blank=True,
        help_text="Ce qui a été traité en séance, une ligne par point. "
        "Inutile d'y remettre le titre du document lié : il est "
        "affiché automatiquement au-dessus.",
    )

    # --- Liaisons : au plus une seule renseignée, cohérente avec la rubrique ---
    cours = models.ForeignKey(
        "contenus.Cours", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="entrees_cahier",
    )
    tp = models.ForeignKey(
        "contenus.TP", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="entrees_cahier",
    )
    devoir = models.ForeignKey(
        "contenus.Devoir", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="entrees_cahier",
    )
    fiche_outil = models.ForeignKey(
        "contenus.FicheOutil", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="entrees_cahier",
    )
    cahier_calcul = models.ForeignKey(
        "contenus.CahierCalcul", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="entrees_cahier",
    )
    programme_colle = models.ForeignKey(
        "contenus.ProgrammeColle", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="entrees_cahier",
    )

    class Meta:
        verbose_name = "entrée du cahier de texte"
        verbose_name_plural = "entrées du cahier de texte"
        ordering = [
            "semaine__date_lundi",
            models.F("jour").asc(nulls_first=True),
            "ordre",
        ]

    def __str__(self):
        return f"{self.semaine} · {self.get_rubrique_display()} — {self.titre}"

    # --- Dérivés ---

    @property
    def date(self):
        """Date réelle de la séance, ou None pour une rubrique hebdomadaire."""
        if self.jour is None:
            return None
        return self.semaine.date_lundi + timedelta(days=self.jour)

    @property
    def objet_lie(self):
        """Le document lié, s'il y en a un."""
        for champ in self.CHAMPS_LIAISON:
            objet = getattr(self, champ, None)
            if objet is not None:
                return objet
        return None


    @property
    def titre_affiche(self):
        """Ce qui s'affiche en tête du bloc."""
        if self.statut != self.Statut.NORMALE:
            return self.titre or self.get_statut_display()
        if self.titre:
            return self.titre
        objet = self.objet_lie
        return str(objet) if objet is not None else ""

    @property
    def detail(self):
        """Corps du bloc, déplié à la demande."""
        if self.statut != self.Statut.NORMALE:
            return ""
        return self.texte

    @property
    def url(self):
        """Cible du lien, ou chaîne vide si le bloc n'est lié à rien.

        Pour un cours ou un TD, on vise directement le fichier élève : le
        modèle `Cours` porte cinq fichiers, et l'élève n'a affaire qu'à un
        seul d'entre eux selon la rubrique. Un fichier non encore déposé
        rend simplement le bloc non cliquable — c'est le cas normal quand
        le programme est publié avant les documents.
        """
        cible = self.FICHIERS_ELEVE.get(self.rubrique)
        if cible is not None:
            nom_fk, nom_fichier = cible
            objet = getattr(self, nom_fk)
            if objet is None:
                return ""
            fichier = getattr(objet, nom_fichier, None)
            return fichier.url if fichier else ""

        objet = self.objet_lie
        if objet is None:
            return ""
        get_url = getattr(objet, "get_absolute_url", None)
        return get_url() if get_url else ""

    def __str__(self):
        return f"{self.semaine} · {self.get_rubrique_display()} — {self.titre_affiche}"

    # --- Validation ---

    def clean(self):
        renseignes = [
            champ for champ in self.CHAMPS_LIAISON
            if getattr(self, f"{champ}_id", None) is not None
        ]

        if len(renseignes) > 1:
            raise ValidationError(
                "Une entrée ne peut être liée qu'à un seul document "
                f"(reçu : {', '.join(renseignes)})."
            )

        if renseignes:
            attendu = self.LIAISONS.get(self.rubrique)
            if attendu != renseignes[0]:
                raise ValidationError({
                    renseignes[0]: (
                        f"La rubrique « {self.get_rubrique_display()} » ne peut pas "
                        f"être liée à ce type de document."
                    )
                })

        if not renseignes and not self.titre and self.statut == self.Statut.NORMALE:
            raise ValidationError(
                "Renseigne au moins un titre ou un document lié."
            )