from django import forms


class ContactForm(forms.Form):
    nom = forms.CharField(
        max_length=100,
        label="Votre nom",
        widget=forms.TextInput(attrs={'placeholder': 'Prénom Nom'})
    )
    email = forms.EmailField(
        label="Votre adresse électronique",
        widget=forms.EmailInput(attrs={'placeholder': 'vous@exemple.fr'})
    )
    sujet = forms.CharField(
        max_length=150,
        label="Sujet",
        widget=forms.TextInput(attrs={'placeholder': 'Objet de votre message'})
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={'rows': 8})
    )
    # Champ piège anti-spam : invisible pour un humain, souvent rempli par les robots
    site_web = forms.CharField(
        required=False,
        label="Ne pas remplir ce champ",
        widget=forms.TextInput(attrs={'autocomplete': 'off', 'tabindex': '-1'})
    )

    def clean_site_web(self):
        valeur = self.cleaned_data.get('site_web')
        if valeur:
            raise forms.ValidationError("Envoi refusé.")
        return valeur