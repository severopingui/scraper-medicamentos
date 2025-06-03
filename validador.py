import sqlite3

DB_PATH = "db/medicamentos.db"

def validar_registros():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM medicamentos")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM medicamentos WHERE categoria_fda IS NULL OR categoria_fda = ''")
    sin_categoria = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM medicamentos WHERE notas IS NULL OR TRIM(notas) = ''")
    sin_notas = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM medicamentos WHERE trimestre_1 = 0 AND trimestre_2 = 0 AND trimestre_3 = 0")
    sin_trimestres = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM medicamentos WHERE observaciones IS NOT NULL AND TRIM(observaciones) != ''")
    con_observaciones = cursor.fetchone()[0]

    print("📊 Validación de medicamentos.db")
    print(f"🔹 Total de registros: {total}")
    print(f"❌ Sin categoría FDA: {sin_categoria}")
    print(f"❌ Sin notas clínicas: {sin_notas}")
    print(f"❌ Sin información de trimestres: {sin_trimestres}")
    print(f"⚠️  Con observaciones marcadas: {con_observaciones}")

    conn.close()

if __name__ == "__main__":
    validar_registros()
