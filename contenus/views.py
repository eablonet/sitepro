from django.shortcuts import render, get_object_or_404
from .models import Theme, TP, Devoir, Cours, FicheOutil, AnneeScolaire

from django.core.mail import EmailMessage
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
from .forms import ContactForm

from itertools import chain

# traçage des erreurs
import logging
logger = logging.getLogger(__name__)


# Vue pour les TP
def liste_tp(request):
    tp_liste = TP.objects.filter(
        publie=True,
        annee_scolaire__est_courante=True
    ).prefetch_related('themes')
    return render(request, 'contenus/liste_tp.html', {'tp_liste': tp_liste})

# Vue pour les devoirs
def liste_devoirs(request):
    theme_slug = request.GET.get('theme')
    type_filtre = request.GET.get('type')

    themes = Theme.objects.all()
    devoirs_qs = Devoir.objects.filter(
        publie=True, annee_scolaire__est_courante=True
    ).prefetch_related('themes')

    theme_actif = None
    if theme_slug:
        theme_actif = get_object_or_404(Theme, slug=theme_slug)
        devoirs_qs = devoirs_qs.filter(themes=theme_actif)

    type_actif = None
    if type_filtre in dict(Devoir.TypeDevoir.choices):
        type_actif = type_filtre
        devoirs_qs = devoirs_qs.filter(type=type_actif)

    devoirs = list(devoirs_qs.order_by('titre'))

    devoirs_par_type = []
    for type_value, type_label in Devoir.TypeDevoir.choices:
        groupe = [d for d in devoirs if d.type == type_value]
        if groupe:
            devoirs_par_type.append({
                'type_value': type_value,
                'type_label': type_label,
                'devoirs': groupe,
            })

    return render(request, 'contenus/liste_devoirs.html', {
        'themes': themes,
        'types_devoir': Devoir.TypeDevoir.choices,
        'devoirs_par_type': devoirs_par_type,
        'theme_actif': theme_actif,
        'type_actif': type_actif,
    })
# vues les cours
def liste_cours(request):
    theme_slug = request.GET.get('theme')

    themes = Theme.objects.all()
    cours_liste = Cours.objects.filter(
        publie=True, annee_scolaire__est_courante=True
    ).select_related('theme').prefetch_related(
        'tp_lies', 'devoirs_lies'
    ).order_by('theme__ordre', 'theme__nom', 'titre')

    theme_actif = None
    if theme_slug:
        theme_actif = get_object_or_404(Theme, slug=theme_slug)
        cours_liste = cours_liste.filter(theme=theme_actif)

    # Fusionner TP et devoirs liés en une seule liste par cours
    for cours in cours_liste:
        tps = list(cours.tp_lies.all())
        devoirs = list(cours.devoirs_lies.all())
        for tp in tps:
            tp.type_doc = 'tp'
        for devoir in devoirs:
            devoir.type_doc = 'devoir'
        cours.documents_lies = sorted(chain(tps, devoirs), key=lambda d: d.titre)

    # Regrouper les cours par thème pour l'affichage en sections
    cours_par_theme = []
    theme_courant = None
    for cours in cours_liste:
        if cours.theme != theme_courant:
            theme_courant = cours.theme
            cours_par_theme.append({'theme': theme_courant, 'cours_liste': []})
        cours_par_theme[-1]['cours_liste'].append(cours)

    return render(request, 'contenus/liste_cours.html', {
        'themes': themes,
        'cours_par_theme': cours_par_theme,
        'theme_actif': theme_actif,
    })

# vue pour les FO
def liste_fiches_outils(request):
    fiches = FicheOutil.objects.filter(
        publie=True,
        annee_scolaire__est_courante=True
    ).prefetch_related('fichiers').order_by('titre')
    return render(request, 'contenus/liste_fiches_outils.html', {'fiches': fiches})

# vues archives (- à modifier en une seule vue -later)
TYPES_ARCHIVE = ['cours', 'tp', 'devoirs', 'fiches']

def archives(request, annee_nom=None):
    annees = AnneeScolaire.objects.filter(est_courante=False)

    if annee_nom:
        annee_active = get_object_or_404(AnneeScolaire, nom=annee_nom, est_courante=False)
    else:
        annee_active = annees.first()  # la plus récente, grâce à Meta.ordering sur AnneeScolaire

    type_actif = request.GET.get('type')
    if type_actif not in TYPES_ARCHIVE:
        type_actif = 'cours'

    contexte = {
        'annees': annees,
        'annee_active': annee_active,
        'type_actif': type_actif,
    }

    if annee_active is None:
        return render(request, 'contenus/archives.html', contexte)

    if type_actif == 'cours':
        cours_liste = Cours.objects.filter(
            annee_scolaire=annee_active
        ).select_related('theme').prefetch_related(
            'tp_lies', 'devoirs_lies'
        ).order_by('theme__ordre', 'theme__nom', 'titre')

        for cours in cours_liste:
            tps = list(cours.tp_lies.all())
            devoirs = list(cours.devoirs_lies.all())
            for tp in tps:
                tp.type_doc = 'tp'
            for devoir in devoirs:
                devoir.type_doc = 'devoir'
            cours.documents_lies = sorted(chain(tps, devoirs), key=lambda d: d.titre)

        cours_par_theme = []
        theme_courant = None
        for cours in cours_liste:
            if cours.theme != theme_courant:
                theme_courant = cours.theme
                cours_par_theme.append({'theme': theme_courant, 'cours_liste': []})
            cours_par_theme[-1]['cours_liste'].append(cours)

        contexte['cours_par_theme'] = cours_par_theme

    elif type_actif == 'tp':
        contexte['tp_liste'] = TP.objects.filter(
            annee_scolaire=annee_active
        ).prefetch_related('themes').order_by('titre')

    elif type_actif == 'devoirs':
        devoirs = list(Devoir.objects.filter(
            annee_scolaire=annee_active
        ).prefetch_related('themes').order_by('titre'))

        devoirs_par_type = []
        for type_value, type_label in Devoir.TypeDevoir.choices:
            groupe = [d for d in devoirs if d.type == type_value]
            if groupe:
                devoirs_par_type.append({
                    'type_value': type_value,
                    'type_label': type_label,
                    'devoirs': groupe,
                })
        contexte['devoirs_par_type'] = devoirs_par_type

    elif type_actif == 'fiches':
        contexte['fiches'] = FicheOutil.objects.filter(
            annee_scolaire=annee_active
        ).prefetch_related('fichiers').order_by('titre')

    return render(request, 'contenus/archives.html', contexte)
    
    
    
# page d'accueil
def accueil(request):
    cours_liste = Cours.objects.filter(
        publie=True, annee_scolaire__est_courante=True
    ).select_related('theme')[:10]

    tp_liste = TP.objects.filter(
        publie=True, annee_scolaire__est_courante=True
    )[:10]

    devoirs = Devoir.objects.filter(
        publie=True, annee_scolaire__est_courante=True
    )[:10]

    fiches = FicheOutil.objects.filter(
        publie=True, annee_scolaire__est_courante=True
    ).prefetch_related('fichiers')[:10]
    
    # On étiquette chaque objet avec son type, pour savoir quoi afficher dans le template
    for c in cours_liste:
        c.type_contenu = 'cours'
    for tp in tp_liste:
        tp.type_contenu = 'tp'
    for d in devoirs:
        d.type_contenu = 'devoir'
    for f in fiches:
        f.type_contenu = 'fiche'

    derniers_contenus = sorted(
        chain(cours_liste, tp_liste, devoirs, fiches),
        key=lambda obj: obj.date_publication,
        reverse=True
    )[:10]

    return render(request, 'contenus/accueil.html', {
        'derniers_contenus': derniers_contenus,
    })
    
def mentions_legales(request):
    return render(request, 'contenus/mentions_legales.html')


def confidentialite(request):
    return render(request, 'contenus/confidentialite.html')



# =====
# Formulaire de contact
# ====
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            nom = form.cleaned_data['nom']
            email = form.cleaned_data['email']
            sujet = form.cleaned_data['sujet']
            message = form.cleaned_data['message']

            corps = (
                f"Message envoyé depuis le formulaire de contact du site.\n\n"
                f"Nom : {nom}\n"
                f"Adresse : {email}\n\n"
                f"{message}"
            )

            try:
                EmailMessage(
                    subject=f"[Site TSI1] {sujet}",
                    body=corps,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.CONTACT_EMAIL],
                    reply_to=[email],
                ).send()
                messages.success(request, "Votre message a bien été envoyé. Merci !")
            except Exception:
                logger.exception("Échec d'envoi du formulaire de contact")
                messages.error(request, "L'envoi a échoué, veuillez réessayer plus tard.")

            return redirect('contenus:contact')
    else:
        form = ContactForm()

    return render(request, 'contenus/contact.html', {'form': form})







