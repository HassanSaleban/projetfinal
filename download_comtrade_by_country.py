#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Télécharge 1 CSV par pays depuis l'API UN Comtrade (dataset HS),
toutes années (ps=all), flux = tous (rg=all), partenaire = Monde (p=0).
Par défaut cc=85, mais tu peux passer un autre code HS en argument.

Exemples:
    python download_comtrade_by_country.py              # HS 85
    python download_comtrade_by_country.py --hs 840     # HS 840
    python download_comtrade_by_country.py --hs TOTAL   # total tous produits
"""

import argparse
import os
import time
import csv
import io
import sys
import textwrap
from typing import Dict, List, Tuple
import requests

# API endpoints (stables côté Comtrade "classic")
REPORTERS_URL = "https://comtrade.un.org/Data/cache/reporterAreas.json"
COMTRADE_GET_URL = (
    "https://comtrade.un.org/api/get"
    "?type=C&freq=A&px=HS&ps=all&rg=all&p=0&r={reporter}&cc={cc}&fmt=csv"
)
# NB: p=0 (World). Tu peux mettre p=all pour tous partenaires, mais les fichiers seront massifs.


def get_reporters() -> List[Tuple[int, str]]:
    """Retourne la liste (id, nom) des reporters (pays) disponibles."""
    resp = requests.get(REPORTERS_URL, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("results", [])
    reporters: List[Tuple[int, str]] = []
    for it in items:
        try:
            _id = int(it["id"])
        except (KeyError, ValueError):
            continue
        name = it.get("text", "").strip()
        # Filtrage: ignorer id <= 0 et entrées "All" / "World" / agrégats
        if _id > 0 and name and "all" not in name.lower():
            reporters.append((_id, name))
    # Tri par nom pour une progression déterministe
    reporters.sort(key=lambda x: x[1])
    return reporters


def sanitize_filename(s: str) -> str:
    """Nettoie un nom pour le système de fichiers."""
    bad = '<>:"/\\|?*'
    for ch in bad:
        s = s.replace(ch, "_")
    return "_".join(s.split())


def save_csv(content: str, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)


def download_country_csv(reporter_id: int, reporter_name: str, hs_code: str, out_dir: str) -> bool:
    """Télécharge le CSV pour un pays (True si un fichier a été écrit)."""
    url = COMTRADE_GET_URL.format(reporter=reporter_id, cc=hs_code)
    r = requests.get(url, timeout=120)
    # L’API peut renvoyer 204 quand il n’y a pas de données
    if r.status_code == 204 or not r.text.strip():
        return False

    # Parfois, Comtrade renvoie du texte "No data" en CSV vide.
    text = r.text
    # S'assurer qu'il y a un entête CSV plausible
    if "Classification" not in text.splitlines()[0]:
        # On tente une détection simple "no data"
        if "No data" in text or "Error Message" in text:
            return False

    filename = f"comtrade_HS{hs_code}_{reporter_id}_{sanitize_filename(reporter_name)}.csv"
    path = os.path.join(out_dir, filename)
    save_csv(text, path)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Télécharge 1 CSV Comtrade par pays pour toutes années (HS).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Paramètres utilisés:
              - freq=A (annuel)
              - rg=all (Import + Export + Re-export etc.)
              - p=0 (partenaire = Monde). Mets --partners all si tu veux tous les partenaires (fichiers très gros).
              - ps=all (toutes années disponibles)
            """
        ),
    )
    parser.add_argument("--hs", dest="hs_code", default="85", help="Code HS/cc (ex: 85, 840, TOTAL). Défaut: 85")
    parser.add_argument("--out", dest="out_dir", default="data_comtrade", help="Répertoire de sortie (défaut: data_comtrade)")
    parser.add_argument("--sleep", dest="sleep_sec", type=float, default=1.2,
                        help="Pause entre requêtes pour respecter le rate limit (défaut: 1.2s)")
    parser.add_argument("--max", dest="max_countries", type=int, default=None,
                        help="Limiter le nombre de pays (pour tests)")

    args = parser.parse_args()

    print("Récupération de la liste des pays (reporters) depuis Comtrade…")
    reporters = get_reporters()
    if not reporters:
        print("Aucun reporter trouvé. Arrêt.", file=sys.stderr)
        sys.exit(1)

    if args.max_countries:
        reporters = reporters[: args.max_countries]

    print(f"{len(reporters)} pays à télécharger | HS={args.hs_code} | dossier={args.out_dir}")
    ok, ko = 0, 0
    for idx, (rid, rname) in enumerate(reporters, start=1):
        try:
            wrote = download_country_csv(rid, rname, args.hs_code, args.out_dir)
            if wrote:
                ok += 1
                print(f"[{idx}/{len(reporters)}] ✓ {rname}")
            else:
                ko += 1
                print(f"[{idx}/{len(reporters)}] – {rname} (pas de données)")
        except requests.HTTPError as e:
            ko += 1
            print(f"[{idx}/{len(reporters)}] ✗ {rname} (HTTP {e.response.status_code})")
        except Exception as e:
            ko += 1
            print(f"[{idx}/{len(reporters)}] ✗ {rname} (erreur: {e})")
        time.sleep(args.sleep_sec)  # respecter le rate limit de l’API

    print(f"Terminé. Fichiers OK: {ok} | Sans données/erreurs: {ko}")


if __name__ == "__main__":
    main()
