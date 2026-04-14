from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from app.db.postgres_db import get_db
from app.db.models.book import Book, ProcessStatus
from app.services.task_manager import start_conversion_task
import uuid
import aiofiles

router = APIRouter()

@router.post("/")
async def upload_pdf(
    request: Request,
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")
    
    book_id = str(uuid.uuid4())
    file_path = settings.UPLOAD_DIR / f"{book_id}.pdf"
    
    # 1. Guardar el archivo físicamente
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    # 2. Crear el registro en PostgreSQL
    new_book = Book(
        id=book_id,
        filename=file.filename,
        original_path=str(file_path),
        status=ProcessStatus.PENDING
    )
    db.add(new_book)
    await db.commit()
    
    # 3. Lanzar la conversión en segundo plano
    # Pasamos el semáforo de la GPU que está en el state de la app
    background_tasks.add_task(
        start_conversion_task, 
        book_id, 
        str(file_path), 
        request.app.state.gpu_semaphore
    )
    
    return {
        "book_id": book_id,
        "status": "queued",
        "message": "Archivo recibido y en cola de procesamiento"
    }