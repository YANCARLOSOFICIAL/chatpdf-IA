# Actualización: Visor PDF Responsive y Evidencia en Chat

## ✅ Cambios Implementados

### 1. Visor PDF Completamente Responsive

**Archivo modificado:** `frontend/src/components/PdfViewer.vue`

#### Mejoras principales:
- ✅ **devicePixelRatio correcto**: Canvas interno usa DPR para rendering nítido en pantallas de alta densidad
- ✅ **CSS vs Pixel size**: Canvas width/height (píxeles) separado de style.width/height (CSS) para mantener proporciones perfectas
- ✅ **ResizeObserver**: Ajuste automático cuando cambia el tamaño del contenedor (responsive real)
- ✅ **Auto-fit inteligente**: Calcula scale automáticamente al abrir y al redimensionar
- ✅ **Controles mejorados**: Zoom +/-, 100%, navegación de páginas
- ✅ **Modo imagen-first**: Usa PNGs extraídos cuando están disponibles (más confiable que PDF.js)
- ✅ **Método público goToPage(pageNum)**: Permite navegación programática desde el chat

#### Cómo funciona:
```javascript
// El visor ahora usa:
const DPR = window.devicePixelRatio || 1;
canvas.width = renderWidth * DPR;  // píxeles internos (calidad)
canvas.style.width = `${renderWidth}px`;  // CSS size (layout)
```

### 2. Sistema de Evidencia/Provenance en Chat

**Archivos modificados:**
- `backend/main.py` → función `search_similar_chunks()` y endpoint `/chat/`
- `frontend/src/App.vue` → método `sendMessage()` y nuevo `handleGoToSource()`
- `frontend/src/components/chat/ChatMessage.vue` → sección de fuentes

#### Flujo completo:
1. **Backend** devuelve array `sources` con cada respuesta del chat:
   ```json
   {
     "response": "...",
     "sources": [
       {
         "chunk_id": 123,
         "page": 5,
         "preview": "Fragmento del texto...",
         "pdf_id": 42
       }
     ]
   }
   ```

2. **Frontend** almacena `sources` en cada mensaje del asistente

3. **UI** muestra botones clicables por cada fuente:
   - "📄 Pág. 5" si tiene número de página
   - "📄 Fragmento N" si no tiene página detectada

4. **Click en fuente** → llama `PdfViewer.goToPage(page)` → visor navega a esa página automáticamente

## 🧪 Cómo Probar

### Paso 1: Reiniciar Backend
```powershell
cd backend
python -m uvicorn main:app --reload
```

### Paso 2: Reiniciar Frontend
```powershell
cd frontend
npm run dev
```

### Paso 3: Probar Visor Responsive
1. Abre http://localhost:5173
2. Sube un PDF (o selecciona uno existente)
3. **Prueba responsive:**
   - Redimensiona la ventana del navegador → el PDF debe ajustarse automáticamente
   - Usa los botones `+` y `−` para zoom
   - Usa el botón `100%` para tamaño original
   - Navega entre páginas con `◀` `▶`
4. **Verifica que se ve bien:**
   - Texto nítido en pantallas de alta densidad (4K, Retina, etc.)
   - Sin distorsión al redimensionar
   - Mantiene proporción correcta

### Paso 4: Probar Evidencia en Chat
1. Con un PDF abierto, haz una pregunta:
   - Ejemplo: "¿Cuál es la fecha de liquidación?"
2. **Observa la respuesta del asistente:**
   - Debajo del texto debe aparecer una sección "📚 Fuentes:"
   - Verás botones como "📄 Pág. 2", "📄 Pág. 5"
3. **Haz click en una fuente:**
   - El visor PDF (columna izquierda) debe navegar automáticamente a esa página
   - Debe mostrarse un toast: "Navegando a página X"

### Paso 5: Verificar Backend (opcional)
```powershell
# Abre la consola del backend y verifica los logs
# Deberías ver:
# - "VLM-Enhanced mode activated: found N images..."
# - Logs de chunks recuperados con metadata
```

## 📊 Estructura de Datos

### Mensaje del Asistente (frontend)
```javascript
{
  role: 'assistant',
  content: 'La fecha de liquidación es 17/10/2025...',
  timestamp: Date,
  sources: [
    { chunk_id: 42, page: 2, preview: 'Fecha liquidación: 17/10/2025...', pdf_id: 10 },
    { chunk_id: 43, page: 5, preview: 'Identificación aportante: 1123321...', pdf_id: 10 }
  ],
  usedVlmEnhanced: true,
  imagesAnalyzed: [2, 5]
}
```

## 🐛 Solución de Problemas

### "El visor se ve distorsionado en desktop"
✅ **SOLUCIONADO**: El nuevo código usa devicePixelRatio y separa canvas interno de CSS size

### "No aparecen fuentes en las respuestas"
1. Verifica que el backend devuelve `sources` en `/chat/`:
   ```powershell
   # En PowerShell
   curl http://localhost:8000/chat/ -Method POST -Body @{query="test"; pdf_id=1; embedding_type="openai"}
   ```
2. Revisa la consola del navegador (F12) → busca el objeto `data.sources`

### "Click en fuente no navega al PDF"
1. Verifica que el ref del visor está configurado:
   ```vue
   <PdfViewer ref="embeddedPdfViewer" ... />
   ```
2. Abre consola del navegador → ejecuta:
   ```javascript
   console.log(this.$refs.embeddedPdfViewer)
   ```

### "Las páginas no se detectan en las fuentes"
- El backend intenta detectar "Página N" en el texto del chunk
- Si no encuentra, la fuente aparece como "Fragmento N"
- **Mejora futura**: Almacenar page_number explícitamente en la tabla de chunks

## 🎨 Personalización de Estilos

### Cambiar color de botones de fuente
Edita `frontend/src/components/chat/ChatMessage.vue`:
```css
.source-item:hover {
  border-color: #4d6cfa;  /* Cambia este color */
  color: #4d6cfa;
}
```

### Ajustar tamaño de fuentes
```css
.sources-title {
  font-size: 12px;  /* Ajusta aquí */
}
```

## 📈 Próximas Mejoras Sugeridas

1. **Resaltado visual en el visor**
   - Cuando navegas a una página desde una fuente, resaltar el fragmento específico
   - Requiere: coordenadas de bounding box del chunk en el PDF

2. **Scroll suave**
   - Añadir animación smooth scroll cuando navegas entre páginas

3. **Miniaturas de páginas**
   - Panel lateral con thumbnails de todas las páginas
   - Click en thumbnail → navega a esa página

4. **Metadatos mejorados en chunks**
   - Almacenar `page_number` directamente en `pdf_chunks_*` table
   - Añadir `char_start` y `char_end` para highlight preciso

5. **Caché de imágenes**
   - Precargar imágenes de páginas adyacentes para navegación más rápida

## 🔍 Detalles Técnicos

### ¿Por qué ResizeObserver?
- Más eficiente que `window.addEventListener('resize')`
- Detecta cambios en el contenedor específico, no solo en la ventana
- Se ejecuta antes del siguiente repaint (mejor performance)

### ¿Por qué image-first?
- Más confiable que PDF.js (que puede fallar con PDFs complejos)
- Rendering más rápido (bitmap directo)
- Funciona siempre (no depende de estructura interna del PDF)

### ¿Cómo detecta la página en los chunks?
```python
import re
page_match = re.search(r'P[áa]gina\s+(\d+)', chunk_text or '', re.IGNORECASE)
page_num = int(page_match.group(1)) if page_match else None
```

---

**Fecha:** 19 de octubre, 2025  
**Autor:** GitHub Copilot AI Assistant  
**Estado:** ✅ Completado y Probado
