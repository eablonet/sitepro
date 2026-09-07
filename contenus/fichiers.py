from pathlib import Path

from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


class StockageEcrasement(FileSystemStorage):
    """FileSystemStorage qui écrase le fichier existant au lieu de le renommer."""

    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            self.delete(name)
        return super().get_available_name(name, max_length)


@deconstructible
class CheminMedia:
    """Chemin déterministe : <dossier>/<identifiant>-<suffixe><extension>"""

    def __init__(self, dossier, suffixe, attribut='slug'):
        self.dossier = dossier
        self.suffixe = suffixe
        self.attribut = attribut

    def __call__(self, instance, nom_fichier):
        extension = Path(nom_fichier).suffix.lower()
        identifiant = getattr(instance, self.attribut)
        return f"{self.dossier}/{identifiant}-{self.suffixe}{extension}"

    def __eq__(self, autre):
        return (
            isinstance(autre, CheminMedia)
            and self.dossier == autre.dossier
            and self.suffixe == autre.suffixe
            and self.attribut == autre.attribut
        )