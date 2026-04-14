from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings

# 1. Crear el motor asíncrono
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Cambiar a True para ver SQL en consola
    future=True
)

# 2. Fábrica de sesiones
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 3. Clase Base para los modelos
Base = declarative_base()

# Dependencia para FastAPI (Inyección de dependencia)
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()