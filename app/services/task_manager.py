import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.orchestrator import Orchestrator
from app.db.postgres_db import AsyncSessionLocal
from loguru import logger

async def start_conversion_task(book_id: str, pdf_path: str, gpu_semaphore: asyncio.Semaphore):
    """
    Tarea en segundo plano que inicializa el orquestador.
    """
    async with AsyncSessionLocal() as session:
        try:
            orchestrator = Orchestrator(book_id, pdf_path, session)
            await orchestrator.run(gpu_semaphore)
        except Exception as e:
            logger.error(f"Error en la tarea de fondo para el libro {book_id}: {e}")