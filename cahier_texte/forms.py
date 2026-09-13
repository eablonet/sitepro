"""À ajouter dans `cahier_texte/forms.py`."""

from django import forms

from contenus.models import (
    AnneeScolaire, CahierCalcul, Cours, Devoir, FicheOutil, ProgrammeColle, TP,
)

from .models import EntreeCahier

# nom du champ FK -> (modèle, libellé du groupe dans la liste)
MODELES_LIES = {
    "cours": (Cours, "Cours et TD"),
    "tp": (TP, "TP"),
    "devoir": (Devoir, "Devoirs et interrogations"),
    "fiche_outil": (FicheOutil, "Fiches outil"),
    "cahier_calcul": (CahierCalcul, "Cahiers de calcul"),
    "programme_colle": (ProgrammeColle, "Programmes de colle"),
}


def choix_documents():
    """Construit une fois la liste groupée de tous les documents liables.

    À appeler DANS LA VUE, pas dans le formulaire : une page d'édition
    affiche des dizaines de formulaires, et reconstruire les choix pour
    chacun ferait six requêtes par entrée.
    """
    choix = [("", "— aucun —")]
    for champ, (modele, libelle) in MODELES_LIES.items():
        options = [(f"{champ}:{objet.pk}", str(objet)) for objet in modele.objects.all()]
        if options:
            choix.append((libelle, options))
    return choix


class EntreeRapideForm(forms.ModelForm):
    """Formulaire d'édition en place d'une entrée.

    Les six clés étrangères sont repliées en un champ unique dont la valeur
    encode le type : « cours:5 ». Le décodage et la vérification de
    cohérence avec la rubrique se font dans clean().
    """

    document = forms.ChoiceField(label="Document lié", required=False)

    class Meta:
        model = EntreeCahier
        fields = ("rubrique", "jour", "ordre", "statut", "titre", "texte")
        widgets = {
            "texte": forms.Textarea(attrs={"rows": 3}),
            "titre": forms.TextInput(attrs={"placeholder": "titre du document lié"}),
        }

    def __init__(self, *args, choix=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["document"].choices = choix or [("", "— aucun —")]

        if self.instance.pk:
            for champ in EntreeCahier.CHAMPS_LIAISON:
                identifiant = getattr(self.instance, f"{champ}_id", None)
                if identifiant is not None:
                    self.fields["document"].initial = f"{champ}:{identifiant}"
                    break

    def clean(self):
        donnees = super().clean()
        valeur = donnees.get("document") or ""
        self._champ_lie = None

        if valeur:
            champ, _, identifiant = valeur.partition(":")
            attendu = EntreeCahier.LIAISONS.get(donnees.get("rubrique"))
            if champ != attendu:
                raise forms.ValidationError({
                    "document": "Ce type de document ne correspond pas à la rubrique."
                })
            self._champ_lie = (champ, int(identifiant))

        if not valeur and not donnees.get("titre") and donnees.get("statut") == "NORMALE":
            raise forms.ValidationError("Renseigne au moins un titre ou un document.")

        return donnees

    def save(self, commit=True):
        entree = super().save(commit=False)

        # On remet les six à None avant d'en poser une : sans ça, changer de
        # rubrique laisserait l'ancienne liaison en place et clean() du modèle
        # refuserait l'enregistrement suivant.
        for champ in EntreeCahier.CHAMPS_LIAISON:
            setattr(entree, f"{champ}_id", None)

        if self._champ_lie:
            champ, identifiant = self._champ_lie
            setattr(entree, f"{champ}_id", identifiant)

        if commit:
            entree.save()
        return entree
