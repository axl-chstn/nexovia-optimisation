"""Lance uniquement les politiques 0/0, 10/20 et 20/40 sur N50, cinq graines, 20 s."""
# Apport 2 seul (depuis le dossier du notebook) : python code/renouvellement_N50.py
# Pour chaque graine, les trois politiques sont lancées ensemble.

import argparse, json, hashlib, multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from experiences import ROOT, essai, initialiser, POLITIQUES


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--graines', type=int, nargs='+', default=[1, 2, 3, 4, 5])
    p.add_argument('--sortie', default='nouveaux_essais_N50')
    a = p.parse_args()
    out = ROOT / a.sortie
    folder = out / 'renouvellement_N50'
    if list(folder.glob('*.json')):
        raise RuntimeError('Choisir un nouveau dossier --sortie')
    out.mkdir(parents=True, exist_ok=True)
    meta = {'experience': 'Renouvellement N50, budget 20 s', 'graines': a.graines, 'politiques': [[0, 0], [10, 20], [20, 40]], 'empreintes': {str(q.relative_to(ROOT)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (ROOT / 'code').glob('*.py')}}
    (out / 'protocole.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    # la barrière (3 places) fait démarrer les 3 politiques d'une graine ensemble
    ctx = multiprocessing.get_context('spawn')
    barrier = ctx.Barrier(3)
    with ProcessPoolExecutor(max_workers=3, mp_context=ctx, initializer=initialiser, initargs=(barrier,)) as pool:
        for g in a.graines:
            fs = [pool.submit(essai, ('renouvellement', c, g, 20, b, r, str(folder))) for c, b, r in POLITIQUES]
            for f in as_completed(fs):
                print(f.result(), flush=True)


if __name__ == '__main__':
    main()