"""`cahier_texte/forms_admin.py` — formulaires des vues d'admin."""

from django import forms

from contenus.models import AnneeScolaire


class GenerationSemainesForm(forms.Form):
    annee = forms.ModelChoiceField(
        queryset=AnneeScolaire.objects.all(),
        label="Année scolaire",
    )
    debut = forms.DateField(
        label="Première semaine",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="N'importe quel jour de la semaine : la date est ramenée au lundi.",
    )
    fin = forms.DateField(
        label="Dernière semaine",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    numeroter = forms.BooleanField(
        label="Numéroter les semaines à la suite",
        required=False,
        initial=True,
        help_text="À décocher si tu préfères saisir les numéros toi-même "
                  "(les vacances décalent la numérotation).",
    )

    def clean(self):
        donnees = super().clean()
        debut, fin = donnees.get("debut"), donnees.get("fin")
        if debut and fin and fin < debut:
            raise forms.ValidationError("La dernière semaine précède la première.")
        return donnees


class ReinitialisationForm(forms.Form):
    PORTEE_ENTREES = "entrees"
    PORTEE_TOUT = "tout"

    annee = forms.ModelChoiceField(
        queryset=AnneeScolaire.objects.all(),
        label="Année scolaire",
    )
    portee = forms.ChoiceField(
        label="Ce qui doit être supprimé",
        widget=forms.RadioSelect,
        choices=[
            (PORTEE_ENTREES, "Les entrées seulement — les semaines et leur "
                             "numérotation sont conservées"),
            (PORTEE_TOUT, "Tout — entrées et semaines"),
        ],
        initial=PORTEE_ENTREES,
    )
    confirmation = forms.CharField(
        label="Confirmation",
        help_text="Saisis SUPPRIMER en majuscules pour confirmer.",
    )

    def clean_confirmation(self):
        valeur = self.cleaned_data["confirmation"]
        if valeur != "SUPPRIMER":
            raise forms.ValidationError(
                "Saisie incorrecte : la suppression n'a pas été effectuée."
            )
        return valeur
