# undata_comtrade_selenium.py
# ------------------------------------------------------------
# Simule un utilisateur UNdata (Comtrade) avec Firefox/Selenium
# - Sélectionne un pays dans "Country or Area"
# - Coche les années demandées (ou toutes si YEARS=None)
# - Ouvre "Select columns" et choisit les colonnes souhaitées
# - Télécharge le CSV (Download → CSV) dans DOWNLOAD_DIR
# ------------------------------------------------------------

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

import os
import time

# ------------- CONFIG -----------------
START_URL = "https://data.un.org/Data.aspx?d=ComTrade&f=_l1Code%3a85"  # HS=85
DOWNLOAD_DIR = os.path.abspath("downloads_csv")  # dossier de téléchargement
COUNTRY = "Greece"                               # pays à sélectionner
YEARS = ["2024", "2023", "2022"]                 # None => toutes les années visibles
COLUMNS = [                                      # colonnes souhaitées
    "Country or Area",
    "Year",
    "Comm. Code",
    "Commodity",
    "Flow Code",
    "Flow",
    "Trade (USD)",
    "Weight (kg)",
    "Quantity Name",
    "Quantity",
]
WAIT_S = 25                   # timeout d’attente explicite
SLEEP_BETWEEN_STEPS = 0.6     # micro-pauses pour stabilité
# --------------------------------------


# ---------- Utils Selenium ----------
def make_firefox(download_dir: str) -> webdriver.Firefox:
    """Instancie Firefox et configure le téléchargement CSV sans popup."""
    os.makedirs(download_dir, exist_ok=True)

    options = webdriver.FirefoxOptions()
    # Téléchargement auto des CSV
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", download_dir)
    options.set_preference(
        "browser.helperApps.neverAsk.saveToDisk",
        "text/csv,application/vnd.ms-excel,application/csv,application/octet-stream",
    )
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("pdfjs.disabled", True)
    options.set_preference("network.proxy.type", 5)  # utiliser le proxy système

    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    driver.maximize_window()
    driver.implicitly_wait(2)
    return driver


def wait(driver: webdriver.Firefox) -> WebDriverWait:
    return WebDriverWait(driver, WAIT_S)


def scroll_into_view(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    time.sleep(0.2)


def safe_click(driver, element):
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def dismiss_possible_cookie(driver):
    """Tente de fermer une éventuelle bannière cookies (si présente)."""
    texts = ["Accept", "I agree", "J'accepte", "OK", "Ok", "Got it"]
    for t in texts:
        try:
            btn = driver.find_element(By.XPATH, f"//button[normalize-space()='{t}'] | //a[normalize-space()='{t}']")
            scroll_into_view(driver, btn)
            safe_click(driver, btn)
            time.sleep(0.4)
            break
        except Exception:
            pass


def click_label_by_text_anywhere(driver, text: str):
    """Coche un label portant ce texte, où qu'il soit (panneau gauche)."""
    w = wait(driver)
    lbl = w.until(EC.presence_of_element_located((By.XPATH, f"(//label[normalize-space()='{text}'])[1]")))
    scroll_into_view(driver, lbl)
    safe_click(driver, lbl)
    time.sleep(SLEEP_BETWEEN_STEPS)


def uncheck_all_via_remove_all(driver):
    try:
        link = driver.find_element(By.XPATH, "//a[normalize-space()='Remove All']")
        scroll_into_view(driver, link)
        safe_click(driver, link)
        time.sleep(1.0)
    except Exception:
        pass


def open_select_columns(driver):
    w = wait(driver)
    # Plusieurs variantes existent sur le site
    for xp in [
        "//a[normalize-space()='Select columns']",
        "//a[contains(@onclick,'ShowInlinePopup') and contains(.,'Select columns')]",
    ]:
        try:
            btn = w.until(EC.element_to_be_clickable((By.XPATH, xp)))
            scroll_into_view(driver, btn)
            safe_click(driver, btn)
            time.sleep(0.8)
            return
        except Exception:
            continue
    raise RuntimeError("Bouton 'Select columns' introuvable.")


def set_columns_in_popup(driver, columns):
    w = wait(driver)
    # Popup affiché inline (display:block)
    popup = w.until(EC.presence_of_element_located(
        (By.XPATH, "//div[contains(@style,'display') and contains(@style,'block')][.//label]")
    ))

    # Select none (si présent)
    for none_x in [".//a[normalize-space()='Select none']", ".//a[normalize-space()='None']",
                   ".//button[normalize-space()='Select none']"]:
        try:
            select_none = popup.find_element(By.XPATH, none_x)
            scroll_into_view(driver, select_none)
            safe_click(driver, select_none)
            time.sleep(0.4)
            break
        except Exception:
            pass

    # Coche les colonnes demandées
    for col in columns:
        try:
            lbl = popup.find_element(By.XPATH, f".//label[normalize-space()='{col}']")
            scroll_into_view(driver, lbl)
            cb_id = lbl.get_attribute("for")
            cb = popup.find_element(By.ID, cb_id) if cb_id else None
            if cb is None:
                try:
                    cb = lbl.find_element(By.XPATH, "preceding-sibling::input[1]")
                except Exception:
                    cb = lbl.find_element(By.XPATH, "following-sibling::input[1]")
            if not cb.is_selected():
                safe_click(driver, lbl)
                time.sleep(0.15)
        except Exception:
            print(f"  - colonne absente: {col}")

    # Appliquer/OK
    for ok_text in ["Apply", "OK", "Ok", "Valider"]:
        try:
            ok_btn = popup.find_element(By.XPATH, f".//button[normalize-space()='{ok_text}'] | .//a[normalize-space()='{ok_text}']")
            scroll_into_view(driver, ok_btn)
            safe_click(driver, ok_btn)
            time.sleep(0.8)
            return
        except Exception:
            continue
    # fallback: ESC
    try:
        driver.switch_to.active_element.send_keys("\uE00C")
    except Exception:
        pass
    time.sleep(0.5)


def click_download_csv(driver):
    w = wait(driver)
    dl = w.until(EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Download']")))
    scroll_into_view(driver, dl)
    safe_click(driver, dl)
    time.sleep(0.5)
    # Sous-menu CSV si présent
    try:
        csv_link = w.until(EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='CSV' or contains(.,'CSV')]")))
        safe_click(driver, csv_link)
    except Exception:
        pass
    time.sleep(2.0)


def newest_file_in(folder: str):
    files = [os.path.join(folder, f) for f in os.listdir(folder)] if os.path.exists(folder) else []
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def wait_for_new_download(before_ts: float, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        f = newest_file_in(DOWNLOAD_DIR)
        if f and os.path.getmtime(f) >= before_ts and not f.endswith(".part"):
            part = f + ".part"
            if os.path.exists(part):
                time.sleep(0.5); continue
            return f
        time.sleep(0.5)
    return None
# ------------------------------------


def main():
    print("[1/8] Démarrage Firefox…")
    driver = make_firefox(DOWNLOAD_DIR)
    try:
        print("[2/8] Navigation :", START_URL)
        driver.get(START_URL)
        print("    Title:", driver.title or "(vide)")
        dismiss_possible_cookie(driver)

        # Barre d'actions avec Download / Select columns
        print("[3/8] Attente de la barre d’actions…")
        wait(driver).until(EC.presence_of_element_located(
            (By.XPATH, "//a[normalize-space()='Download'] | //a[normalize-space()='Select columns']")
        ))

        # Reset filtres
        print("[4/8] Reset filtres (Remove All)…")
        uncheck_all_via_remove_all(driver)

        # Pays
        print(f"[5/8] Sélection du pays: {COUNTRY}")
        click_label_by_text_anywhere(driver, COUNTRY)

        # Années
        if YEARS is None:
            print("[6/8] Sélection de toutes les années visibles…")
            labels = driver.find_elements(By.XPATH, "//div[.//div[normalize-space()='Year']]//label")
            for lbl in labels:
                try:
                    cb_id = lbl.get_attribute("for")
                    cb = driver.find_element(By.ID, cb_id) if cb_id else lbl.find_element(By.XPATH, "preceding-sibling::input[1]")
                    if not cb.is_selected():
                        scroll_into_view(driver, lbl)
                        safe_click(driver, lbl)
                        time.sleep(0.05)
                except Exception:
                    pass
        else:
            print(f"[6/8] Sélection des années: {YEARS}")
            for y in YEARS:
                click_label_by_text_anywhere(driver, str(y))

        # Colonnes
        print("[7/8] Select columns…")
        open_select_columns(driver)
        set_columns_in_popup(driver, COLUMNS)

        # Download
        print("[8/8] Download CSV…")
        before = time.time()
        click_download_csv(driver)
        print("   ⏳ Attente du fichier dans :", DOWNLOAD_DIR)
        fpath = wait_for_new_download(before_ts=before, timeout=120)
        if fpath:
            print("   ✅ Téléchargé :", os.path.basename(fpath))
            pretty = f"undata_HS85_{COUNTRY.replace(' ','_')}.csv"
            dest = os.path.join(DOWNLOAD_DIR, pretty)
            try:
                os.replace(fpath, dest)
                print("   📦 Fichier renommé →", dest)
            except Exception:
                pass
        else:
            print("   ⚠️ Aucun nouveau fichier détecté. (Antivirus/proxy ?)")
        time.sleep(1.0)

    finally:
        time.sleep(1.0)
        driver.quit()


if __name__ == "__main__":
    main()
