import os
import json
from pathlib import Path
from typing import List, Any, Optional
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- CONFIGURACIÓN DE APP ---
    # Usamos validation_alias para que lea "APP_NAME" del .env pero se llame PROJECT_NAME en el código
    PROJECT_NAME: str = Field(default="Cthuluceno Converter", validation_alias="APP_NAME")
    VERSION: str = Field(default="2.1.0", validation_alias="APP_VERSION")
    DEBUG: bool = True
    SECRET_KEY: str = "default_secret_key"
    API_V1_STR: str = "/api/v1"

    # --- BASES DE DATOS (Postgres) ---
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "admin"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "cthuluceno_db"
    
    # Esta variable recibirá lo que haya en el .env
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: Any, info: Any) -> Any:
        # Si la URL en el .env tiene ${} o está vacía, la construimos manualmente
        # Pydantic no resuelve variables de entorno internas como lo hace Bash
        if isinstance(v, str) and "${" not in v and v.strip() != "":
            return v
        return None # Dejamos que se construya en el siguiente paso

    # --- BASES DE DATOS (Mongo) ---
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "cthuluceno_storage"

    # --- RUTAS DE ALMACENAMIENTO ---
    BASE_DIR: Path = Path(__file__).resolve().parent
    UPLOAD_DIR: Path = BASE_DIR / "storage" / "uploads"
    TEMP_DIR: Path = BASE_DIR / "storage" / "temp"
    PROCESSED_DIR: Path = BASE_DIR / "storage" / "processed"

    # --- MOTOR DE IA (RTX 4060) ---
    USE_GPU: bool = True
    CUDA_DEVICE_ID: int = 0
    GPU_MEM_FRACTION: float = 0.7
    MAX_CONCURRENT_TASKS: int = 1

    # --- OCR SETTINGS ---
    OCR_LANGUAGE: Any = ["es", "en"]

    @field_validator("OCR_LANGUAGE", mode="before")
    @classmethod
    def parse_ocr_languages(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                cleaned_v = v.strip("'").strip('"')
                if cleaned_v.startswith("["):
                    return json.loads(cleaned_v)
                return [lang.strip() for lang in cleaned_v.split(",")]
            except:
                return ["es", "en"]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_file_encoding='utf-8'
    )

    def create_directories(self):
        """Crea las carpetas físicas si no existen."""
        for path in [self.UPLOAD_DIR, self.TEMP_DIR, self.PROCESSED_DIR]:
            path.mkdir(parents=True, exist_ok=True)

# 1. Instanciar la configuración
settings = Settings()

# 2. Corregir la DATABASE_URL si Pydantic no pudo resolver las variables ${} del .env
if not settings.DATABASE_URL or "${" in settings.DATABASE_URL:
    settings.DATABASE_URL = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
        f"{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )

# 3. Crear directorios
settings.create_directories()