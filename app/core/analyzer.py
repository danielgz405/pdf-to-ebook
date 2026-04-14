from typing import List, Dict
from pydantic import BaseModel
from loguru import logger

class TextBlock(BaseModel):
    text: str
    type: str  # paragraph, header, footer, caption
    confidence: float
    bbox: List[List[float]]

class PageStructure(BaseModel):
    page_num: int
    blocks: List[TextBlock]

class LayoutAnalyzer:
    def __init__(self):
        # Umbrales para heurística (ajustables)
        self.header_threshold = 1.5  # Multiplicador de altura para considerar título
        self.paragraph_gap = 20      # Distancia en píxeles para separar párrafos

    async def analyze_page(self, page_num: int, ocr_results: List[Dict]) -> PageStructure:
        """
        Analiza la disposición espacial del OCR para reconstruir la estructura.
        """
        if not ocr_results:
            return PageStructure(page_num=page_num, blocks=[])

        # 1. Ordenar bloques por posición Y (arriba hacia abajo) y luego X
        # Esto asegura que leemos en el orden correcto
        sorted_results = sorted(
            ocr_results, 
            key=lambda x: (x['coords'][0][1], x['coords'][0][0])
        )

        structured_blocks = []
        current_block = None

        for item in sorted_results:
            text = item['text'].strip()
            coords = item['coords']
            conf = item['confidence']
            
            # Calcular altura del bloque actual
            height = coords[2][1] - coords[0][1]
            
            # 2. Identificar y descartar ruidos (ej. números de página muy pequeños o aislados)
            if self._is_garbage(text, coords):
                continue

            # 3. Lógica de Agrupación (Merging)
            # Si el bloque actual está muy cerca del anterior, los unimos en el mismo párrafo
            if current_block and self._is_same_paragraph(current_block, coords):
                current_block.text += f" {text}"
                # Actualizar el bbox para que cubra ambos
                current_block.bbox[2] = coords[2] 
            else:
                # Determinar tipo de bloque
                block_type = "paragraph"
                if height > 25: # Heurística simple para títulos (ajustar según el PDF)
                    block_type = "header"

                current_block = TextBlock(
                    text=text,
                    type=block_type,
                    confidence=conf,
                    bbox=coords
                )
                structured_blocks.append(current_block)

        return PageStructure(page_num=page_num, blocks=structured_blocks)

    def _is_same_paragraph(self, last_block: TextBlock, current_coords: List) -> bool:
        """Determina si una línea pertenece al párrafo anterior basándose en la distancia Y."""
        last_y_bottom = last_block.bbox[2][1]
        current_y_top = current_coords[0][1]
        gap = current_y_top - last_y_bottom
        
        return 0 <= gap <= self.paragraph_gap

    def _is_garbage(self, text: str, coords: List) -> bool:
        """Filtra ruidos comunes como números de página sueltos."""
        # Si es solo un número y está muy arriba o muy abajo
        if text.isdigit() and (coords[0][1] < 50 or coords[0][1] > 1000):
            return True
        if len(text) < 2:
            return True
        return False

analyzer = LayoutAnalyzer()