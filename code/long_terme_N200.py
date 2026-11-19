"""Lance uniquement le génétique FINAL ORIGINAL sur N200 jusqu'à 400 s."""
# Apport 1 seul (depuis le dossier du notebook) : python code/long_terme_N200.py
# 5 graines, budget de 400 s.

import argparse, json, hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from experiences import ROOT, essai


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--graines', type=int, nargs='+', default=[1, 2, 3, 4, 5])
    p.add_argument('--processus', type=int, default=4)
    p.add_argument('--sortie', default='nouveaux_essais_N200')
    a = p.parse_args()
    if a.processus < 1:
        p.error('--processus doit être positif')
    out = ROOT / a.sortie
    folder = out / 'long_terme_N200'
    if list(folder.glob('*.json')):
        raise RuntimeError('Choisir un nouveau dossier --sortie')
    out.mkdir(parents=True, exist_ok=True)
    # on garde une trace du protocole et des empreintes du code utilisé
    meta = {'experience': 'AG original N200, budget 400 s', 'graines': a.graines, 'processus': a.processus, 'empreintes': {str(q.relative_to(ROOT)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (ROOT / 'code').glob('*.py')}}
    (out / 'protocole.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    with ProcessPoolExecutor(max_workers=a.processus) as pool:
        fs = [pool.submit(essai, ('long_terme', 'AG_original', g, 400, None, None, str(folder))) for g in a.graines]
        for f in as_completed(fs):
            print(f.result(), flush=True)


if __name__ == '__main__':
    main()