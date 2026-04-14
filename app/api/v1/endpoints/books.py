from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.postgres_db import get_db
from app.db.models.book import Book
import os

router = APIRouter()

@router.get("/")
async def list_books(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Book).order_by(Book.created_at.desc()))
    books = result.scalars().all()
    return books

@router.get("/{book_id}")
async def get_book_status(book_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
        
    return {
        "id": book.id,
        "filename": book.filename,
        "status": book.status,
        "progress": f"{book.current_page}/{book.total_pages}",
        "epub_ready": book.epub_path is not None
    }

@router.get("/{book_id}/download")
async def download_book(book_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    
    if not book or not book.epub_path:
        raise HTTPException(status_code=404, detail="Archivo no listo para descarga")
    
    if not os.path.exists(book.epub_path):
        raise HTTPException(status_code=404, detail="El archivo físico no se encuentra")

    return FileResponse(
        path=book.epub_path, 
        filename=f"{book.filename.split('.')[0]}.epub",
        media_type='application/epub+zip'
    )