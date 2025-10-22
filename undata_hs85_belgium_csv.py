#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import argparse
from playwright.sync_api import sync_playwright

def download_undata_csv(out_csv: Path, headless: bool = True,
                        country_label: str = "Belgium",
                        start_year: int = 2010, end_year: int = 2024):
    out_csv = out_csv.resolve()
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()

        # 1) Ouvre l’explorateur
        page.goto("https://data.un.org/Explorer.aspx", wait_until="domcontentloaded")

        # 2) Ouvre le dataset “Commodity Trade Statistics Database”
        page.get_by_text("Commodity Trade Statistics Database", exact=True).click()

        # 3) Ligne HS 85 → "View data"
        page.get_by_text("Trade of goods, US$, HS, 85", exact=False).scroll_into_view_if_needed()
        # premier lien "View data" sur la ligne HS 85
        page.get_by_role("link", name="View data").nth(0).click()

        # 4) (optionnel) Nettoie les filtres courants s'il y a
        try:
            page.get_by_text("Remove All").click(timeout=2000)
            page.wait_for_load_state("networkidle")
        except:
            pass

        # 5) Coche le pays
        page.get_by_text("Select filters:", exact=False).scroll_into_view_if_needed()
        page.get_by_label(country_label).check()

        # 6) Coche les années 2010–2024
        for y in range(start_year, end_year + 1):
            try:
                page.get_by_label(str(y)).check()
            except:
                pass

        # 7) Clique “Download → CSV”
        with page.expect_download() as dl_info:
            page.get_by_role("link", name="Download").click()
            # Sur certaines versions, un choix CSV peut s'afficher ; on clique le bouton Download directement
            try:
                page.get_by_label("CSV").check(timeout=2000)
            except:
                pass
            page.get_by_role("button", name="Download").click()
        download = dl_info.value
        download.save_as(str(out_csv))

        ctx.close()
        browser.close()

def main():
    ap = argparse.ArgumentParser(description="Télécharge depuis UNdata (sans API) le CSV HS 85 Belgique 2010–2024.")
    ap.add_argument("--out", default="undata_be_hs85_2010_2024.csv", help="Chemin du CSV de sortie")
    ap.add_argument("--headful", action="store_true", help="Afficher la fenêtre du navigateur (débogage)")
    args = ap.parse_args()

    download_undata_csv(
        out_csv=Path(args.out),
        headless=not args.headful,
        country_label="Belgium",
        start_year=2010,
        end_year=2024,
    )
    print(f"✅ CSV sauvegardé tel quel depuis UNdata → {args.out}")

if __name__ == "__main__":
    main()
