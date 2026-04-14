import cv2
import numpy as np

class ImageProcessor:
    @staticmethod
    def optimize_for_ocr(image_path: str):
        """Lee una imagen y la optimiza para mejorar el reconocimiento de texto."""
        # Leer imagen
        img = cv2.imread(image_path)
        
        # 1. Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 2. Reducción de ruido (Denoising)
        # preserva bordes pero suaviza el fondo
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        
        # 3. Binarización Adaptativa (Opcional, a veces PaddleOCR prefiere grises)
        # La dejamos comentada por si el motor necesita más contraste
        # thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        return denoised

    @staticmethod
    def get_image_size(image_path: str):
        img = cv2.imread(image_path)
        return img.shape[:2] # height, width