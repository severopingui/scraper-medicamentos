# medicamentos_scraper/fda_orange_book_scraper.py
import requests
import sqlite3
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import json

class FDAOrangeBookScraper:
    def __init__(self):
        self.base_url = "https://www.accessdata.fda.gov/scripts/cder/ob"
        self.search_url = f"{self.base_url}/default.cfm"
        self.ua = UserAgent()
        self.session = requests.Session()
        
        # Headers robustos basados en tu archivo de citaciones
        self.headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    
    def buscar_medicamento_fda(self, nombre_medicamento):
        """Busca medicamento en FDA Orange Book"""
        search_params = {
            'Ingredient': nombre_medicamento,
            'DrugName': '',
            'tableType': 'OB'
        }
        
        try:
            response = self.session.get(
                self.search_url,
                params=search_params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return self._parsear_fda_response(response.text, nombre_medicamento)
            else:
                print(f"Error FDA {response.status_code} para {nombre_medicamento}")
                return None
                
        except Exception as e:
            print(f"Error buscando en FDA {nombre_medicamento}: {e}")
            return None
    
    def _parsear_fda_response(self, html, medicamento):
        """Extrae información oficial de FDA"""
        soup = BeautifulSoup(html, 'html.parser')
        
        info = {
            'nombre': medicamento,
            'categoria_fda': '',
            'numero_aplicacion': '',
            'fecha_aprobacion': '',
            'laboratorio': '',
            'fuente': 'FDA Orange Book',
            'estado_aprobacion': ''
        }
        
        # Parsear tabla de resultados FDA
        try:
            tabla = soup.find('table', {'class': 'standardTable'})
            if tabla:
                filas = tabla.find_all('tr')[1:]  # Skip header
                for fila in filas:
                    celdas = fila.find_all('td')
                    if len(celdas) >= 6:
                        info['numero_aplicacion'] = celdas[0].text.strip()
                        info['nombre'] = celdas[1].text.strip()
                        info['laboratorio'] = celdas[2].text.strip()
                        info['fecha_aprobacion'] = celdas[4].text.strip()
                        break
        except Exception as e:
            print(f"Error parseando FDA: {e}")
        
        return info
