import secrets
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect

CLE_SESSION = 'colloscope_niveau'
CLE_SUIVANT = 'colloscope_suivant'
DUREE_SESSION = 60 * 60 * 24 * 4  # 4 jours glissants

MAX_ECHECS = 10          # tentatives ratées tolérées
FENETRE_BLOCAGE = 30 * 60  # blocage de 30 minutes


def adresse_ip(request):
    """IP réelle du visiteur, en tenant compte du proxy Nginx.

    Suppose que Nginx écrase X-Forwarded-For avec $remote_addr : l'en-tête
    contient alors une seule valeur, non falsifiable par le client.
    """
    transmise = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if transmise:
        return transmise.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', 'inconnue')


def _cle_echecs(request):
    return f"colloscope-echecs-{adresse_ip(request)}"


def echecs_restants(request):
    """Nombre de tentatives encore autorisées (0 = bloqué)."""
    return max(0, MAX_ECHECS - cache.get(_cle_echecs(request), 0))


def enregistrer_echec(request):
    cle = _cle_echecs(request)
    # set() réarme le délai à chaque échec : quelqu'un qui insiste reste
    # bloqué tant qu'il n'a pas cessé pendant toute la fenêtre.
    cache.set(cle, cache.get(cle, 0) + 1, FENETRE_BLOCAGE)


def reinitialiser_echecs(request):
    cache.delete(_cle_echecs(request))


def verifier_mot_de_passe(saisi):
    """Retourne 'prof', 'eleve' ou None selon le mot de passe fourni."""
    couples = (
        ('prof', settings.COLLOSCOPE_MDP_PROF),
        ('eleve', settings.COLLOSCOPE_MDP_ELEVE),
    )
    for niveau, attendu in couples:
        if attendu and secrets.compare_digest(saisi, attendu):
            return niveau
    return None


def acces_colloscope(vue):
    """Redirige vers la page de mot de passe si la session n'est pas ouverte."""
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if request.session.get(CLE_SESSION) not in ('eleve', 'prof'):
            request.session[CLE_SUIVANT] = request.get_full_path()
            return redirect('colloscope:acces')
        return vue(request, *args, **kwargs)
    return enveloppe