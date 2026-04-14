from fastapi import APIRouter, Request
import shutil
from config import settings

router = APIRouter()

@router.get("/")
async def get_system_status(request: Request):
    # Verificamos espacio en disco del storage
    total, used, free = shutil.disk_usage(settings.BASE_DIR)
    
    # Intentamos ver si el semáforo de la GPU está bloqueado
    gpu_locked = request.app.state.gpu_semaphore.locked()
    
    return {
        "status": "online",
        "gpu": {
            "enabled": settings.USE_GPU,
            "busy": gpu_locked,
            "info": "RTX 4060 detected (Semaphore active)"
        },
        "storage": {
            "free_gb": round(free / (2**30), 2),
            "total_gb": round(total / (2**30), 2)
        },
        "version": settings.VERSION
    }