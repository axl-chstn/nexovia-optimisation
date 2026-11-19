"""Contrôles indépendants des résultats, directement sur les CSV."""
# Recalcule le coût d'une solution en relisant les csv avec le module csv (sans pandas
# et sans les fonctions du socle). Si une contrainte n'est pas respectée, assert s'arrête.
# Ça permet de vérifier nos résultats avec un code écrit séparément.

import csv, json, hashlib, math
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parent.parent


def lignes(path):
    with path.open(encoding='utf-8-sig') as entree:
        return list(csv.DictReader(entree, delimiter=';'))


def verifier(S, nom):
    # Lecture des données de l'instance
    base = ROOT / 'donnees' / nom
    techs = {r['technicien']: r for r in lignes(base / 'techniciens.csv')}
    jobs = {r['intervention']: r for r in lignes(base / 'interventions.csv')}
    trajets = {(r['origine'], r['destination']): (float(r['temps_min']), float(r['distance_km'])) for r in lignes(base / 'trajets.csv')}
    dispos = {t: [] for t in techs}
    for r in lignes(base / 'disponibilites.csv'):
        dispos[r['technicien']].append((float(r['debut_min']), float(r['fin_min'])))
    for a in dispos.values():
        a.sort()
    c = float(next(r['valeur'] for r in lignes(base / 'parametres.csv') if r['parametre'] == 'cout_report'))

    # chaque intervention apparaît exactement une fois
    assert set(S) == set(techs) | {'reportees'}
    assert Counter([m for t in techs for m in S[t]] + S['reportees']) == Counter(jobs.keys())
    total = 0

    def arriver(depart, duree, plages):
        # heure d'arrivée d'un trajet qui ne roule que pendant les créneaux
        reste = duree
        if reste <= 1e-9:
            return depart
        for a, b in plages:
            debut = max(a, depart)
            if debut >= b:
                continue
            disponible = b - debut
            if reste <= disponible + 1e-9:
                return debut + reste
            reste -= disponible
        raise AssertionError('Trajet hors disponibilités')

    # on refait chaque tournée minute par minute
    for t, info in techs.items():
        if not S[t]:
            continue
        plages = dispos[t]
        heure = plages[0][0]
        lieu = info['domicile']
        for m in S[t]:
            j = jobs[m]
            assert int(info[j['competence_requise']]) == 1
            duree, distance = trajets[(lieu, m)]
            heure = arriver(heure, duree, plages)
            total += distance
            duree = float(j['duree_min'])
            w0 = float(j['debut_fenetre_min'])
            w1 = float(j['fin_fenetre_min'])
            # débuts possibles : la mission doit tenir dans un créneau et dans sa fenêtre
            debuts = [max(heure, w0, a) for a, b in plages if max(heure, w0, a) + duree <= min(b, w1) + 1e-9]
            assert debuts, 'Intervention hors créneau ou coupure'
            heure = min(debuts) + duree
            lieu = m
        # retour au domicile
        duree, distance = trajets[(lieu, info['domicile'])]
        arriver(heure, duree, plages)
        total += distance
    return total + c * len(S['reportees'])