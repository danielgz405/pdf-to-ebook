import sys
import os
from paddleocr import PaddleOCR
import paddle
from config import settings
from loguru import logger

# Desactivar checks de red innecesarios
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

class OCREngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.info("Inicializando PaddleOCR...")
            cls._instance = super(OCREngine, cls).__new__(cls)
            
            # --- TRUCO CRÍTICO ---
            # Guardamos los argumentos del sistema y los limpiamos temporalmente.
            # Esto evita que PaddleOCR intente parsear "main.py" como un argumento de OCR.
            actual_argv = sys.argv
            sys.argv = [actual_argv[0]] 

            try:
                # Determinar si usamos GPU
                use_gpu = settings.USE_GPU and paddle.device.is_compiled_with_cuda()
                
                if use_gpu:
                    paddle.device.set_device('gpu')
                else:
                    paddle.device.set_device('cpu')

                # Inicialización limpia
                cls._instance.ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='es',
                    use_gpu=use_gpu,
                    show_log=False  # En v2.8.1 esto suele funcionar bien
                )
                logger.info(f"✅ PaddleOCR cargado con éxito (GPU: {use_gpu})")
            
            except Exception as e:
                logger.error(f"❌ Error al iniciar PaddleOCR: {e}")
                # Fallback final a CPU sin argumentos
                cls._instance.ocr = PaddleOCR(lang='es', use_gpu=False)
            
            finally:
                # Restauramos los argumentos originales del sistema
                sys.argv = actual_argv
                
        return cls._instance

    def process_image(self, image_path: str):
        """Ejecuta el OCR en una imagen."""
        try:
            result = self.ocr.ocr(image_path, cls=True)
            processed_results = []
            if result and result[0]:
                for line in result[0]:
                    processed_results.append({
                        "coords": line[0],
                        "text": line[1][0],
                        "confidence": line[1][1]
                    })
            return processed_results
        except Exception as e:
            logger.error(f"Error procesando imagen {image_path}: {e}")
            return []

# Instancia global
ocr_engine = OCREngine()