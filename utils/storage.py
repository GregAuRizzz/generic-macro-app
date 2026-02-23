"""
Local JSON storage for macros.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import List

from models.macro import Macro

# Détermine le dossier racine du projet (compatible avec le futur .exe)
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Dossier des macros situé directement dans le projet
MACROS_DIR = PROJECT_ROOT / "macros"

def ensure_dir():
    """Crée le dossier macros s'il n'existe pas."""
    MACROS_DIR.mkdir(parents=True, exist_ok=True)

def save_macro(macro: Macro, path=None) -> Path:
    """Sauvegarde une macro au format JSON."""
    ensure_dir()
    if path is None:
        # Crée un nom de fichier propre à partir du nom de la macro
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in macro.name)
        if not safe.strip():
            safe = "Unnamed_Macro"
        path = MACROS_DIR / f"{safe}.json"
    
    path = Path(path)
    path.write_text(macro.to_json(), encoding="utf-8")
    return path

def load_macro(path) -> Macro:
    """Charge une macro depuis un fichier JSON."""
    return Macro.from_json(Path(path).read_text(encoding="utf-8"))

def list_macros() -> List[Path]:
    """Liste tous les fichiers de macros disponibles."""
    ensure_dir()
    return sorted(MACROS_DIR.glob("*.json"))

def delete_macro(path):
    """Supprime un fichier de macro."""
    Path(path).unlink(missing_ok=True)