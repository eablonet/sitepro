"""`cahier_texte/views.py`"""

from datetime import date, timedelta
from urllib.parse import urlencode

from django.db.models import Prefetch
from django.shortcuts import render

from .models import EntreeCahier, SemaineCahier


SEMAINES_AVANT = 1          # semaines passées visibles dans la fenêtre
SEMAINES_APRES = 2          # semaines à venir visibles
TAILLE_FENETRE = SEMAINES_AVANT + 1 + SEMAINES_APRES

JOURS_AFFICHES = (0, 1, 2, 3, 4)  # lundi → vendredi

# Trois colonnes thématiques, volontairement inégales.
COLONNES_EVIDENCE = (
    ("DS", "DM", "IC"),
    ("COURS", "TD", "TP", "AP"),
    ("PC", "CC"),
)

def _colonnes_evidence(evidence, decalage):
    """Construit les puces, avec l'URL qui bascule chacune sans perdre les autres.

    Le calcul est fait ici plutôt que dans le gabarit : construire une
    query string par différence symétrique est illisible en langage de
    template, et le résultat serait fragile.
    """
    libelles = dict(EntreeCahier.Rubrique.choices)
    colonnes = []
    for groupe in COLONNES_EVIDENCE:
        puces = []
        for valeur in groupe:
            bascule = set(evidence) ^ {valeur}
            parametres = [("decalage", decalage)]
            parametres += [("evidence", v) for v in sorted(bascule)]
            puces.append({
                "valeur": valeur,
                "libelle": libelles[valeur],
                "active": valeur in evidence,
                "url": "?" + urlencode(parametres),
            })
        colonnes.append(puces)
    return colonnes




def _lundi_de(jour):
    """Le lundi de la semaine contenant `jour`.

    C'est ici que se joue la règle « on ne change de semaine que le lundi » :
    samedi et dimanche renvoient encore le lundi écoulé.
    """
    return jour - timedelta(days=jour.weekday())


def _semaine_de_reference(lundi):
    """La semaine courante, ou la plus proche si l'année n'a pas commencé/est finie."""
    qs = SemaineCahier.objects.select_related("annee")
    return (
        qs.filter(date_lundi=lundi).first()
        or qs.filter(date_lundi__gte=lundi).order_by("date_lundi").first()
        or qs.order_by("date_lundi").last()
    )


def _libelle_dates(semaine):
    """« 14 au 18 septembre », ou « 28 septembre au 2 octobre » à cheval."""
    debut = semaine.date_lundi
    fin = debut + timedelta(days=4)
    if debut.month == fin.month:
        return f"{debut.day} au {fin.day} {_MOIS[fin.month]}"
    return f"{debut.day} {_MOIS[debut.month]} au {fin.day} {_MOIS[fin.month]}"


_MOIS = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre",
    12: "décembre",
}


def _entier(valeur, defaut=0):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return defaut


def cahier_texte(request):
    aujourdhui = date.today()
    lundi = _lundi_de(aujourdhui)

    reference = _semaine_de_reference(lundi)
    if reference is None:
        return render(request, "cahier_texte/cahier.html", {"semaines": []})

    liaisons = EntreeCahier.CHAMPS_LIAISON
    semaines = list(
        SemaineCahier.objects
        .filter(annee=reference.annee)
        .order_by("date_lundi")
        .prefetch_related(Prefetch(
            "entrees",
            queryset=EntreeCahier.objects.select_related(*liaisons),
        ))
    )

    # --- Fenêtre glissante : sa taille ne change jamais, seule son origine bouge.
    index = semaines.index(reference)
    decalage = _entier(request.GET.get("decalage"))
    debut = index - SEMAINES_AVANT + decalage
    debut = max(0, min(debut, len(semaines) - TAILLE_FENETRE))
    debut = max(debut, 0)
    fenetre = semaines[debut:debut + TAILLE_FENETRE]

    # --- Mise en évidence : on ne filtre pas, on souligne.
    rubriques_valides = {r.value for r in EntreeCahier.Rubrique}
    evidence = {r for r in request.GET.getlist("evidence") if r in rubriques_valides}

    contexte_semaines = []
    for semaine in fenetre:
        entrees = list(semaine.entrees.all())

        if semaine.date_lundi < lundi:
            etat = "passee"
        elif semaine.date_lundi == lundi:
            etat = "courante"
        else:
            etat = "a_venir"

        jours = []
        for numero in JOURS_AFFICHES:
            du_jour = [e for e in entrees if e.jour == numero]
            jour_date = semaine.date_lundi + timedelta(days=numero)
            jours.append({
                "numero": numero,
                "date": jour_date,
                "entrees": du_jour,
                "vide": not du_jour,
                "aujourdhui": jour_date == aujourdhui,
            })

        contexte_semaines.append({
            "objet": semaine,
            "etat": etat,
            "libelle_dates": _libelle_dates(semaine),
            "jours": jours,
            "hebdomadaires": [e for e in entrees if e.jour is None],
        })

    return render(request, "cahier_texte/cahier.html", {
        "semaines": contexte_semaines,
        "evidence": evidence,
        "colonnes_evidence": _colonnes_evidence(evidence, decalage),
        "suffixe_evidence": "".join(f"&evidence={r}" for r in sorted(evidence)),
        "decalage": decalage,
        "peut_remonter": debut > 0,
        "peut_descendre": debut + TAILLE_FENETRE < len(semaines),
        "jours_entetes": ["lundi", "mardi", "mercredi", "jeudi", "vendredi"],
    })
