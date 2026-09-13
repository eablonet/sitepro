"""`cahier_texte/services.py`

Opérations de masse sur le calendrier, appelées aussi bien par la commande
de gestion que par l'admin. Une seule implémentation, deux points d'entrée.
"""

from datetime import timedelta

from django.db import transaction

from .models import EntreeCahier, SemaineCahier


def lundi_de(jour):
    return jour - timedelta(days=jour.weekday())


@transaction.atomic
def generer_semaines(annee, debut, fin, numeroter=True):
    """Crée les semaines manquantes entre deux dates. Idempotent.

    `debut` et `fin` sont ramenées au lundi de leur semaine : l'appelant
    n'a pas à s'en préoccuper. Les semaines déjà présentes ne sont jamais
    modifiées — relancer après avoir renuméroté à la main ne casse rien.

    Retourne (créées, déjà présentes).
    """
    debut, fin = lundi_de(debut), lundi_de(fin)
    if fin < debut:
        raise ValueError("La date de fin précède la date de début.")

    creees = existantes = 0
    lundi, numero = debut, 1

    while lundi <= fin:
        _, cree = SemaineCahier.objects.get_or_create(
            annee=annee,
            date_lundi=lundi,
            defaults={"numero": numero if numeroter else None},
        )
        creees += cree
        existantes += not cree
        lundi += timedelta(days=7)
        numero += 1

    return creees, existantes


@transaction.atomic
def reinitialiser_annee(annee, supprimer_semaines=False):
    """Vide le calendrier d'une année scolaire.

    Deux portées, parce que les deux besoins sont réels et très différents :
      - vider les entrées seulement : on garde la structure de semaines,
        déjà numérotée et marquée vacances, pour ressaisir par-dessus ;
      - tout supprimer : on repart de zéro, y compris les semaines.

    Retourne (entrées supprimées, semaines supprimées).
    """
    semaines = SemaineCahier.objects.filter(annee=annee)

    nb_entrees, _ = EntreeCahier.objects.filter(semaine__in=semaines).delete()

    nb_semaines = 0
    if supprimer_semaines:
        nb_semaines, _ = semaines.delete()

    return nb_entrees, nb_semaines
