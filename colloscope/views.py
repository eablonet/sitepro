from datetime import date

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AccesForm

from .models import Colleur, Creneau, Eleve, GroupeColle, Passage, Semaine, ImportColloscope
from .acces import (
    CLE_SESSION, CLE_SUIVANT, DUREE_SESSION, MAX_ECHECS,
    acces_colloscope, echecs_restants, enregistrer_echec,
    reinitialiser_echecs, verifier_mot_de_passe,
)


def acces(request):
    if request.session.get(CLE_SESSION) in ('eleve', 'prof'):
        return redirect('colloscope:colloscope')

    restants = echecs_restants(request)
    bloque = restants == 0

    if request.method == 'POST' and not bloque:
        form = AccesForm(request.POST)
        if form.is_valid():
            niveau = verifier_mot_de_passe(form.cleaned_data['mot_de_passe'])
            if niveau:
                reinitialiser_echecs(request)
                # Régénère l'identifiant de session : empêche qu'un identifiant
                # obtenu avant la saisie du mot de passe reste valide après.
                request.session.cycle_key()
                request.session[CLE_SESSION] = niveau
                request.session.set_expiry(DUREE_SESSION)
                suivant = request.session.pop(CLE_SUIVANT, None)
                if suivant and suivant.startswith('/'):
                    return redirect(suivant)
                return redirect('colloscope:colloscope')

            enregistrer_echec(request)
            restants = echecs_restants(request)
            bloque = restants == 0
            if bloque:
                form.add_error(None, "Trop de tentatives. Réessayez dans 30 minutes.")
            else:
                form.add_error('mot_de_passe', "Mot de passe incorrect.")
    else:
        form = AccesForm()

    return render(request, 'colloscope/acces.html', {
        'form': form,
        'bloque': bloque,
        'restants': restants,
        'avertir': 0 < restants <= 3,
    })


@require_POST
def deconnexion(request):
    request.session.pop(CLE_SESSION, None)
    request.session.pop(CLE_SUIVANT, None)
    return redirect('colloscope:acces')


@acces_colloscope
def colloscope(request):
    niveau = request.session[CLE_SESSION]
    dernier_import = ImportColloscope.objects.first()

    contexte = {
        'niveau': niveau,
        'libelle_annee': dernier_import.libelle_annee if dernier_import else '',
    }

    semaines = Semaine.objects.all()
    if not semaines.exists():
        return render(request, 'colloscope/colloscope.html', contexte)

    groupes = GroupeColle.objects.all()
    colleurs = Colleur.objects.all()
    matieres = sorted(
        m for m in colleurs.values_list('matiere', flat=True).distinct() if m
    )

    passages = Passage.objects.select_related(
        'creneau', 'creneau__colleur', 'semaine', 'groupe'
    )

    # --- Semaine (par défaut : la plus récente déjà commencée) ---
    semaine_active = None
    semaine_param = request.GET.get('semaine', '')
    if semaine_param == 'toutes':
        pass
    elif semaine_param.isdigit():
        semaine_active = semaines.filter(numero=int(semaine_param)).first()
    else:
        semaine_active = (
            semaines.filter(date_debut__lte=date.today())
            .order_by('-date_debut').first()
            or semaines.first()
        )
    if semaine_active:
        passages = passages.filter(semaine=semaine_active)

    # --- Groupe ---
    groupe_actif = None
    if request.GET.get('groupe'):
        groupe_actif = groupes.filter(nom=request.GET['groupe']).first()
        if groupe_actif:
            passages = passages.filter(groupe=groupe_actif)

    # --- Élève (niveau prof uniquement) ---
    eleve_actif = None
    if niveau == 'prof' and request.GET.get('eleve', '').isdigit():
        eleve_actif = Eleve.objects.filter(pk=int(request.GET['eleve'])).first()
        if eleve_actif:
            passages = passages.filter(groupe__in=eleve_actif.groupes.all())

    # --- Colleur ---
    colleur_actif = None
    if request.GET.get('colleur', '').isdigit():
        colleur_actif = colleurs.filter(pk=int(request.GET['colleur'])).first()
        if colleur_actif:
            passages = passages.filter(creneau__colleur=colleur_actif)

    # --- Matière ---
    matiere_active = request.GET.get('matiere') or None
    if matiere_active in matieres:
        passages = passages.filter(creneau__colleur__matiere=matiere_active)
    else:
        matiere_active = None

    passages = list(passages)

    membres = {}
    if niveau == 'prof':
        for eleve in Eleve.objects.prefetch_related('groupes'):
            for groupe in eleve.groupes.all():
                membres.setdefault(groupe.pk, []).append(str(eleve))
    for passage in passages:
        passage.membres = membres.get(passage.groupe_id, [])

    planning = []
    for passage in passages:
        if not planning or planning[-1]['semaine'] != passage.semaine:
            planning.append({'semaine': passage.semaine, 'jours': []})
        jours = planning[-1]['jours']
        libelle = passage.creneau.get_jour_display()
        if not jours or jours[-1]['libelle'] != libelle:
            jours.append({'libelle': libelle, 'passages': []})
        jours[-1]['passages'].append(passage)

    contexte.update({
        'planning': planning,
        'semaines': semaines,
        'groupes': groupes,
        'colleurs': colleurs,
        'matieres': matieres,
        'eleves': Eleve.objects.all() if niveau == 'prof' else None,
        'semaine_active': semaine_active,
        'groupe_actif': groupe_actif,
        'eleve_actif': eleve_actif,
        'colleur_actif': colleur_actif,
        'matiere_active': matiere_active,
    })
    return render(request, 'colloscope/colloscope.html', contexte)