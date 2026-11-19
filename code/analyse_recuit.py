# Fabrique les tableaux et les figures du recuit et de l'epsilon-contrainte à partir
# des résultats déjà enregistrés dans resultats/*.json (rien n'est relancé, sauf la
# figure de dynamique sur N50, qui refait deux courts recuits).
# Sorties : resultats/tableaux/*.csv et resultats/figures/*.png
# À lancer depuis le dossier du notebook : python code/analyse_recuit.py

import json, os, statistics as st
import matplotlib
matplotlib.use("Agg")      # pas besoin d'écran, on enregistre seulement les images
import matplotlib.pyplot as plt
import pandas as pd
from epsilon_contrainte import *
from epsilon_contrainte import f, objectifs, hypervolume_2d, filtrer_non_domines

INST = ["N0", "N10", "N20", "N30", "N50", "N80", "N100", "N150", "N200"]

# couleurs des graphiques
BLEU, ORANGE, AQUA, JAUNE = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
GRIS, ENCRE, ENCRE2 = "#b8b7b2", "#0b0b0b", "#52514e"
os.makedirs("resultats/tableaux", exist_ok=True)
os.makedirs("resultats/figures", exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.edgecolor": GRIS, "axes.labelcolor": ENCRE2,
                     "xtick.color": ENCRE2, "ytick.color": ENCRE2, "axes.grid": True,
                     "grid.color": "#e6e5e0", "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "lines.linewidth": 2, "figure.dpi": 150,
                     "axes.titlesize": 10, "axes.titleweight": "bold"})


def sd(x):
    # écart-type, 0 s'il n'y a qu'une valeur
    return st.stdev(x) if len(x) > 1 else 0.0


def ref_S0():
    # Pour chaque instance : les données, S0 et ses valeurs (sert de référence partout)
    out = {}
    for nom in INST:
        N = lire_instance(os.path.join("donnees", nom))
        preparer_instance(N)
        S0 = json.load(open("S0_communs.json"))[nom]
        D, R = objectifs(S0, N)
        out[nom] = {"N": N, "S0": S0, "f0": f(S0, N), "D0": D, "R0": R, "c": N["penalite"],
                    "n": len(N["interventions"]), "m": len(N["techs"])}
    return out


REF = ref_S0()


# ---------------------------------------------------------------- mono-objectif
def mono():
    if not os.path.exists("resultats/mono.json"):
        return None
    data = json.load(open("resultats/mono.json"))
    lignes, detail = [], []
    for nom in INST:
        runs = sorted([r for r in data if r["instance"] == nom], key=lambda r: r["graine"])
        f0 = REF[nom]["f0"]

        # tableau de synthèse : meilleure, moyenne, écart-type... pour chaque budget
        for B in (60, 120, 180):
            vals = [l["f"] for r in runs for l in r["lignes"] if l["budget"] == B]
            tb = [l["temps_meilleur"] for r in runs for l in r["lignes"] if l["budget"] == B]
            lignes.append({"Instance": nom, "n": REF[nom]["n"], "m": REF[nom]["m"], "Budget (s)": B,
                           "f(S0)": round(f0, 2), "Meilleure": round(min(vals), 2),
                           "Moyenne": round(st.mean(vals), 2), "Écart-type": round(sd(vals), 2),
                           "Pire": round(max(vals), 2),
                           "Amélioration meilleure (%)": round(100 * (f0 - min(vals)) / f0, 2),
                           "Amélioration moyenne (%)": round(100 * (f0 - st.mean(vals)) / f0, 2),
                           "Temps moyen au meilleur (s)": round(st.mean(tb), 1)})

        # détail de chaque exécution
        for r in runs:
            detail.append({"Instance": nom, "Graine": r["graine"], "f(60s)": round(r["lignes"][0]["f"], 2),
                           "f(120s)": round(r["lignes"][1]["f"], 2), "f(180s)": round(r["f"], 2),
                           "D": r["D"], "R": r["R"], "Itérations": r["iterations"],
                           "Acceptés (%)": round(100 * r["acceptes"] / r["iterations"], 1),
                           "T0": round(r["T0"], 2), "Palier": r["palier"], "Réchauffages": r["rechauffages"],
                           "Temps au meilleur (s)": round(r["temps_meilleur"], 1)})
    T = pd.DataFrame(lignes)
    Dt = pd.DataFrame(detail)
    T.to_csv("resultats/tableaux/recuit_synthese.csv", index=False, sep=";", decimal=",")
    Dt.to_csv("resultats/tableaux/recuit_detail_runs.csv", index=False, sep=";", decimal=",")

    # Figure de convergence : amélioration (%) du meilleur coût en fonction du temps,
    # moyenne des 5 graines avec la zone min-max
    fig, axs = plt.subplots(3, 3, figsize=(10, 8), sharex=True)
    # instants où on lit la courbe (plus serrés au début, où ça bouge beaucoup)
    grille = [0.01 * 1.06 ** k for k in range(200)]
    grille = [0.0] + [g for g in grille if g <= 180] + [180]
    for ax, nom in zip(axs.flat, INST):
        f0 = REF[nom]["f0"]
        courbes = []
        for r in [r for r in data if r["instance"] == nom]:
            h, c, k = r["historique"], [], 0
            # pour chaque instant de la grille, on prend la dernière amélioration connue
            for t in grille:
                while k + 1 < len(h) and h[k + 1][0] <= t:
                    k += 1
                c.append(100 * (f0 - h[k][1]) / f0)
            courbes.append(c)
        moy = [st.mean(v) for v in zip(*courbes)]
        ax.fill_between(grille, [min(v) for v in zip(*courbes)], [max(v) for v in zip(*courbes)],
                        color=BLEU, alpha=0.18, linewidth=0)
        ax.plot(grille, moy, color=BLEU)
        for B in (60, 120):
            ax.axvline(B, color=GRIS, linewidth=0.8, linestyle="--")
        ax.set_xscale("symlog", linthresh=1)
        ax.set_xlim(0, 180)
        ax.set_title(f"{nom}  (f(S0) = {f0:.1f})", loc="left")
        ax.set_xticks([0, 1, 10, 60, 180])
        ax.set_xticklabels(["0", "1", "10", "60", "180"])
    for ax in axs[-1]:
        ax.set_xlabel("Temps (s, échelle log)")
    for ax in axs[:, 0]:
        ax.set_ylabel("Amélioration vs S0 (%)")
    fig.suptitle("Recuit simulé — convergence du meilleur coût (moyenne et min–max sur 5 exécutions)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig("resultats/figures/recuit_convergence.png")
    plt.close(fig)

    # Dynamique d'une exécution sur N50 (20 s) : réglage initial contre réglage retenu.
    # C'est le seul endroit où on relance un calcul (2 recuits de 20 s).
    N, S0 = REF["N50"]["N"], REF["N50"]["S0"]
    fig, axs = plt.subplots(2, 2, figsize=(11, 5.5), sharex=True, sharey="row",
                            gridspec_kw={"height_ratios": [2, 1]})
    for col, (titre, p) in enumerate([("Réglage initial : τ0=0,5  α=0,95  k=5", dict(tau0=0.5, alpha=0.95, k_palier=5)),
                                      ("Réglage retenu : τ0=0,1  α=0,99  k=20", dict(tau0=0.1, alpha=0.99, k_palier=20))]):
        _, _, info = recuit_simule(S0, N, temps_max=20, graine=1, garder_trace=True, **p)
        tr, hb = info["trace"], info["historique"]
        a1, a2 = axs[0, col], axs[1, col]
        # en haut : coût courant et meilleur coût ; en bas : la température
        a1.plot([q[0] for q in tr], [q[1] for q in tr], color=GRIS, linewidth=0.7, label="coût courant")
        a1.step([h[0] for h in hb], [h[1] for h in hb], where="post", color=BLEU, label="meilleur coût")
        a1.set_title(f"{titre}\n{info['rechauffages']} réchauffage(s), meilleur = {hb[-1][1]:.1f}", loc="left")
        a2.plot([q[0] for q in tr], [q[2] for q in tr], color=ORANGE, linewidth=1)
        a2.set_yscale("log")
        a2.set_xlabel("Temps (s)")
    axs[0, 0].set_ylabel("f = D + c·R")
    axs[1, 0].set_ylabel("Température T")
    axs[0, 0].legend(frameon=False)
    fig.suptitle("N50 — dynamique d'une exécution de 20 s", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig("resultats/figures/recuit_dynamique_N50.png")
    plt.close(fig)

    # Réglage initial contre réglage retenu (mêmes graines, mêmes budgets), si le fichier existe
    if os.path.exists("resultats/mono_reglage_initial.json"):
        ini = json.load(open("resultats/mono_reglage_initial.json"))
        comp = []
        for nom in INST:
            for B in (60, 120, 180):
                a = [l["f"] for r in ini if r["instance"] == nom for l in r["lignes"] if l["budget"] == B]
                b = [l["f"] for r in data if r["instance"] == nom for l in r["lignes"] if l["budget"] == B]
                comp.append({"Instance": nom, "Budget (s)": B, "Initial moyenne": round(st.mean(a), 2),
                             "Initial meilleure": round(min(a), 2), "Retenu moyenne": round(st.mean(b), 2),
                             "Retenu meilleure": round(min(b), 2),
                             "Gain moyen (%)": round(100 * (st.mean(a) - st.mean(b)) / st.mean(a), 2)})
        pd.DataFrame(comp).to_csv("resultats/tableaux/recuit_reglage_initial_vs_retenu.csv", index=False, sep=";", decimal=",")
    return T, Dt


# ---------------------------------------------------------------- sensibilité
def sensi(best_connu):
    # best_connu : meilleur coût connu de chaque instance, pour calculer un écart en %
    if not os.path.exists("resultats/sensi_etape1.json"):
        return None
    data = json.load(open("resultats/sensi_etape1.json"))
    df = pd.DataFrame([{k: v for k, v in r.items() if k != "historique"} for r in data])
    df["ecart"] = df.apply(lambda r: 100 * (r["f"] - best_connu[r["instance"]]) / best_connu[r["instance"]], axis=1)
    agg = df.groupby(["parametre", "tau0", "alpha", "k_palier", "instance"]).agg(
        Meilleure=("f", "min"), Moyenne=("f", "mean"), Ecart_type=("f", "std"),
        Ecart_moyen_pct=("ecart", "mean"), T0=("T0", "mean"), Iterations=("iterations", "mean"),
        Rechauffes=("rechauffages", "mean"), Temps_meilleur=("temps_meilleur", "mean")).round(2).reset_index()
    agg.to_csv("resultats/tableaux/recuit_sensibilite.csv", index=False, sep=";", decimal=",")

    # une courbe par paramètre (les deux autres restent au réglage initial)
    base = df[df.parametre == "base"]
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    couleurs = dict(zip(["N20", "N50", "N100", "N200"], [BLEU, ORANGE, AQUA, JAUNE]))
    for ax, (p, lib) in zip(axs, [("tau0", "τ0 (taux d'acceptation initial → T0)"),
                                  ("alpha", "α (coefficient de refroidissement)"),
                                  ("k_palier", "k (longueur du palier = k × n)")]):
        sous = pd.concat([base, df[df.parametre == p]])
        for nom, coul in couleurs.items():
            g = sous[sous.instance == nom].groupby(p)["ecart"].agg(["mean", "std"]).reset_index()
            ax.errorbar(g[p], g["mean"], yerr=g["std"], color=coul, marker="o", markersize=5, capsize=3,
                        linewidth=1.6, label=nom)
        ax.set_xlabel(lib)
        if p == "k_palier":
            ax.set_xscale("log")
            ax.set_xticks([1, 5, 20])
            ax.set_xticklabels(["1", "5", "20"])
    axs[0].set_ylabel("Écart moyen au meilleur connu (%)")
    axs[0].legend(frameon=False, title="Instance")
    fig.suptitle("Sensibilité du recuit, étape 1 (30 s, 5 graines ; un paramètre varie, les autres au réglage initial τ0=0,5 α=0,95 k=5)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig("resultats/figures/recuit_sensibilite.png")
    plt.close(fig)

    # étape 2 : les combinaisons de paramètres (60 s)
    if os.path.exists("resultats/sensi_etape2.json"):
        d2 = pd.DataFrame([{k: v for k, v in r.items() if k != "historique"} for r in json.load(open("resultats/sensi_etape2.json"))])
        d2.groupby(["instance", "parametre"]).agg(Meilleure=("f", "min"), Moyenne=("f", "mean"), Ecart_type=("f", "std"),
                                               Rechauffes=("rechauffages", "mean"), Temps_meilleur=("temps_meilleur", "mean")
                                               ).round(2).reset_index().to_csv(
            "resultats/tableaux/recuit_sensibilite_etape2.csv", index=False, sep=";", decimal=",")
    return agg


# ---------------------------------------------------------------- epsilon-contrainte
def eps(mono_best_pts):
    # mono_best_pts : meilleur point (D, R) du recuit mono-objectif, affiché sur les fronts
    if not os.path.exists("resultats/eps.json"):
        return None
    data = json.load(open("resultats/eps.json"))
    lignes, par_eps = [], []
    # front exact de N0 (calculé par exact_N0.py), pour comparer
    exact = json.load(open("resultats/N0_exact.json")) if os.path.exists("resultats/N0_exact.json") else None
    fig, axs = plt.subplots(3, 3, figsize=(11, 9))
    fronts_union = {}
    for ax, nom in zip(axs.flat, INST):
        runs = sorted([r for r in data if r["instance"] == nom], key=lambda r: r["graine"])
        n = REF[nom]["n"]
        # point de référence de l'hypervolume : un peu moins bon que tous les points
        # (10 % de marge sur la distance de S0, et n + 1 reports)
        ref = (REF[nom]["D0"] * 1.1 + 1, n + 1)
        hvs = [hypervolume_2d([(p["D"], p["R"]) for p in r["front"]], ref) for r in runs]
        # union des fronts des 5 graines
        union = filtrer_non_domines([(p["D"], p["R"], None) for r in runs for p in r["front"]])
        fronts_union[nom] = [(p[0], p[1]) for p in union]
        lignes.append({"Instance": nom, "Nb ε": len(runs[0]["bruts"]),
                       "Temps par exécution (s)": round(st.mean(r["temps_total"] for r in runs), 1),
                       "Taille front (moy.)": round(st.mean(len(r["front"]) for r in runs), 1),
                       "Taille front union": len(union),
                       "Hypervolume moyen": round(st.mean(hvs), 1), "Hypervolume écart-type": round(sd(hvs), 1),
                       "Hypervolume union": round(hypervolume_2d(fronts_union[nom], ref), 1),
                       "Point de référence (D, R)": f"({ref[0]:.1f}, {ref[1]})"})

        # détail pour chaque valeur de epsilon
        for k in range(len(runs[0]["bruts"])):
            bs = [r["bruts"][k] for r in runs]
            ok = [b for b in bs if b["respecte"]]
            par_eps.append({"Instance": nom, "ε": bs[0]["epsilon"], "Exécutions respectant ε": f"{len(ok)}/5",
                            "D meilleure": round(min(b["D"] for b in ok), 2) if ok else None,
                            "D moyenne": round(st.mean(b["D"] for b in ok), 2) if ok else None,
                            "D écart-type": round(sd([b["D"] for b in ok]), 2) if ok else None,
                            "R obtenu (min–max)": f"{min(b['R'] for b in bs)}–{max(b['R'] for b in bs)}",
                            "Temps (s)": round(st.mean(b["temps"] for b in bs), 1)})

        # graphique du front
        if nom == "N0" and exact:
            ex = sorted((float(D), int(R)) for R, D in exact["front"].items())
            ax.scatter([p[1] for p in ex], [p[0] for p in ex], s=110, facecolors="none", edgecolors=ENCRE2,
                       linewidths=1.2, label="front exact", zorder=2)
        pts = sorted(fronts_union[nom], key=lambda p: p[1])
        ax.plot([p[1] for p in pts], [p[0] for p in pts], color=BLEU, marker="o", markersize=5,
                linewidth=1.2, label="ε-contrainte (union 5 graines)", zorder=3)
        if nom in mono_best_pts:
            D, R = mono_best_pts[nom]
            ax.scatter([R], [D], marker="D", s=50, color=ORANGE, edgecolors="white", linewidths=1.5,
                       label="recuit mono-objectif (meilleur)", zorder=4)
        ax.scatter([REF[nom]["R0"]], [REF[nom]["D0"]], marker="s", s=40, color=GRIS, edgecolors="white",
                   label="heuristique S0", zorder=4)
        ax.set_title(nom, loc="left")
    for ax in axs[-1]:
        ax.set_xlabel("R : nombre de reports")
    for ax in axs[:, 0]:
        ax.set_ylabel("D : distance (km)")
    h, l = axs.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False)
    fig.suptitle("Méthode ε-contrainte (min D s.c. R ≤ ε) — fronts non dominés obtenus",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig("resultats/figures/epsilon_fronts.png")
    plt.close(fig)
    T = pd.DataFrame(lignes)
    P = pd.DataFrame(par_eps)
    T.to_csv("resultats/tableaux/epsilon_synthese.csv", index=False, sep=";", decimal=",")
    P.to_csv("resultats/tableaux/epsilon_par_valeur.csv", index=False, sep=";", decimal=",")
    # ce fichier sert aussi à la comparaison avec la PLS
    json.dump(fronts_union, open("resultats/tableaux/epsilon_fronts_union.json", "w"), indent=1)
    return T, P


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    m = mono()
    best_connu, best_pts = {}, {}
    if m:
        data = json.load(open("resultats/mono.json"))
        # meilleure solution connue de chaque instance (sert à la sensibilité et aux fronts)
        for nom in INST:
            r = min((r for r in data if r["instance"] == nom), key=lambda r: r["f"])
            best_connu[nom], best_pts[nom] = r["f"], (r["D"], r["R"])
        print(m[0].to_string(index=False))
    if os.path.exists("resultats/sensi_etape1.json"):
        sd_ = json.load(open("resultats/sensi_etape1.json"))
        if os.path.exists("resultats/sensi_etape2.json"):
            sd_ += json.load(open("resultats/sensi_etape2.json"))
        # on complète le meilleur connu avec les essais de sensibilité
        for nom in set(r["instance"] for r in sd_):
            best_connu[nom] = min([best_connu.get(nom, 1e18)] + [r["f"] for r in sd_ if r["instance"] == nom])
        print(sensi(best_connu).to_string(index=False))
    e = eps(best_pts)
    if e:
        print(e[0].to_string(index=False))