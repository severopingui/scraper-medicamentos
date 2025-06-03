# medicamentos_scraper/main_scraper.py
from integrador_flutter import IntegradorMedicamentos

def main():
    integrador = IntegradorMedicamentos()
    
    # Lista de medicamentos comunes en obstetricia
    medicamentos = [
        'Acetaminophen', 'Ibuprofen', 'Aspirin', 'Metformin',
        'Insulin', 'Folic Acid', 'Iron', 'Prenatal Vitamins'
    ]
    
    for medicamento in medicamentos:
        print(f"\n{'='*50}")
        print(f"Procesando: {medicamento}")
        print('='*50)
        
        resultado = integrador.buscar_medicamento_completo(medicamento)
        
        if resultado['consolidado']['confiabilidad'] > 2:
            integrador.actualizar_db_flutter(resultado['consolidado'])
        else:
            print(f"⚠️ Información insuficiente para {medicamento}")
        
        time.sleep(5)  # Rate limiting entre medicamentos

if __name__ == "__main__":
    main()
