from ebooklib import epub
from app.db.mongo_db import db_mongo
from app.db.postgres_db import AsyncSessionLocal
from app.db.models.book import Book
from config import settings
from sqlalchemy import select
from loguru import logger
import os

class EpubBuilder:
    def __init__(self, book_id: str):
        self.book_id = book_id
        self.output_path = settings.PROCESSED_DIR / f"{book_id}.epub"

    async def generate_epub(self):
        """Lee los datos de Mongo y genera el archivo EPUB."""
        # 1. Obtener metadatos de Postgres
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Book).where(Book.id == self.book_id))
            book_meta = result.scalar_one_or_none()
        
        if not book_meta:
            logger.error(f"No se encontró el libro {self.book_id} en Postgres.")
            return

        # 2. Crear el objeto EPUB
        book = epub.EpubBook()
        book.set_identifier(str(self.book_id))
        book.set_title(book_meta.title or book_meta.filename)
        book.set_language('es')
        book.add_author(book_meta.author or "Cthuluceno AI")

        # 3. Obtener contenido estructurado de MongoDB
        cursor = db_mongo.db["book_structures"].find({"book_id": self.book_id}).sort("page", 1)
        pages = await cursor.to_list(length=None)

        # 4. Construir el contenido HTML
        chapters = []
        full_html_content = ""
        current_chapter_num = 1
        
        # Agruparemos todo en un solo flujo o por capítulos si detectamos 'headers'
        html_body = "<html><body>"
        
        for page in pages:
            for block in page['blocks']:
                text = block['text']
                if block['type'] == "header":
                    html_body += f"<h1>{text}</h1>"
                else:
                    html_body += f"<p>{text}</p>"
        
        html_body += "</body></html>"

        # 5. Crear el capítulo principal (Simplificado por ahora)
        c1 = epub.EpubHtml(title='Contenido Principal', file_name='content.xhtml', lang='es')
        c1.content = html_body
        book.add_item(c1)

        # 6. Definir Estructura de Navegación
        book.toc = (epub.Link('content.xhtml', 'Inicio', 'intro'),)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # 7. Definir el "Spine" (Orden de lectura)
        book.spine = ['nav', c1]

        # 8. Guardar archivo
        epub.write_epub(str(self.output_path), book, {})
        logger.info(f"EPUB generado exitosamente en: {self.output_path}")
        
        return self.output_path

builder = EpubBuilder