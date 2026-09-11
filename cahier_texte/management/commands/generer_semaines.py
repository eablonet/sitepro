"""
`cahier_texte/management/commands/generer_semaines.py`

Crée d'un coup toutes les semaines de l'année scolaire, du premier au dernier
lundi. Idempotente : relancée, elle ne duplique rien et ne touche pas aux
semaines déjà saisies.

    python manage.py generer_semaines --annee-id 1 --debut 2026-08-31 --fin 2027-07-05
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

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
        debut, fin = options["debut"], options["fin"]

        if debut.weekday() != 0 or fin.weekday() != 0:
            raise CommandError("--debut et --fin doivent tomber un lundi.")
        if fin < debut:
            raise CommandError("--fin est antérieure à --debut.")

        try:
            annee = AnneeScolaire.objects.get(pk=options["annee_id"])
        except AnneeScolaire.DoesNotExist:
            raise CommandError(f"Aucune AnneeScolaire d'identifiant {options['annee_id']}.")

        creees = existantes = 0
        lundi, numero = debut, 1

        while lundi <= fin:
            _, cree = SemaineCahier.objects.get_or_create(
                annee=annee,
                date_lundi=lundi,
                defaults={"numero": None if options["sans_numero"] else numero},
            )
            creees += cree
            existantes += not cree
            lundi += timedelta(days=7)
            numero += 1

        self.stdout.write(self.style.SUCCESS(
            f"{creees} semaine(s) créée(s) pour {annee}."
            + (f" {existantes} déjà présente(s), inchangée(s)." if existantes else "")
        ))
