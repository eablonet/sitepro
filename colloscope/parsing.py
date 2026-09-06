import csv
import unicodedata
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Colleur, Creneau, Eleve, GroupeColle, Passage, Semaine

JOURS_CSV = {
    'lun': Creneau.Jour.LUNDI,
    'mar': Creneau.Jour.MARDI,
    'mer': Creneau.Jour.MERCREDI,
    'jeu': Creneau.Jour.JEUDI,
    'ven': Creneau.Jour.VENDREDI,
    'sam': Creneau.Jour.SAMEDI,
}

# Colonnes de métadonnées attendues dans colloscope.csv (hors semaines).
META_COLLOSCOPE = ('matiere', 'nom', 'jour', 'horaire', 'salle')


def _normaliser(texte):
    """Minuscules, sans accents : 'Matière' -> 'matiere'."""
    texte = unicodedata.normalize('NFKD', texte.strip().lower())
    return ''.join(c for c in texte if not unicodedata.combining(c))


def _lire(fichier):
    """Retourne la liste des lignes du CSV, chaque ligne étant une liste de champs.

    utf-8-sig absorbe le BOM émis par la plupart des tableurs : sans lui, le
    premier champ du fichier commencerait par un caractère invisible.
    """
    fichier.open('rb')
    try:
        texte = fichier.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValidationError(
            "Le fichier n'est pas encodé en UTF-8. Vérifiez l'export."
        )
    finally:
        fichier.close()
    # splitlines() uniformise les fins de ligne (LF, CRLF, CR).
    return [ligne for ligne in csv.reader(texte.splitlines(), delimiter=';')
            if any(champ.strip() for champ in ligne)]


def _numero_semaine(brut, contexte):
    """'S12' ou '12' -> 12."""
    brut = brut.strip().upper().lstrip('S')
    if not brut.isdigit():
        raise ValidationError(f"{contexte} : numéro de semaine « {brut} » invalide.")
    return int(brut)


# --------------------------------------------------------------------------
# Étape 1 — semaines.csv : semaine;date_debut  (S1;2025-08-31)
# --------------------------------------------------------------------------
def _importer_semaines(fichier):
    lignes = _lire(fichier)
    if len(lignes) < 2:
        raise ValidationError("semaines.csv : aucune donnée après l'en-tête.")

    semaines = {}
    for numero_ligne, ligne in enumerate(lignes[1:], start=2):
        contexte = f"semaines.csv ligne {numero_ligne}"
        if len(ligne) < 2:
            raise ValidationError(f"{contexte} : deux colonnes attendues.")

        numero = _numero_semaine(ligne[0], contexte)
        try:
            date_debut = date.fromisoformat(ligne[1].strip())
        except ValueError:
            raise ValidationError(
                f"{contexte} : date « {ligne[1].strip()} » illisible. "
                "Format attendu : AAAA-MM-JJ."
            )

        semaines[numero] = Semaine.objects.create(
            numero=numero, date_debut=date_debut
        )
    return semaines


# --------------------------------------------------------------------------
# Étape 2 — colloscope.csv : Matière;Nom;Jour;Horaire;Salle;S1;S2;…
# --------------------------------------------------------------------------
def _importer_colloscope(fichier, semaines, groupes):
    lignes = _lire(fichier)
    if len(lignes) < 2:
        raise ValidationError("colloscope.csv : aucune donnée après l'en-tête.")

    # Les colonnes sont repérées par leur nom, pas par leur position : ajouter
    # ou déplacer « Salle » ne casse rien.
    meta = {}
    colonnes_semaines = []
    for index, entete in enumerate(lignes[0]):
        nom = _normaliser(entete)
        if nom in META_COLLOSCOPE:
            meta[nom] = index
        elif nom.startswith('s') and nom[1:].isdigit():
            colonnes_semaines.append((index, int(nom[1:])))

    for obligatoire in ('nom', 'jour', 'horaire'):
        if obligatoire not in meta:
            raise ValidationError(
                f"colloscope.csv : colonne « {obligatoire} » absente de l'en-tête."
            )
    if not colonnes_semaines:
        raise ValidationError(
            "colloscope.csv : aucune colonne de semaine (en-têtes S1, S2, …)."
        )

    manquantes = sorted({n for _, n in colonnes_semaines} - set(semaines))
    if manquantes:
        raise ValidationError(
            "colloscope.csv : les semaines "
            f"{', '.join('S' + str(n) for n in manquantes)} ne figurent pas "
            "dans semaines.csv."
        )

    def champ(ligne, nom):
        index = meta.get(nom)
        if index is None or index >= len(ligne):
            return ''
        return ligne[index].strip()

    nb_creneaux = 0
    nb_passages = 0

    for numero_ligne, ligne in enumerate(lignes[1:], start=2):
        contexte = f"colloscope.csv ligne {numero_ligne}"
        nom_colleur = champ(ligne, 'nom')
        if not nom_colleur:
            continue

        jour_brut = champ(ligne, 'jour').lower()[:3]
        jour = JOURS_CSV.get(jour_brut)
        if jour is None:
            raise ValidationError(
                f"{contexte} : jour « {champ(ligne, 'jour')} » non reconnu "
                f"({', '.join(JOURS_CSV)})."
            )

        colleur, _ = Colleur.objects.get_or_create(
            nom=nom_colleur, matiere=champ(ligne, 'matiere')
        )
        creneau = Creneau.objects.create(
            colleur=colleur,
            jour=jour,
            horaire=champ(ligne, 'horaire'),
            salle=champ(ligne, 'salle'),
        )
        nb_creneaux += 1

        for index, numero in colonnes_semaines:
            if index >= len(ligne):
                continue
            nom_groupe = ligne[index].strip().upper()
            if not nom_groupe:
                continue  # créneau libre cette semaine-là

            if nom_groupe not in groupes:
                groupes[nom_groupe] = GroupeColle.objects.create(
                    nom=nom_groupe
                )
            Passage.objects.create(
                creneau=creneau,
                semaine=semaines[numero],
                groupe=groupes[nom_groupe],
            )
            nb_passages += 1

    return nb_creneaux, nb_passages


# --------------------------------------------------------------------------
# Étape 3 — eleves.csv : prenom;nom;groupes  (prenom1;nom1;"T1;B1")
# --------------------------------------------------------------------------
def _importer_eleves(fichier, groupes):
    lignes = _lire(fichier)
    if len(lignes) < 2:
        raise ValidationError("eleves.csv : aucune donnée après l'en-tête.")

    nb_eleves = 0
    groupes_inconnus = set()

    for numero_ligne, ligne in enumerate(lignes[1:], start=2):
        contexte = f"eleves.csv ligne {numero_ligne}"
        if len(ligne) < 3:
            raise ValidationError(f"{contexte} : trois colonnes attendues.")

        prenom, nom = ligne[0].strip(), ligne[1].strip()
        if not nom:
            continue

        eleve = Eleve.objects.create(prenom=prenom, nom=nom)
        nb_eleves += 1

        # Le champ groupes est entre guillemets et utilise lui aussi « ; » :
        # le module csv le restitue tel quel, on le redécoupe ici.
        noms_groupes = [g.strip().upper() for g in ligne[2].split(';') if g.strip()]
        if not noms_groupes:
            raise ValidationError(f"{contexte} : aucun groupe pour {prenom} {nom}.")

        for nom_groupe in noms_groupes:
            if nom_groupe not in groupes:
                groupes[nom_groupe] = GroupeColle.objects.create(
                    nom=nom_groupe
                )
                groupes_inconnus.add(nom_groupe)
            eleve.groupes.add(groupes[nom_groupe])

    return nb_eleves, groupes_inconnus


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
@transaction.atomic
def importer_tout(fichier_semaines, fichier_colloscope, fichier_eleves):
    """Remplace intégralement le contenu du colloscope.

    Tout est écrit dans une transaction unique : si le troisième fichier est
    mal formé, les deux premiers ne sont pas enregistrés non plus.
    """
    vider_colloscope()

    groupes = {}
    semaines = _importer_semaines(fichier_semaines)
    nb_creneaux, nb_passages = _importer_colloscope(
        fichier_colloscope, semaines, groupes
    )
    nb_eleves, groupes_hors_colloscope = _importer_eleves(fichier_eleves, groupes)

    avertissements = []
    if groupes_hors_colloscope:
        avertissements.append(
            "Groupes présents chez les élèves mais absents du colloscope : "
            + ', '.join(sorted(groupes_hors_colloscope))
        )
    sans_eleve = sorted(
        nom for nom, groupe in groupes.items() if not groupe.eleves.exists()
    )
    if sans_eleve:
        avertissements.append(
            "Groupes du colloscope sans aucun élève : " + ', '.join(sans_eleve)
        )

    return {
        'semaines': len(semaines),
        'creneaux': nb_creneaux,
        'passages': nb_passages,
        'groupes': len(groupes),
        'eleves': nb_eleves,
        'avertissements': avertissements,
    }


def vider_colloscope():
    """Efface toutes les données du colloscope, y compris les élèves.

    Utilisé au début de chaque import et par l'action d'admin de fin d'année.
    """
    Passage.objects.all().delete()
    Creneau.objects.all().delete()
    Colleur.objects.all().delete()
    Eleve.objects.all().delete()
    GroupeColle.objects.all().delete()
    Semaine.objects.all().delete()