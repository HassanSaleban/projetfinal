#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Comtrade v1 (preview) — Importations de la Belgique (reporterCode 56),
chapitre HS 85, 2010–2024, partenaire Monde (0).

- On n'envoie QUE les paramètres acceptés par preview pour éviter les 400.
- Gestion robuste des 429 (Too Many Requests) avec retry/backoff.
- Possibilité de basculer en endpoint 'get' si tu as une clé (voir call_api()).

Sortie: be_imports_hs85_2010_2024.csv
"""

import os
import time
import math
import requests
import pandas as pd
from typing import Dict, Any

# Endpoints
BASE_PREVIEW = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
BASE_GET = "https://comtradeapi.un.org/public/v1/get/C/A/HS"  # nécessite une clé

# Paramètres STRICTEMENT requis par l'endpoint preview
CORE_PARAMS = dict(
    cmdCode="85",          # Chapitre HS 85
    flowCode="M",          # M = Imports (X = Exports)
    partnerCode="0",       # 0 = Monde
    reporterCode="56"      # 56 = Belgique
)

HEADERS_JSON = {"Accept": "application/json"}

def call_api(period: int, session: requests.Session, use_get: bool = False) -> Dict[str, Any]:
    """
    Appelle preview (par défaut) ou get (si use_get=True + clé).
    Gère 429 avec backoff progressif.
    """
    params = CORE_PARAMS.copy()
    params["period"] = str(period)

    if use_get:
        # Nécessite une clé (variable d'env COMTRADE_API_KEY)
        api_key = os.getenv("COMTRADE_API_KEY")
        if not api_key:
            raise RuntimeError("Définis COMTRADE_API_KEY pour utiliser l'endpoint GET.")
        url = BASE_GET
        headers = {**HEADERS_JSON, "Ocp-Apim-Subscription-Key": api_key}
    else:
        url = BASE_PREVIEW
        headers = HEADERS_JSON

    # Retrys avec backoff
    attempts = 0
    while True:
        attempts += 1
        resp = session.get(url, params=params, headers=headers, timeout=60)
        if resp.status_code == 429:
            # Respecter Retry-After s'il est présent, sinon backoff exponentiel
            wait = resp.headers.get("Retry-After")
            wait_s = int(wait) if wait and wait.isdigit() else min(60, 1 + 2 ** (attempts - 1))
            print(f"   · 429 reçu — attente {wait_s}s puis retry…")
            time.sleep(wait_s)
            continue
        if resp.status_code >= 400:
            # 400/404/500 -> on n'insiste pas au-delà de 3 tentatives
            if attempts < 3:
                wait_s = min(15, 1 + 2 ** (attempts - 1))
                print(f"   · {resp.status_code} {resp.reason} — retry dans {wait_s}s…")
                time.sleep(wait_s)
                continue
            resp.raise_for_status()
        # OK
        return resp.json()

def normalize(payload: Dict[str, Any]) -> pd.DataFrame:
    rows = payload.get("data") or []
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)

    # colonnes usuelles
    rename = {
        "period": "year",
        "reporterDesc": "reporter",
        "partnerDesc": "partner",
        "cmdDesc": "hs_desc_en",
        "primaryValue": "trade_value_usd",
        "netWgt": "net_weight_kg"
    }
    keep = [
        "period","reporterDesc","partnerDesc","cmdCode","cmdDesc",
        "flowCode","flowDesc","primaryValue","netWgt","qty","qtyUnit",
        "reporterCode","reporterISO","partnerCode","partnerISO"
    ]
    keep = [c for c in keep if c in df.columns]
    df = df[keep].rename(columns=rename)

    for c in ["year", "trade_value_usd", "net_weight_kg", "qty"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def main():
    years = range(2010, 2025)
    frames = []
    with requests.Session() as s:
        for y in years:
            print(f"Téléchargement {y}…")
            try:
                js = call_api(y, s, use_get=False)  # passe à True si tu as COMTRADE_API_KEY
                df = normalize(js)
                if not df.empty:
                    frames.append(df)
            except Exception as e:
                print(f"⚠️  {y}: {e}")
            # petite pause “politesse” pour preview
            time.sleep(1.2)

    if not frames:
        print("Aucune donnée récupérée.")
        return

    out = pd.concat(frames, ignore_index=True)
    order = [
        "year","reporter","partner","flowDesc",
        "cmdCode","hs_desc_en","trade_value_usd",
        "net_weight_kg","qty","qtyUnit",
        "reporterCode","reporterISO","partnerCode","partnerISO","flowCode"
    ]
    out = out[[c for c in order if c in out.columns] + [c for c in out.columns if c not in order]]
    out.to_csv("be_imports_hs85_2010_2024.csv", index=False, encoding="utf-8")
    print(f"✅ Fichier écrit: be_imports_hs85_2010_2024.csv  ({len(out):,} lignes)")

if __name__ == "__main__":
    main()
