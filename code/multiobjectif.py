# Partie Axel : recherche locale de Pareto (PLS) pour le problème biobjectif
# (minimiser la distance D et le nombre de reports R).
# Les distances sont comptées en mètres entiers (km x 1000) pour comparer les points
# sans problème d'arrondi. La PLS est déterministe : pas de hasard, une seule exécution.

import time, collections, math, itertools
from functools import lru_cache
from socle import *


def cle(S, N):
    # empreinte d'un planning, pour ne pas évaluer deux fois le même voisin
    return tuple(tuple(S[t]) for t in N['techs']) + (tuple(sorted(S['reportees'])),)


def copier(S):
    return {t: v[:] for t, v in S.items()}


def modele(N):
    # Prépare deux fonctions qui gardent en mémoire les tournées déjà calculées.
    dist = {k: int(round(v * 1000)) for k, v in N['dist'].items()}

    # route(t, seq) : distance en mètres de la tournée seq du technicien t,
    # ou None si elle est impossible. lru_cache évite de revérifier la même tournée.
    @lru_cache(maxsize=100000)
    def route(t, seq):
        if not seq:
            return 0
        if not verifier_tournee({t: list(seq)}, N, t):
            return None
        loc = N['domicile'][t]
        d = 0
        for m in seq:
            d += dist[loc, m]
            loc = m
        return d + dist[loc, N['domicile'][t]]

    # objectifs(S) : le couple (D en mètres, R), ou None si le planning est impossible
    def objectifs(S):
        ds = [route(t, tuple(S[t])) for t in N['techs']]
        if any(d is None for d in ds):
            return None
        return sum(ds), len(S['reportees'])

    return route, objectifs


def domine(p, q):
    # p domine q : pas pire sur les deux objectifs, et différent
    return p[0] <= q[0] and p[1] <= q[1] and p != q


def voisins(S, N, route, limite):
    """Relocate, insertion/report, swap et inversion d'un segment (2-opt)."""
    # C'est un générateur : il donne les voisins réalisables un par un (avec le nom du mouvement)
    # et s'arrête dès que l'heure limite est atteinte.
    listes = N['techs'] + ['reportees']
    vus = {cle(S, N)}

    def accepte(V, changes):
        # on ne revérifie que les tournées modifiées, et on refuse les voisins déjà vus
        if any(route(t, tuple(V[t])) is None for t in changes if t != 'reportees'):
            return False
        k = cle(V, N)
        if k in vus:
            return False
        vus.add(k)
        return True

    # 1) relocate : déplacer une mission (vers un autre technicien, une autre position ou les reports)
    for src in listes:
        for i, m in enumerate(S[src]):
            for dst in listes:
                if src == dst == 'reportees':
                    continue
                # le technicien de destination doit avoir la compétence
                if dst != 'reportees' and N['habilite'][dst][N['comp'][m]] != 1:
                    continue
                V0 = copier(S)
                V0[src].pop(i)
                positions = [len(V0[dst])] if dst == 'reportees' else range(len(V0[dst]) + 1)
                for pos in positions:
                    if time.perf_counter() >= limite:
                        return
                    V = copier(V0)
                    V[dst].insert(pos, m)
                    if accepte(V, {src, dst}):
                        yield V, 'relocate'

    # 2) swap : échanger deux missions (avec une reportée, ça fait un remplacement)
    places = [(t, i) for t in listes for i in range(len(S[t]))]
    for a, (t, i) in enumerate(places):
        for u, j in places[a + 1:]:
            if time.perf_counter() >= limite:
                return
            if t == u == 'reportees':
                continue
            V = copier(S)
            V[t][i], V[u][j] = V[u][j], V[t][i]
            if accepte(V, {t, u}):
                yield V, 'swap'

    # 3) 2-opt : inverser un morceau d'une tournée
    for t in N['techs']:
        for i in range(len(S[t])):
            for j in range(i + 2, len(S[t]) + 1):
                if time.perf_counter() >= limite:
                    return
                V = copier(S)
                V[t][i:j] = reversed(V[t][i:j])
                if accepte(V, {t}):
                    yield V, '2-opt'


def pls(S0, N, budget=180, solutions_initiales=None):
    # A : archive des solutions non dominées, rangées par leur point (D, R)
    # U : file des points de l'archive dont on n'a pas encore exploré le voisinage
    debut = time.perf_counter()
    limite = debut + budget
    route, objectifs = modele(N)
    A = {}
    U = collections.deque()
    trace = []
    evenements = []
    examines = 0
    explores = 0

    def ajouter(S, origine):
        # Essaie d'ajouter S à l'archive. Refusé s'il est impossible, déjà présent ou dominé.
        # S'il est ajouté, on retire de l'archive les points qu'il domine.
        nonlocal examines
        p = objectifs(S)
        examines += 1
        if p is None or p in A or any(domine(q, p) for q in A):
            return False
        elim = [q for q in A if domine(p, q)]
        for q in elim:
            del A[q]
        A[p] = copier(S)
        U.append(p)
        # on garde les 12 premiers événements pour illustrer le fonctionnement dans le rapport
        if len(evenements) < 12:
            evenements.append({'origine': origine, 'ajout': [p[0] / 1000, p[1]], 'retraits': [[q[0] / 1000, q[1]] for q in elim],
                               'archive': [[q[0] / 1000, q[1]] for q in sorted(A)]})
        trace.append({'temps': time.perf_counter() - debut, 'points': [[q[0] / 1000, q[1]] for q in sorted(A)]})
        return True

    for S in (solutions_initiales or [S0]):
        ajouter(S, 'initialisation')

    # Boucle principale : on prend un point de la file et on explore tout son voisinage
    while U and time.perf_counter() < limite:
        p = U.popleft()
        # il a pu être retiré de l'archive entre-temps (dominé par un nouveau point)
        if p not in A:
            continue
        S = A[p]
        complet = True
        for V, mvt in voisins(S, N, route, limite):
            if time.perf_counter() >= limite:
                complet = False
                break
            ajouter(V, mvt)
        if time.perf_counter() >= limite:
            complet = False
        if complet:
            explores += 1
        else:
            # budget fini au milieu de l'exploration : on remet le point dans la file et on arrête
            U.appendleft(p)
            break

    # le front final, trié par nombre de reports, avec D en km
    front = [{'D': p[0] / 1000, 'R': p[1], 'solution': S} for p, S in sorted(A.items(), key=lambda e: e[0][1])]
    return {'methode': 'PLS', 'budget': budget, 'temps': time.perf_counter() - debut, 'front': front,
            'arret': 'archive explorée' if not U else 'budget', 'voisins_evalues': examines, 'solutions_explorees': explores,
            'archive_trace': trace, 'illustration': evenements, 'initialisation': 'S0' if solutions_initiales is None else 'solutions fournies'}


def non_domines(points):
    # garde seulement les points non dominés (sans doublons)
    pts = sorted(set(tuple(p) for p in points))
    return [p for p in pts if not any(domine(q, p) for q in pts)]


def hypervolume(points, reference):
    # Aire dominée par les points et bornée par le point de référence (xmax, ymax).
    # Points triés par D croissant : on ajoute un rectangle à chaque fois que R descend.
    pts = non_domines(points)
    xmax, ymax = reference
    niveau = ymax
    aire = 0.0
    for x, y in sorted(pts):
        if x > xmax or y > ymax:
            continue
        if y < niveau:
            aire += (xmax - x) * (niveau - y)
            niveau = y
    return aire


def couverture(A, B):
    # C(A, B) : part des points de B qui sont dominés (ou égalés) par au moins un point de A
    return sum(any(a[0] <= b[0] + 1e-9 and a[1] <= b[1] for a in A) for b in B) / len(B) if B else None