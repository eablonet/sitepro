"""`cahier_texte/views.py` — fichier complet, à remplacer tel quel.

Organisation :
  - outils de date et de libellé ;
  - `_contexte()` : tout le calcul de la fenêtre glissante, partagé ;
  - `cahier_texte()` : la page publique ;
  - `cahier_edition()` et les deux vues d'écriture, réservées au staff.
"""

from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import EntreeRapideForm, choix_documents
from .models import EntreeCahier, SemaineCahier

SEMAINES_AVANT = 1
SEMAINES_APRES = 2
TAILLE_FENETRE = SEMAINES_AVANT + 1 + SEMAINES_APRES

JOURS_AFFICHES = (0, 1, 2, 3, 4)

_MOIS = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre",
    12: "décembre",
}


# --- Outils ---------------------------------------------------------------

def _lundi_de(jour):
    """Règle « on ne change de semaine que le lundi » : samedi et dimanche
    renvoient encore le lundi écoulé."""
    return jour - timedelta(days=jour.weekday())


def _semaine_de_reference(lundi):
    qs = SemaineCahier.objects.select_related("annee")
    return (
        qs.filter(date_lundi=lundi).first()
        or qs.filter(date_lundi__gte=lundi).order_by("date_lundi").first()
        or qs.order_by("date_lundi").last()
    )


def _libelle_dates(semaine):
    debut = semaine.date_lundi
    fin = debut + timedelta(days=4)
    if debut.month == fin.month:
        return f"{debut.day} au {fin.day} {_MOIS[fin.month]}"
    return f"{debut.day} {_MOIS[debut.month]} au {fin.day} {_MOIS[fin.month]}"


def _entier(valeur, defaut=0):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return defaut


# --- Contexte partagé -----------------------------------------------------

def _contexte(request):
    """Tout le calcul commun aux deux pages.

    Retourne un dictionnaire prêt pour le gabarit, ou `None` si le
    calendrier est vide — c'est à l'appelant de décider quoi en faire.
    """
    aujourdhui = date.today()
    lundi = _lundi_de(aujourdhui)

    reference = _semaine_de_reference(lundi)
    if reference is None:
        return {"semaines": []}

    semaines = list(
        SemaineCahier.objects
        .filter(annee=reference.annee)
        .order_by("date_lundi")
        .prefetch_related(Prefetch(
            "entrees",
            queryset=(
                EntreeCahier.objects
                .select_related(*EntreeCahier.CHAMPS_LIAISON)
                .prefetch_related("fiche_outil__fichiers")
            ),
        ))
    )

    # Fenêtre glissante : sa taille ne change jamais, seule son origine bouge.
    index = semaines.index(reference)
    decalage = _entier(request.GET.get("decalage"))
    debut = index - SEMAINES_AVANT + decalage
    debut = max(0, min(debut, max(0, len(semaines) - TAILLE_FENETRE)))
    fenetre = semaines[debut:debut + TAILLE_FENETRE]

    # rubriques_valides = {r.value for r in EntreeCahier.Rubrique}

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

    return {
        "semaines": contexte_semaines,
        "decalage": decalage,
        "peut_remonter": debut > 0,
        "peut_descendre": debut + TAILLE_FENETRE < len(semaines),
    }


# --- Page publique --------------------------------------------------------

def cahier_texte(request):
    return render(request, "cahier_texte/cahier.html", _contexte(request))


# --- Page d'édition -------------------------------------------------------

def _greffer_formulaires(contexte):
    """Attache un formulaire à chaque entrée et à chaque semaine.

    Les choix de documents sont construits UNE fois puis partagés : six
    modèles interrogés par formulaire feraient des centaines de requêtes
    sur une page qui en affiche quarante.
    """
    choix = choix_documents()

    for semaine in contexte["semaines"]:
        toutes = [e for jour in semaine["jours"] for e in jour["entrees"]]
        toutes += semaine["hebdomadaires"]
        for entree in toutes:
            entree.formulaire = EntreeRapideForm(
                instance=entree, choix=choix, prefix=f"e{entree.pk}"
            )
        semaine["formulaire_ajout"] = EntreeRapideForm(
            choix=choix, prefix=f"s{semaine['objet'].pk}"
        )


@staff_member_required
def cahier_edition(request):
    """`staff_member_required` réutilise la session de l'admin : aucune page
    de connexion à écrire, et un compte élève éventuel n'y accéderait pas."""
    contexte = _contexte(request)
    if contexte["semaines"]:
        _greffer_formulaires(contexte)
    contexte["edition"] = True
    return render(request, "cahier_texte/cahier_edition.html", contexte)


def _redirection(request, semaine_id=None):
    cible = request.POST.get("retour") or reverse("cahier_texte:edition")
    if semaine_id:
        cible += f"#semaine-{semaine_id}"
    return redirect(cible)


@staff_member_required
@require_POST
def entree_creer(request, semaine_id):
    semaine = get_object_or_404(SemaineCahier, pk=semaine_id)
    formulaire = EntreeRapideForm(
        request.POST, choix=choix_documents(), prefix=f"s{semaine_id}"
    )

    if formulaire.is_valid():
        entree = formulaire.save(commit=False)
        entree.semaine = semaine
        entree.save()
        messages.success(request, "Entrée ajoutée.")
    else:
        messages.error(request, f"Ajout impossible : {formulaire.errors.as_text()}")

    return _redirection(request, semaine_id)


@staff_member_required
@require_POST
def entree_modifier(request, pk):
    entree = get_object_or_404(EntreeCahier, pk=pk)
    semaine_id = entree.semaine_id

    if "supprimer" in request.POST:
        entree.delete()
        messages.warning(request, "Entrée supprimée.")
        return _redirection(request, semaine_id)

    formulaire = EntreeRapideForm(
        request.POST, instance=entree, choix=choix_documents(), prefix=f"e{pk}"
    )
    if formulaire.is_valid():
        formulaire.save()
        messages.success(request, "Entrée enregistrée.")
    else:
        messages.error(
            request, f"Enregistrement impossible : {formulaire.errors.as_text()}"
        )

    return _redirection(request, semaine_id)
