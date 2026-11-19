import pandas as pd
from pathlib import Path
EPS=1e-9

import pandas as pd
from pathlib import Path

def lire_instance(nom):
    # nom = chemin du dossier de l'instance (ex : "donnees/N50")
    # chaque instance est un dossier avec 6 fichiers csv séparés par des ;
    dossier = Path(nom)

    instance = {
        "techniciens": pd.read_csv(dossier / "techniciens.csv", sep=";"),
        "interventions": pd.read_csv(dossier / "interventions.csv", sep=";"),
        "disponibilites": pd.read_csv(dossier / "disponibilites.csv", sep=";"),
        "lieux": pd.read_csv(dossier / "lieux.csv", sep=";"),
        "trajets": pd.read_csv(dossier / "trajets.csv", sep=";"),
        "parametres": pd.read_csv(dossier / "parametres.csv", sep=";")
    }

    return instance

def preparer_instance(N):
    # On recopie les tableaux pandas dans des dictionnaires.
    # Chercher une valeur dans un dictionnaire est beaucoup plus rapide que filtrer
    # un DataFrame, et ces fonctions sont appelées des millions de fois.

    # Distances et temps de trajet, avec la clé (origine, destination)
    N["dist"] = {}
    N["temps"] = {}

    for _, ligne in N["trajets"].iterrows():
        origine = ligne["origine"]
        destination = ligne["destination"]
        N["dist"][(origine, destination)] = ligne["distance_km"]
        N["temps"][(origine, destination)] = ligne["temps_min"]

    # Informations sur les interventions : durée, fenêtre horaire et compétence
    N["duree"] = {}
    N["debut"] = {}
    N["fin"] = {}
    N["comp"] = {}

    for _, ligne in N["interventions"].iterrows():
        i = ligne["intervention"]
        N["duree"][i] = ligne["duree_min"]
        N["debut"][i] = ligne["debut_fenetre_min"]
        N["fin"][i] = ligne["fin_fenetre_min"]
        N["comp"][i] = ligne["competence_requise"]

    # Informations sur les techniciens : domicile, compétences (1 ou 0)
    # et liste de leurs créneaux de disponibilité
    N["domicile"] = {}
    N["habilite"] = {}
    N["dispos"] = {}

    for _, ligne in N["techniciens"].iterrows():
        t = ligne["technicien"]

        N["domicile"][t] = ligne["domicile"]
        N["habilite"][t] = {
            "ELEC": ligne["ELEC"],
            "EAU": ligne["EAU"],
            "COMPTEUR": ligne["COMPTEUR"]
        }
        N["dispos"][t] = []

    # on trie les créneaux par heure de début pour les parcourir dans l'ordre
    lignes = N["disponibilites"].sort_values("debut_min")
    for _, ligne in lignes.iterrows():
        N["dispos"][ligne["technicien"]].append(
            (ligne["debut_min"], ligne["fin_min"])
        )

    # Liste des techniciens et coût d'un report (2e ligne de parametres.csv)
    N["techs"] = N["techniciens"]["technicien"].tolist()
    N["penalite"] = float(N["parametres"]["valeur"].iloc[1])

def verifier_missions(S, N):
    # Chaque intervention doit apparaître exactement une fois :
    # soit dans une tournée, soit dans les reportées.

    missions = []

    for tech in N["techniciens"]["technicien"]:
        missions += S[tech]

    missions += S["reportees"]

    toutes = N["interventions"]["intervention"].tolist()

    # si on trie les deux listes, elles doivent être identiques
    return sorted(missions) == sorted(toutes)

def verifier_competences(S, N):
    # Un technicien ne peut faire que les interventions de ses compétences.
    # (version lente avec pandas, utilisée seulement dans est_realisable)

    for tech in N["techniciens"]["technicien"]:

        ligne_tech = N["techniciens"][
            N["techniciens"]["technicien"] == tech
        ].iloc[0]

        for mission in S[tech]:

            intervention = N["interventions"][
                N["interventions"]["intervention"] == mission
            ].iloc[0]

            competence = intervention["competence_requise"]

            if ligne_tech[competence] != 1:
                return False

    return True

def lire_disponibilites(N, tech):
    # Renvoie les créneaux (debut, fin) d'un technicien, triés.
    # Sert à afficher_planning ; les autres fonctions utilisent N["dispos"].

    lignes = N["disponibilites"][
        N["disponibilites"]["technicien"] == tech
    ].sort_values("debut_min")

    disponibilites = []

    for _, ligne in lignes.iterrows():
        disponibilites.append(
            (ligne["debut_min"], ligne["fin_min"])
        )

    return disponibilites

# petite tolérance pour éviter les erreurs d'arrondi sur les minutes
EPS = 1e-9

def faire_trajet(N, origine, destination, heure, disponibilites):
    # Fait rouler le technicien de origine à destination à partir de "heure".
    # Il ne peut rouler que pendant ses créneaux : s'il y a une pause, le trajet
    # est coupé en deux et reprend au créneau suivant.
    # Renvoie l'heure d'arrivée, ou None si le trajet ne tient pas dans la journée.

    if origine == destination:
        return heure

    reste = N["temps"][(origine, destination)]   # minutes de route qu'il reste à faire

    for debut, fin in disponibilites:

        # si on est avant le créneau, on attend son début
        heure = max(heure, debut)

        # créneau déjà fini : on passe au suivant
        if heure >= fin:
            continue

        temps_disponible = fin - heure

        # le reste du trajet tient dans ce créneau : on arrive
        if reste <= temps_disponible + EPS:
            return heure + reste

        # sinon on roule jusqu'à la fin du créneau et on continue au suivant
        reste = reste - temps_disponible
        heure = fin

    return None


def verifier_tournee(S, N, tech):
    # Vérifie la tournée d'un seul technicien : compétences, créneaux,
    # fenêtres horaires des interventions et retour au domicile.
    # C'est la fonction la plus utilisée : les métaheuristiques ne revérifient
    # que les tournées qu'elles viennent de modifier.

    domicile = N["domicile"][tech]
    disponibilites = N["dispos"][tech]


    # Compétences
    for mission in S[tech]:
        competence = N["comp"][mission]
        if N["habilite"][tech][competence] != 1:
            return False

    # départ du domicile au début du premier créneau
    heure = disponibilites[0][0]
    lieu = domicile

    for mission in S[tech]:

        # Aller à l'intervention
        heure = faire_trajet(N, lieu, mission, heure, disponibilites)

        if heure is None:
            return False

        # Chercher une heure possible pour la mission : elle doit tenir en entier
        # dans un créneau du technicien et finir avant la fin de sa fenêtre
        possible = False

        for debut, fin in disponibilites:

            debut_mission = max(heure, debut, N["debut"][mission])
            fin_mission = debut_mission + N["duree"][mission]

            if fin_mission <= fin + EPS and fin_mission <= N["fin"][mission] + EPS:
                heure = fin_mission
                possible = True
                break

        if possible == False:
            return False


        lieu = mission

    # Retour au domicile, lui aussi pendant les créneaux
    retour = faire_trajet(N, lieu, domicile, heure, disponibilites)

    return retour is not None


def distance_tournee(N, tech, missions):
    # Distance d'une tournée : domicile -> missions dans l'ordre -> domicile

    if len(missions) == 0:
        return 0

    domicile = N["domicile"][tech]
    tournee = [domicile] + missions + [domicile]

    distance = 0

    for i in range(len(tournee) - 1):
        distance += N["dist"][(tournee[i], tournee[i + 1])]

    return distance


def f(S, N):
    # Fonction objectif : distance totale + coût de report x nombre de reports

    distance_totale = 0

    for tech in N["techs"]:
        distance_totale += distance_tournee(N, tech, S[tech])


    return distance_totale + N["penalite"] * len(S["reportees"])

def est_realisable(S, N):
    # Vérification complète d'une solution (plus lente) : on s'en sert
    # pour contrôler les solutions finales.

    if verifier_missions(S, N) == False:
        return False

    if verifier_competences(S, N) == False:
        return False

    for tech in N["techniciens"]["technicien"]:

        if verifier_tournee(S, N, tech) == False:
            return False

    return True

def heuristique_gloutonne(N):
    # Construit la solution de départ S0.
    # On prend les interventions par fin de fenêtre croissante et on place chacune
    # là où elle ajoute le moins de kilomètres. Si elle ne rentre nulle part,
    # elle est reportée.

    # Au début, les tournées sont vides
    S = {}

    for tech in N["techs"]:
        S[tech] = []

    S["reportees"] = []

    # On commence par les interventions qui finissent le plus tôt
    interventions = N["interventions"].sort_values("fin_fenetre_min")

    for mission in interventions["intervention"]:

        meilleur_tech = None
        meilleure_position = None
        meilleur_cout = float("inf")

        # On essaie chaque technicien
        for tech in N["techs"]:

            ancienne_distance = distance_tournee(N, tech, S[tech])

            # On teste toutes les positions possibles
            for position in range(len(S[tech]) + 1):

                S[tech].insert(position, mission)

                # On vérifie seulement la tournée modifiée
                if verifier_tournee(S, N, tech):

                    nouvelle_distance = distance_tournee(N, tech, S[tech])
                    cout_ajoute = nouvelle_distance - ancienne_distance

                    if cout_ajoute < meilleur_cout:
                        meilleur_cout = cout_ajoute
                        meilleur_tech = tech
                        meilleure_position = position

                # On enlève la mission pour tester une autre position
                S[tech].pop(position)

        # On garde la meilleure insertion trouvée
        if meilleur_tech is not None:
            S[meilleur_tech].insert(meilleure_position, mission)

        else:
            S["reportees"].append(mission)

    return S