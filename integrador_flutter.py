# medicamentos_scraper/integrador_flutter.py
from fda_orange_book_scraper import FDAOrangeBookScraper
from webmd_scraper import WebMDScraper
from elactancia_scraper import ELactanciaScraperAvanzado
import sqlite3

class IntegradorMedicamentos:
    def __init__(self):
        self.fda_scraper = FDAOrangeBookScraper()
        self.webmd_scraper = WebMDScraper()
        self.elactancia_scraper = ELactanciaScraperAvanzado()
    
    def buscar_medicamento_completo(self, nombre):
        """Busca en todas las fuentes y consolida información"""
        resultados = {
            'nombre': nombre,
            'fda_info': None,
            'webmd_info': None,
            'elactancia_info': None,
            'consolidado': {}
        }
        
        print(f"🔍 Buscando {nombre} en múltiples fuentes...")
        
        # FDA Orange Book
        try:
            resultados['fda_info'] = self.fda_scraper.buscar_medicamento_fda(nombre)
            time.sleep(2)  # Rate limiting
        except Exception as e:
            print(f"Error FDA: {e}")
        
        # WebMD
        try:
            resultados['webmd_info'] = self.webmd_scraper.buscar_medicamento_webmd(nombre)
            time.sleep(2)
        except Exception as e:
            print(f"Error WebMD: {e}")
        
        # e-lactancia
        try:
            resultados['elactancia_info'] = self.elactancia_scraper.buscar_medicamento(nombre)
            time.sleep(2)
        except Exception as e:
            print(f"Error e-lactancia: {e}")
        
        # Consolidar información
        resultados['consolidado'] = self._consolidar_informacion(resultados)
        
        return resultados
    
    def _consolidar_informacion(self, resultados):
        """Consolida información de múltiples fuentes"""
        consolidado = {
            'nombre': resultados['nombre'],
            'categoria_fda': '',
            'notas_embarazo': '',
            'notas_lactancia': '',
            'fuentes': [],
            'confiabilidad': 0
        }
        
        # Priorizar FDA para categorías oficiales
        if resultados['fda_info']:
            consolidado['categoria_fda'] = resultados['fda_info'].get('categoria_fda', '')
            consolidado['fuentes'].append('FDA Orange Book')
            consolidado['confiabilidad'] += 3
        
        # WebMD para información clínica
        if resultados['webmd_info']:
            consolidado['notas_embarazo'] = resultados['webmd_info'].get('precauciones_embarazo', '')
            consolidado['fuentes'].append('WebMD')
            consolidado['confiabilidad'] += 2
        
        # e-lactancia para lactancia
        if resultados['elactancia_info']:
            consolidado['notas_lactancia'] = resultados['elactancia_info'].get('notas_lactancia', '')
            consolidado['fuentes'].append('e-lactancia.org')
            consolidado['confiabilidad'] += 2
        
        return consolidado
    
    def actualizar_db_flutter(self, medicamento_consolidado):
        """Actualiza la base de datos de Flutter"""
        conn = sqlite3.connect('db/medicamentos.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO medicamentos 
            (nombre, categoria_fda, notas_clinicas, fuente, trimestre_1, trimestre_2, trimestre_3)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            medicamento_consolidado['nombre'],
            medicamento_consolidado['categoria_fda'],
            f"{medicamento_consolidado['notas_embarazo']}\n\nLactancia: {medicamento_consolidado['notas_lactancia']}",
            ', '.join(medicamento_consolidado['fuentes']),
            1 if medicamento_consolidado['categoria_fda'] in ['A', 'B'] else 0,
            1 if medicamento_consolidado['categoria_fda'] in ['A', 'B'] else 0,
            1 if medicamento_consolidado['categoria_fda'] in ['A', 'B'] else 0
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ {medicamento_consolidado['nombre']} actualizado en Flutter DB")
