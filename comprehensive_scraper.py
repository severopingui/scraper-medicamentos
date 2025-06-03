import asyncio
import aiohttp
import sqlite3
from dataclasses import dataclass
from typing import List, Optional
import random
import time
from bs4 import BeautifulSoup
import logging
import re
from fake_useragent import UserAgent
import os
from datetime import datetime

@dataclass
class MedicationData:
    nombre: str
    categoria_fda: Optional[str] = None
    notas_clinicas: Optional[str] = None
    trimestres_seguro: Optional[str] = None
    fuente: str = ""
    observaciones: Optional[str] = None
    confianza_score: int = 0
    fecha_actualizacion: str = ""

class ComprehensiveMedScraper:
    def __init__(self, db_path: str = "db/medicamentos.db"):
        self.db_path = db_path
        self.ua = UserAgent()
        self.session = None
        self.setup_logging()
        
        # Lista de medicamentos comunes (simplificada para prueba)
        self.medications = [
            # ANALGÉSICOS Y ANTIINFLAMATORIOS
            'acetaminophen', 'paracetamol', 'ibuprofen', 'aspirin', 'naproxen',
            'diclofenac', 'tramadol', 'codeine', 'morphine',
            
            # ANTIBIÓTICOS
            'amoxicillin', 'penicillin', 'azithromycin', 'cephalexin', 'clindamycin',
            'erythromycin', 'ciprofloxacin', 'doxycycline', 'metronidazole',
            
            # CARDIOVASCULARES
            'metoprolol', 'propranolol', 'nifedipine', 'amlodipine',
            'lisinopril', 'enalapril', 'hydrochlorothiazide', 'furosemide',
            
            # DIABETES Y ENDOCRINO
            'insulin', 'metformin', 'levothyroxine', 'prednisone',
            
            # OTROS IMPORTANTES
            'folic acid', 'iron', 'prenatal vitamins', 'progesterone'
        ]

    def setup_logging(self):
        """Configurar logging SOLO a consola (sin archivos)"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()  # Solo consola
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_headers(self):
        """Headers anti-bloqueo basados en código de referencia (BSD-3/Apache-2.0)"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }

    async def init_session(self):
        """Inicializar sesión HTTP"""
        connector = aiohttp.TCPConnector(limit=5, limit_per_host=1)
        timeout = aiohttp.ClientTimeout(total=45)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )

    async def smart_request(self, url: str, retries: int = 3) -> Optional[str]:
        """Request inteligente con retry y delays adaptativos"""
        delays = [3, 8, 15]
        
        for attempt in range(retries):
            try:
                if attempt > 0:
                    delay = delays[min(attempt-1, len(delays)-1)] + random.uniform(0, 5)
                    self.logger.info(f"Esperando {delay:.1f}s antes del intento {attempt+1}")
                    await asyncio.sleep(delay)
                
                headers = self.get_headers()
                async with self.session.get(url, headers=headers, allow_redirects=True) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        self.logger.warning(f"Rate limited, esperando 60s...")
                        await asyncio.sleep(60)
                    elif response.status == 403:
                        self.logger.warning(f"Bloqueado (403) en {url}")
                    else:
                        self.logger.warning(f"HTTP {response.status} para {url}")
                        
            except Exception as e:
                self.logger.error(f"Error en intento {attempt+1} para {url}: {e}")
                
        return None

    async def scrape_drugs_com(self, drug_name: str) -> Optional[MedicationData]:
        """Scraper mejorado para drugs.com"""
        search_url = f"https://www.drugs.com/search.php?searchterm={drug_name.replace(' ', '+')}"
        
        html = await self.smart_request(search_url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar enlaces a medicamentos
        drug_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/mtm/' in href or '/monograph/' in href:
                drug_links.append(href)
        
        if not drug_links:
            self.logger.warning(f"No se encontraron enlaces para {drug_name} en drugs.com")
            return None
        
        # Obtener página del medicamento
        drug_url = drug_links[0] if drug_links[0].startswith('http') else f"https://www.drugs.com{drug_links[0]}"
        drug_html = await self.smart_request(drug_url)
        
        if not drug_html:
            return None
            
        drug_soup = BeautifulSoup(drug_html, 'html.parser')
        
        # Extraer información
        categoria_fda = self.extract_fda_category(drug_soup)
        notas_clinicas = self.extract_pregnancy_info(drug_soup)
        
        return MedicationData(
            nombre=drug_name,
            categoria_fda=categoria_fda,
            notas_clinicas=notas_clinicas,
            fuente="drugs.com",
            confianza_score=5,
            fecha_actualizacion=datetime.now().strftime("%Y-%m-%d")
        )

    def extract_fda_category(self, soup) -> Optional[str]:
        """Extraer categoría FDA"""
        text = soup.get_text()
        
        patterns = [
            r'FDA[^\w]*pregnancy[^\w]*category[^\w]*([A-DX])',
            r'pregnancy[^\w]*category[^\w]*([A-DX])',
            r'category[^\w]*([A-DX])[^\w]*pregnancy',
            r'Pregnancy Category:?\s*([A-DX])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None

    def extract_pregnancy_info(self, soup) -> Optional[str]:
        """Extraer información sobre embarazo"""
        pregnancy_keywords = ['pregnancy', 'pregnant', 'fetal', 'teratogenic']
        
        sections = []
        for keyword in pregnancy_keywords:
            elements = soup.find_all(text=lambda x: x and keyword.lower() in x.lower())
            
            for element in elements[:2]:  # Limitar a 2 por keyword
                parent = element.parent
                if parent and len(element.strip()) > 30:
                    clean_text = re.sub(r'\s+', ' ', element.strip())
                    if len(clean_text) > 50 and clean_text not in sections:
                        sections.append(clean_text[:300])  # Limitar longitud
        
        return ' | '.join(sections[:2]) if sections else None

    def setup_database(self):
        """Configurar base de datos SQLite"""
        os.makedirs('db', exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medicamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                categoria_fda TEXT,
                notas_clinicas TEXT,
                trimestres_seguro TEXT,
                fuente TEXT,
                observaciones TEXT,
                confianza_score INTEGER DEFAULT 0,
                fecha_actualizacion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    def save_medication(self, medication: MedicationData):
        """Guardar medicamento en base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO medicamentos 
            (nombre, categoria_fda, notas_clinicas, trimestres_seguro, fuente, observaciones, confianza_score, fecha_actualizacion, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            medication.nombre,
            medication.categoria_fda,
            medication.notas_clinicas,
            medication.trimestres_seguro,
            medication.fuente,
            medication.observaciones,
            medication.confianza_score,
            medication.fecha_actualizacion
        ))
        
        conn.commit()
        conn.close()

    async def run_comprehensive_scraping(self):
        """Ejecutar scraping completo"""
        self.setup_database()
        await self.init_session()
        
        total = len(self.medications)
        successful = 0
        failed = 0
        
        self.logger.info(f"🚀 Iniciando scraping de {total} medicamentos")
        start_time = time.time()
        
        for i, drug_name in enumerate(self.medications):
            try:
                self.logger.info(f"[{i+1}/{total}] Procesando: {drug_name}")
                
                result = await self.scrape_drugs_com(drug_name)
                
                if result:
                    self.save_medication(result)
                    successful += 1
                    self.logger.info(f"✅ Guardado: {drug_name} (FDA: {result.categoria_fda or 'N/A'})")
                else:
                    failed += 1
                    self.logger.warning(f"❌ Sin datos para: {drug_name}")
                
                # Delay entre medicamentos
                delay = random.uniform(8, 15)
                await asyncio.sleep(delay)
                
                # Progreso cada 5 medicamentos
                if (i + 1) % 5 == 0:
                    elapsed = time.time() - start_time
                    self.logger.info(f"📊 Progreso: {i+1}/{total} | Exitosos: {successful} | Fallidos: {failed}")
                
            except Exception as e:
                failed += 1
                self.logger.error(f"💥 Error procesando {drug_name}: {e}")
        
        await self.session.close()
        
        elapsed = time.time() - start_time
        self.logger.info(f"🏁 Scraping completado!")
        self.logger.info(f"📈 Resumen: {successful} exitosos, {failed} fallidos de {total} total")
        self.logger.info(f"⏱️  Tiempo total: {elapsed/60:.2f} minutos")

if __name__ == "__main__":
    scraper = ComprehensiveMedScraper()
    asyncio.run(scraper.run_comprehensive_scraping())
