import asyncio
import fitz  # PyMuPDF
from pathlib import Path
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from config import settings
from app.core.ocr_engine import ocr_engine
from app.core.analyzer import analyzer
from app.core.builder import EpubBuilder
from app.db.mongo_db import db_mongo
from app.db.models.book import Book, ProcessStatus

class Orchestrator:
    def __init__(self, book_id: str, pdf_path: str, db_session: AsyncSession):
        self.book_id = book_id
        self.pdf_path = pdf_path
        self.db = db_session
        self.temp_dir = settings.TEMP_DIR / book_id
        
        # Asegurar que el directorio temporal del libro exista
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def _update_db_status(self, status: ProcessStatus, current_page: int = 0, total_pages: int = 0, epub_path: str = None):
        """Actualiza el progreso y estado en PostgreSQL."""
        values = {
            "status": status,
            "current_page": current_page,
            "total_pages": total_pages
        }
        if epub_path:
            values["epub_path"] = epub_path

        query = (
            update(Book)
            .where(Book.id == self.book_id)
            .values(**values)
        )
        await self.db.execute(query)
        await self.db.commit()

    async def run(self, gpu_semaphore: asyncio.Semaphore):
        """Ciclo de vida completo: PDF -> OCR -> Estructura -> EPUB."""
        doc = None
        try:
            # 1. Abrir documento y preparar metadatos
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            
            await self._update_db_status(ProcessStatus.PROCESSING, 0, total_pages)
            logger.info(f"🚀 Iniciando procesamiento del libro {self.book_id} ({total_pages} págs)")

            # 2. Procesar cada página
            for page_num in range(total_pages):
                # A. Renderizar página a imagen (PNG)
                page = doc.load_page(page_num)
                # Matrix 2.0 = 200% escala (buen equilibrio entre peso y precisión OCR)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
                img_path = self.temp_dir / f"page_{page_num}.png"
                pix.save(str(img_path))

                # B. Ejecución de OCR (Protegido por semáforo de GPU)
                async with gpu_semaphore:
                    logger.debug(f"GPU Lock: Procesando pág {page_num} del libro {self.book_id}")
                    # Ejecutamos en thread para no bloquear el event loop de la API
                    raw_ocr_results = await asyncio.to_thread(
                        ocr_engine.process_image, str(img_path)
                    )

                # C. Análisis de Layout (Convertir líneas en párrafos/títulos)
                structured_page = await analyzer.analyze_page(page_num, raw_ocr_results)

                # D. Persistencia en MongoDB
                await db_mongo.db["book_structures"].update_one(
                    {"book_id": self.book_id, "page": page_num},
                    {"$set": structured_page.model_dump()},
                    upsert=True
                )

                # E. Actualizar progreso y limpiar imagen temporal
                await self._update_db_status(ProcessStatus.PROCESSING, page_num + 1, total_pages)
                if img_path.exists():
                    img_path.unlink()

            # 3. Cerrar PDF original
            doc.close()
            doc = None

            # 4. Generación del EPUB final
            logger.info(f"🏗️ Generando archivo EPUB para {self.book_id}...")
            builder_inst = EpubBuilder(self.book_id)
            epub_path = await builder_inst.generate_epub()

            # 5. Marcar como completado
            await self._update_db_status(
                ProcessStatus.COMPLETED, 
                total_pages, 
                total_pages, 
                epub_path=str(epub_path)
            )
            
            logger.info(f"✅ Libro {self.book_id} procesado con éxito.")
            
            # Limpiar carpeta temporal del libro
            if self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)

            return True

        except Exception as e:
            logger.error(f"❌ Error crítico en Orchestrator ({self.book_id}): {str(e)}")
            if doc:
                doc.close()
            await self._update_db_status(ProcessStatus.ERROR)
            raise e