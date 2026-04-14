import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Importaciones de configuración y base de datos
from config import settings
from app.db.postgres_db import engine, Base
from app.db.mongo_db import connect_to_mongo, close_mongo_connection

# IMPORTANTE: Importar los modelos para que SQLAlchemy los "vea" y cree las tablas
from app.db.models.book import Book 

# Importación de rutas
from app.api.v1.endpoints import upload, status, books

# 1. Definición del Ciclo de Vida (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP: Lo que ocurre al encender el servidor ---
    logger.info(f"🚀 Iniciando {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # A. Crear tablas en PostgreSQL (si no existen)
    try:
        async with engine.begin() as conn:
            # Esto busca todas las clases que hereden de 'Base' (como Book)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ PostgreSQL: Tablas verificadas/creadas.")
    except Exception as e:
        logger.error(f"❌ Error conectando a PostgreSQL: {e}")

    # B. Conectar a MongoDB
    try:
        await connect_to_mongo()
        logger.info("✅ MongoDB: Conexión establecida.")
    except Exception as e:
        logger.error(f"❌ Error conectando a MongoDB: {e}")
    
    # C. Inicializar Semáforo de GPU
    # Esto limita a 1 proceso de IA a la vez para no saturar la VRAM de la RTX 4060
    app.state.gpu_semaphore = asyncio.Semaphore(1)
    logger.info("✅ GPU Semaphore: Configurado para 1 proceso simultáneo.")

    yield # Aquí es donde la app se mantiene corriendo

    # --- SHUTDOWN: Lo que ocurre al apagar el servidor ---
    await close_mongo_connection()
    logger.info(f"🛑 {settings.PROJECT_NAME} apagado.")

# 2. Inicialización de la Aplicación
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Sistema de conversión de PDF a E-book con IA (PaddleOCR + GPU)",
    lifespan=lifespan
)

# 3. Middlewares (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción, cambia esto por tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Inclusión de Rutas
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(status.router, prefix="/api/v1/status", tags=["Status"])
app.include_router(books.router, prefix="/api/v1/books", tags=["Library"])

# 5. Endpoint de Bienvenida / Health
@app.get("/", tags=["Health"])
async def root():
    return {
        "message": f"Bienvenido a {settings.PROJECT_NAME} API",
        "docs": "/docs",
        "status": "active"
    }

if __name__ == "__main__":
    import uvicorn
    # reload=True recarga el servidor automáticamente al guardar cambios
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)