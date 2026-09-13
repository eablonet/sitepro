"""
`cahier_texte/management/commands/generer_semaines.py`

Crée d'un coup toutes les semaines de l'année scolaire, du premier au dernier
lundi. Idempotente : relancée, elle ne duplique rien et ne touche pas aux
semaines déjà saisies.

    python manage.py generer_semaines --annee-id 1 --debut 2026-08-31 --fin 2027-07-05
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from cahier_texte.services import generer_semaines
from cahier_texte.models import SemaineCahier
from contenus.models import AnneeScolaire


class Command(BaseCommand):
    help = "Génère les semaines du cahier de texte pour une année scolaire."

    def add_arguments(self, parser):
        parser.add_argument("--annee-id", type=int, required=True,
                            help="Identifiant de l'AnneeScolaire.")
        parser.add_argument("--debut", type=date.fromisoformat, required=True,
                            help="Premier lundi (AAAA-MM-JJ).")
        parser.add_argument("--fin", type=date.fromisoformat, required=True,
                            help="Dernier lundi (AAAA-MM-JJ).")
        parser.add_argument("--sans-numero", action="store_true",
                            help="Ne pas pré-numéroter les semaines.")

    def handle(self, *args, **options):
        try:
            annee = AnneeScolaire.objects.get(pk=options["annee_id"])
        except AnneeScolaire.DoesNotExist:
            raise CommandError(f"Aucune AnneeScolaire d'identifiant {options['annee_id']}.")

        try:
            creees, existantes = generer_semaines(
                annee, options["debut"], options["fin"],
                numeroter=not options["sans_numero"],
            )
        except ValueError as erreur:
            raise CommandError(str(erreur))
 
        self.stdout.write(self.style.SUCCESS(
            f"{creees} semaine(s) créée(s) pour {annee}."
            + (f" {existantes} déjà présente(s)." if existantes else "")
        ))
