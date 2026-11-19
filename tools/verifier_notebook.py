"""Exécute le notebook dans une copie temporaire, sans toucher au dépôt."""
from pathlib import Path
import shutil
import tempfile
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory(prefix="nexovia-notebook-") as dossier:
        copie = Path(dossier) / "projet"
        shutil.copytree(ROOT, copie, ignore=shutil.ignore_patterns(
            ".git", ".venv", "__pycache__", ".ipynb_checkpoints", ".matplotlib",
            "nouveaux_*", "analyses", "analyses_regenerees"))
        nb = nbformat.read(copie / "Nexovia.ipynb", as_version=4)
        NotebookClient(nb, timeout=180, kernel_name="python3",
                       resources={"metadata": {"path": str(copie)}}).execute()
        print("Notebook : toutes les cellules exécutées ; campagnes longues désactivées.")

if __name__ == "__main__":
    main()
