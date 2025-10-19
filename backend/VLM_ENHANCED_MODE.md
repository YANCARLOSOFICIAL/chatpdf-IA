# VLM-Enhanced Query Mode 🖼️

## ¿Qué es?

**VLM-Enhanced Query Mode** es una mejora al sistema ChatPDF que permite al modelo de IA **ver realmente las imágenes originales** del PDF cuando respondes preguntas, en lugar de solo leer descripciones de texto.

## ¿Cómo funciona?

### Antes (Caption-Only Mode)
1. Usuario sube PDF con imágenes
2. Sistema genera descripciones textuales (captions) de las imágenes
3. Durante el chat, el modelo solo lee las descripciones
4. **Limitación**: El modelo no puede ver detalles visuales específicos

### Ahora (VLM-Enhanced Mode)
1. Usuario sube PDF con imágenes
2. Sistema guarda las imágenes permanentemente en `uploads/images/{pdf_id}/`
3. Sistema genera captions Y guarda referencias en BD (tabla `pdf_images`)
4. Durante el chat:
   - Si detecta `[IMAGE_CAPTIONS]` en el contexto
   - **Carga las imágenes originales desde disco**
   - **Envía imágenes + texto al modelo de visión (GPT-4o-mini)**
   - El modelo "ve" realmente los gráficos, diagramas, tablas, etc.

## Cambios Implementados

### 1. Base de Datos
**Nueva tabla**: `pdf_images`
```sql
CREATE TABLE pdf_images (
    id SERIAL PRIMARY KEY,
    pdf_id INTEGER REFERENCES pdfs(id) ON DELETE CASCADE,
    image_path TEXT NOT NULL,
    page_number INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Extracción de Imágenes
**Función modificada**: `extract_images_from_pdf(file_path, pdf_id=None)`
- Ahora acepta `pdf_id` opcional
- Si se proporciona `pdf_id`, guarda imágenes permanentemente en:
  - `backend/uploads/images/{pdf_id}/page_1.png`
  - `backend/uploads/images/{pdf_id}/page_2.png`
  - etc.
- Retorna lista de tuplas: `[(image_path, page_number), ...]`

### 3. Upload de PDFs
**Endpoints modificados**: `/upload_pdf/` y `/upload_pdfs/`
- Crea entrada de PDF **PRIMERO** para obtener `pdf_id`
- Extrae imágenes con `pdf_id` para guardarlas permanentemente
- Registra cada imagen en tabla `pdf_images`:
  ```python
  INSERT INTO pdf_images (pdf_id, image_path, page_number) 
  VALUES (pdf_id, '/path/to/image', page_num)
  ```
- Las imágenes **NO se borran** después del procesamiento

### 4. Endpoint de Chat
**Endpoint modificado**: `/chat/`
- Detecta si contexto contiene `[IMAGE_CAPTIONS]`
- Si es así, activa **VLM-Enhanced Mode**:
  ```python
  if "[IMAGE_CAPTIONS]" in context:
      # Cargar imágenes del PDF desde BD
      SELECT image_path, page_number FROM pdf_images WHERE pdf_id = ?
      
      # Para OpenAI: enviar imágenes + texto al modelo
      messages = [
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": [
              {"type": "text", "text": query + context},
              {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
          ]}
      ]
  ```
- Usa modelo `gpt-4o-mini` (capaz de procesar visión)
- Limita a primeras 5 imágenes para evitar exceder límites de tokens
- **Fallback automático** a modo text-only si hay errores

## Ventajas

✅ **Precisión mejorada**: El modelo ve los detalles visuales reales  
✅ **Respuestas más específicas**: Puede leer valores exactos de gráficos, tablas, etc.  
✅ **Mejor experiencia**: Usuario puede preguntar "¿qué dice el gráfico de la página 3?" y el modelo lo ve  
✅ **Retrocompatibilidad**: Si no hay imágenes, funciona como antes  
✅ **Fallback automático**: Si VLM-enhanced falla, usa captions como antes  

## Uso

### Variables de Entorno
```bash
OPENAI_API_KEY=sk-...           # Requerido para VLM-Enhanced Mode
ENABLE_VISION_CAPTIONS=true     # Auto-activado si OPENAI_API_KEY presente
ENABLE_OCR=true                 # OCR adicional con Tesseract
```

### Ejemplo de Pregunta
```
Usuario: "¿Qué valores muestra el gráfico de barras en la página 3?"

Sistema (VLM-Enhanced):
1. Recupera chunks relevantes (incluyen [IMAGE_CAPTIONS])
2. Detecta marcador [IMAGE_CAPTIONS]
3. Carga imagen de página 3 desde disco
4. Envía imagen + contexto a GPT-4o-mini
5. Modelo "ve" el gráfico y responde con valores específicos
```

## Límites y Consideraciones

⚠️ **Límite de imágenes**: Máximo 5 imágenes por query (evitar exceder tokens)  
⚠️ **Tamaño de imagen**: Imágenes >100KB base64 se saltan automáticamente  
⚠️ **Costo**: VLM-Enhanced usa más tokens que text-only (más costoso)  
⚠️ **Latencia**: Enviar imágenes toma más tiempo que solo texto  
⚠️ **Fallback**: Si imagen no existe o hay error, usa captions como antes  

## Logs de Debug

Busca estos mensajes en los logs:
```
INFO:main:Detected IMAGE_CAPTIONS in context, loading images for VLM-enhanced mode
INFO:main:Loaded 6 images for pdf_id=123
INFO:main:Using VLM-enhanced mode with 6 images
INFO:main:Added image from page 1 to VLM request
INFO:main:VLM-enhanced response generated successfully
```

Si VLM-enhanced falla:
```
WARNING:main:VLM-enhanced mode failed: ...
INFO:main:Using text-only mode (no images or no API key)
```

## Próximos Pasos

🔄 **Context-Aware Captions**: Incluir texto circundante al generar captions  
🔄 **Ollama VLM Support**: Agregar soporte para modelos de visión en Ollama  
🔄 **Selective Image Loading**: Solo cargar imágenes mencionadas en query  
🔄 **Image Compression**: Comprimir imágenes antes de enviar (reducir tokens)  

## Testing

Para probar VLM-Enhanced Mode:
1. Sube un PDF con gráficos/tablas/diagramas
2. Verifica que se crearon archivos en `backend/uploads/images/{pdf_id}/`
3. Haz una pregunta específica sobre una imagen
4. Revisa logs para confirmar "Using VLM-enhanced mode"
5. Compara respuesta vs. modo caption-only

---
**Implementado**: 18 de Octubre, 2025  
**Autor**: GitHub Copilot  
**Versión**: 1.0
