import requests
import sqlite3
from bs4 import BeautifulSoup
from tqdm import tqdm
import time
from datetime import datetime

BASE_URL = "https://www.drugs.com"
INDEX_URL = "https://www.drugs.com/pregnancy.html"
DB_PATH = "db/medicamentos.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            categoria_fda TEXT,
            notas TEXT,
            fuente TEXT,
            trimestre_1 INTEGER,
            trimestre_2 INTEGER,
            trimestre_3 INTEGER,
            ultima_fuente_actualizada TEXT,
            observaciones TEXT
        )
    """)
    conn.commit()
    return conn

def extract_links():
    response = requests.get(INDEX_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    letter_links = soup.select(".ddc-paging li a")
    all_links = [BASE_URL + link["href"] for link in letter_links]
    return all_links

def parse_medications(letter_url):
    response = requests.get(letter_url)
    soup = BeautifulSoup(response.text, "html.parser")
    meds = soup.select("ul.column-list li a")
    return [BASE_URL + med["href"] for med in meds]

def parse_medication_detail(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    try:
        title = soup.select_one("h1").text.strip()
        category = ""
        notes = soup.select_one("div.contentBox p").text.strip()
        fda_info = soup.find("strong", string=lambda s: s and "FDA pregnancy category" in s)
        fuente = "drugs.com"

        if fda_info and fda_info.next_sibling:
            category = fda_info.next_sibling.strip().split()[0]
            if "Briggs" in fda_info.next_sibling:
                fuente = "drugs.com / Briggs"
            elif "FDA" in fda_info.next_sibling:
                fuente = "drugs.com / FDA"

        notas = notes.replace("\n", " ").strip()
        lower_notes = notes.lower()
        tr1 = int("first trimester" in lower_notes)
        tr2 = int("second trimester" in lower_notes)
        tr3 = int("third trimester" in lower_notes)

        observaciones = ""
        if not category:
            observaciones += "⚠️ Sin categoría FDA detectada. "
        if not notas:
            observaciones += "⚠️ Sin notas clínicas. "

        return (
            title,
            category or None,
            notas or None,
            fuente,
            tr1,
            tr2,
            tr3,
            datetime.now().isoformat(),
            observaciones.strip() or None
        )
    except Exception:
        return None

def save_to_db(conn, datos):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO medicamentos (
            nombre, categoria_fda, notas, fuente, trimestre_1, trimestre_2, trimestre_3, 
            ultima_fuente_actualizada, observaciones
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(nombre) DO UPDATE SET
            categoria_fda=excluded.categoria_fda,
            notas=excluded.notas,
            fuente=excluded.fuente,
            trimestre_1=excluded.trimestre_1,
            trimestre_2=excluded.trimestre_2,
            trimestre_3=excluded.trimestre_3,
            ultima_fuente_actualizada=excluded.ultima_fuente_actualizada,
            observaciones=excluded.observaciones
    """, datos)
    conn.commit()

def main():
    conn = init_db()
    links = extract_links()
    for letter_url in tqdm(links, desc="Letras"):
        med_links = parse_medications(letter_url)
        for med_url in tqdm(med_links, desc="Medicamentos", leave=False):
            datos = parse_medication_detail(med_url)
            if datos:
                save_to_db(conn, datos)
            time.sleep(0.3)

    conn.close()
    print("✅ Drugs.com scraping completado.")

if __name__ == "__main__":
    main()
