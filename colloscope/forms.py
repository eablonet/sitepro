from django import forms

class AccesForm(forms.Form):
    mot_de_passe = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )