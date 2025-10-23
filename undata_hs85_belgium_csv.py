#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import argparse
import re
from playwright.sync_api import sync_playwright

def download_undata_csv(out_csv: Path, headless: bool = True,
                        start_year: int = 2010, end_year: int = 2024):
    out_csv = out_csv.resolve()
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()

        # 1) Explorer
        page.goto("https://data.un.org/Explorer.aspx", wait_until="domcontentloaded")

        # 2) Ouvrir le dataset puis HS 85 -> View data
        page.get_by_text("Commodity Trade Statistics Database", exact=True).click()
        page.get_by_text("Trade of goods, US$, HS, 85", exact=False).scroll_into_view_if_needed()
        page.get_by_role("link", name="View data").nth(0).click()
        page.wait_for_load_state("networkidle")

        # 3) Nettoyer filtres si présent
        try:
            page.get_by_text("Remove All").click(timeout=1500)
            page.wait_for_load_state("networkidle")
        except:
            pass

        # 4) Choisir le pays = Belgium (et pas Belgium-Luxembourg)
        #    a) préférer une regex ancrée
        try:
            page.get_by_role("checkbox", name=re.compile(r"^Belgium$")).check(timeout=3000)
        except:
            #    b) fallback: cocher via l'id (rtCode=56 -> id 'rtCode%3a56')
            page.locator('input[id="rtCode%3a56"]').check()

        # 5) Coche les années 2010–2024
        for y in range(start_year, end_year + 1):
            try:
                page.get_by_role("checkbox", name=re.compile(fr"^{y}$")).check()
            except:
                # certaines années sont peut-être déjà cochées ou virtuelles
                pass

        # 6) Download CSV
        with page.expect_download() as dl_info:
            page.get_by_role("link", name="Download").click()
            try:
                page.get_by_label("CSV").check(timeout=1500)
            except:
                pass
            page.get_by_role("button", name="Download").click()
        dl = dl_info.value
        dl.save_as(str(out_csv))

        ctx.close()
        browser.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="undata_be_hs85_2010_2024.csv")
    ap.add_argument("--headful", action="store_true", help="voir le navigateur")
    ap.add_argument("--start", type=int, default=2010)
    ap.add_argument("--end", type=int, default=2024)
    args = ap.parse_args()

    download_undata_csv(
        out_csv=Path(args.out),
        headless=not args.headful,
        start_year=args.start,
        end_year=args.end,
    )
    print(f"✅ CSV UNdata sauvegardé → {args.out}")

if __name__ == "__main__":
    main()
