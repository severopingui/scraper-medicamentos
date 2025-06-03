import asyncio
import aiohttp
import sqlite3
from bs4 import BeautifulSoup
import logging
import time
import random
from fake_useragent import UserAgent
import re
from datetime import datetime

class ELactanciaEmbarazoScraper:
    def __init__(self, db_path: str = "db/medicamentos.db"):
        self.db_path = db_path
        self.ua = UserAgent()
        self.session = None
        self.setup_logging()
        
        # Medicamentos en español E inglés para máxima cobertura
        self.medications = {
            # ANALGÉSICOS
            'acetaminophen': 'paracetamol',
            'ibuprofen': 'ibuprofeno', 
            'aspirin': 'aspirina',
            'naproxen': 'naproxeno',
            'diclofenac': 'diclofenaco',
            'tramadol': 'tramadol',
            'codeine': 'codeina',
            'morphine': 'morfina',
            
            # ANTIBIÓTICOS
            'amoxicillin': 'amoxicilina',
            'penicillin': 'penicilina',
            'azithromycin': 'azitromicina',
            'erythromycin': 'eritromicina',
            'ciprofloxacin': 'ciprofloxacina',
            'doxycycline': 'doxiciclina',
            'metronidazole': 'metronidazol',
            'clindamycin': 'clindamicina',
            
            # CARDIOVASCULARES
            'metoprolol': 'metoprolol',
            'propranolol': 'propranolol',
            'amlodipine': 'amlodipina',
            'lisinopril': 'lisinopril',
            'hydrochlorothiazide': 'hidroclorotiazida',
            'furosemide': 'furosemida',
            'warfarin': 'warfarina',
            'heparin': 'heparina',
            
            # DIABETES Y ENDOCRINO
            'insulin': 'insulina',
            'metformin': 'metformina',
            'levothyroxine': 'levotiroxina',
            'prednisone': 'prednisona',
            'prednisolone': 'prednisolona',
            'hydrocortisone': 'hidrocortisona',
            
            # GASTROINTESTINALES
            'omeprazole': 'omeprazol',
            'ranitidine': 'ranitidina',
            'famotidine': 'famotidina',
            'ondansetron': 'ondansetron',
            'metoclopramide': 'metoclopramida',
            
            # PSIQUIÁTRICOS
            'sertraline': 'sertralina',
            'fluoxetine': 'fluoxetina',
            'paroxetine': 'paroxetina',
            'citalopram': 'citalopram',
            'lorazepam': 'lorazepam',
            'diazepam': 'diazepam',
            
            # ANTIHISTAMÍNICOS
            'diphenhydramine': 'difenhidramina',
            'loratadine': 'loratadina',
            'cetirizine': 'cetirizina',
            
            # OTROS IMPORTANTES
            'folic acid': 'acido folico',
            'iron': 'hierro',
            'progesterone': 'progesterona',
            'misoprostol': 'misoprostol'
        }

    def setup_logging(self):
        """Configurar logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def get_headers(self):
        """Headers basados en código de referencia (BSD-3/Apache-2.0)"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en-US,en;q=0.8',  # Español primero, inglés segundo
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }

    async def init_session(self):
        """Inicializar sesión HTTP"""
        connector = aiohttp.TCPConnector(limit=3, limit_per_host=1)
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )

    async def smart_request(self, url: str, retries: int = 3) -> str:
        """Request inteligente con retry"""
        for attempt in range(retries):
            try:
                if attempt > 0:
                    delay = [5, 10, 20][min(attempt-1, 2)] + random.uniform(0, 5)
                    self.logger.info(f"⏳ Esperando {delay:.1f}s antes del intento {attempt+1}")
                    await asyncio.sleep(delay)
                
                headers = self.get_headers()
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        self.logger.warning(f"HTTP {response.status} para {url}")
                        
            except Exception as e:
                self.logger.error(f"Error en intento {attempt+1}: {e}")
                
        return None

    async def buscar_medicamento_dual(self, nombre_ingles: str, nombre_espanol: str):
        """Buscar medicamento en inglés Y español para máxima cobertura"""
        resultados = {}
        
        # Probar ambos nombres
        for nombre, idioma in [(nombre_ingles, 'inglés'), (nombre_espanol, 'español')]:
            self.logger.info(f"🔍 Buscando '{nombre}' ({idioma})")
            
            # URL directa verificada que funciona
            url = f"https://www.e-lactancia.org/breastfeeding/{nombre}/product/"
            
            html = await self.smart_request(url)
            if html and self.es_pagina_valida(html, nombre):
                info = self.extraer_info_embarazo(html, nombre, url, idioma)
                if info:
                    resultados[idioma] = info
                    self.logger.info(f"✅ Datos encontrados en {idioma}")
            else:
                self.logger.warning(f"❌ Sin datos válidos para '{nombre}' ({idioma})")
            
            # Delay entre búsquedas
            await asyncio.sleep(random.uniform(3, 6))
        
        # Retornar el mejor resultado (español preferido)
        if 'español' in resultados:
            return resultados['español']
        elif 'inglés' in resultados:
            return resultados['inglés']
        else:
            return None

    def es_pagina_valida(self, html: str, nombre_medicamento: str):
        """Verificar si la página contiene información médica válida"""
        soup = BeautifulSoup(html, 'html.parser')
        contenido = soup.get_text().lower()
        
        # Palabras clave que indican contenido médico válido
        keywords_medicos = [
            'pregnancy', 'embarazo', 'pregnant', 'embarazada', 'fetal', 'maternal',
            'risk', 'riesgo', 'compatible', 'contraindicated', 'contraindicado',
            'trimester', 'trimestre', 'gestation', 'gestacion', 'teratogenic'
        ]
        
        # Contar menciones del medicamento y palabras médicas
        menciones_medicamento = contenido.count(nombre_medicamento.lower())
        palabras_medicas = sum(1 for keyword in keywords_medicos if keyword in contenido)
        
        # Válida si tiene al menos 1 mención del medicamento y 3 palabras médicas
        return menciones_medicamento >= 1 and palabras_medicas >= 3

    def extraer_info_embarazo(self, html: str, nombre: str, url: str, idioma: str):
        """Extraer información específica sobre EMBARAZO"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extraer nivel de riesgo
        nivel_riesgo = self.extraer_nivel_riesgo(soup)
        
        # Extraer información específica de embarazo
        info_embarazo = self.extraer_detalles_embarazo(soup)
        
        # Extraer trimestres seguros
        trimestres_seguros = self.extraer_trimestres_seguros(soup)
        
        # Extraer recomendaciones
        recomendaciones = self.extraer_recomendaciones(soup)
        
        return {
            'nombre': nombre,
            'categoria_fda': nivel_riesgo,
            'notas_clinicas': info_embarazo,
            'trimestres_seguro': trimestres_seguros,
            'fuente': f"e-lactancia.org ({idioma}) - {url}",
            'observaciones': recomendaciones,
            'fecha_actualizacion': datetime.now().strftime("%Y-%m-%d")
        }

    def extraer_nivel_riesgo(self, soup):
        """Extraer nivel de riesgo específico de embarazo"""
        contenido = soup.get_text().lower()
        
        # Patrones de riesgo de e-lactancia
        patrones_riesgo = [
            (r'very low risk', 'Muy Bajo Riesgo'),
            (r'low risk', 'Bajo Riesgo'), 
            (r'moderate risk', 'Riesgo Moderado'),
            (r'high risk', 'Alto Riesgo'),
            (r'very high risk', 'Muy Alto Riesgo'),
            (r'compatible', 'Compatible'),
            (r'probably compatible', 'Probablemente Compatible'),
            (r'use with caution', 'Usar con Precaución'),
            (r'avoid', 'Evitar'),
            (r'contraindicated', 'Contraindicado'),
            
            # Patrones en español
            (r'riesgo muy bajo', 'Muy Bajo Riesgo'),
            (r'riesgo bajo', 'Bajo Riesgo'),
            (r'riesgo moderado', 'Riesgo Moderado'),
            (r'riesgo alto', 'Alto Riesgo'),
            (r'riesgo muy alto', 'Muy Alto Riesgo'),
            (r'compatible', 'Compatible'),
            (r'contraindicado', 'Contraindicado')
        ]
        
        for patron, nivel in patrones_riesgo:
            if re.search(patron, contenido):
                return nivel
        
        return None

    def extraer_detalles_embarazo(self, soup):
        """Extraer información detallada sobre embarazo"""
        contenido = soup.get_text()
        
        # Palabras clave específicas de embarazo
        keywords_embarazo = [
            'pregnancy', 'embarazo', 'pregnant', 'embarazada', 'fetal', 'feto',
            'maternal', 'materna', 'trimester', 'trimestre', 'gestation', 'gestacion',
            'teratogenic', 'teratogenico', 'birth defect', 'defecto congenito',
            'prenatal', 'conception', 'concepcion'
        ]
        
        parrafos_embarazo = []
        
        # Buscar párrafos relevantes
        for parrafo in contenido.split('\n'):
            parrafo = parrafo.strip()
            if len(parrafo) > 100:  # Solo párrafos sustanciales
                for keyword in keywords_embarazo:
                    if keyword.lower() in parrafo.lower():
                        # Limpiar y agregar
                        parrafo_limpio = re.sub(r'\s+', ' ', parrafo)
                        if len(parrafo_limpio) > 150:
                            parrafos_embarazo.append(parrafo_limpio[:400])
                        break
        
        # Retornar los 3 párrafos más relevantes
        return ' || '.join(parrafos_embarazo[:3]) if parrafos_embarazo else None

    def extraer_trimestres_seguros(self, soup):
        """Extraer información sobre seguridad por trimestres"""
        contenido = soup.get_text().lower()
        
        trimestres = {
            'trimestre 1': False,
            'trimestre 2': False, 
            'trimestre 3': False
        }
        
        # Patrones para detectar seguridad por trimestre
        patrones_seguridad = [
            r'first trimester.*safe',
            r'primer trimestre.*seguro',
            r'second trimester.*safe',
            r'segundo trimestre.*seguro',
            r'third trimester.*safe',
            r'tercer trimestre.*seguro',
            r'safe.*first trimester',
            r'seguro.*primer trimestre'
        ]
        
        for patron in patrones_seguridad:
            if re.search(patron, contenido):
                if 'first' in patron or 'primer' in patron:
                    trimestres['trimestre 1'] = True
                elif 'second' in patron or 'segundo' in patron:
                    trimestres['trimestre 2'] = True
                elif 'third' in patron or 'tercer' in patron:
                    trimestres['trimestre 3'] = True
        
        # Formatear resultado
        seguros = [t for t, seguro in trimestres.items() if seguro]
        return ', '.join(seguros) if seguros else None

    def extraer_recomendaciones(self, soup):
        """Extraer recomendaciones y alternativas"""
        contenido = soup.get_text()
        
        keywords_recomendaciones = [
            'alternative', 'alternativa', 'instead', 'en lugar de', 'substitute',
            'sustituto', 'recommend', 'recomienda', 'safer', 'mas seguro',
            'avoid', 'evitar', 'caution', 'precaucion'
        ]
        
        recomendaciones = []
        
        for parrafo in contenido.split('.'):
            parrafo = parrafo.strip()
            if len(parrafo) > 50:
                for keyword in keywords_recomendaciones:
                    if keyword.lower() in parrafo.lower():
                        parrafo_limpio = re.sub(r'\s+', ' ', parrafo)
                        if len(parrafo_limpio) > 80:
                            recomendaciones.append(parrafo_limpio[:250])
                        break
        
        return ' | '.join(recomendaciones[:2]) if recomendaciones else None

    def setup_database(self):
        """Configurar base de datos"""
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
                fecha_actualizacion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info("✅ Base de datos configurada")

    def save_medication(self, med_data):
        """Guardar medicamento en base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO medicamentos 
            (nombre, categoria_fda, notas_clinicas, trimestres_seguro, fuente, observaciones, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            med_data['nombre'],
            med_data['categoria_fda'],
            med_data['notas_clinicas'],
            med_data['trimestres_seguro'],
            med_data['fuente'],
            med_data['observaciones'],
            med_data['fecha_actualizacion']
        ))
        
        conn.commit()
        conn.close()

    async def run_embarazo_scraping(self):
        """Ejecutar scraping enfocado en EMBARAZO"""
        self.logger.info("🚀 Iniciando scraping de e-lactancia enfocado en EMBARAZO...")
        
        self.setup_database()
        await self.init_session()
        
        total = len(self.medications)
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        for i, (nombre_ingles, nombre_espanol) in enumerate(self.medications.items()):
            try:
                self.logger.info(f"\n[{i+1}/{total}] Procesando: {nombre_ingles} / {nombre_espanol}")
                
                result = await self.buscar_medicamento_dual(nombre_ingles, nombre_espanol)
                
                if result:
                    self.save_medication(result)
                    successful += 1
                    riesgo = result['categoria_fda'] or 'N/A'
                    trimestres = result['trimestres_seguro'] or 'N/A'
                    self.logger.info(f"✅ Guardado: {result['nombre']}")
                    self.logger.info(f"   🎯 Riesgo embarazo: {riesgo}")
                    self.logger.info(f"   📅 Trimestres seguros: {trimestres}")
                else:
                    failed += 1
                    self.logger.warning(f"❌ Sin datos para: {nombre_ingles}/{nombre_espanol}")
                
                # Delay respetuoso entre medicamentos (10-18 segundos)
                delay = random.uniform(10, 18)
                self.logger.info(f"⏳ Esperando {delay:.1f}s...")
                await asyncio.sleep(delay)
                
                # Progreso cada 5 medicamentos
                if (i + 1) % 5 == 0:
                    elapsed = time.time() - start_time
                    remaining = total - i - 1
                    eta_minutes = (elapsed / (i + 1)) * remaining / 60
                    self.logger.info(f"📊 Progreso: {i+1}/{total} | Exitosos: {successful} | Fallidos: {failed} | ETA: {eta_minutes:.1f} min")
                
            except Exception as e:
                failed += 1
                self.logger.error(f"💥 Error procesando {nombre_ingles}/{nombre_espanol}: {e}")
        
        await self.session.close()
        
        elapsed = time.time() - start_time
        self.logger.info(f"\n🏁 SCRAPING DE EMBARAZO COMPLETADO!")
        self.logger.info(f"📈 Resumen final:")
        self.logger.info(f"   ✅ Exitosos: {successful}")
        self.logger.info(f"   ❌ Fallidos: {failed}")
        self.logger.info(f"   📊 Total: {total}")
        self.logger.info(f"   ⏱️  Tiempo: {elapsed/60:.2f} minutos")
        self.logger.info(f"   📁 Base de datos: {self.db_path}")

if __name__ == "__main__":
    scraper = ELactanciaEmbarazoScraper()
    asyncio.run(scraper.run_embarazo_scraping())
