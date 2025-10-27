
import fastapi
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import shutil
import hashlib
import logging
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import PyPDF2
import requests
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()

import json
from pathlib import Path

# Simple JSON metadata store for folders, document metadata (favorites, tags, folder assignments)
METADATA_PATH = Path(__file__).resolve().parent / 'metadata_store.json'

def load_metadata():
    if not METADATA_PATH.exists():
        return {"folders": [], "documents": {}}
    # Try multiple encodings to avoid decode errors from files saved on Windows
    try:
        with open(METADATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except UnicodeDecodeError:
        try:
            with open(METADATA_PATH, 'r', encoding='latin-1') as f:
                return json.load(f)
        except Exception:
            # Fallback: read bytes and replace invalid chars
            with open(METADATA_PATH, 'rb') as f:
                text = f.read().decode('utf-8', errors='replace')
                return json.loads(text)

def save_metadata(data):
    with open(METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

app = FastAPI()

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure CORS. Prefer an explicit FRONTEND_ORIGIN in env for dev or prod usage.
# If FRONTEND_ORIGIN is not set, fall back to localhost:5173 (Vite dev server).
FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')
allow_origins = [o.strip() for o in FRONTEND_ORIGIN.split(',')] if FRONTEND_ORIGIN else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Authorization", "Content-Disposition"],
)

# Configuración de la base de datos
# Try to parse PG_CONN or use individual parameters to avoid encoding issues
PG_CONN = os.getenv("PG_CONN", "")
if PG_CONN and not any(ord(c) > 127 for c in PG_CONN):
    # Safe ASCII connection string
    conn = psycopg2.connect(PG_CONN)
else:
    # Use individual parameters to avoid encoding issues
    conn = psycopg2.connect(
        dbname=os.getenv("PG_DATABASE", "chatpdf"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", "postgres"),
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432")
    )
register_vector(conn)

# Ensure folders table and folder_id column exist
def init_db_schema():
    with conn.cursor() as cur:
        # create folders table if not exists
        cur.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        # add folder_id column to pdfs if it doesn't exist
        try:
            cur.execute("ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS folder_id INTEGER REFERENCES folders(id)")
        except Exception:
            # older Postgres versions might not support IF NOT EXISTS; try simple add and ignore error
            try:
                cur.execute("ALTER TABLE pdfs ADD COLUMN folder_id INTEGER REFERENCES folders(id)")
            except Exception:
                pass
        # create pdf_metadata table for favorites/tags/uploaded_at
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pdf_metadata (
                pdf_id INTEGER PRIMARY KEY REFERENCES pdfs(id) ON DELETE CASCADE,
                favorite BOOLEAN DEFAULT FALSE,
                tags JSONB DEFAULT '[]'::jsonb,
                uploaded_at TIMESTAMPTZ
            )
        ''')
        # add hash column to pdfs for duplicate detection
        try:
            cur.execute("ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS hash TEXT UNIQUE")
        except Exception:
            try:
                cur.execute("ALTER TABLE pdfs ADD COLUMN hash TEXT")
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS pdfs_hash_idx ON pdfs(hash)")
            except Exception:
                pass
        # create pdf_images table for storing extracted images
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pdf_images (
                id SERIAL PRIMARY KEY,
                pdf_id INTEGER REFERENCES pdfs(id) ON DELETE CASCADE,
                image_path TEXT NOT NULL,
                page_number INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        # Ensure caption column exists for storing per-image captions
        try:
            cur.execute("ALTER TABLE pdf_images ADD COLUMN IF NOT EXISTS caption TEXT")
        except Exception:
            try:
                cur.execute("ALTER TABLE pdf_images ADD COLUMN caption TEXT")
            except Exception:
                pass
        # Create table to store per-chunk bounding boxes (PDF coordinates)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pdf_chunk_spans (
                id SERIAL PRIMARY KEY,
                chunk_table TEXT,
                chunk_id INTEGER,
                pdf_id INTEGER REFERENCES pdfs(id) ON DELETE CASCADE,
                page_number INTEGER,
                x FLOAT,
                y FLOAT,
                width FLOAT,
                height FLOAT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        # Users and roles for basic RBAC
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, role_id)
            )
        ''')
        # System configuration table for global settings (default models, etc)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Conversations table - stores chat sessions per user per PDF or folder
        cur.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                pdf_id INTEGER REFERENCES pdfs(id) ON DELETE CASCADE,
                title TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Add folder_id column to conversations for folder-wide chats
        try:
            cur.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS folder_id INTEGER REFERENCES folders(id) ON DELETE CASCADE")
        except Exception:
            try:
                cur.execute("ALTER TABLE conversations ADD COLUMN folder_id INTEGER REFERENCES folders(id) ON DELETE CASCADE")
            except Exception:
                pass
        
        # Messages table - stores individual messages in conversations
        cur.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources JSONB,
                page_number INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Add user_id to pdfs table if not exists (to track who uploaded)
        try:
            cur.execute("ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)")
        except Exception:
            try:
                cur.execute("ALTER TABLE pdfs ADD COLUMN user_id INTEGER REFERENCES users(id)")
            except Exception:
                pass
        
        conn.commit()
        
        # Insert default system configuration
        cur.execute('''
            INSERT INTO system_config (key, value) VALUES 
            ('default_embedding_type', 'openai'),
            ('default_ollama_model', 'qwen3-embedding:0.6b'),
            ('default_openai_model', 'text-embedding-3-large')
            ON CONFLICT (key) DO NOTHING
        ''')
        conn.commit()

init_db_schema()

# Ensure a default admin user and role exist (use env vars to override)
try:
    DEFAULT_ADMIN_USERNAME = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
    DEFAULT_ADMIN_PASSWORD = os.getenv('DEFAULT_ADMIN_PASSWORD', 'adminpass')
    if DEFAULT_ADMIN_USERNAME and DEFAULT_ADMIN_PASSWORD:
        with conn.cursor() as cur:
            # ensure admin role
            cur.execute("INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", ('admin',))
            conn.commit()
            cur.execute("SELECT id FROM roles WHERE name = %s", ('admin',))
            rid = cur.fetchone()[0]

            # ensure user
            cur.execute("SELECT id FROM users WHERE username = %s", (DEFAULT_ADMIN_USERNAME,))
            ur = cur.fetchone()
            if not ur:
                ph = create_password_hash(DEFAULT_ADMIN_PASSWORD)
                cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id", (DEFAULT_ADMIN_USERNAME, ph))
                uid = cur.fetchone()[0]
                conn.commit()
                cur.execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (uid, rid))
                conn.commit()
                logger.info('Default admin user created: %s', DEFAULT_ADMIN_USERNAME)
            else:
                uid = ur[0]
                cur.execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (uid, rid))
                conn.commit()
                logger.info('Default admin user ensured and role assigned: %s', DEFAULT_ADMIN_USERNAME)
except Exception as e:
    logger.exception('Failed to ensure default admin user: %s', e)

# DB metadata helpers
def get_pdf_metadata_from_db(pdf_id):
    with conn.cursor() as cur:
        cur.execute("SELECT favorite, tags::text, uploaded_at FROM pdf_metadata WHERE pdf_id = %s", (pdf_id,))
        r = cur.fetchone()
        if not r:
            return {}
        favorite, tags_text, uploaded_at = r
        try:
            tags = json.loads(tags_text)
        except Exception:
            tags = []
        return {'favorite': bool(favorite), 'tags': tags, 'uploadedAt': uploaded_at}

def upsert_pdf_metadata_db(pdf_id, meta):
    with conn.cursor() as cur:
        # ensure uploaded_at is set if provided
        fav = meta.get('favorite')
        tags = json.dumps(meta.get('tags', [])) if 'tags' in meta else None
        uploaded = meta.get('uploadedAt')
        # try update
        cur.execute("SELECT 1 FROM pdf_metadata WHERE pdf_id = %s", (pdf_id,))
        exists = cur.fetchone()
        if exists:
            if fav is not None:
                cur.execute("UPDATE pdf_metadata SET favorite = %s WHERE pdf_id = %s", (fav, pdf_id))
            if tags is not None:
                cur.execute("UPDATE pdf_metadata SET tags = %s::jsonb WHERE pdf_id = %s", (tags, pdf_id))
            if uploaded:
                cur.execute("UPDATE pdf_metadata SET uploaded_at = %s WHERE pdf_id = %s", (uploaded, pdf_id))
        else:
            cur.execute("INSERT INTO pdf_metadata (pdf_id, favorite, tags, uploaded_at) VALUES (%s, %s, %s::jsonb, %s)", (pdf_id, fav if fav is not None else False, tags if tags is not None else '[]', uploaded))
        conn.commit()

from datetime import datetime
from fastapi import Depends
import jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# JWT / auth setup
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-change-me')
JWT_ALGO = 'HS256'
ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv('ACCESS_TOKEN_EXPIRE_SECONDS', '3600'))

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def create_password_hash(password: str) -> str:
    # bcrypt (used by pwd_ctx) has a 72-byte input limit and some platforms
    # expose backend import issues. To avoid runtime exceptions during user
    # registration, prefer a safer fallback:
    try:
        # If password bytes exceed bcrypt limit, skip trying bcrypt and
        # use pbkdf2_sha256 which supports arbitrary lengths.
        pw_bytes = password.encode('utf-8') if isinstance(password, str) else bytes(password)
        if len(pw_bytes) > 72:
            from passlib.hash import pbkdf2_sha256
            logger.info('create_password_hash: password >72 bytes, using pbkdf2_sha256')
            return pbkdf2_sha256.hash(password)

        # Try the primary (bcrypt) via passlib context
        return pwd_ctx.hash(password)
    except Exception as e:
        # Log and fallback to pbkdf2_sha256 for maximum compatibility
        logger.warning('create_password_hash: pwd_ctx.hash failed (%s). Falling back to pbkdf2_sha256.', e)
        try:
            from passlib.hash import pbkdf2_sha256
            return pbkdf2_sha256.hash(password)
        except Exception as e2:
            logger.exception('create_password_hash: pbkdf2_sha256 fallback also failed: %s', e2)
            # Re-raise the original exception to fail fast if both methods fail
            raise

def verify_password(password: str, hash: str) -> bool:
    # Primary path: let passlib handle verification (supports bcrypt)
    try:
        return pwd_ctx.verify(password, hash)
    except Exception as e:
        # Log the failure and try fallbacks. On some Windows installs the
        # underlying 'bcrypt' package may be present but not expose the
        # metadata passlib expects, causing an AttributeError during probing.
        logger.warning('pwd_ctx.verify raised exception: %s. Trying fallbacks.', e)

    # Fallback 1: try the bcrypt package directly if available
    try:
        import bcrypt as _bcrypt
        try:
            h = hash.encode('utf-8') if isinstance(hash, str) else hash
            pw = password.encode('utf-8')
            ok = _bcrypt.checkpw(pw, h)
            logger.info('verify_password: bcrypt.checkpw fallback used, result=%s', ok)
            return bool(ok)
        except Exception as e2:
            logger.warning('bcrypt.checkpw fallback failed: %s', e2)
    except Exception:
        # bcrypt not installed or failed to import
        pass

    # Fallback 2: try common passlib alternative (pbkdf2_sha256) in case
    # the stored hash uses a different scheme.
    try:
        from passlib.hash import pbkdf2_sha256
        try:
            ok2 = pbkdf2_sha256.verify(password, hash)
            logger.info('verify_password: pbkdf2_sha256 fallback used, result=%s', ok2)
            return bool(ok2)
        except Exception:
            pass
    except Exception:
        pass

    # If all methods fail, return False
    return False

def create_access_token(payload: dict, expire_in: int = ACCESS_TOKEN_EXPIRE_SECONDS) -> str:
    data = payload.copy()
    data['exp'] = datetime.utcnow().timestamp() + expire_in
    token = jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGO)
    return token

def decode_access_token(token: str) -> dict:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return data
    except Exception:
        return {}

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    token = creds.credentials
    data = decode_access_token(token)
    user_id = data.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail='Invalid token')
    with conn.cursor() as cur:
        cur.execute('SELECT id, username FROM users WHERE id = %s', (user_id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=401, detail='User not found')
        return {'id': r[0], 'username': r[1]}

def get_current_user_optional(creds: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    """Obtiene el usuario actual si está autenticado, o None si no lo está"""
    if not creds:
        return None
    try:
        token = creds.credentials
        data = decode_access_token(token)
        user_id = data.get('user_id')
        if not user_id:
            return None
        with conn.cursor() as cur:
            cur.execute('SELECT id, username FROM users WHERE id = %s', (user_id,))
            r = cur.fetchone()
            if not r:
                return None
            return {'id': r[0], 'username': r[1]}
    except Exception:
        return None

def require_role(role_name: str):
    def _dep(user = Depends(get_current_user)):
        uid = user.get('id')
        with conn.cursor() as cur:
            cur.execute('SELECT r.name FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = %s', (uid,))
            rows = [r[0] for r in cur.fetchall()]
            if role_name not in rows:
                raise HTTPException(status_code=403, detail='Insufficient role')
            return user
    return _dep


# Path to write a simple migration result summary (used by status endpoint)
MIGRATION_RESULT_PATH = Path(__file__).resolve().parent / 'migration_result.json'


def run_migration():
    """Run migration from metadata_store.json into DB and return a summary dict.
    This function will be used both at startup (when MIGRATE_METADATA=true) and
    via the POST /migration/run endpoint.
    """
    summary = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'folders_processed': 0,
        'folders_inserted': 0,
        'documents_processed': 0,
        'pdfs_folder_updated': 0,
        'pdf_metadata_upserted': 0,
        'notes': []
    }

    if not METADATA_PATH.exists():
        summary['notes'].append('metadata_store.json not found; nothing to migrate')
        # write result file
        try:
            with open(MIGRATION_RESULT_PATH, 'w', encoding='utf-8') as rf:
                json.dump(summary, rf, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return summary

    data = load_metadata()
    docs = data.get('documents', {})
    folders = data.get('folders', [])

    with conn.cursor() as cur:
        # insert folders if not present
        for f in folders:
            summary['folders_processed'] += 1
            try:
                # try to insert with provided id (ON CONFLICT DO NOTHING)
                cur.execute("INSERT INTO folders (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", (int(f.get('id')), f.get('name')))
                if cur.rowcount:
                    summary['folders_inserted'] += 1
                else:
                    # If no row affected, try a plain insert (fallback)
                    pass
            except Exception:
                try:
                    cur.execute("INSERT INTO folders (name) VALUES (%s)", (f.get('name'),))
                    if cur.rowcount:
                        summary['folders_inserted'] += 1
                except Exception:
                    summary['notes'].append(f"failed to insert folder: {f}")
        conn.commit()

        # migrate each document metadata
        for pdf_id_str, meta in docs.items():
            try:
                pid = int(pdf_id_str)
            except Exception:
                continue
            summary['documents_processed'] += 1
            # folderId
            folderId = meta.get('folderId')
            if folderId:
                try:
                    cur.execute("UPDATE pdfs SET folder_id = %s WHERE id = %s", (folderId, pid))
                    summary['pdfs_folder_updated'] += cur.rowcount if cur.rowcount else 0
                except Exception:
                    summary['notes'].append(f"failed to update folder for pdf {pid}")
            # other metadata: call upsert (we count it as processed)
            try:
                upsert_pdf_metadata_db(pid, {'favorite': meta.get('favorite', False), 'tags': meta.get('tags', []), 'uploadedAt': meta.get('uploadedAt')})
                summary['pdf_metadata_upserted'] += 1
            except Exception:
                summary['notes'].append(f"failed to upsert metadata for pdf {pid}")
        conn.commit()

    # write summary to file for status endpoint
    try:
        with open(MIGRATION_RESULT_PATH, 'w', encoding='utf-8') as rf:
            json.dump(summary, rf, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return summary


# Optional one-time migration from metadata_store.json into DB at startup
def migrate_metadata_to_db():
    if os.getenv('MIGRATE_METADATA', 'false').lower() != 'true':
        return
    # run the more featureful migration that produces a summary
    run_migration()


migrate_metadata_to_db()

def create_smart_chunks(text):
    """
    Crear chunks inteligentes dividiendo por párrafos/secciones en lugar de caracteres.
    Cada chunk conserva información de contexto (página, número de párrafo).
    Esto permite rastrear exactamente dónde en el PDF vino cada chunk.
    """
    import re
    
    chunks = []
    current_pos = 0
    chunk_size = 0
    max_chunk_size = 1500  # Chunks más grandes para mantener contexto
    
    # Dividir por líneas en blanco (párrafos)
    paragraphs = re.split(r'\n\s*\n', text)
    
    current_chunk = []
    chunk_paragraphs = []  # Rastrear # de párrafos en este chunk
    para_counter = 0
    
    for para_idx, paragraph in enumerate(paragraphs):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        
        # Detectar página del párrafo
        page_match = re.search(r'\[PAGINA_(\d+)\]', paragraph)
        page_num = page_match.group(1) if page_match else None
        
        para_counter += 1
        para_size = len(paragraph)
        
        # Si agregar este párrafo excede el límite, guardar chunk actual
        if current_chunk and chunk_size + para_size > max_chunk_size:
            chunk_text = '\n\n'.join(current_chunk)
            # Agregar metadata al chunk
            chunk_with_meta = f"[CHUNK_PARAGRAPHS_{para_counter-len(chunk_paragraphs)}-{para_counter}]\n{chunk_text}"
            chunks.append(chunk_with_meta)
            current_chunk = []
            chunk_size = 0
        
        # Agregar párrafo al chunk actual
        current_chunk.append(paragraph)
        chunk_size += para_size + 2  # +2 para "\n\n"
        chunk_paragraphs.append(para_idx)
    
    # Agregar último chunk
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        chunk_with_meta = f"[CHUNK_PARAGRAPHS_{para_counter-len(chunk_paragraphs)+1}-{para_counter}]\n{chunk_text}"
        chunks.append(chunk_with_meta)
    
    # Fallback: si no hay párrafos (texto muy corto), usar chunking simple
    if not chunks:
        chunks = [text[i:i+1500] for i in range(0, len(text), 1500)]
    
    logger.info(f"Created {len(chunks)} smart chunks from text")
    return chunks

def extract_text_from_pdf(file_path):
    """
    Extract text from PDF with PAGE MARKERS. Try PyPDF2 first; if extracted text is very small,
    fall back to OCR using pdf2image + pytesseract to handle image-based PDFs
    (scanned documents, math expressions embedded as images, etc.). We also
    attempt table extraction as a future enhancement (Camelot/Tabula), but
    that requires system dependencies and is optional.
    
    IMPORTANTE: Agrega marcadores de página "[PAGINA_N]" en el texto para tracking posterior.
    """
    text_parts = []
    current_page = 1
    
    # Primary extraction using PyPDF2 con información de página
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    # Agregar marcador de página al inicio
                    text_parts.append(f"[PAGINA_{page_num}]\n{page_text}")
                    current_page = page_num
    except Exception as e:
        logger.debug(f"PyPDF2 extraction failed: {e}")

    text = "\n\n".join(text_parts) if text_parts else ""

    # If little or no text extracted, try OCR on each page image
    if not text or len(text.strip()) < 50:
        try:
            from pdf2image import convert_from_path
            import pytesseract
            images = convert_from_path(file_path, dpi=200)
            ocr_text_parts = []
            for page_num, img in enumerate(images, start=1):
                try:
                    page_ocr_text = pytesseract.image_to_string(img, lang='eng')
                except Exception:
                    # try without specifying lang
                    try:
                        page_ocr_text = pytesseract.image_to_string(img)
                    except Exception:
                        page_ocr_text = ""
                
                if page_ocr_text.strip():
                    # Agregar marcador de página
                    ocr_text_parts.append(f"[PAGINA_{page_num}]\n{page_ocr_text}")
            
            ocr_text = "\n\n".join(ocr_text_parts) if ocr_text_parts else ""
            if ocr_text and len(ocr_text.strip()) > len(text):
                text = ocr_text
                logger.info(f"OCR extraction used, total pages: {len(ocr_text_parts)}")
        except Exception as e:
            logger.debug(f"OCR extraction failed: {e}")
            # pdf2image/pytesseract not available or failed — keep whatever text we have
            pass

    # NOTE: Table extraction with Camelot or Tabula could be integrated here
    # to parse tables into text (CSV/TSV) and append to `text`. Camelot needs
    # system dependencies (ghostscript, opencv) so we leave it as optional.

    logger.info(f"PDF text extraction complete. Total length: {len(text)} chars, page markers included")
    return text

def get_ollama_embedding(text, model="embeddinggemma:latest"):
    """Call the local Ollama-compatible server but prefer Qwen embedding model
    names present in the environment. The system lists `embeddinggemma:latest`
    as available; if Qwen embedding model is desired, set the model argument
    accordingly when calling this function.
    """
    response = requests.post(f"http://localhost:11434/api/embeddings", json={"model": model, "prompt": text})
    return response.json().get("embedding")


def generate_text_with_qwen(prompt, model="qwen3:4b"):
    """Synchronous generate call to local Ollama (Qwen). Returns plain text if available."""
    try:
        resp = requests.post("http://localhost:11434/api/generate", json={"model": model, "prompt": prompt})
        if resp.ok:
            data = resp.json()
            # Ollama generate responses commonly include 'response' field
            return data.get('response') or data.get('text') or ''
    except Exception:
        pass
    return ''


def extract_images_from_pdf(file_path, pdf_id=None):
    """Extract page images from a PDF using pdf2image (if available).
    If pdf_id is provided, saves images permanently in uploads/images/{pdf_id}/ directory.
    Returns a list of tuples: [(image_path, page_number), ...]
    """
    try:
        from pdf2image import convert_from_path
    except Exception as e:
        logger.warning("pdf2image not available: %s", e)
        return []
    images = []
    try:
        logger.info("Extracting images from PDF: %s", file_path)
        pil_images = convert_from_path(file_path, dpi=200)
        logger.info("Extracted %d page images", len(pil_images))
        
        # Determine where to save images
        if pdf_id:
            # Permanent storage in uploads/images/{pdf_id}/
            base_dir = Path(__file__).resolve().parent / 'uploads' / 'images' / str(pdf_id)
            base_dir.mkdir(parents=True, exist_ok=True)
            delete_after = False
        else:
            # Temporary storage (legacy behavior)
            base_dir = Path(tempfile.gettempdir())
            delete_after = True
        
        for i, img in enumerate(pil_images):
            if pdf_id:
                img_path = base_dir / f"page_{i+1}.png"
                img.save(str(img_path), format='PNG')
                images.append((str(img_path), i+1))  # Return tuple with page number
                logger.info("Saved page %d image permanently to: %s", i+1, img_path)
            else:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_page_{i}.png")
                img.save(tmp.name, format='PNG')
                images.append((tmp.name, i+1))
                logger.info("Saved page %d image to temp: %s", i+1, tmp.name)
    except Exception as e:
        logger.exception("Failed to extract images from PDF: %s", e)
        return []
    return images


def ocr_image_file(path):
    try:
        import pytesseract
        from PIL import Image
        # Configure Tesseract path for Windows
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        logger.info("Running OCR on image: %s", path)
        result = pytesseract.image_to_string(Image.open(path)) or ''
        logger.info("OCR result length: %d chars", len(result))
        return result
    except Exception as e:
        # Log as warning instead of exception to reduce noise
        logger.warning("OCR unavailable or failed for image %s: %s", path, str(e))
        return ''


def generate_image_with_qwen(image_path, prompt, model="qwen2.5vl:latest"):
    """Send an image to a local Ollama vision-capable model. Returns the generated text.
    Tries both /api/chat (preferred for vision) and /api/generate as fallback.
    """
    try:
        import base64
        logger.info("Generating caption for image: %s with model: %s", image_path, model)
        with open(image_path, 'rb') as f:
            b = f.read()
        b64 = base64.b64encode(b).decode('ascii')
        logger.info("Image encoded to base64, length: %d chars", len(b64))
        
        # Try /api/chat endpoint first (better for vision models in newer Ollama)
        try:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [b64]
                    }
                ],
                "stream": False
            }
            resp = requests.post("http://localhost:11434/api/chat", 
                               json=payload,
                               timeout=30)
            logger.info("Ollama /api/chat response status: %d", resp.status_code)
            if resp.ok:
                data = resp.json()
                result = data.get('message', {}).get('content', '') or data.get('response', '')
                if result:
                    logger.info("Caption generated via /api/chat, length: %d chars", len(result))
                    return result
            else:
                logger.warning("Ollama /api/chat failed: %s", resp.text[:500])
        except Exception as e:
            logger.warning("Failed /api/chat, trying fallback: %s", e)
        
        # Fallback: try /api/generate with markdown image tag
        combined_prompt = f"![image](data:image/png;base64,{b64})\n\n{prompt}"
        resp = requests.post("http://localhost:11434/api/generate", 
                           json={"model": model, "prompt": combined_prompt, "stream": False},
                           timeout=30)
        logger.info("Ollama /api/generate response status: %d", resp.status_code)
        if resp.ok:
            data = resp.json()
            result = data.get('response') or data.get('text') or ''
            logger.info("Caption generated via /api/generate, length: %d chars", len(result))
            return result
        else:
            logger.warning("Ollama /api/generate also failed: %s", resp.text[:500])
            
    except Exception as e:
        logger.exception("Failed to generate image caption: %s", e)
        return ''
    return ''


def generate_image_with_openai(image_path, prompt, openai_api_key, model="gpt-4o-mini"):
    """Generate a caption/analysis for an image using OpenAI chat endpoint by embedding
    the image as a data URI in a markdown image tag inside the user message. Falls back
    cleanly on errors and returns empty string on failure.
    """
    try:
        import base64
        from PIL import Image
        from io import BytesIO

        # Load and normalize image
        img = Image.open(image_path).convert('RGB')

        # Resize/compress thumbnail to reduce token cost
        max_dim = 512
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buf = BytesIO()
        img.save(buf, format='JPEG', quality=30, optimize=True)
        b = buf.getvalue()
        b64 = base64.b64encode(b).decode('ascii')

        # If still too large, skip OpenAI and let caller fallback
        if len(b64) > 100000:
            logger.warning("Compressed image base64 still large (%d chars). Skipping OpenAI caption.", len(b64))
            return ''

        user_content = f"![image](data:image/jpeg;base64,{b64})\n\n{prompt}"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an assistant that describes images succinctly and extracts any visible text, formulas or chart summaries."},
                {"role": "user", "content": user_content}
            ],
            "max_tokens": 300,
            "temperature": 0.0
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        text_snippet = ''
        try:
            text_snippet = resp.text[:2000]
        except Exception:
            text_snippet = '<unreadable response body>'

        if resp.ok:
            try:
                j = resp.json()
            except Exception:
                logger.warning("OpenAI caption: response ok but JSON decode failed; raw: %s", text_snippet)
                return ''

            content = ''
            if isinstance(j, dict):
                try:
                    content = j.get('choices', [])[0].get('message', {}).get('content', '')
                except Exception:
                    content = ''
                if not content:
                    try:
                        content = j.get('output_text') or j.get('output', '')
                    except Exception:
                        content = ''

            logger.info("OpenAI caption response keys: %s", list(j.keys()) if isinstance(j, dict) else type(j))
            if content:
                logger.info("OpenAI caption generated, length=%d", len(content))
                return content
            else:
                logger.warning("OpenAI caption: no textual content found in response; raw: %s", text_snippet)
        else:
            # If OpenAI returns a context length error, treat as non-fatal and fallback
            try:
                jerr = resp.json()
                err_code = jerr.get('error', {}).get('code')
                if err_code == 'context_length_exceeded':
                    logger.warning("OpenAI context length exceeded for image; skipping OpenAI caption. Raw: %s", text_snippet)
                    return ''
            except Exception:
                pass
            logger.warning("OpenAI caption request failed (status %s): %s", resp.status_code, text_snippet)

    except Exception as e:
        logger.exception("OpenAI caption generation failed: %s", e)

    return ''


@app.post('/admin/test_image_caption/')
async def admin_test_image_caption(image: UploadFile = File(...), provider: str = Form('openai')):
    """Upload a single image and return caption from OpenAI or Ollama. Useful for debugging.
    provider: 'openai' or 'ollama'
    """
    # save temp file
    try:
        data = await image.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image.filename)[1] or '.png') as tmp:
            tmp.write(data)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded image: {e}")

    result = {'provider': provider, 'filename': image.filename}
    try:
        prompt = "Describe this image briefly and highlight important visual elements. If there are any texts, formulas or charts, summarize them."
        if provider == 'openai':
            openai_api_key = os.getenv('OPENAI_API_KEY', '')
            if not openai_api_key:
                raise HTTPException(status_code=400, detail='OPENAI_API_KEY not configured')
            cap = generate_image_with_openai(tmp_path, prompt, openai_api_key)
            result['caption'] = cap
        else:
            cap = generate_image_with_qwen(tmp_path, prompt)
            result['caption'] = cap
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    return result

def get_qwen_embedding(text, api_key):
    url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "text-embedding-v2", "input": text}
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    if "output" not in data:
        print("Qwen API error response:", data)
        raise Exception(f"Qwen API error: {data}")
    return data["output"]["embeddings"][0]["embedding"]

# OpenAI Embedding
def get_openai_embedding(text, api_key, model="text-embedding-3-large"):
    url = "https://api.openai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": text, "dimensions": 1536}
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    if "data" not in data:
        print("OpenAI API error response:", data)
        raise Exception(f"OpenAI API error: {data}")
    embedding = data["data"][0]["embedding"]
    print(f"OpenAI embedding dimensions: {len(embedding)}")
    return embedding
def save_embedding(pdf_id, chunk, embedding, embedding_type):
    table_name = "pdf_chunks_ollama" if embedding_type == "ollama" else "pdf_chunks_openai"
    alt_table = "pdf_chunks_openai" if table_name == "pdf_chunks_ollama" else "pdf_chunks_ollama"
    try:
        with conn.cursor() as cur:
            cur.execute(f"INSERT INTO {table_name} (pdf_id, chunk, embedding) VALUES (%s, %s, %s) RETURNING id", (pdf_id, chunk, embedding))
            inserted_id = cur.fetchone()[0]
            conn.commit()
        return inserted_id
    except Exception as e:
        # If the error is due to vector dimension mismatch (Postgres/vector), try the alternate table
        msg = str(e).lower()
        if ('dimension' in msg) or ('expected' in msg) or ('vector' in msg) or ('expected' in msg and 'dimensions' in msg):
            logger.warning('save_embedding: dimension mismatch inserting into %s: %s. Trying alternate table %s', table_name, e, alt_table)
            try:
                # Rollback the failed transaction so we can attempt a new one
                try:
                    conn.rollback()
                except Exception:
                    pass
                with conn.cursor() as cur:
                    cur.execute(f"INSERT INTO {alt_table} (pdf_id, chunk, embedding) VALUES (%s, %s, %s) RETURNING id", (pdf_id, chunk, embedding))
                    inserted_id = cur.fetchone()[0]
                    conn.commit()
                # Update the pdfs.embedding_type so future searches use the correct table
                try:
                    new_provider = 'ollama' if alt_table == 'pdf_chunks_ollama' else 'openai'
                    with conn.cursor() as cur2:
                        cur2.execute('UPDATE pdfs SET embedding_type = %s WHERE id = %s', (new_provider, pdf_id))
                        conn.commit()
                    logger.info('save_embedding: updated pdfs.embedding_type for pdf_id=%s to %s', pdf_id, new_provider)
                except Exception:
                    pass
                return inserted_id
            except Exception as e2:
                logger.exception('save_embedding: failed inserting into alternate table %s: %s', alt_table, e2)
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
        else:
            # Not a dimension error — re-raise
            logger.exception('save_embedding: failed inserting into %s: %s', table_name, e)
            raise


def reindex_pdf_to_provider(pdf_id: int, target_provider: str, ollama_model: str = None, openai_model: str = None, max_chunks: int = 1000):
    """Attempt to (synchronously) generate embeddings for an existing PDF into the
    target_provider's chunk table so that searches with that provider will work.

    Strategy:
    - If the target table already contains chunks for this pdf, do nothing.
    - Otherwise, find source chunks from the other provider's table (or either table)
      and compute embeddings with the target provider, saving them into the target table.
    - To avoid long-running work, limit the number of chunks processed (default 1000).

    Raises an Exception on failure (no source chunks, missing API key for OpenAI,
    or if chunk count exceeds limit).
    Returns a dict with status and counts on success.
    """
    target = target_provider.lower() if isinstance(target_provider, str) else target_provider
    if target not in ('ollama', 'openai'):
        raise Exception(f'Unsupported target provider: {target_provider}')

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM pdf_chunks_ollama WHERE pdf_id = %s", (pdf_id,))
        ollama_cnt = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM pdf_chunks_openai WHERE pdf_id = %s", (pdf_id,))
        openai_cnt = cur.fetchone()[0]

    # If already indexed for target, nothing to do
    if target == 'ollama' and ollama_cnt and ollama_cnt > 0:
        return {'status': 'already_indexed', 'count': ollama_cnt, 'target': 'ollama'}
    if target == 'openai' and openai_cnt and openai_cnt > 0:
        return {'status': 'already_indexed', 'count': openai_cnt, 'target': 'openai'}

    # Determine where to get source chunks from (prefer the opposite table)
    source_rows = []
    source_provider = None
    with conn.cursor() as cur:
        if target == 'ollama' and openai_cnt and openai_cnt > 0:
            cur.execute("SELECT id, chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id", (pdf_id,))
            source_rows = cur.fetchall()
            source_provider = 'openai'
        elif target == 'openai' and ollama_cnt and ollama_cnt > 0:
            cur.execute("SELECT id, chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id", (pdf_id,))
            source_rows = cur.fetchall()
            source_provider = 'ollama'

    # If not found, try either table as fallback
    if not source_rows:
        with conn.cursor() as cur:
            cur.execute("SELECT id, chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id", (pdf_id,))
            s = cur.fetchall()
            if s:
                source_rows = s
                source_provider = 'ollama'
            else:
                cur.execute("SELECT id, chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id", (pdf_id,))
                s2 = cur.fetchall()
                if s2:
                    source_rows = s2
                    source_provider = 'openai'

    if not source_rows:
        raise Exception('No existing text chunks available to reindex for this PDF')

    if len(source_rows) > max_chunks:
        raise Exception(f'PDF has {len(source_rows)} chunks which exceeds the synchronous reindex limit ({max_chunks}). Consider re-uploading or increasing the limit.')

    # Determine model names
    if target == 'ollama':
        model = ollama_model or 'embeddinggemma:latest'
    else:
        model = openai_model or 'text-embedding-3-large'

    openai_api_key = os.getenv('OPENAI_API_KEY', '')

    processed = 0
    for _id, chunk in source_rows:
        try:
            if target == 'ollama':
                emb = get_ollama_embedding(chunk, model=model)
            else:
                if not openai_api_key:
                    raise Exception('OPENAI_API_KEY not configured; cannot generate OpenAI embeddings')
                emb = get_openai_embedding(chunk, openai_api_key, model=model)

            save_embedding(pdf_id, chunk, emb, target)
            processed += 1
        except Exception as e:
            logger.warning('reindex_pdf_to_provider: failed embedding chunk id=%s: %s', _id, e)
            # continue with rest; do not fail whole operation for a single chunk
            continue

    return {'status': 'reindexed', 'processed': processed, 'source': source_provider, 'target': target}


def reindex_pdf_from_file(pdf_id: int, target_provider: str, max_chunks: int = 500):
    """Re-ingest a stored PDF file and generate embeddings into the target provider.

    This is a best-effort synchronous reprocessing step used by `/chat/` when a
    PDF has no chunks stored. It will:
    - locate uploads/pdfs/{pdf_id}.pdf
    - extract text (PyPDF2 + OCR fallback)
    - extract images and generate OCR/captions (best-effort)
    - chunk the combined text, generate embeddings with the target provider,
      save them into the appropriate chunk table, and update pdfs.embedding_type
    - return a dict with 'processed' count

    Raises Exception on failure (missing file, no text, missing API keys for OpenAI, too many chunks).
    """
    pdf_path = Path(__file__).resolve().parent / 'uploads' / 'pdfs' / f"{pdf_id}.pdf"
    if not pdf_path.exists():
        raise Exception('Original PDF file not found on disk')

    # Extract text (will attempt OCR when necessary)
    text = extract_text_from_pdf(str(pdf_path))

    # If text is empty, attempt to extract images and run OCR/captions
    if not text or len(text.strip()) < 50:
        imgs = extract_images_from_pdf(str(pdf_path), pdf_id=pdf_id)
        ocr_texts = []
        captions = []
        openai_api_key = os.getenv('OPENAI_API_KEY', '')
        enable_ocr = True
        enable_vision = bool(openai_api_key)
        for img_path, page_num in imgs:
            # OCR
            if enable_ocr:
                try:
                    ocr_res = ocr_image_file(img_path)
                    if ocr_res and len(ocr_res.strip()) > 10:
                        ocr_texts.append(ocr_res)
                except Exception:
                    pass
            # Captions
            if enable_vision:
                try:
                    cap = ''
                    if openai_api_key:
                        cap = generate_image_with_openai(img_path, 'Describe this image briefly.', openai_api_key)
                    if not cap:
                        cap = generate_image_with_qwen(img_path, 'Describe this image briefly.')
                    if cap and len(cap.strip()) > 0:
                        captions.append(cap)
                except Exception:
                    pass

        if ocr_texts:
            text += "\n\n[OCR_EXTRACTED_TEXT]\n" + "\n".join(ocr_texts)
        if captions:
            text += "\n\n[IMAGE_CAPTIONS]\n" + "\n".join(captions)

    if not text or len(text.strip()) == 0:
        raise Exception('No textual content could be extracted from the PDF')

    # Chunk and embed
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    if len(chunks) > max_chunks:
        raise Exception(f'PDF chunk count {len(chunks)} exceeds synchronous limit {max_chunks}')

    # Determine model names
    ollama_model = None
    openai_model = None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'default_ollama_model'")
            r = cur.fetchone()
            ollama_model = r[0] if r and r[0] else None
            cur.execute("SELECT value FROM system_config WHERE key = 'default_openai_model'")
            r2 = cur.fetchone()
            openai_model = r2[0] if r2 and r2[0] else None
    except Exception:
        pass

    openai_api_key = os.getenv('OPENAI_API_KEY', '')
    processed = 0
    for chunk in chunks:
        try:
            if target_provider == 'ollama':
                emb = get_ollama_embedding(chunk, model=ollama_model) if ollama_model else get_ollama_embedding(chunk)
            else:
                if not openai_api_key:
                    raise Exception('OPENAI_API_KEY not configured; cannot generate OpenAI embeddings')
                emb = get_openai_embedding(chunk, openai_api_key, model=openai_model) if openai_model else get_openai_embedding(chunk, openai_api_key)

            save_embedding(pdf_id, chunk, emb, target_provider)
            processed += 1
        except Exception as e:
            logger.warning('reindex_pdf_from_file: failed embedding chunk: %s', e)
            continue

    # Update pdfs.embedding_type to reflect that it's now indexed for this provider
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE pdfs SET embedding_type = %s WHERE id = %s', (target_provider, pdf_id))
            conn.commit()
    except Exception:
        pass

    # If nothing was processed for the chosen target (e.g. dimension mismatch),
    # attempt the alternative provider automatically to improve success rate.
    if processed == 0:
        try:
            alt = 'openai' if target_provider == 'ollama' else 'ollama'
            logger.info('reindex_pdf_from_file: no chunks processed for %s, attempting alternative provider %s', target_provider, alt)
            alt_processed = 0
            # Re-run loop for alternative provider
            for chunk in chunks:
                try:
                    if alt == 'ollama':
                        emb = get_ollama_embedding(chunk, model=ollama_model) if ollama_model else get_ollama_embedding(chunk)
                    else:
                        if not openai_api_key:
                            raise Exception('OPENAI_API_KEY not configured; cannot generate OpenAI embeddings')
                        emb = get_openai_embedding(chunk, openai_api_key, model=openai_model) if openai_model else get_openai_embedding(chunk, openai_api_key)

                    save_embedding(pdf_id, chunk, emb, alt)
                    alt_processed += 1
                except Exception as e:
                    logger.warning('reindex_pdf_from_file (alt=%s): failed embedding chunk: %s', alt, e)
                    continue

            if alt_processed > 0:
                # Update embedding_type to alt so subsequent queries pick the right table
                try:
                    with conn.cursor() as cur:
                        cur.execute('UPDATE pdfs SET embedding_type = %s WHERE id = %s', (alt, pdf_id))
                        conn.commit()
                except Exception:
                    pass
                return {'status': 'reindexed_from_file', 'processed': alt_processed, 'target': alt}
        except Exception as e:
            logger.warning('reindex_pdf_from_file: alternative provider attempt failed: %s', e)

    return {'status': 'reindexed_from_file', 'processed': processed, 'target': target_provider}


def save_chunk_span(chunk_table, chunk_id, pdf_id, page_number, x, y, width, height):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pdf_chunk_spans (chunk_table, chunk_id, pdf_id, page_number, x, y, width, height) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (chunk_table, chunk_id, pdf_id, page_number, x, y, width, height)
        )
        conn.commit()

def create_pdf_entry(filename, embedding_type):
    # kept for backward compatibility
    return create_pdf_entry_with_hash(filename, embedding_type, None)


def create_pdf_entry_with_hash(filename, embedding_type, file_hash=None, user_id=None):
    with conn.cursor() as cur:
        if file_hash:
            cur.execute("INSERT INTO pdfs (filename, embedding_type, hash, user_id) VALUES (%s, %s, %s, %s) RETURNING id", (filename, embedding_type, file_hash, user_id))
        else:
            cur.execute("INSERT INTO pdfs (filename, embedding_type, user_id) VALUES (%s, %s, %s) RETURNING id", (filename, embedding_type, user_id))
        pdf_id = cur.fetchone()[0]
        conn.commit()
    return pdf_id


def map_chunk_to_bbox(pdf_path, chunk_text, inserted_chunk_id, chunk_table, pdf_id):
    """Attempt to map a chunk of text back to a page bbox using pdfplumber.
    Usa búsqueda exacta primero, luego fuzzy matching si es necesario.
    Guarda en pdf_chunk_spans para futuras búsquedas.
    """
    try:
        import pdfplumber
    except Exception as e:
        logger.warning(f"map_chunk_to_bbox: pdfplumber not available: {e}")
        return None

    try:
        # IMPORTANTE: Limpiar el chunk de marcadores internos ANTES de buscar
        import re
        cleaned_chunk = chunk_text or ""
        cleaned_chunk = re.sub(r'\[PAGINA_\d+\]\n?', '', cleaned_chunk)
        cleaned_chunk = re.sub(r'\[CHUNK_PARAGRAPHS_\d+-\d+\]', '', cleaned_chunk)
        cleaned_chunk = re.sub(r'\s+', ' ', cleaned_chunk).strip()
        
        # Extraer múltiples snippets de diferentes longitudes para búsqueda robusta
        # PRIORITARIO: Buscar el chunk COMPLETO primero, luego fragmentos
        snippets = []
        # Snippet muy largo (primeros 300 chars - preferimos matches más específicas)
        if len(cleaned_chunk) > 200:
            snippets.append((cleaned_chunk[:300].strip(), 'full'))
        # Snippet largo (primeros 150 chars)
        if len(cleaned_chunk) > 100:
            snippets.append((cleaned_chunk[:150].strip(), 'long'))
        # Snippet mediano (primeros 80 chars)
        if len(cleaned_chunk) > 50:
            snippets.append((cleaned_chunk[:80].strip(), 'medium'))
        # Snippet corto (primeros 40 chars)
        if len(cleaned_chunk) > 20:
            snippets.append((cleaned_chunk[:40].strip(), 'short'))
        
        if not snippets:
            logger.warning(f"map_chunk_to_bbox: No snippets generated for chunk_id={inserted_chunk_id} (empty or too short): {len(cleaned_chunk)} chars")
            return None

        logger.info(f"map_chunk_to_bbox: Attempting to find {len(snippets)} snippets for chunk_id={inserted_chunk_id}")
        logger.info(f"  Cleaned chunk (first 150): {cleaned_chunk[:150]}")
        logger.info(f"  Snippets to search: {[s[0][:50] for s in snippets]}")

        with pdfplumber.open(pdf_path) as doc:
            logger.info(f"map_chunk_to_bbox: PDF opened, {len(doc.pages)} pages")
            for pnum, page in enumerate(doc.pages, start=1):
                try:
                    words = page.extract_words(use_text_flow=True)
                except Exception as e:
                    logger.debug(f"  Page {pnum}: extract_words failed: {e}")
                    words = []
                
                # Si no hay palabras, intentar extracción de texto plano
                if not words:
                    try:
                        pg_text = (page.extract_text() or '').strip()
                    except Exception as e:
                        logger.debug(f"  Page {pnum}: extract_text failed: {e}")
                        pg_text = ''
                    
                    # Búsqueda en texto plano
                    for snippet, snippet_type in snippets:
                        if snippet.lower() in pg_text.lower():
                            # Aproximar bbox a página completa
                            w = page.width
                            h = page.height
                            save_chunk_span(chunk_table, inserted_chunk_id, pdf_id, pnum, 0.0, 0.0, w, h)
                            logger.info(f"map_chunk_to_bbox: Found chunk via text extract on page {pnum}")
                            return {'page': pnum, 'x': 0.0, 'y': 0.0, 'w': w, 'h': h}
                    continue

                # Construir texto unido de palabras
                texts = [w.get('text', '') for w in words]
                joined = ' '.join(texts)
                
                # Intentar búsqueda con cada snippet (de mayor a menor especificidad)
                for snippet, snippet_type in snippets:
                    # Búsqueda exacta primero
                    idx = joined.find(snippet)
                    if idx == -1:
                        # Búsqueda case-insensitive
                        idx = joined.lower().find(snippet.lower())
                    
                    if idx != -1:
                        logger.info(f"map_chunk_to_bbox: Found {snippet_type} snippet on page {pnum}, idx={idx}")
                        # Encontró coincidencia - mapear palabras
                        char_count = 0
                        start_i = None
                        end_i = None
                        
                        for i, t in enumerate(texts):
                            prev = char_count
                            char_count += len(t) + 1
                            if start_i is None and prev <= idx < char_count:
                                start_i = i
                            if start_i is not None and char_count >= idx + len(snippet):
                                end_i = i
                                break
                        
                        if start_i is None:
                            start_i = 0
                        if end_i is None:
                            end_i = min(len(texts)-1, start_i+10)
                        
                        # Agregar coordenadas de las palabras encontradas
                        try:
                            xs = [float(words[i].get('x0', 0)) for i in range(start_i, end_i+1) if i < len(words)]
                            ys = [float(words[i].get('top', 0)) for i in range(start_i, end_i+1) if i < len(words)]
                            x1s = [float(words[i].get('x1', 0)) for i in range(start_i, end_i+1) if i < len(words)]
                            y1s = [float(words[i].get('bottom', 0)) for i in range(start_i, end_i+1) if i < len(words)]
                            
                            if not xs:
                                logger.debug(f"  Page {pnum}: No coordinates found for words {start_i}-{end_i}")
                                continue
                            
                            x_min = min(xs)
                            y_min = min(ys)
                            x_max = max(x1s)
                            y_max = max(y1s)
                            width = max(0.0, x_max - x_min)
                            height = max(0.0, y_max - y_min)
                            
                            logger.info(f"map_chunk_to_bbox: Coordinates found: page={pnum}, x={x_min:.1f}, y={y_min:.1f}, w={width:.1f}, h={height:.1f}")
                            save_chunk_span(chunk_table, inserted_chunk_id, pdf_id, pnum, x_min, y_min, width, height)
                            logger.info(f"map_chunk_to_bbox: Mapped chunk on page {pnum} ({snippet_type} match)")
                            return {'page': pnum, 'x': x_min, 'y': y_min, 'w': width, 'h': height}
                        except Exception as e:
                            logger.debug(f"Error computing bbox on page {pnum}: {e}")
                            continue

    except Exception as e:
        logger.exception('map_chunk_to_bbox failed: %s', e)
    
    logger.warning(f"map_chunk_to_bbox: No bbox found for chunk_id={inserted_chunk_id} (first 100 chars): {chunk_text[:100]}")
    return None


def sanitize_suggested_questions_from_text(txt, max_q=3):
    """Sanitize raw LLM output and extract up to `max_q` clean question strings.
    Strategies (in order):
     - Parse a JSON array if present
     - Parse JSON objects and pull fields like response/thinking/text/content
     - Extract explicit question-like lines (lines containing '?')
     - Regex-extract sentence fragments that end with '?'
     - Fallback to the first non-empty lines truncated and ensured to end with '?'
    """
    import re, json

    def clean_question(s):
        if not s:
            return ''
        s = str(s)
        # Unescape common escapes
        s = s.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', ' ').replace('\\"', '"')
        # Remove stray braces or leading/trailing quotes
        s = s.strip().strip('"').strip('\'')
        # Remove leading numbering/bullets
        s = re.sub(r'^[\s\d\)\.\-•]+', '', s)
        # Collapse whitespace
        s = re.sub(r'\s+', ' ', s).strip()
        if not s:
            return ''
        # If there are multiple questions in the same string, keep up to the last '?'
        if '?' in s:
            s = s[:s.rfind('?')+1]
        # Ensure it ends with a question mark
        if not s.endswith('?'):
            s = s + '?'
        # Discard too-short results (avoid returning just punctuation)
        core = re.sub(r'[^\wÁÉÍÓÚÜÑáéíóúüñ]', '', s)
        if len(core) < 3:
            return ''
        return s

    def extract_question_lines(text):
        lines = [l.strip() for l in re.split(r'[\r\n]+', text) if l.strip()]
        qs = []
        for l in lines:
            if l.endswith('?') or l.startswith('¿') or '?' in l:
                q = clean_question(l)
                if q and q not in qs:
                    qs.append(q)
                if len(qs) >= max_q:
                    break
        # Try sentence-level regex if none found
        if not qs:
            matches = re.findall(r'([A-ZÁÉÍÓÚÑ][^\?\.!\n]{10,}?\?)', text)
            for m in matches:
                q = clean_question(m)
                if q and q not in qs:
                    qs.append(q)
                if len(qs) >= max_q:
                    break
        return qs

    if not txt:
        return []

    # 1) Try to find a JSON array in the text
    try:
        m = re.search(r'(\[\s\S]{0,2000}?\])', txt, re.S)
        if m:
            try:
                arr = json.loads(m.group(1))
                if isinstance(arr, list):
                    qs = [clean_question(x) for x in arr if isinstance(x, str)]
                    qs = [q for q in qs if q]
                    if qs:
                        return qs[:max_q]
            except Exception:
                pass
    except Exception:
        pass

    # 2) Try to find JSON objects and extract common fields
    try:
        objs = re.findall(r'(\{[\s\S]{0,2000}?\})', txt)
        collected = []
        for o in objs:
            try:
                jo = json.loads(o)
                for k in ('response', 'thinking', 'text', 'content', 'message'):
                    v = jo.get(k) if isinstance(jo, dict) else None
                    if isinstance(v, str) and v.strip():
                        qs = extract_question_lines(v)
                        for q in qs:
                            if q not in collected:
                                collected.append(q)
                                if len(collected) >= max_q:
                                    break
                if len(collected) >= max_q:
                    break
            except Exception:
                continue
        if collected:
            return collected[:max_q]
    except Exception:
        pass

    # 3) Extract question-like lines directly from the raw text
    qlines = extract_question_lines(txt)
    if qlines:
        return qlines[:max_q]

    # 4) Fallback: regex for fragments ending with '?'
    try:
        frag = re.findall(r'([^\r\n]{10,}?\?)', txt)
        out = []
        for f in frag:
            q = clean_question(f)
            if q and q not in out:
                out.append(q)
            if len(out) >= max_q:
                break
        if out:
            return out[:max_q]
    except Exception:
        pass

    # 5) Last resort: use first non-empty lines and ensure they are short and end with '?'
    lines = [l.strip() for l in re.split(r'[\r\n]+', txt) if l.strip()]
    out = []
    for l in lines:
        q = clean_question(l)
        if q:
            out.append(q)
        if len(out) >= max_q:
            break
    return out[:max_q]

def get_pdf_embedding_type(pdf_id):
    with conn.cursor() as cur:
        cur.execute("SELECT embedding_type FROM pdfs WHERE id = %s", (pdf_id,))
        result = cur.fetchone()
        if not result or not result[0]:
            return None
        try:
            val = str(result[0]).strip().lower()
        except Exception:
            return None
        # Treat various sentinel/invalid values as None
        if val in ('', 'undefined', 'null', 'none'):
            return None
        # Map common names to normalized provider identifiers
        if 'openai' in val:
            return 'openai'
        if 'ollama' in val or 'qwen' in val or 'embedding' in val:
            return 'ollama'
        # Default: return the raw (lowercased) value
        return val

def search_similar_chunks(pdf_id, query_embedding, embedding_type, top_k=3):
    """Return both chunks and metadata for provenance/evidence tracking.
    Returns: (chunks_list, sources_list) where sources contain id, chunk text, page hints.
    MEJORADO: Extrae información exacta de párrafo/sección.
    """
    table_name = "pdf_chunks_ollama" if embedding_type == "ollama" else "pdf_chunks_openai"
    with conn.cursor() as cur:
        # Convertir la lista de Python a string de vector de PostgreSQL
        vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
        cur.execute(f"""
            SELECT id, chunk FROM {table_name}
            WHERE pdf_id = %s
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, (pdf_id, vector_str, top_k))
        results = cur.fetchall()
    
    chunks = []
    sources = []
    import re
    
    for chunk_id, chunk_text in results:
        chunks.append(chunk_text)
        
        # MEJORADO: Extraer información precisa del chunk
        # 1. Detectar número de párrafo si existe
        para_match = re.search(r'\[CHUNK_PARAGRAPHS_(\d+)-(\d+)\]', chunk_text or '')
        para_start = para_match.group(1) if para_match else None
        para_end = para_match.group(2) if para_match else None
        
        # 2. Remover marcadores y limpiar texto
        preview_text = chunk_text or ""
        preview_text = re.sub(r'\[CHUNK_PARAGRAPHS_\d+-\d+\]', '', preview_text)
        preview_text = re.sub(r'\[PAGINA_\d+\]\n?', '', preview_text)
        preview_text = re.sub(r'\s+', ' ', preview_text).strip()
        
        # 3. Extraer primeras 2-3 oraciones para preview
        sentences = re.split(r'(?<=[.!?])\s+', preview_text)
        preview_parts = []
        char_count = 0
        for sentence in sentences:
            if char_count + len(sentence) > 280:
                break
            preview_parts.append(sentence)
            char_count += len(sentence) + 1
        
        preview = ' '.join(preview_parts).strip()
        if len(preview) == 0:
            preview = preview_text[:200].strip()
        
        if len(preview_text) > len(preview):
            preview += '...'
        
        # 4. Agregar información de párrafo si existe
        location_info = ""
        if para_start and para_end:
            if para_start == para_end:
                location_info = f"Párrafo {para_start}"
            else:
                location_info = f"Párrafos {para_start}-{para_end}"
        
        # PRIORIDAD 1: Buscar en pdf_chunk_spans (datos guardados durante la carga del PDF)
        page_num = None
        span = None
        try:
            with conn.cursor() as cur2:
                cur2.execute(
                    "SELECT page_number, x, y, width, height FROM pdf_chunk_spans WHERE chunk_id = %s AND pdf_id = %s ORDER BY id LIMIT 1", 
                    (chunk_id, pdf_id)
                )
                rspan = cur2.fetchone()
                if rspan:
                    page_num = int(rspan[0])
                    span = {'page': rspan[0], 'x': float(rspan[1]), 'y': float(rspan[2]), 'w': float(rspan[3]), 'h': float(rspan[4])}
        except Exception as e:
            logger.debug(f"Error fetching chunk span for chunk_id={chunk_id}: {e}")
        
        # PRIORIDAD 2: Buscar marcador [PAGINA_N] en el chunk
        if page_num is None:
            page_match = re.search(r'\[PAGINA_(\d+)\]', chunk_text or '')
            if page_match:
                page_num = int(page_match.group(1))
        
        # PRIORIDAD 3: Regex fallback
        if page_num is None:
            patterns = [
                r'P[áa]gina\s+(\d+)',
                r'Page\s+(\d+)',
                r'pág\.\s*(\d+)',
                r'p\.\s*(\d+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, chunk_text or '', re.IGNORECASE)
                if match:
                    page_num = int(match.group(1))
                    break
        
        # Construir preview con ubicación exacta
        if location_info:
            full_preview = f"[Pág. {page_num}, {location_info}]\n{preview}" if page_num else f"[{location_info}]\n{preview}"
        else:
            full_preview = preview
        
        src = {
            'chunk_id': chunk_id,
            'page': page_num,
            'preview': full_preview,
            'location': location_info,  # Nueva: información de párrafo
            'pdf_id': pdf_id
        }
        if span:
            src['coords'] = span
        sources.append(src)
    
    # OPTIMIZACIÓN: Reordenar sources para que los que tengan coords aparezcan primero
    # Esto mejora la probabilidad de que el LLM cite una source con coordenadas
    sources_with_coords = [s for s in sources if s.get('coords')]
    sources_without_coords = [s for s in sources if not s.get('coords')]
    sources = sources_with_coords + sources_without_coords
    
    return chunks, sources

@app.post("/upload_pdf/")
async def upload_pdf(pdf: UploadFile = File(...), embedding_type: str = Form(None), file_hash: str = Form(None), user = Depends(get_current_user)):
    # If no embedding_type provided, use system default
    if not embedding_type or embedding_type.strip() == '':
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM system_config WHERE key = 'default_embedding_type'")
                row = cur.fetchone()
                embedding_type = row[0] if row and row[0] else 'openai'
                logger.info(f"Using embedding_type from config: {embedding_type}")
        except Exception as e:
            logger.warning(f"Could not read system_config, defaulting to 'openai': {e}")
            embedding_type = 'openai'
    
    # Validate embedding_type
    if embedding_type not in ['openai', 'ollama']:
        logger.error(f"Invalid embedding_type received: '{embedding_type}'")
        embedding_type = 'openai'
    
    logger.info(f"Final embedding_type for upload: {embedding_type}, user_id={user['id']}")
    
    # Read bytes and compute hash if not provided
    file_bytes = await pdf.read()
    computed_hash = hashlib.sha256(file_bytes).hexdigest()
    file_hash = file_hash or computed_hash

    # Server-side duplicate check by hash (preferred)
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM pdfs WHERE hash = %s", (file_hash,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"PDF with same content already exists")

    # Fallback: if hash column wasn't populated historically, also check filename
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM pdfs WHERE filename = %s", (pdf.filename,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"PDF with filename '{pdf.filename}' already exists")

    # Heuristic: some existing PDFs might store a hash computed from extracted
    # chunks (or have NULL). Compare the incoming binary file hash against a
    # chunk-derived fingerprint for existing PDFs. If matched, update the
    # existing row to the binary file hash (so future checks are direct) and
    # reject the upload.
    with conn.cursor() as cur_all:
        cur_all.execute("SELECT id, hash FROM pdfs")
        all_rows = cur_all.fetchall()

    for existing_id, stored_hash in all_rows:
        # If stored_hash equals the incoming binary hash, we already handled it
        if stored_hash == file_hash:
            raise HTTPException(status_code=409, detail=f"PDF with same content already exists")

        # Compute chunk-based fingerprint and compare to incoming binary hash
        chunks = []
        with conn.cursor() as cur2:
            try:
                cur2.execute("SELECT chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id", (existing_id,))
                chunks += [r[0] for r in cur2.fetchall()]
            except Exception:
                pass
            try:
                cur2.execute("SELECT chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id", (existing_id,))
                chunks += [r[0] for r in cur2.fetchall()]
            except Exception:
                pass

        if not chunks:
            continue

        combined = ''.join([c or '' for c in chunks])
        chunk_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        if chunk_hash == file_hash:
            # Update the stored hash to the binary file hash for faster future checks
            with conn.cursor() as cur3:
                cur3.execute("UPDATE pdfs SET hash = %s WHERE id = %s", (file_hash, existing_id))
                conn.commit()
            raise HTTPException(status_code=409, detail=f"PDF with same content already exists (matched by stored text chunks)")

    # write temp file for text extraction
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    
    text = extract_text_from_pdf(tmp_path)
    logger.info("Extracted base text length: %d chars", len(text))
    
    # Create PDF entry first to get pdf_id for image storage
    pdf_id = create_pdf_entry_with_hash(pdf.filename, embedding_type, file_hash, user_id=user['id'])
    logger.info("Created PDF entry with id=%d, user_id=%d", pdf_id, user['id'])
    # Persist the uploaded PDF immediately so it is always available for viewing
    try:
        uploads_pdf_dir = Path(__file__).resolve().parent / 'uploads' / 'pdfs'
        uploads_pdf_dir.mkdir(parents=True, exist_ok=True)
        dest_pdf = uploads_pdf_dir / f"{pdf_id}.pdf"
        # Use copy2 so the original temp file remains available for processing
        shutil.copy2(tmp_path, str(dest_pdf))
        logger.info("Copied uploaded PDF to permanent storage: %s", dest_pdf)
    except Exception as e:
        logger.exception("Failed to persist uploaded PDF to uploads/pdfs: %s", e)
    
    # Extract images and produce OCR + vision captions, append to text
    try:
        # Pass pdf_id to save images permanently
        image_data = extract_images_from_pdf(tmp_path, pdf_id=pdf_id)
        logger.info("Found %d images in PDF", len(image_data))

        ocr_texts = []
        captions = []
        # Check if OCR and vision captions are enabled via env var. If OPENAI_API_KEY
        # is present, prefer OpenAI captions automatically (they are higher quality)
        openai_api_key = os.getenv('OPENAI_API_KEY', '')
        enable_ocr = os.getenv('ENABLE_OCR', 'true').lower() == 'true'  # OCR enabled by default
        enable_vision = os.getenv('ENABLE_VISION_CAPTIONS', 'false').lower() == 'true' or bool(openai_api_key)
        logger.info("Vision captions enabled=%s; OPENAI_API_KEY present=%s", enable_vision, bool(openai_api_key))

        for image_path, page_num in image_data:
            # Save image reference to database
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO pdf_images (pdf_id, image_path, page_number) VALUES (%s, %s, %s)",
                    (pdf_id, image_path, page_num)
                )
                conn.commit()
            logger.info("Saved image reference for page %d: %s", page_num, image_path)
            
            # Only run OCR if enabled and Tesseract is available
            if enable_ocr:
                ocr_result = ocr_image_file(image_path)
                if ocr_result and len(ocr_result.strip()) > 10:
                    ocr_texts.append(ocr_result)
                    logger.info("OCR text added: %d chars", len(ocr_result))

            # Only generate captions if enabled (can be slow / costly with many images)
            if enable_vision:
                try:
                    caption_prompt = "Describe this image briefly and highlight important visual elements. If there are any texts, formulas or charts, summarize them."
                    cap = ''
                    # Prefer OpenAI Vision (chat completions with embedded data URI) when API key is present
                    if openai_api_key:
                        cap = generate_image_with_openai(image_path, caption_prompt, openai_api_key)
                        if cap:
                            logger.info("Caption produced by OpenAI for image: %s", image_path)
                    # Fallback to local Ollama if OpenAI not configured or failed
                    if not cap:
                        cap = generate_image_with_qwen(image_path, caption_prompt)
                        if cap:
                            logger.info("Caption produced by Ollama for image: %s", image_path)

                    if cap and len(cap.strip()) > 0:
                        captions.append(cap)
                        logger.info("Caption added: %d chars", len(cap))
                except Exception as e:
                    logger.warning("Skipping caption for image due to error: %s", e)

        if ocr_texts:
            text += "\n\n[OCR_EXTRACTED_TEXT]\n" + "\n".join(ocr_texts)
            logger.info("Appended OCR texts to document")
        if captions:
            text += "\n\n[IMAGE_CAPTIONS]\n" + "\n".join(captions)
            logger.info("Appended image captions to document")
        logger.info("Final text length after images: %d chars", len(text))
    except Exception as e:
        logger.exception("Error processing images: %s", e)
    # Cleanup: remove the working temp file if it still exists (we already copied it)
    try:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            logger.info("Removed temporary upload file: %s", tmp_path)
    except Exception:
        # Best-effort cleanup; do not fail the upload if removal fails
        logger.warning("Failed to remove temporary upload file: %s", tmp_path)

    # MEJORADO: Dividir texto en chunks por párrafos/secciones, no por caracteres
    # Esto permite rastrear exactamente de dónde vino cada chunk
    chunks = create_smart_chunks(text)

    # Get specific model from config if using ollama
    ollama_model = "embeddinggemma:latest"
    openai_model = "text-embedding-3-large"
    
    if embedding_type == "ollama":
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'default_ollama_model'")
            row = cur.fetchone()
            if row and row[0]:
                ollama_model = row[0]
    elif embedding_type == "openai":
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'default_openai_model'")
            row = cur.fetchone()
            if row and row[0]:
                openai_model = row[0]

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    for chunk in chunks:
        print("Chunk type:", type(chunk), "Chunk length:", len(chunk))
        if embedding_type == "ollama":
            embedding = get_ollama_embedding(chunk, model=ollama_model)
        elif embedding_type == "openai":
            embedding = get_openai_embedding(chunk, openai_api_key, model=openai_model)
        else:
            raise Exception("Tipo de embedding no soportado")
        try:
            inserted_chunk_id = save_embedding(pdf_id, chunk, embedding, embedding_type)
        except Exception:
            inserted_chunk_id = None
        try:
            pdf_path = str(Path(__file__).resolve().parent / 'uploads' / 'pdfs' / f"{pdf_id}.pdf")
            if inserted_chunk_id and os.path.exists(pdf_path):
                map_chunk_to_bbox(pdf_path, chunk, inserted_chunk_id, 'pdf_chunks_ollama' if embedding_type=='ollama' else 'pdf_chunks_openai', pdf_id)
        except Exception as e:
            logger.exception(f"Error in map_chunk_to_bbox call: {e}")

    return {"filename": pdf.filename, "embedding_type": embedding_type, "pdf_id": pdf_id}


@app.post('/upload_pdfs/')
async def upload_pdfs(pdfs: list[UploadFile] = File(...), embedding_type: str = Form(None), file_hashes: list[str] | None = Form(None)):
    """Accept multiple PDF uploads in one request. Returns per-file results.
    Expect multiple 'pdf' files and optionally multiple 'file_hashes' values in the same order.
    """
    # If no embedding_type provided, use system default
    if not embedding_type or embedding_type.strip() == '':
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM system_config WHERE key = 'default_embedding_type'")
                row = cur.fetchone()
                embedding_type = row[0] if row and row[0] else 'openai'
                logger.info(f"Using embedding_type from config (batch): {embedding_type}")
        except Exception as e:
            logger.warning(f"Could not read system_config (batch), defaulting to 'openai': {e}")
            embedding_type = 'openai'
    
    # Validate embedding_type
    if embedding_type not in ['openai', 'ollama']:
        logger.error(f"Invalid embedding_type received (batch): '{embedding_type}'")
        embedding_type = 'openai'
    
    logger.info(f"Final embedding_type for batch upload: {embedding_type}")
    
    results = []
    # Normalize file_hashes
    if file_hashes is None:
        file_hashes = [None] * len(pdfs)

    for idx, pdf in enumerate(pdfs):
        fh = None
        if idx < len(file_hashes):
            fh = file_hashes[idx]

        try:
            file_bytes = await pdf.read()
            computed_hash = hashlib.sha256(file_bytes).hexdigest()
            file_hash = fh or computed_hash

            # Quick check by hash
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM pdfs WHERE hash = %s", (file_hash,))
                if cur.fetchone():
                    results.append({'filename': pdf.filename, 'status': 'duplicate', 'reason': 'hash_exists'})
                    continue

            # Filename check
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM pdfs WHERE filename = %s", (pdf.filename,))
                if cur.fetchone():
                    results.append({'filename': pdf.filename, 'status': 'duplicate', 'reason': 'filename_exists'})
                    continue

            # Chunk-based heuristic for existing rows
            with conn.cursor() as cur_all:
                cur_all.execute("SELECT id, hash FROM pdfs")
                all_rows = cur_all.fetchall()

            matched_existing = False
            for existing_id, stored_hash in all_rows:
                if stored_hash == file_hash:
                    matched_existing = True
                    break

                # compute chunk hash
                chunks = []
                with conn.cursor() as cur2:
                    try:
                        cur2.execute("SELECT chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id", (existing_id,))
                        chunks += [r[0] for r in cur2.fetchall()]
                    except Exception:
                        pass
                    try:
                        cur2.execute("SELECT chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id", (existing_id,))
                        chunks += [r[0] for r in cur2.fetchall()]
                    except Exception:
                        pass

                if not chunks:
                    continue

                combined = ''.join([c or '' for c in chunks])
                chunk_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
                if chunk_hash == file_hash:
                    # update existing row
                    with conn.cursor() as cur3:
                        cur3.execute("UPDATE pdfs SET hash = %s WHERE id = %s", (file_hash, existing_id))
                        conn.commit()
                    matched_existing = True
                    break

            if matched_existing:
                results.append({'filename': pdf.filename, 'status': 'duplicate', 'reason': 'matched_by_chunks'})
                continue

            # If new, create entry and save embeddings
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            text = extract_text_from_pdf(tmp_path)
            logger.info("PDF '%s': Extracted base text length: %d chars", pdf.filename, len(text))
            
            # Create PDF entry first to get pdf_id for image storage
            pdf_id = create_pdf_entry_with_hash(pdf.filename, embedding_type, file_hash)
            logger.info("PDF '%s': Created PDF entry with id=%d", pdf.filename, pdf_id)
            
            # Extract images and produce OCR + vision captions, append to text
            try:
                # Pass pdf_id to save images permanently
                image_data = extract_images_from_pdf(tmp_path, pdf_id=pdf_id)
                logger.info("PDF '%s': Found %d images", pdf.filename, len(image_data))
                ocr_texts = []
                captions = []
                openai_api_key = os.getenv('OPENAI_API_KEY', '')
                enable_ocr = os.getenv('ENABLE_OCR', 'true').lower() == 'true'  # OCR enabled by default
                enable_vision = os.getenv('ENABLE_VISION_CAPTIONS', 'false').lower() == 'true' or bool(openai_api_key)
                logger.info("Vision captions enabled=%s; OPENAI_API_KEY present=%s", enable_vision, bool(openai_api_key))
                
                for image_path, page_num in image_data:
                    # Save image reference to database
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO pdf_images (pdf_id, image_path, page_number) VALUES (%s, %s, %s)",
                            (pdf_id, image_path, page_num)
                        )
                        conn.commit()
                    logger.info("PDF '%s': Saved image reference for page %d: %s", pdf.filename, page_num, image_path)
                    
                    # Only run OCR if enabled and Tesseract is available
                    if enable_ocr:
                        ocr_result = ocr_image_file(image_path)
                        if ocr_result and len(ocr_result.strip()) > 10:
                            ocr_texts.append(ocr_result)
                            logger.info("OCR text added: %d chars", len(ocr_result))
                    
                    # Only generate captions if enabled (can be slow/costly with many images)
                    if enable_vision:
                        try:
                            caption_prompt = "Describe this image briefly and highlight important visual elements. If there are any texts, formulas or charts, summarize them."
                            cap = ''
                            if openai_api_key:
                                cap = generate_image_with_openai(image_path, caption_prompt, openai_api_key)
                                if cap:
                                    logger.info("Caption produced by OpenAI for image: %s", image_path)
                            if not cap:
                                cap = generate_image_with_qwen(image_path, caption_prompt)
                                if cap:
                                    logger.info("Caption produced by Ollama for image: %s", image_path)
                            if cap and len(cap.strip()) > 0:
                                captions.append(cap)
                                logger.info("Caption added: %d chars", len(cap))
                        except Exception as e:
                            logger.warning("Skipping caption for image due to error: %s", e)
                
                if ocr_texts:
                    text += "\n\n[OCR_EXTRACTED_TEXT]\n" + "\n".join(ocr_texts)
                    logger.info("PDF '%s': Appended OCR texts", pdf.filename)
                if captions:
                    text += "\n\n[IMAGE_CAPTIONS]\n" + "\n".join(captions)
                    logger.info("PDF '%s': Appended image captions", pdf.filename)
                logger.info("PDF '%s': Final text length: %d chars", pdf.filename, len(text))
            except Exception as e:
                logger.exception("PDF '%s': Error processing images: %s", pdf.filename, e)
                # Move the temp PDF to permanent storage for later viewing
                try:
                    uploads_pdf_dir = Path(__file__).resolve().parent / 'uploads' / 'pdfs'
                    uploads_pdf_dir.mkdir(parents=True, exist_ok=True)
                    dest_pdf = uploads_pdf_dir / f"{pdf_id}.pdf"
                    shutil.move(tmp_path, str(dest_pdf))
                    logger.info("Saved uploaded PDF permanently to: %s", dest_pdf)
                except Exception:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

            chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]

            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            for chunk in chunks:
                if embedding_type == "ollama":
                    embedding = get_ollama_embedding(chunk)
                elif embedding_type == "openai":
                    embedding = get_openai_embedding(chunk, openai_api_key)
                else:
                    raise Exception("Tipo de embedding no soportado")
                # Save embedding and get the inserted chunk id
                try:
                    inserted_chunk_id = save_embedding(pdf_id, chunk, embedding, embedding_type)
                except Exception:
                    inserted_chunk_id = None

                # Try to map the chunk to a bbox in the saved PDF (best-effort)
                try:
                    pdf_path = str(Path(__file__).resolve().parent / 'uploads' / 'pdfs' / f"{pdf_id}.pdf")
                    if inserted_chunk_id and os.path.exists(pdf_path):
                        map_chunk_to_bbox(pdf_path, chunk, inserted_chunk_id, 'pdf_chunks_ollama' if embedding_type=='ollama' else 'pdf_chunks_openai', pdf_id)
                except Exception as e:
                    logger.exception(f"Error in map_chunk_to_bbox call (reindex): {e}")

            results.append({'filename': pdf.filename, 'status': 'uploaded', 'pdf_id': pdf_id})
        except HTTPException as he:
            results.append({'filename': pdf.filename, 'status': 'error', 'detail': str(he.detail)})
        except Exception as e:
            results.append({'filename': pdf.filename, 'status': 'error', 'detail': str(e)})

    return {'results': results}


@app.post('/upload_folder/')
async def upload_folder(
    folder_name: str = Form(...),
    pdfs: list[UploadFile] = File(...),
    embedding_type: str = Form(None),
    user = Depends(get_current_user)
):
    """Upload a complete folder with multiple PDFs.
    Creates a new folder and uploads all PDFs to it.
    Returns folder_id and upload results.
    """
    # If no embedding_type provided, use system default
    if not embedding_type or embedding_type.strip() == '':
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM system_config WHERE key = 'default_embedding_type'")
                row = cur.fetchone()
                embedding_type = row[0] if row and row[0] else 'openai'
                logger.info(f"upload_folder: using embedding_type from config: {embedding_type}")
        except Exception as e:
            logger.warning(f"upload_folder: could not read system_config, defaulting to 'openai': {e}")
            embedding_type = 'openai'
    
    # Validate embedding_type
    if embedding_type not in ['openai', 'ollama']:
        logger.error(f"upload_folder: invalid embedding_type received: '{embedding_type}'")
        embedding_type = 'openai'
    
    logger.info(f"upload_folder: folder_name={folder_name}, pdfs_count={len(pdfs)}, embedding_type={embedding_type}")
    
    # Filter only PDF files
    pdf_files = [pdf for pdf in pdfs if pdf.filename.lower().endswith('.pdf')]
    
    if len(pdf_files) == 0:
        raise HTTPException(status_code=400, detail="No se encontraron archivos PDF en la carpeta")
    
    # Create folder first
    folder_id = None
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO folders (name) VALUES (%s) RETURNING id", (folder_name,))
            folder_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"upload_folder: created folder with id={folder_id}")
    except Exception as e:
        logger.exception(f"upload_folder: failed to create folder: {e}")
        raise HTTPException(status_code=500, detail=f"Error al crear la carpeta: {str(e)}")
    
    # Now upload all PDFs to this folder
    results = []
    uploaded_count = 0
    
    logger.info(f"upload_folder: Starting to process {len(pdf_files)} PDF files")
    for idx, pdf in enumerate(pdf_files):
        logger.info(f"upload_folder: Processing file {idx+1}/{len(pdf_files)}: {pdf.filename}")
        try:
            file_bytes = await pdf.read()
            computed_hash = hashlib.sha256(file_bytes).hexdigest()
            logger.info(f"upload_folder: File '{pdf.filename}' hash: {computed_hash}")
            
            # Quick check by hash (skip duplicates)
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM pdfs WHERE hash = %s", (computed_hash,))
                existing = cur.fetchone()
                if existing:
                    logger.warning(f"upload_folder: File '{pdf.filename}' is duplicate (hash exists as pdf_id={existing[0]})")
                    results.append({'filename': pdf.filename, 'status': 'duplicate', 'reason': 'hash_exists'})
                    continue
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            
            text = extract_text_from_pdf(tmp_path)
            logger.info(f"upload_folder: PDF '{pdf.filename}': Extracted text length: {len(text)} chars")
            
            # Create PDF entry with folder_id and user_id
            pdf_id = None
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO pdfs (filename, embedding_type, hash, folder_id, user_id) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (pdf.filename, embedding_type, computed_hash, folder_id, user['id'])
                )
                pdf_id = cur.fetchone()[0]
                conn.commit()
            logger.info(f"upload_folder: PDF '{pdf.filename}': Created entry with id={pdf_id}")
            
            # Extract images and process
            try:
                image_data = extract_images_from_pdf(tmp_path, pdf_id=pdf_id)
                logger.info(f"upload_folder: PDF '{pdf.filename}': Found {len(image_data)} images")
                
                ocr_texts = []
                captions = []
                openai_api_key = os.getenv('OPENAI_API_KEY', '')
                enable_ocr = os.getenv('ENABLE_OCR', 'true').lower() == 'true'
                enable_vision = os.getenv('ENABLE_VISION_CAPTIONS', 'false').lower() == 'true' or bool(openai_api_key)
                
                for image_path, page_num in image_data:
                    # Save image reference
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO pdf_images (pdf_id, image_path, page_number) VALUES (%s, %s, %s)",
                            (pdf_id, image_path, page_num)
                        )
                        conn.commit()
                    
                    # OCR
                    if enable_ocr:
                        ocr_result = ocr_image_file(image_path)
                        if ocr_result and len(ocr_result.strip()) > 10:
                            ocr_texts.append(ocr_result)
                    
                    # Vision captions
                    if enable_vision:
                        try:
                            caption_prompt = "Describe this image briefly and highlight important visual elements. If there are any texts, formulas or charts, summarize them."
                            cap = ''
                            if openai_api_key:
                                cap = generate_image_with_openai(image_path, caption_prompt, openai_api_key)
                            if not cap:
                                cap = generate_image_with_qwen(image_path, caption_prompt)
                            if cap and len(cap.strip()) > 0:
                                captions.append(cap)
                        except Exception as e:
                            logger.warning(f"upload_folder: skipping caption for image: {e}")
                
                if ocr_texts:
                    text += "\n\n[OCR_EXTRACTED_TEXT]\n" + "\n".join(ocr_texts)
                if captions:
                    text += "\n\n[IMAGE_CAPTIONS]\n" + "\n".join(captions)
                
                logger.info(f"upload_folder: PDF '{pdf.filename}': Final text length: {len(text)} chars")
            except Exception as e:
                logger.exception(f"upload_folder: error processing images for '{pdf.filename}': {e}")
            
            # Save PDF file
            try:
                uploads_pdf_dir = Path(__file__).resolve().parent / 'uploads' / 'pdfs'
                uploads_pdf_dir.mkdir(parents=True, exist_ok=True)
                dest_pdf = uploads_pdf_dir / f"{pdf_id}.pdf"
                shutil.move(tmp_path, str(dest_pdf))
                logger.info(f"upload_folder: saved PDF permanently to: {dest_pdf}")
            except Exception as e:
                logger.warning(f"upload_folder: failed to save PDF file: {e}")
                try:
                    os.remove(tmp_path)
                except:
                    pass
            
            # Create chunks and embeddings
            chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            
            for chunk in chunks:
                if embedding_type == "ollama":
                    embedding = get_ollama_embedding(chunk)
                elif embedding_type == "openai":
                    embedding = get_openai_embedding(chunk, openai_api_key)
                else:
                    raise Exception("Tipo de embedding no soportado")
                
                try:
                    inserted_chunk_id = save_embedding(pdf_id, chunk, embedding, embedding_type)
                except Exception:
                    inserted_chunk_id = None
                
                # Map chunk to bbox
                try:
                    pdf_path = str(Path(__file__).resolve().parent / 'uploads' / 'pdfs' / f"{pdf_id}.pdf")
                    if inserted_chunk_id and os.path.exists(pdf_path):
                        map_chunk_to_bbox(pdf_path, chunk, inserted_chunk_id, 
                                        'pdf_chunks_ollama' if embedding_type=='ollama' else 'pdf_chunks_openai', 
                                        pdf_id)
                except Exception as e:
                    logger.warning(f"upload_folder: error in map_chunk_to_bbox: {e}")
            
            results.append({'filename': pdf.filename, 'status': 'uploaded', 'pdf_id': pdf_id})
            uploaded_count += 1
            logger.info(f"upload_folder: Successfully uploaded '{pdf.filename}' as pdf_id={pdf_id}")
            
        except Exception as e:
            logger.exception(f"upload_folder: error uploading '{pdf.filename}': {e}")
            results.append({'filename': pdf.filename, 'status': 'error', 'detail': str(e)})
    
    logger.info(f"upload_folder: Completed processing. Uploaded {uploaded_count} of {len(pdf_files)} files")
    return {
        'folder_id': folder_id,
        'folder_name': folder_name,
        'uploaded_count': uploaded_count,
        'total_files': len(pdf_files),
        'results': results
    }


@app.post("/chat/")
async def chat(query: str = Form(...), pdf_id: int = Form(...), embedding_type: str = Form("ollama"), include_suggestions: str = Form('0'), conversation_id: int = Form(None), user = Depends(get_current_user)):
    # Normalize embedding_type and fallback to system default when necessary
    try:
        if embedding_type is None:
            embedding_type = ''
        embedding_type = embedding_type.strip().lower()
    except Exception:
        embedding_type = 'ollama'

    # If empty or unknown, read system default
    if embedding_type not in ('ollama', 'openai'):
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM system_config WHERE key = 'default_embedding_type'")
                row = cur.fetchone()
                embedding_type = (row[0].strip().lower() if row and row[0] else 'openai')
                logger.info(f"chat: using system default embedding_type={embedding_type}")
        except Exception as e:
            logger.warning(f"chat: failed reading system_config default, defaulting to openai: {e}")
            embedding_type = 'openai'

    # Determine specific model names from config (do this early so we can reindex if needed)
    ollama_model = None
    openai_model = None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'default_ollama_model'")
            r = cur.fetchone()
            ollama_model = r[0] if r and r[0] else None
            cur.execute("SELECT value FROM system_config WHERE key = 'default_openai_model'")
            r2 = cur.fetchone()
            openai_model = r2[0] if r2 and r2[0] else None
    except Exception:
        # Best-effort: continue with None and let embedding callers use their defaults
        ollama_model = ollama_model or None
        openai_model = openai_model or None

    # Verificar que el tipo de embedding coincida con el del PDF (si existe)
    pdf_embedding_type = get_pdf_embedding_type(pdf_id)
    if pdf_embedding_type and pdf_embedding_type.lower() != embedding_type:
        logger.info("chat: provider mismatch (pdf=%s, requested=%s). Attempting best-effort reindex.", pdf_embedding_type, embedding_type)
        # Try to reindex the PDF into the requested provider's chunk table.
        try:
            re_res = reindex_pdf_to_provider(pdf_id, embedding_type, ollama_model=ollama_model, openai_model=openai_model, max_chunks=500)
            logger.info("chat: reindex result: %s", re_res)
            # If reindex processed some chunks, proceed using requested provider
            if re_res.get('processed', 0) > 0 or re_res.get('status') == 'already_indexed':
                logger.info("chat: reindex successful or already indexed; continuing with provider %s", embedding_type)
                # continue as normal
            else:
                # Reindex didn't produce usable chunks; fall back to original provider to avoid hard error
                logger.warning("chat: reindex did not produce chunks; falling back to PDF's original provider: %s", pdf_embedding_type)
                embedding_type = pdf_embedding_type
        except Exception as e:
            # If reindex fails (missing API keys, too many chunks, etc), log and fall back to original provider
            logger.exception("chat: reindex attempt failed: %s", e)
            embedding_type = pdf_embedding_type

    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    # Compute query embedding using the correct provider and model. Be resilient:
    # - Try the requested provider first
    # - If it fails, attempt to use the PDF's original provider (pdf_embedding_type)
    # - If both fail, return an informative 500 error
    query_embedding = None
    embedding_provider_used = None

    def _gen_ollama(q):
        if ollama_model:
            return get_ollama_embedding(q, model=ollama_model)
        return get_ollama_embedding(q)

    def _gen_openai(q):
        if openai_model:
            return get_openai_embedding(q, openai_api_key, model=openai_model)
        return get_openai_embedding(q, openai_api_key)

    last_exc = None
    if embedding_type == 'ollama':
        try:
            query_embedding = _gen_ollama(query)
            embedding_provider_used = 'ollama'
        except Exception as e:
            logger.exception('chat: Ollama embedding generation failed: %s', e)
            last_exc = e
    elif embedding_type == 'openai':
        try:
            query_embedding = _gen_openai(query)
            embedding_provider_used = 'openai'
        except Exception as e:
            logger.exception('chat: OpenAI embedding generation failed: %s', e)
            last_exc = e
    else:
        logger.error("chat: unsupported embedding_type '%s'", embedding_type)
        raise fastapi.HTTPException(status_code=400, detail=f"Tipo de embedding no soportado: {embedding_type}")

    # If initial attempt failed, try the PDF's original provider as fallback
    if query_embedding is None and pdf_embedding_type and pdf_embedding_type != embedding_type:
        try:
            logger.info('chat: attempting fallback embedding generation using PDF original provider: %s', pdf_embedding_type)
            if pdf_embedding_type == 'ollama':
                query_embedding = _gen_ollama(query)
                embedding_provider_used = 'ollama'
            elif pdf_embedding_type == 'openai':
                query_embedding = _gen_openai(query)
                embedding_provider_used = 'openai'
        except Exception as e:
            logger.exception('chat: fallback embedding generation failed: %s', e)
            last_exc = e

    if query_embedding is None:
        # Nothing worked — return a clear 500 error advising the admin to check services
        logger.error('chat: failed to generate query embedding for pdf_id=%s using requested (%s) and pdf original (%s). Last error: %s', pdf_id, embedding_type, pdf_embedding_type, last_exc)
        raise fastapi.HTTPException(status_code=500, detail='Failed to generate embeddings for the query. Check Ollama service status and OPENAI_API_KEY configuration.')
    try:
        chunks, sources = search_similar_chunks(pdf_id, query_embedding, embedding_type)
    except Exception as e:
        logger.exception("Error searching similar chunks for pdf_id=%s", pdf_id)
        raise HTTPException(status_code=500, detail=f"Error retrieving context for PDF: {e}")

    # NUEVO: Construir contexto con identificadores únicos para citación
    # Cada chunk obtiene un ID [SOURCE_N] que el LLM puede usar para citar
    import re
    context_with_sources = []
    source_map = {}  # Mapear ID de SOURCE a índice en sources list
    
    for idx, chunk in enumerate(chunks):
        source_id = f"SOURCE_{idx + 1}"
        source_map[source_id] = idx
        
        # Remover marcadores internos
        cleaned = chunk
        cleaned = re.sub(r'\[PAGINA_\d+\]\n?', '', cleaned)
        cleaned = re.sub(r'\[CHUNK_PARAGRAPHS_\d+-\d+\]', '', cleaned)
        cleaned = cleaned.strip()
        
        # Agregar identificador de fuente al inicio del chunk
        context_with_sources.append(f"[{source_id}]\n{cleaned}")
    
    context = "\n\n---\n\n".join(context_with_sources)

    # Metadata to return so frontend can show whether vision was used
    used_vlm_enhanced = False
    images_analyzed = []

    # If context is empty, include a helpful diagnostic message
    if not context.strip():
        # collect some diagnostics
        with conn.cursor() as cur:
            cur.execute("SELECT hash, embedding_type FROM pdfs WHERE id = %s", (pdf_id,))
            pdf_row = cur.fetchone()
        pdf_hash = pdf_row[0] if pdf_row else None
        pdf_embed_type = pdf_row[1] if pdf_row else None
        # count chunks available
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pdf_chunks_ollama WHERE pdf_id = %s", (pdf_id,))
            ollama_chunks = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM pdf_chunks_openai WHERE pdf_id = %s", (pdf_id,))
            openai_chunks = cur.fetchone()[0]
        detail = {
            'message': 'No context available for this PDF. It may have failed ingestion or OCR/captions were empty.',
            'pdf_id': pdf_id,
            'hash': pdf_hash,
            'pdf_embedding_type': pdf_embed_type,
            'chunks_ollama': ollama_chunks,
            'chunks_openai': openai_chunks
        }
        logger.info("Empty context diagnostics: %s", detail)

        # If there are no chunks for either provider, attempt a synchronous reindex from the stored PDF file
        try:
            if (ollama_chunks == 0 and openai_chunks == 0):
                logger.info('chat: no chunks found for pdf_id=%s, attempting reindex from stored PDF file into provider=%s', pdf_id, embedding_type)
                re_res = reindex_pdf_from_file(pdf_id, embedding_type, max_chunks=500)
                logger.info('chat: reindex_from_file result: %s', re_res)
                # If we generated some chunks, retry the search
                if re_res.get('processed', 0) > 0:
                        # If reindex produced chunks, switch the in-memory embedding_type
                        # to the provider we just reindexed into and regenerate the
                        # query embedding using that provider before searching.
                        new_target = re_res.get('target')
                        if new_target:
                            embedding_type = new_target
                            logger.info('chat: switching embedding_type to %s after reindex', embedding_type)
                            try:
                                # regenerate query embedding for the new provider
                                if embedding_type == 'ollama':
                                    query_embedding = _gen_ollama(query)
                                else:
                                    query_embedding = _gen_openai(query)
                            except Exception as e:
                                logger.exception('chat: failed to regenerate query embedding after reindex: %s', e)
                                query_embedding = None

                        try:
                            if query_embedding is not None:
                                chunks, sources = search_similar_chunks(pdf_id, query_embedding, embedding_type)
                                context = "\n".join(chunks)
                            else:
                                logger.warning('chat: no query_embedding available to search after reindex')
                        except Exception as e:
                            logger.exception('chat: failed search after reindex: %s', e)
        except Exception as e:
            logger.warning('chat: reindex_from_file attempt failed: %s', e)

        if not context.strip():
            # After attempting reindex, still no context available
            raise fastapi.HTTPException(status_code=404, detail=detail)

    # VLM-Enhanced Query Mode: Check if PDF has images stored in DB
    # If yes, load them and their stored captions for summaries. We'll also support
    # selective image loading when the user mentions a specific page number ("página 2").
    pdf_images = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT image_path, page_number, caption FROM pdf_images WHERE pdf_id = %s ORDER BY page_number",
            (pdf_id,)
        )
        pdf_images = cur.fetchall()

    if pdf_images:
        logger.info("VLM-Enhanced mode activated: found %d images for pdf_id=%d", len(pdf_images), pdf_id)
    else:
        logger.info("No images found for pdf_id=%d, using text-only mode", pdf_id)

    # Build a short per-page summary block so captions aren't lost in chunk boundaries
    image_summaries = []
    for img_path, page_num, caption in pdf_images:
        short = (caption or '').strip()
        if not short:
            short = f"Imagen en página {page_num}: sin descripción disponible."
        image_summaries.append(f"Página {page_num}: {short}")
    if image_summaries:
        # Prepend an explicit marker so models see per-page summaries early
        context = "\n[IMAGE_SUMMARIES]\n" + "\n".join(image_summaries) + "\n\n" + context

    # Detect explicit page reference in the user's query (e.g. "página 2")
    import re
    page_refs = re.findall(r"p(?:á|a)gina\s*(\d+)", query.lower())
    requested_pages = [int(p) for p in page_refs] if page_refs else []

    # Select which images to attach to the VLM request.
    if requested_pages:
        # Filter images to only those requested by page number
        selected_images = [t for t in pdf_images if t[1] in requested_pages]
        if not selected_images:
            # If requested pages not found, fall back to first 3 images
            selected_images = pdf_images[:3]
    else:
        # Default: first 5 images (each tuple is (path, page, caption))
        selected_images = pdf_images[:5]

    # Prepare a list to track which images we actually attach to the VLM call
    images_added = []

    # Generar respuesta en lenguaje natural usando el modelo seleccionado
    if embedding_type == "ollama":
        # Usar Qwen (disponible en Ollama) para generar respuesta
        ollama_model = "qwen3:4b"  # modelo conversacional instalado en Ollama
        prompt = f"""Eres un asistente experto en análisis de documentos PDF. Tu tarea es responder preguntas citando OBLIGATORIAMENTE las fuentes.

REGLAS IMPERATIVAS DE CITACIÓN (NO PUEDES OMITIRLAS):
1. CADA vez que mencionas un dato, hecho o información, DEBES citar inmediatamente [SOURCE_N]
2. Formato EXACTO: "La temperatura es 25°C [SOURCE_1]" o "El proceso incluye 3 pasos [SOURCE_2]"
3. Si usas información de múltiples fuentes: "El resultado es X [SOURCE_1] y también Y [SOURCE_3]"
4. NUNCA respondas sin citar. Si mencionas algo, cita de dónde lo sacaste
5. Las citas van INMEDIATAMENTE después de la información, NO al final del párrafo

FORMATO DE RESPUESTA:
- Responde de forma DIRECTA y CONCISA
- NO hagas introducciones largas
- Cita CADA dato con [SOURCE_N] justo después del dato
- Si no estás seguro de qué fuente usar, usa [SOURCE_1]

Pregunta: {query}

Contexto con referencias (cada bloque empieza con [SOURCE_N]):
{context}"""
        ollama_response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": ollama_model, "prompt": prompt},
            stream=True
        )
        # Procesar respuesta streaming línea por línea
        fragments = []
        for line in ollama_response.iter_lines():
            if line:
                try:
                    data = line.decode("utf-8")
                    import json
                    obj = json.loads(data)
                    if "response" in obj:
                        fragments.append(obj["response"])
                except Exception:
                    continue
        answer = "".join(fragments).strip()
        if not answer:
            answer = "No se pudo generar respuesta."
    elif embedding_type == "openai":
        # VLM-Enhanced Mode: If we have images, use OpenAI Vision to analyze them directly
        if pdf_images and openai_api_key:
            logger.info("Using VLM-enhanced mode with %d images", len(pdf_images))
            used_vlm_enhanced = True
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
            
            # Build messages array with text + images
            system_prompt = """Eres un asistente experto en análisis de documentos PDF.

REGLAS IMPERATIVAS DE CITACIÓN (OBLIGATORIAS - NO PUEDES OMITIRLAS):
1. CADA dato, hecho o información DEBE ir seguido INMEDIATAMENTE de [SOURCE_N]
2. Formato EXACTO obligatorio:
   ✓ CORRECTO: "La temperatura es 25°C [SOURCE_1]"
   ✓ CORRECTO: "El costo es $100 [SOURCE_1] y el plazo es 30 días [SOURCE_2]"
   ✗ INCORRECTO: "Según el documento, la temperatura es 25°C" (sin citar)
   ✗ INCORRECTO: "La temperatura es 25°C. [SOURCE_1]" (punto antes de cita)
3. Las citas van INMEDIATAMENTE después del dato (sin punto antes)
4. Si usas información de múltiples fuentes, cita cada una donde corresponde
5. NUNCA respondas sin citar. Si dudas, usa [SOURCE_1]
6. NO uses frases genéricas como "según el documento" - cita la fuente específica

FORMATO DE RESPUESTA:
- Responde DIRECTAMENTE al punto sin rodeos
- NO hagas introducciones innecesarias
- Cada información → cita inmediata con [SOURCE_N]
- Si preguntan "¿cuál es X?", responde "X es Y [SOURCE_N]"

Tienes acceso a:
1. Texto extraído marcado con [SOURCE_N] al inicio de cada bloque
2. Imágenes del documento para análisis visual

Usa ambos para responder con PRECISIÓN y CITACIONES OBLIGATORIAS."""
            
            # Create user message with text context
            user_content = [
                {"type": "text", "text": f"Pregunta: {query}\n\nContexto del documento con referencias:\n{context}"}
            ]
            
            # Add images (from selected_images which respects page refs)
            for img_path, page_num, img_caption in selected_images:
                if os.path.exists(img_path):
                    try:
                        # Read and encode image
                        import base64
                        with open(img_path, 'rb') as img_file:
                            img_data = img_file.read()
                        base64_img = base64.b64encode(img_data).decode('utf-8')
                        
                        # Skip if image is too large
                        if len(base64_img) < 100000:  # ~100KB limit
                            user_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_img}",
                                    "detail": "high"
                                },
                                "meta": {"page": page_num, "caption": (img_caption or '')[:200]}
                            })
                            images_added.append(page_num)
                            logger.info("Added image from page %d to VLM request", page_num)
                    except Exception as e:
                        logger.warning("Failed to load image %s: %s", img_path, e)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            payload = {
                "model": "gpt-4o-mini",  # Vision-capable model
                "messages": messages,
                "max_tokens": 500
            }
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                answer = response.json()["choices"][0]["message"]["content"]
                logger.info("VLM-enhanced response generated successfully")
            except Exception as e:
                logger.exception("VLM-enhanced mode failed: %s", e)
                # If VLM failed, mark it and fallback to text-only mode
                used_vlm_enhanced = False
                logger.warning("Falling back to text-only mode after VLM failure")
                # Fallback to text-only mode
                answer = "Error al procesar imágenes. Intenta de nuevo."
        else:
            # Text-only mode (legacy)
            logger.info("Using text-only mode (no images or no API key)")
            openai_model = "gpt-4-turbo"  # Cambia por el modelo que prefieras
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
            system_prompt = """Eres un asistente experto en análisis de documentos PDF.

REGLAS IMPERATIVAS DE CITACIÓN (OBLIGATORIAS):
1. CADA dato DEBE ir seguido INMEDIATAMENTE de [SOURCE_N]
2. Formato EXACTO:
   ✓ "El valor es 42 [SOURCE_1]"
   ✓ "El proceso tiene 5 pasos [SOURCE_2] y dura 3 días [SOURCE_1]"
   ✗ NUNCA sin citar: "El valor es 42" (incorrecto)
3. Cita INMEDIATAMENTE después del dato (sin punto antes)
4. Si usas múltiples fuentes, cita cada una en su lugar
5. NUNCA omitas citas. Si dudas, usa [SOURCE_1]

FORMATO:
- Responde DIRECTO al punto
- NO introducciones largas
- Cada dato → [SOURCE_N] inmediato

El contexto incluye texto extraído marcado con [SOURCE_N] al inicio de cada bloque."""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Pregunta: {query}\n\nContexto del documento con referencias:\n{context}"}
            ]
            payload = {"model": openai_model, "messages": messages, "max_tokens": 256}
            
            try:
                openai_response = requests.post(url, json=payload, headers=headers, timeout=30)
                openai_response.raise_for_status()
                answer = openai_response.json().get("choices", [{}])[0].get("message", {}).get("content", "No se pudo generar respuesta.")
            except Exception as e:
                logger.exception("OpenAI text-only mode failed: %s", e)
                answer = "Error al generar respuesta. Intenta de nuevo."
    else:
        answer = "No se pudo generar respuesta."

    # Final metadata: images_analyzed are the pages we actually attached
    images_analyzed = images_added

    suggested_questions = []
    # Only generate suggestions when explicitly requested (frontend will ask only for first assistant response)
    do_suggest = str(include_suggestions).lower() in ('1', 'true', 'yes', 'y')
    if do_suggest:
        try:
            followup_prompt = (
                f"Genera tres preguntas de seguimiento concisas en español basadas en la siguiente respuesta y la pregunta original."
                f" Devuelve únicamente una lista clara de preguntas (una por línea o un JSON array).\n\nRespuesta: {answer}\nPregunta original: {query}\n\nEjemplo output (JSON): [\"Pregunta 1\", \"Pregunta 2\", \"Pregunta 3\"]"
            )

            txt = ''
            # Choose provider order based on how the PDF was uploaded to avoid unnecessary fallbacks
            try:
                provider_pref = []
                if pdf_embedding_type and str(pdf_embedding_type).lower() == 'openai':
                    provider_pref = ['openai', 'ollama']
                else:
                    provider_pref = ['ollama', 'openai']
            except Exception:
                provider_pref = ['ollama', 'openai']

            for provider in provider_pref:
                if provider == 'ollama':
                    try:
                        logger.info('chat(): trying Ollama for follow-up suggestions (pdf_id=%s)', pdf_id)
                        ollama_res = requests.post("http://localhost:11434/api/generate", json={"model": "qwen3:4b", "prompt": followup_prompt}, timeout=8)
                        if ollama_res.ok:
                            try:
                                jr = ollama_res.json()
                                txt = jr.get('response') or jr.get('text') or ''
                            except Exception:
                                txt = ollama_res.text
                    except Exception as e:
                        logger.warning('chat(): Ollama follow-up failed: %s', e)
                else:
                    # openai
                    if not openai_api_key:
                        continue
                    try:
                        logger.info('chat(): trying OpenAI for follow-up suggestions (pdf_id=%s)', pdf_id)
                        url2 = "https://api.openai.com/v1/chat/completions"
                        headers2 = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
                        payload2 = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": followup_prompt}], "max_tokens": 150}
                        r2 = requests.post(url2, headers=headers2, json=payload2, timeout=10)
                        if r2.ok:
                            txt = r2.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                    except Exception as e:
                        logger.warning('chat(): OpenAI follow-up failed: %s', e)

                if txt:
                    logger.info('chat(): follow-up suggestions generated by %s for pdf_id=%s', provider, pdf_id)
                    break

            # Parse & sanitize model output to produce up to 3 clean questions
            try:
                suggested_questions = sanitize_suggested_questions_from_text(txt, max_q=3)
            except Exception:
                suggested_questions = []
        except Exception:
            # Outer try guard: on any unexpected failure, return no suggestions
            suggested_questions = []
    # Ensure it's a list of max 3 strings
    if not isinstance(suggested_questions, list):
        suggested_questions = []
    suggested_questions = [str(s).strip() for s in suggested_questions if str(s).strip()][:3]

    # Save conversation and messages to database
    try:
        # Get or create conversation
        if not conversation_id:
            # Create new conversation with title based on first query
            title = query[:100] if len(query) <= 100 else query[:97] + "..."
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO conversations (user_id, pdf_id, title) VALUES (%s, %s, %s) RETURNING id",
                    (user['id'], pdf_id, title)
                )
                conversation_id = cur.fetchone()[0]
                conn.commit()
                logger.info("Created new conversation id=%d for user=%d, pdf=%d", conversation_id, user['id'], pdf_id)
        else:
            # Validate conversation belongs to user
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM conversations WHERE id = %s", (conversation_id,))
                row = cur.fetchone()
                if not row or row[0] != user['id']:
                    raise HTTPException(status_code=403, detail="Conversation does not belong to user")
        
        # Save user message
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                (conversation_id, 'user', query)
            )
            conn.commit()
        
        # Save assistant message with sources
        import json
        import re
        
        # NUEVO: Parsear qué fuentes fueron realmente citadas en la respuesta
        cited_source_ids = set()
        source_citations = re.findall(r'\[SOURCE_(\d+)\]', answer)
        logger.info(f"=== SOURCE PARSING DEBUG ===")
        logger.info(f"RAW ANSWER: {answer[:800]}")
        logger.info(f"SOURCE CITATIONS FOUND: {source_citations}")
        logger.info(f"TOTAL SOURCES AVAILABLE: {len(sources)}")
        
        for src_idx, src in enumerate(sources):
            logger.info(f"  SOURCE[{src_idx}]: page={src.get('page')}, has_coords={bool(src.get('coords'))}, preview={src.get('preview', '')[:80]}")
        
        # Parsear las citas encontradas
        for source_num in source_citations:
            source_idx = int(source_num) - 1
            if 0 <= source_idx < len(sources):
                cited_source_ids.add(source_idx)
                logger.info(f"VALID CITATION: [SOURCE_{source_num}] -> sources[{source_idx}]")
            else:
                logger.warning(f"INVALID CITATION: [SOURCE_{source_num}] out of range (max={len(sources)})")
        
        # FALLBACK MEJORADO: Si no hay citaciones válidas
        if not cited_source_ids and sources:
            logger.warning(f"NO VALID CITATIONS FOUND - Using intelligent fallback")
            # Estrategia 1: Usar la fuente con mejor score (primera)
            cited_source_ids.add(0)
            # Estrategia 2: Si hay coordenadas, usar también esa
            for idx, src in enumerate(sources[:3]):  # Revisar top 3
                if src.get('coords'):
                    cited_source_ids.add(idx)
                    logger.info(f"FALLBACK: Added source[{idx}] because it has coordinates")
                    break
        
        # Filtrar sources para mostrar solo las citadas
        actual_sources = [sources[i] for i in sorted(cited_source_ids)]
        
        # VERIFICACIÓN CRÍTICA: Asegurar que al menos hay UNA fuente con coordenadas
        has_coords = any(src.get('coords') for src in actual_sources)
        if not has_coords and sources:
            logger.warning(f"CRITICAL: No cited sources have coordinates - searching for alternative")
            # Buscar en TODAS las sources disponibles una que tenga coordenadas
            for idx, src in enumerate(sources):
                if src.get('coords'):
                    logger.info(f"FOUND ALTERNATIVE with coords at sources[{idx}]")
                    # Insertar como primera fuente
                    actual_sources.insert(0, src)
                    break
        
        # Si aún no hay sources, usar TODAS como último recurso
        if not actual_sources:
            actual_sources = sources
            logger.warning(f"EMERGENCY FALLBACK: Using all {len(sources)} sources")
        
        logger.info(f"FINAL ACTUAL_SOURCES COUNT: {len(actual_sources)}")
        for src_idx, src in enumerate(actual_sources):
            logger.info(f"  FINAL[{src_idx}]: page={src.get('page')}, has_coords={bool(src.get('coords'))}, location={src.get('location', 'N/A')}")
        logger.info(f"=== END SOURCE PARSING ===\n")
        
        # IMPORTANTE: Convertir [SOURCE_N] a superíndices visibles [N]
        # Esto permite al usuario VER qué parte del texto corresponde a qué fuente
        clean_answer = answer
        
        # Crear mapeo de SOURCE_N citado al índice en actual_sources (1-indexed para el usuario)
        source_display_map = {}
        for new_idx, old_idx in enumerate(sorted(cited_source_ids), start=1):
            source_display_map[f"SOURCE_{old_idx + 1}"] = new_idx
        
        logger.info(f"SOURCE DISPLAY MAP: {source_display_map}")
        
        # Reemplazar [SOURCE_N] con [N] donde N es el índice en actual_sources
        for source_id, display_num in source_display_map.items():
            # Convertir [SOURCE_1] -> ¹ (superíndice) o [1] (corchetes simples)
            clean_answer = clean_answer.replace(f"[{source_id}]", f"[{display_num}]")
        
        # Limpiar cualquier [SOURCE_N] que no haya sido mapeado (no debería pasar)
        clean_answer = re.sub(r'\[SOURCE_\d+\]', '', clean_answer)
        
        # Limpiar espacios múltiples
        clean_answer = re.sub(r'\s+', ' ', clean_answer)
        clean_answer = clean_answer.strip()
        
        # Limpiar espacios antes de puntuación
        clean_answer = re.sub(r'\s+([.,;:!?])', r'\1', clean_answer)
        
        logger.info(f"ANSWER AFTER CLEANING: {clean_answer[:500]}")
        
        sources_json = json.dumps(actual_sources) if actual_sources else None
        page_number = actual_sources[0].get('page') if actual_sources and len(actual_sources) > 0 and 'page' in actual_sources[0] else None
        
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content, sources, page_number) VALUES (%s, %s, %s, %s, %s)",
                (conversation_id, 'assistant', clean_answer, sources_json, page_number)
            )
            conn.commit()
        
        # Update conversation timestamp
        with conn.cursor() as cur:
            cur.execute("UPDATE conversations SET updated_at = NOW() WHERE id = %s", (conversation_id,))
            conn.commit()
        
        logger.info("Saved messages to conversation id=%d", conversation_id)
    except Exception as e:
        logger.exception("Failed to save conversation: %s", e)
        # Don't fail the entire request if saving fails

    return {
        "response": clean_answer if 'clean_answer' in locals() else answer,
        "used_vlm_enhanced": bool(used_vlm_enhanced and len(images_analyzed) > 0),
        "images_analyzed": images_analyzed,
        "sources": actual_sources if 'actual_sources' in locals() else sources,  # Devolver solo fuentes citadas
        "suggested_questions": suggested_questions,
        "conversation_id": conversation_id
    }


# ============ FOLDER CHAT ENDPOINT ============

@app.post("/chat_folder/")
async def chat_folder(query: str = Form(...), folder_id: int = Form(...), embedding_type: str = Form("ollama"), include_suggestions: str = Form('0'), conversation_id: int = Form(None), user = Depends(get_current_user)):
    """Chat with all PDFs in a folder. This searches across all documents and combines results."""
    import re
    import json
    
    # Normalize embedding_type and fallback to system default when necessary
    try:
        if embedding_type is None:
            embedding_type = ''
        embedding_type = embedding_type.strip().lower()
    except Exception:
        embedding_type = 'ollama'

    # If empty or unknown, read system default
    if embedding_type not in ('ollama', 'openai'):
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM system_config WHERE key = 'default_embedding_type'")
                row = cur.fetchone()
                embedding_type = (row[0].strip().lower() if row and row[0] else 'openai')
                logger.info(f"chat_folder: using system default embedding_type={embedding_type}")
        except Exception as e:
            logger.warning(f"chat_folder: failed reading system_config default, defaulting to openai: {e}")
            embedding_type = 'openai'

    # Get all PDFs in this folder
    with conn.cursor() as cur:
        cur.execute("SELECT id, filename FROM pdfs WHERE folder_id = %s", (folder_id,))
        pdf_rows = cur.fetchall()
    
    if not pdf_rows:
        raise HTTPException(status_code=404, detail="No PDFs found in this folder")
    
    pdf_ids = [row[0] for row in pdf_rows]
    pdf_names = {row[0]: row[1] for row in pdf_rows}
    
    logger.info(f"chat_folder: Found {len(pdf_ids)} PDFs in folder {folder_id}")

    # Determine specific model names from config
    ollama_model = None
    openai_model = None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'default_ollama_model'")
            r = cur.fetchone()
            ollama_model = r[0] if r and r[0] else None
            cur.execute("SELECT value FROM system_config WHERE key = 'default_openai_model'")
            r2 = cur.fetchone()
            openai_model = r2[0] if r2 and r2[0] else None
    except Exception:
        ollama_model = ollama_model or None
        openai_model = openai_model or None

    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    # Generate query embedding
    def _gen_ollama(q):
        if ollama_model:
            return get_ollama_embedding(q, model=ollama_model)
        return get_ollama_embedding(q)

    def _gen_openai(q):
        if openai_model:
            return get_openai_embedding(q, openai_api_key, model=openai_model)
        return get_openai_embedding(q, openai_api_key)

    query_embedding = None
    if embedding_type == 'ollama':
        try:
            query_embedding = _gen_ollama(query)
        except Exception as e:
            logger.exception('chat_folder: Ollama embedding generation failed: %s', e)
    elif embedding_type == 'openai':
        try:
            query_embedding = _gen_openai(query)
        except Exception as e:
            logger.exception('chat_folder: OpenAI embedding generation failed: %s', e)

    if query_embedding is None:
        raise HTTPException(status_code=500, detail='Failed to generate embeddings for the query.')

    # Search across all PDFs in the folder and combine results
    all_chunks = []
    all_sources = []
    
    for pdf_id in pdf_ids:
        try:
            chunks, sources = search_similar_chunks(pdf_id, query_embedding, embedding_type, top_k=3)
            # Add PDF name to sources for identification
            for src in sources:
                src['pdf_id'] = pdf_id
                src['pdf_name'] = pdf_names[pdf_id]
            all_chunks.extend(chunks)
            all_sources.extend(sources)
        except Exception as e:
            logger.warning(f"chat_folder: Error searching PDF {pdf_id}: {e}")
            continue

    if not all_chunks:
        raise HTTPException(status_code=404, detail="No relevant content found in folder PDFs")

    # Build context with source IDs
    import re
    context_with_sources = []
    source_map = {}
    
    for idx, chunk in enumerate(all_chunks):
        source_id = f"SOURCE_{idx + 1}"
        source_map[source_id] = idx
        
        # Clean chunk
        cleaned = chunk
        cleaned = re.sub(r'\[PAGINA_\d+\]\n?', '', cleaned)
        cleaned = re.sub(r'\[CHUNK_PARAGRAPHS_\d+-\d+\]', '', cleaned)
        cleaned = cleaned.strip()
        
        # Add source identifier and PDF name
        pdf_name = all_sources[idx].get('pdf_name', 'Unknown')
        context_with_sources.append(f"[{source_id}] (Documento: {pdf_name})\n{cleaned}")
    
    context = "\n\n---\n\n".join(context_with_sources)

    # Generate response
    if embedding_type == "ollama":
        ollama_model = "qwen3:4b"
        prompt = f"""Eres un asistente experto en análisis de documentos. Estás analizando MÚLTIPLES documentos de una carpeta.

REGLAS IMPERATIVAS DE CITACIÓN:
1. CADA dato DEBE ir seguido de [SOURCE_N] inmediatamente
2. MENCIONA el nombre del documento cuando cites información importante
3. Formato: "La temperatura es 25°C [SOURCE_1] según DocumentoX.pdf [SOURCE_2]"
4. Si hay información contradictoria entre documentos, mencionalo
5. NUNCA respondas sin citar

Pregunta: {query}

Contexto de múltiples documentos:
{context}"""
        
        ollama_response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": ollama_model, "prompt": prompt},
            stream=True
        )
        fragments = []
        for line in ollama_response.iter_lines():
            if line:
                try:
                    data = line.decode("utf-8")
                    obj = json.loads(data)
                    if "response" in obj:
                        fragments.append(obj["response"])
                except Exception:
                    continue
        answer = "".join(fragments).strip()
        if not answer:
            answer = "No se pudo generar respuesta."
    elif embedding_type == "openai":
        openai_model = "gpt-4-turbo"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
        
        system_prompt = """Eres un asistente experto en análisis de múltiples documentos PDF.

REGLAS IMPERATIVAS:
1. CADA dato DEBE citarse con [SOURCE_N] inmediatamente después
2. MENCIONA el nombre del documento cuando sea relevante
3. Si hay información contradictoria, señálalo claramente
4. Formato: "X es Y [SOURCE_1] (de DocumentoA.pdf)"
5. NUNCA omitas citas

Estás analizando múltiples documentos de una carpeta. Cada fuente incluye el nombre del documento."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Pregunta: {query}\n\nContexto:\n{context}"}
        ]
        
        payload = {
            "model": openai_model,
            "messages": messages,
            "max_tokens": 800,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.exception("OpenAI request failed: %s", e)
            answer = "Error al generar respuesta."

    # Extract cited sources from answer
    cited_refs = re.findall(r'\[SOURCE_(\d+)\]', answer)
    cited_indices = [int(ref) - 1 for ref in cited_refs if int(ref) - 1 < len(all_sources)]
    actual_sources = [all_sources[i] for i in cited_indices if i < len(all_sources)]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_sources = []
    for src in actual_sources:
        src_key = (src.get('pdf_id'), src.get('page'), src.get('preview', '')[:50])
        if src_key not in seen:
            seen.add(src_key)
            unique_sources.append(src)
    
    actual_sources = unique_sources

    # Save conversation (modify to support folder_id)
    conversation_id = conversation_id or None
    try:
        if conversation_id:
            # Verify conversation exists
            with conn.cursor() as cur:
                cur.execute("SELECT id, user_id FROM conversations WHERE id = %s", (conversation_id,))
                row = cur.fetchone()
                if not row or row[1] != user['id']:
                    conversation_id = None
        
        if not conversation_id:
            # Create new conversation for folder
            title = f"Carpeta: {query[:50]}" if len(query) > 50 else f"Carpeta: {query}"
            with conn.cursor() as cur:
                # Create conversation with folder_id instead of pdf_id
                cur.execute(
                    "INSERT INTO conversations (user_id, folder_id, title) VALUES (%s, %s, %s) RETURNING id",
                    (user['id'], folder_id, title)
                )
                conversation_id = cur.fetchone()[0]
                conn.commit()
            logger.info("Created new folder conversation id=%d for folder_id=%d", conversation_id, folder_id)
        
        # Save user message
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                (conversation_id, 'user', query)
            )
            conn.commit()
        
        # Save assistant response with sources
        clean_answer = answer.strip()
        sources_json = json.dumps(actual_sources) if actual_sources else None
        
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content, sources) VALUES (%s, %s, %s, %s)",
                (conversation_id, 'assistant', clean_answer, sources_json)
            )
            conn.commit()
        
        # Update conversation timestamp
        with conn.cursor() as cur:
            cur.execute("UPDATE conversations SET updated_at = NOW() WHERE id = %s", (conversation_id,))
            conn.commit()
        
        logger.info("Saved folder conversation messages to id=%d", conversation_id)
    except Exception as e:
        logger.exception("Failed to save folder conversation: %s", e)

    # Generate suggested questions for folder context (only if requested)
    suggested_questions = []
    if include_suggestions and include_suggestions != '0':
        try:
            # Generate questions based on the folder context
            if embedding_type == "ollama":
                sugg_prompt = f"""Basándote en esta conversación sobre múltiples documentos, genera 3 preguntas de seguimiento breves y relevantes que el usuario podría hacer.

Pregunta previa: {query}
Respuesta: {answer[:500]}

Genera exactamente 3 preguntas cortas (máximo 80 caracteres cada una) que exploren diferentes aspectos de los documentos en la carpeta. Devuelve solo las preguntas, una por línea, sin numeración."""
                
                try:
                    sugg_resp = requests.post(
                        "http://localhost:11434/api/generate",
                        json={"model": "qwen3:4b", "prompt": sugg_prompt},
                        stream=True,
                        timeout=15
                    )
                    sugg_fragments = []
                    for line in sugg_resp.iter_lines():
                        if line:
                            try:
                                obj = json.loads(line.decode("utf-8"))
                                if "response" in obj:
                                    sugg_fragments.append(obj["response"])
                            except Exception:
                                continue
                    raw_suggestions = "".join(sugg_fragments).strip()
                    suggested_questions = sanitize_suggested_questions_from_text(raw_suggestions, max_q=3)
                except Exception as e:
                    logger.warning("Failed to generate Ollama suggestions for folder: %s", e)
            elif embedding_type == "openai":
                sugg_prompt = f"""Basándote en esta conversación sobre múltiples documentos, genera 3 preguntas de seguimiento breves.

Pregunta previa: {query}
Respuesta: {answer[:500]}

Genera 3 preguntas cortas (máximo 80 caracteres) que exploren diferentes aspectos de los documentos. Solo devuelve las preguntas, una por línea."""
                
                try:
                    sugg_response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"},
                        json={
                            "model": "gpt-3.5-turbo",
                            "messages": [{"role": "user", "content": sugg_prompt}],
                            "max_tokens": 200,
                            "temperature": 0.7
                        },
                        timeout=15
                    )
                    if sugg_response.ok:
                        raw_suggestions = sugg_response.json()["choices"][0]["message"]["content"]
                        suggested_questions = sanitize_suggested_questions_from_text(raw_suggestions, max_q=3)
                except Exception as e:
                    logger.warning("Failed to generate OpenAI suggestions for folder: %s", e)
        except Exception as e:
            logger.warning("Suggestion generation failed for folder: %s", e)

    return {
        "response": clean_answer if 'clean_answer' in locals() else answer,
        "sources": actual_sources,
        "conversation_id": conversation_id,
        "folder_id": folder_id,
        "pdf_count": len(pdf_ids),
        "pdf_names": list(pdf_names.values()),
        "suggested_questions": suggested_questions
    }


# ============ CONVERSATION HISTORY ENDPOINTS ============

@app.get("/conversations/")
async def get_conversations(user = Depends(get_current_user)):
    """Get all conversations for the authenticated user"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.pdf_id, c.folder_id, c.title, c.created_at, c.updated_at, 
                       p.filename as pdf_filename, f.name as folder_name
                FROM conversations c
                LEFT JOIN pdfs p ON c.pdf_id = p.id
                LEFT JOIN folders f ON c.folder_id = f.id
                WHERE c.user_id = %s
                ORDER BY c.updated_at DESC
            """, (user['id'],))
            
            rows = cur.fetchall()
            conversations = []
            for row in rows:
                conversations.append({
                    'id': row[0],
                    'pdf_id': row[1],
                    'folder_id': row[2],
                    'title': row[3],
                    'created_at': row[4].isoformat() if row[4] else None,
                    'updated_at': row[5].isoformat() if row[5] else None,
                    'pdf_filename': row[6],
                    'folder_name': row[7],
                    'type': 'folder' if row[2] else 'pdf'  # Indicar si es chat de carpeta o PDF
                })
            
            return {"conversations": conversations}
    except Exception as e:
        logger.exception("Error getting conversations: %s", e)
        raise HTTPException(status_code=500, detail="Error al obtener conversaciones")


@app.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int, user = Depends(get_current_user)):
    """Get all messages for a specific conversation"""
    try:
        # Verify conversation belongs to user
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM conversations WHERE id = %s", (conversation_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if row[0] != user['id']:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Get messages
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, role, content, sources, page_number, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
            """, (conversation_id,))
            
            rows = cur.fetchall()
            messages = []
            for row in rows:
                import json
                raw_sources = row[3]
                sources = []
                if raw_sources:
                    try:
                        # psycopg2 may already decode JSON/JSONB into Python list/dict
                        if isinstance(raw_sources, (list, dict)):
                            sources = raw_sources
                        elif isinstance(raw_sources, (bytes, bytearray)):
                            sources = json.loads(raw_sources.decode('utf-8'))
                        elif isinstance(raw_sources, str):
                            sources = json.loads(raw_sources)
                        else:
                            # Fallback: try to coerce to string then parse
                            sources = json.loads(str(raw_sources))
                    except Exception as _exc:
                        logger.warning("Could not parse message sources for message id=%s: %s - raw=%r", row[0], _exc, raw_sources)
                        sources = []

                messages.append({
                    'id': row[0],
                    'role': row[1],
                    'content': row[2],
                    'sources': sources,
                    'page_number': row[4],
                    'created_at': row[5].isoformat() if row[5] else None
                })
            
            return {"messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting messages: %s", e)
        raise HTTPException(status_code=500, detail="Error al obtener mensajes")


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, user = Depends(get_current_user)):
    """Delete a conversation and all its messages"""
    try:
        # Verify conversation belongs to user
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM conversations WHERE id = %s", (conversation_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if row[0] != user['id']:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete messages first (foreign key constraint)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
            conn.commit()
        
        # Delete conversation
        with conn.cursor() as cur:
            cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
            conn.commit()
        
        logger.info("Deleted conversation id=%d for user=%d", conversation_id, user['id'])
        return {"status": "success", "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting conversation: %s", e)
        raise HTTPException(status_code=500, detail="Error al eliminar conversación")


@app.get('/pdfs/{pdf_id}/debug')
async def pdf_debug(pdf_id: int):
    """Return debugging info for a PDF: stored chunks, OCR/captions markers, hash and metadata counts."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, filename, embedding_type, hash, folder_id FROM pdfs WHERE id = %s", (pdf_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="PDF not found")
        pdf_info = {'id': row[0], 'filename': row[1], 'embedding_type': row[2], 'hash': row[3], 'folder_id': row[4]}

    # fetch chunks from both chunk tables
    chunks_ollama = []
    chunks_openai = []
    with conn.cursor() as cur:
        try:
            cur.execute("SELECT id, chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id", (pdf_id,))
            chunks_ollama = [{'id': r[0], 'chunk': r[1]} for r in cur.fetchall()]
        except Exception:
            pass
        try:
            cur.execute("SELECT id, chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id", (pdf_id,))
            chunks_openai = [{'id': r[0], 'chunk': r[1]} for r in cur.fetchall()]
        except Exception:
            pass

    # Try to detect OCR/IMAGE caption markers inside chunks
    ocr_snippets = []
    caption_snippets = []
    for c in chunks_ollama + chunks_openai:
        ch = c.get('chunk') or ''
        if '[OCR_EXTRACTED_TEXT]' in ch:
            ocr_snippets.append(ch[ch.find('[OCR_EXTRACTED_TEXT]'):][:1000])
        if '[IMAGE_CAPTIONS]' in ch:
            caption_snippets.append(ch[ch.find('[IMAGE_CAPTIONS]'):][:1000])

    # metadata
    meta = get_pdf_metadata_from_db(pdf_id)

    return {
        'pdf': pdf_info,
        'metadata': meta,
        'chunks_ollama_count': len(chunks_ollama),
        'chunks_openai_count': len(chunks_openai),
        'ocr_snippets': ocr_snippets,
        'caption_snippets': caption_snippets,
        'chunks_ollama_sample': chunks_ollama[:3],
        'chunks_openai_sample': chunks_openai[:3]
    }



@app.get('/pdfs/{pdf_id}/suggest_questions')
async def suggest_questions(pdf_id: int):
    """Generate up to 3 suggested starter questions for a PDF using available models.
    This endpoint is intended to be called when a user opens/selects a document so the UI
    can show starter suggestions immediately.
    """
    # Build a compact context from stored captions and OCR snippets
    with conn.cursor() as cur:
        cur.execute("SELECT caption, page_number FROM pdf_images WHERE pdf_id = %s ORDER BY page_number", (pdf_id,))
        imgs = cur.fetchall()
        # assemble short image summaries
        image_summaries = []
        for cap, pnum in imgs:
            if cap and cap.strip():
                image_summaries.append(f"Página {pnum}: {str(cap)[:200]}")

        # fetch some representative chunks to form context
        chunks = []
        try:
            cur.execute("SELECT chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id LIMIT 6", (pdf_id,))
            chunks += [r[0] for r in cur.fetchall()]
        except Exception:
            pass
        try:
            cur.execute("SELECT chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id LIMIT 6", (pdf_id,))
            chunks += [r[0] for r in cur.fetchall()]
        except Exception:
            pass

    context = ''
    if image_summaries:
        context += '[IMAGE_SUMMARIES]\n' + '\n'.join(image_summaries) + '\n\n'
    context += '\n'.join([c for c in chunks if c])

    followup_prompt = (
        f"Genera tres preguntas de seguimiento concisas en español basadas en el siguiente extracto del documento."
        f" Devuelve únicamente una lista clara de preguntas (una por línea o un JSON array).\n\nExtracto:\n{context}\n\nEjemplo output (JSON): [\"Pregunta 1\", \"Pregunta 2\", \"Pregunta 3\"]"
    )

    txt = ''
    # Choose provider order based on how the PDF was uploaded
    openai_api_key = os.getenv('OPENAI_API_KEY', '')
    try:
        pdf_embed = get_pdf_embedding_type(pdf_id)
    except Exception:
        pdf_embed = None

    provider_pref = ['ollama', 'openai']
    if pdf_embed and str(pdf_embed).lower() == 'openai':
        provider_pref = ['openai', 'ollama']

    for provider in provider_pref:
        if provider == 'ollama':
            try:
                logger.info('suggest_questions: trying Ollama (/api/chat) for pdf_id=%s', pdf_id)
                # Prefer the /api/chat endpoint for cleaner text responses
                payload = {
                    'model': 'qwen3:4b',
                    'messages': [{'role': 'user', 'content': followup_prompt}],
                    'stream': False
                }
                try:
                    resp = requests.post('http://localhost:11434/api/chat', json=payload, timeout=8)
                    if resp.ok:
                        jr = resp.json()
                        # Ollama chat tends to put text in message.content
                        txt = (jr.get('message', {}) or {}).get('content') or jr.get('response') or jr.get('text') or ''
                except Exception:
                    # Fallback to /api/generate if /api/chat isn't available
                    logger.info('suggest_questions: /api/chat failed, falling back to /api/generate for pdf_id=%s', pdf_id)
                    resp = requests.post('http://localhost:11434/api/generate', json={'model': 'qwen3:4b', 'prompt': followup_prompt, 'stream': False}, timeout=8)
                    if resp.ok:
                        try:
                            jr = resp.json()
                            txt = jr.get('response') or jr.get('text') or ''
                        except Exception:
                            txt = resp.text
            except Exception as e:
                logger.warning('suggest_questions: Ollama call failed completely: %s', e)
        else:
            if not openai_api_key:
                continue
            try:
                logger.info('suggest_questions: trying OpenAI for pdf_id=%s', pdf_id)
                url = 'https://api.openai.com/v1/chat/completions'
                headers = {'Authorization': f'Bearer {openai_api_key}', 'Content-Type': 'application/json'}
                payload = { 'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': followup_prompt}], 'max_tokens': 150 }
                r2 = requests.post(url, headers=headers, json=payload, timeout=8)
                if r2.ok:
                    txt = r2.json().get('choices', [{}])[0].get('message', {}).get('content', '')
            except Exception as e:
                logger.warning('suggest_questions: OpenAI call failed: %s', e)

        if txt:
            logger.info('suggest_questions: generated suggestions with %s for pdf_id=%s', provider, pdf_id)
            break

    # Parse & sanitize model output to ensure up to 3 clean questions
    try:
        suggested_questions = sanitize_suggested_questions_from_text(txt, max_q=3)
    except Exception:
        suggested_questions = []

    return {'suggested_questions': suggested_questions}


@app.get('/folders/{folder_id}/suggest_questions')
async def suggest_questions_folder(folder_id: int):
    """Generate up to 3 suggested starter questions for a folder with multiple PDFs.
    This endpoint is called when a user opens/selects a folder for chat.
    """
    # Get all PDFs in this folder
    with conn.cursor() as cur:
        cur.execute("SELECT id, filename FROM pdfs WHERE folder_id = %s", (folder_id,))
        pdf_rows = cur.fetchall()
    
    if not pdf_rows:
        return {'suggested_questions': []}
    
    pdf_ids = [row[0] for row in pdf_rows]
    pdf_names = [row[1] for row in pdf_rows]
    
    logger.info(f"suggest_questions_folder: Found {len(pdf_ids)} PDFs in folder {folder_id}")
    
    # Build context from all PDFs in folder (sample from each)
    all_chunks = []
    all_image_summaries = []
    
    for pdf_id in pdf_ids[:5]:  # Limit to first 5 PDFs to avoid too much context
        with conn.cursor() as cur:
            # Get image summaries
            cur.execute("SELECT caption, page_number FROM pdf_images WHERE pdf_id = %s ORDER BY page_number LIMIT 3", (pdf_id,))
            imgs = cur.fetchall()
            for cap, pnum in imgs:
                if cap and cap.strip():
                    all_image_summaries.append(f"[{pdf_names[pdf_ids.index(pdf_id)]}] Pág {pnum}: {str(cap)[:150]}")
            
            # Get sample chunks
            try:
                cur.execute("SELECT chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id LIMIT 2", (pdf_id,))
                all_chunks += [r[0] for r in cur.fetchall()]
            except Exception:
                pass
            try:
                cur.execute("SELECT chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id LIMIT 2", (pdf_id,))
                all_chunks += [r[0] for r in cur.fetchall()]
            except Exception:
                pass
    
    # Build context
    context = ''
    if all_image_summaries:
        context += '[RESÚMENES DE IMÁGENES]\n' + '\n'.join(all_image_summaries[:10]) + '\n\n'
    
    # Clean and limit chunks
    import re
    cleaned_chunks = []
    for chunk in all_chunks[:10]:
        if chunk:
            cleaned = re.sub(r'\[PAGINA_\d+\]\n?', '', chunk)
            cleaned = re.sub(r'\[CHUNK_PARAGRAPHS_\d+-\d+\]', '', cleaned)
            cleaned_chunks.append(cleaned.strip()[:300])
    
    context += '\n'.join(cleaned_chunks)
    
    # Create prompt mentioning multiple documents
    followup_prompt = (
        f"Esta carpeta contiene {len(pdf_names)} documentos: {', '.join(pdf_names[:3])}{'...' if len(pdf_names) > 3 else ''}.\n\n"
        f"Basándote en los siguientes extractos de estos documentos, genera 3 preguntas exploratorias concisas en español "
        f"que un usuario podría hacer para analizar el contenido de esta carpeta de documentos.\n\n"
        f"Extractos:\n{context[:2000]}\n\n"
        f"Devuelve únicamente un JSON array con las 3 preguntas, ejemplo: [\"¿Pregunta 1?\", \"¿Pregunta 2?\", \"¿Pregunta 3?\"]"
    )
    
    txt = ''
    openai_api_key = os.getenv('OPENAI_API_KEY', '')
    
    # Try providers (prefer OpenAI for better multi-doc understanding, then Ollama)
    provider_pref = ['openai', 'ollama'] if openai_api_key else ['ollama']
    
    for provider in provider_pref:
        if provider == 'ollama':
            try:
                logger.info('suggest_questions_folder: trying Ollama for folder_id=%s', folder_id)
                payload = {
                    'model': 'qwen3:4b',
                    'messages': [{'role': 'user', 'content': followup_prompt}],
                    'stream': False
                }
                try:
                    resp = requests.post('http://localhost:11434/api/chat', json=payload, timeout=10)
                    if resp.ok:
                        jr = resp.json()
                        txt = (jr.get('message', {}) or {}).get('content') or jr.get('response') or ''
                except Exception:
                    resp = requests.post('http://localhost:11434/api/generate', json={'model': 'qwen3:4b', 'prompt': followup_prompt, 'stream': False}, timeout=10)
                    if resp.ok:
                        jr = resp.json()
                        txt = jr.get('response') or jr.get('text') or ''
            except Exception as e:
                logger.warning('suggest_questions_folder: Ollama failed: %s', e)
        else:
            try:
                logger.info('suggest_questions_folder: trying OpenAI for folder_id=%s', folder_id)
                url = 'https://api.openai.com/v1/chat/completions'
                headers = {'Authorization': f'Bearer {openai_api_key}', 'Content-Type': 'application/json'}
                payload = {
                    'model': 'gpt-4o-mini',
                    'messages': [{'role': 'user', 'content': followup_prompt}],
                    'max_tokens': 200
                }
                r2 = requests.post(url, headers=headers, json=payload, timeout=10)
                if r2.ok:
                    txt = r2.json().get('choices', [{}])[0].get('message', {}).get('content', '')
            except Exception as e:
                logger.warning('suggest_questions_folder: OpenAI failed: %s', e)
        
        if txt:
            logger.info('suggest_questions_folder: generated suggestions with %s', provider)
            break
    
    # Parse & sanitize
    try:
        suggested_questions = sanitize_suggested_questions_from_text(txt, max_q=3)
    except Exception:
        suggested_questions = []
    
    return {'suggested_questions': suggested_questions}


# --- Metadata endpoints for frontend sync (folders, favorites, tags) ---
@app.get("/metadata/")
async def get_metadata():
    # Aggregate folders and documents metadata from DB
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM folders ORDER BY id DESC")
        folders = [{'id': r[0], 'name': r[1]} for r in cur.fetchall()]
        # fetch pdf ids
        cur.execute("SELECT id FROM pdfs")
        pdf_rows = cur.fetchall()
    docs = {}
    for (pid,) in pdf_rows:
        meta = get_pdf_metadata_from_db(pid)
        if meta:
            docs[str(pid)] = meta
        else:
            docs[str(pid)] = {}
    return {'folders': folders, 'documents': docs}


@app.post('/migration/run')
async def migration_run():
    """Force migration run and return summary JSON."""
    summary = run_migration()
    return summary


@app.get('/migration/status')
async def migration_status():
    """Return last migration result summary if present, otherwise a quick DB check."""
    if MIGRATION_RESULT_PATH.exists():
        try:
            with open(MIGRATION_RESULT_PATH, 'r', encoding='utf-8') as rf:
                data = json.load(rf)
                return {'status': 'ok', 'result': data}
        except Exception:
            pass

    # Fallback: quick check of counts
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM pdfs')
        pdfs_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM pdf_metadata')
        meta_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM folders')
        folders_count = cur.fetchone()[0]

    return {'status': 'ok', 'pdfs': pdfs_count, 'pdf_metadata': meta_count, 'folders': folders_count}


@app.post("/folders/")
async def create_folder(name: str = Form(...)):
    # create folder in DB
    with conn.cursor() as cur:
        cur.execute("INSERT INTO folders (name) VALUES (%s) RETURNING id, name", (name,))
        row = cur.fetchone()
        conn.commit()
    folder = {"id": row[0], "name": row[1]}
    return folder


@app.delete("/folders/{folder_id}")
async def delete_folder(folder_id: int):
    # delete folder from DB and unset folder_id on pdfs
    with conn.cursor() as cur:
        cur.execute("UPDATE pdfs SET folder_id = NULL WHERE folder_id = %s", (folder_id,))
        cur.execute("DELETE FROM folders WHERE id = %s", (folder_id,))
        conn.commit()
    return {"ok": True}


@app.get("/documents/{pdf_id}/metadata")
async def get_document_metadata(pdf_id: int):
    # Return metadata for a single PDF from DB
    with conn.cursor() as cur:
        cur.execute("SELECT folder_id FROM pdfs WHERE id = %s", (pdf_id,))
        r = cur.fetchone()
        folder_val = r[0] if r else None
    meta = get_pdf_metadata_from_db(pdf_id)
    result = meta or {}
    result['folderId'] = folder_val
    return result


@app.post("/documents/{pdf_id}/metadata")
async def set_document_metadata(pdf_id: int, metadata: str = Form(...)):
    # metadata: JSON string with keys like favorite, tags, folderId
    try:
        meta_obj = json.loads(metadata)
    except Exception:
        meta_obj = {}
    # If folderId present, update DB
    if 'folderId' in meta_obj:
        folder_id = meta_obj.get('folderId')
        with conn.cursor() as cur:
            cur.execute("UPDATE pdfs SET folder_id = %s WHERE id = %s", (folder_id, pdf_id))
            conn.commit()

    # Store other metadata in DB table pdf_metadata
    meta_to_store = {k: v for k, v in meta_obj.items() if k != 'folderId'}
    if meta_to_store:
        upsert_pdf_metadata_db(pdf_id, meta_to_store)

    # Return merged view
    with conn.cursor() as cur:
        cur.execute("SELECT folder_id FROM pdfs WHERE id = %s", (pdf_id,))
        r = cur.fetchone()
        folder_val = r[0] if r else None
    meta = get_pdf_metadata_from_db(pdf_id)
    result = meta or {}
    result['folderId'] = folder_val
    return result


@app.get("/pdfs/")
async def list_pdfs(folder_id: int = None, name: str = None, hash: str = None, user = Depends(get_current_user_optional)):
    # Si no hay usuario autenticado, no mostrar PDFs (requiere autenticación)
    if not user:
        return {'pdfs': []}
    
    # Verificar si el usuario es admin
    is_admin = False
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT r.name FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = %s', (user['id'],))
            roles = [r[0] for r in cur.fetchall()]
            is_admin = 'admin' in roles
    except Exception:
        pass
    
    # Fetch PDFs from database with optional folder_id or exact name filter
    # Los usuarios normales solo ven sus PDFs, los admins ven todos
    with conn.cursor() as cur:
        if hash:
            # exact hash match
            if is_admin:
                cur.execute("SELECT id, filename, embedding_type, folder_id, hash, user_id FROM pdfs WHERE hash = %s ORDER BY id DESC", (hash,))
            else:
                cur.execute("SELECT id, filename, embedding_type, folder_id, hash, user_id FROM pdfs WHERE hash = %s AND user_id = %s ORDER BY id DESC", (hash, user['id']))
        elif name:
            # exact filename match (case-insensitive)
            if is_admin:
                cur.execute("SELECT id, filename, embedding_type, folder_id, hash, user_id FROM pdfs WHERE LOWER(filename) = LOWER(%s) ORDER BY id DESC", (name,))
            else:
                cur.execute("SELECT id, filename, embedding_type, folder_id, hash, user_id FROM pdfs WHERE LOWER(filename) = LOWER(%s) AND user_id = %s ORDER BY id DESC", (name, user['id']))
        elif folder_id is None:
            if is_admin:
                cur.execute("SELECT id, filename, embedding_type, folder_id, hash, user_id FROM pdfs ORDER BY id DESC")
            else:
                cur.execute("SELECT id, filename, embedding_type, folder_id, hash, user_id FROM pdfs WHERE user_id = %s ORDER BY id DESC", (user['id'],))
        else:
            if is_admin:
                cur.execute("SELECT id, filename, embedding_type, folder_id, hash, user_id FROM pdfs WHERE folder_id = %s ORDER BY id DESC", (folder_id,))
            else:
                cur.execute("SELECT id, filename, embedding_type, folder_id, hash, user_id FROM pdfs WHERE folder_id = %s AND user_id = %s ORDER BY id DESC", (folder_id, user['id']))
        rows = cur.fetchall()

    results = []
    for r in rows:
        pdf_id, filename, embedding_type, folder_val, file_hash, user_id = r
        meta = get_pdf_metadata_from_db(pdf_id)
        
        # Intentar obtener el número de páginas del PDF almacenado
        pages = 0
        try:
            pdf_path = Path(__file__).resolve().parent / 'uploads' / 'pdfs' / f"{pdf_id}.pdf"
            if pdf_path.exists():
                import PyPDF2
                with open(pdf_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    pages = len(pdf_reader.pages)
        except Exception:
            pass
        
        entry = {
            'id': pdf_id,
            'name': filename,
            'pages': pages,
            'embeddingType': embedding_type,
            'folderId': folder_val,
            'hash': file_hash,
            'favorite': meta.get('favorite', False),
            'tags': meta.get('tags', []),
            'uploadedAt': meta.get('uploadedAt')
        }
        results.append(entry)

    return {'pdfs': results}


@app.delete('/pdfs/{pdf_id}')
async def delete_pdf(pdf_id: int):
    """Delete a PDF and its related data and files.
    - Removes entries from pdfs, pdf_chunks_{openai,ollama}, pdf_metadata
    - Collects image paths from pdf_images, then deletes image files and the
      uploads/images/{pdf_id} directory if present.
    """
    image_paths = []
    try:
        with conn.cursor() as cur:
            # collect image paths first
            try:
                cur.execute("SELECT image_path FROM pdf_images WHERE pdf_id = %s", (pdf_id,))
                rows = cur.fetchall()
                image_paths = [r[0] for r in rows]
            except Exception:
                image_paths = []

            # delete chunks (if tables exist)
            try:
                cur.execute("DELETE FROM pdf_chunks_openai WHERE pdf_id = %s", (pdf_id,))
            except Exception:
                pass
            try:
                cur.execute("DELETE FROM pdf_chunks_ollama WHERE pdf_id = %s", (pdf_id,))
            except Exception:
                pass

            # delete pdf_metadata row
            try:
                cur.execute("DELETE FROM pdf_metadata WHERE pdf_id = %s", (pdf_id,))
            except Exception:
                pass

            # finally delete pdf row (this will cascade-delete pdf_images if FK has ON DELETE CASCADE)
            cur.execute("DELETE FROM pdfs WHERE id = %s", (pdf_id,))
            conn.commit()
    except Exception as e:
        logger.exception("Failed to delete PDF id=%s: %s", pdf_id, e)
        raise HTTPException(status_code=500, detail=f"Error deleting PDF: {e}")

    # Remove image files from disk
    from pathlib import Path
    import shutil
    for p in image_paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    # Remove the containing directory uploads/images/{pdf_id} if it exists
    try:
        images_dir = Path(__file__).resolve().parent / 'uploads' / 'images' / str(pdf_id)
        if images_dir.exists():
            shutil.rmtree(images_dir)
    except Exception:
        pass

    # Remove the persisted original PDF file if present
    try:
        pdf_file = Path(__file__).resolve().parent / 'uploads' / 'pdfs' / f"{pdf_id}.pdf"
        if pdf_file.exists():
            try:
                os.remove(str(pdf_file))
            except Exception:
                # best-effort: ignore if cannot delete
                logger.warning('Failed to remove persisted PDF file for id=%s: %s', pdf_id, pdf_file)
    except Exception:
        pass

    return {"ok": True}


@app.get('/pdfs/{pdf_id}/file')
async def get_pdf_file(pdf_id: int):
    """Serve the PDF file for viewing"""
    from fastapi.responses import FileResponse
    
    pdf_path = Path(__file__).resolve().parent / 'uploads' / 'pdfs' / f"{pdf_id}.pdf"
    
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        path=str(pdf_path),
        media_type='application/pdf',
        filename=f"{pdf_id}.pdf"
    )


@app.get('/pdfs/{pdf_id}/images/{page_num}')
async def get_pdf_image(pdf_id: int, page_num: int):
    """Serve an extracted page image for a PDF if available.
    This endpoint returns the PNG file saved under uploads/images/{pdf_id}/page_{page_num}.png
    """
    try:
        img_path = Path(__file__).resolve().parent / 'uploads' / 'images' / str(pdf_id) / f'page_{page_num}.png'
        if not img_path.exists():
            raise HTTPException(status_code=404, detail='Image not found')
        return FileResponse(str(img_path), media_type='image/png', headers={"Access-Control-Allow-Origin": "*"})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('Failed to serve image for pdf_id=%s page=%s: %s', pdf_id, page_num, e)
        raise HTTPException(status_code=500, detail='Internal server error')


@app.get('/pdfs/{pdf_id}/file')
async def get_pdf_file(pdf_id: int):
    """Serve the original uploaded PDF if present."""
    try:
        pdf_path = Path(__file__).resolve().parent / 'uploads' / 'pdfs' / f"{pdf_id}.pdf"
        if pdf_path.exists():
            return FileResponse(str(pdf_path), media_type='application/pdf', headers={"Access-Control-Allow-Origin": "*"})

        # Fallback: if original PDF missing, try to assemble one from extracted page images
        images_dir = Path(__file__).resolve().parent / 'uploads' / 'images' / str(pdf_id)
        if images_dir.exists():
            imgs = sorted(images_dir.glob('page_*.png'))
            if imgs:
                try:
                    from PIL import Image
                    import io
                    # open images and convert to RGB
                    pil_imgs = []
                    for p in imgs:
                        im = Image.open(p)
                        if im.mode == 'RGBA':
                            im = im.convert('RGB')
                        pil_imgs.append(im.copy())
                        im.close()

                    # save to a temporary PDF file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                        first, rest = pil_imgs[0], pil_imgs[1:]
                        first.save(tmp_pdf.name, format='PDF', save_all=True, append_images=rest)
                        tmp_path = tmp_pdf.name
                    return FileResponse(str(tmp_path), media_type='application/pdf', headers={"Access-Control-Allow-Origin": "*"})
                except Exception as e:
                    logger.exception('Failed to assemble PDF from images for id=%s: %s', pdf_id, e)

        # If we reach here, no PDF or images available
        raise HTTPException(status_code=404, detail='PDF not found')
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('Failed to serve pdf file for id=%s: %s', pdf_id, e)
        raise HTTPException(status_code=500, detail='Internal server error')


@app.get('/pdfs/{pdf_id}/info')
async def get_pdf_info(pdf_id: int):
    """Return basic info about the stored PDF: page count and stored images."""
    try:
        pdf_path = Path(__file__).resolve().parent / 'uploads' / 'pdfs' / f"{pdf_id}.pdf"
        pages = 0
        if pdf_path.exists():
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(str(pdf_path))
                pages = len(reader.pages)
            except Exception:
                pages = 0

        # count images stored
        images_dir = Path(__file__).resolve().parent / 'uploads' / 'images' / str(pdf_id)
        images = []
        if images_dir.exists():
            for p in sorted(images_dir.glob('page_*.png')):
                try:
                    # extract page number
                    num = int(p.stem.split('_')[-1])
                except Exception:
                    num = None
                images.append({'path': str(p), 'page': num})

        return {'pdf_id': pdf_id, 'pages': pages, 'images': images}

    except Exception as e:
        logger.exception('Failed to get pdf info for id=%s: %s', pdf_id, e)
        raise HTTPException(status_code=500, detail='Internal server error')


@app.post('/admin/reprocess_spans')
async def admin_reprocess_spans(pdf_id: int = None):
    """Reprocess existing PDFs to map stored chunks to bounding boxes (best-effort).
    If pdf_id is provided, process only that PDF; otherwise process all PDFs.
    This can be slow for many PDFs. Requires pdfplumber to be installed.
    """
    processed = []
    failed = []
    with conn.cursor() as cur:
        if pdf_id:
            cur.execute("SELECT id FROM pdfs WHERE id = %s", (pdf_id,))
            rows = cur.fetchall()
        else:
            cur.execute("SELECT id FROM pdfs")
            rows = cur.fetchall()

    for (pid,) in rows:
        try:
            pdf_path = Path(__file__).resolve().parent / 'uploads' / 'pdfs' / f"{pid}.pdf"
            if not pdf_path.exists():
                failed.append({'pdf_id': pid, 'error': 'pdf file missing'})
                continue

            # Fetch chunks from both tables
            all_chunks = []
            with conn.cursor() as cur2:
                try:
                    cur2.execute("SELECT id, chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id", (pid,))
                    all_chunks += [('pdf_chunks_openai', r[0], r[1]) for r in cur2.fetchall()]
                except Exception:
                    pass
                try:
                    cur2.execute("SELECT id, chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id", (pid,))
                    all_chunks += [('pdf_chunks_ollama', r[0], r[1]) for r in cur2.fetchall()]
                except Exception:
                    pass

            for table_name, chunk_id, chunk_text in all_chunks:
                try:
                    # Skip if spans already exist for this chunk
                    with conn.cursor() as cur3:
                        cur3.execute("SELECT 1 FROM pdf_chunk_spans WHERE chunk_id = %s AND pdf_id = %s LIMIT 1", (chunk_id, pid))
                        if cur3.fetchone():
                            continue
                    map_chunk_to_bbox(str(pdf_path), chunk_text, chunk_id, table_name, pid)
                except Exception as e:
                    logger.exception('Failed mapping chunk %s of pdf %s: %s', chunk_id, pid, e)
            processed.append(pid)
        except Exception as e:
            failed.append({'pdf_id': pid, 'error': str(e)})

    return {'processed': processed, 'failed': failed}


@app.post('/auth/register')
async def auth_register(username: str = Form(...), password: str = Form(...)):
    if not username or not password:
        raise HTTPException(status_code=400, detail='username and password required')
    pwd_hash = create_password_hash(password)
    try:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO users (username, password_hash) VALUES (%s,%s) RETURNING id', (username, pwd_hash))
            uid = cur.fetchone()[0]
            conn.commit()
    except Exception as e:
        logger.exception('auth_register failed: %s', e)
        raise HTTPException(status_code=400, detail='User creation failed (maybe username exists)')
    token = create_access_token({'user_id': uid})
    return {'user': {'id': uid, 'username': username}, 'token': token}


@app.post('/auth/login')
async def auth_login(username: str = Form(...), password: str = Form(...)):
    with conn.cursor() as cur:
        cur.execute('SELECT id, password_hash FROM users WHERE username = %s', (username,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=401, detail='Invalid credentials')
        uid, ph = r[0], r[1]
        if not verify_password(password, ph):
            raise HTTPException(status_code=401, detail='Invalid credentials')
    token = create_access_token({'user_id': uid})
    return {'user': {'id': uid, 'username': username}, 'token': token}


@app.get('/auth/me')
async def auth_me(user = Depends(get_current_user)):
    # Include the list of role names assigned to the current user
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT r.name FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = %s', (user.get('id'),))
            rows = cur.fetchall()
            roles = [r[0] for r in rows]
    except Exception:
        roles = []
    return {'user': user, 'roles': roles}


@app.post('/roles')
async def create_role(name: str = Form(...), _admin=Depends(require_role('admin'))):
    try:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id', (name,))
            r = cur.fetchone()
            conn.commit()
            if r:
                return {'id': r[0], 'name': name}
            # already exists
            cur.execute('SELECT id FROM roles WHERE name = %s', (name,))
            eid = cur.fetchone()[0]
            return {'id': eid, 'name': name}
    except Exception as e:
        logger.exception('create_role failed: %s', e)
        raise HTTPException(status_code=500, detail='Failed to create role')


@app.post('/roles/assign')
async def assign_role(username: str = Form(...), role: str = Form(...), _admin=Depends(require_role('admin'))):
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM users WHERE username = %s', (username,))
            ur = cur.fetchone()
            if not ur:
                raise HTTPException(status_code=404, detail='User not found')
            uid = ur[0]
            cur.execute('SELECT id FROM roles WHERE name = %s', (role,))
            rr = cur.fetchone()
            if not rr:
                raise HTTPException(status_code=404, detail='Role not found')
            rid = rr[0]
            cur.execute('INSERT INTO user_roles (user_id, role_id) VALUES (%s,%s) ON CONFLICT DO NOTHING', (uid, rid))
            conn.commit()
            return {'ok': True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('assign_role failed: %s', e)
        raise HTTPException(status_code=500, detail='Failed to assign role')


@app.post('/roles/unassign')
async def unassign_role(username: str = Form(...), role: str = Form(...), _admin=Depends(require_role('admin'))):
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM users WHERE username = %s', (username,))
            ur = cur.fetchone()
            if not ur:
                raise HTTPException(status_code=404, detail='User not found')
            uid = ur[0]
            cur.execute('SELECT id FROM roles WHERE name = %s', (role,))
            rr = cur.fetchone()
            if not rr:
                raise HTTPException(status_code=404, detail='Role not found')
            rid = rr[0]
            cur.execute('DELETE FROM user_roles WHERE user_id = %s AND role_id = %s', (uid, rid))
            conn.commit()
            return {'ok': True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('unassign_role failed: %s', e)
        raise HTTPException(status_code=500, detail='Failed to unassign role')


@app.get('/admin/users')
async def list_users(_admin=Depends(require_role('admin'))):
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT u.id, u.username, array_agg(r.name) as roles FROM users u LEFT JOIN user_roles ur ON u.id = ur.user_id LEFT JOIN roles r ON ur.role_id = r.id GROUP BY u.id, u.username ORDER BY u.id')
            rows = cur.fetchall()
        users = []
        for r in rows:
            uid = r[0]
            uname = r[1]
            rnames = r[2] or []
            # normalize array_agg result which may be returned as list or string
            if isinstance(rnames, str):
                try:
                    import ast
                    parsed = ast.literal_eval(rnames)
                    rnames = parsed if isinstance(parsed, (list, tuple)) else [rnames]
                except Exception:
                    rnames = [rnames]
            users.append({'id': uid, 'username': uname, 'roles': [x for x in (rnames or []) if x]})
        return {'users': users}
    except Exception as e:
        logger.exception('list_users failed: %s', e)
        raise HTTPException(status_code=500, detail='Failed to list users')


@app.get('/roles')
async def list_roles(user = Depends(get_current_user)):
    with conn.cursor() as cur:
        cur.execute('SELECT id, name FROM roles ORDER BY id')
        rows = cur.fetchall()
    return {'roles': [{'id': r[0], 'name': r[1]} for r in rows]}


# ============================================================
# ADMIN ENDPOINTS: USER CRUD
# ============================================================

@app.post('/admin/users')
async def create_user(username: str = Form(...), password: str = Form(...), roles: str = Form(''), _admin=Depends(require_role('admin'))):
    """Create a new user with optional role assignments (comma-separated role names)"""
    try:
        with conn.cursor() as cur:
            # Check if user already exists
            cur.execute('SELECT id FROM users WHERE username = %s', (username,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail='Username already exists')
            
            # Create user
            password_hash = create_password_hash(password)
            cur.execute('INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id', (username, password_hash))
            user_id = cur.fetchone()[0]
            conn.commit()
            
            # Assign roles if provided
            if roles:
                role_list = [r.strip() for r in roles.split(',') if r.strip()]
                for role_name in role_list:
                    cur.execute('SELECT id FROM roles WHERE name = %s', (role_name,))
                    role_row = cur.fetchone()
                    if role_row:
                        cur.execute('INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (user_id, role_row[0]))
                conn.commit()
            
            logger.info(f'Admin created user: {username} with roles: {roles}')
            return {'ok': True, 'user_id': user_id, 'username': username}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('create_user failed: %s', e)
        raise HTTPException(status_code=500, detail='Failed to create user')


@app.put('/admin/users/{user_id}/password')
async def update_user_password(user_id: int, new_password: str = Form(...), _admin=Depends(require_role('admin'))):
    """Change a user's password"""
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, username FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail='User not found')
            
            password_hash = create_password_hash(new_password)
            cur.execute('UPDATE users SET password_hash = %s WHERE id = %s', (password_hash, user_id))
            conn.commit()
            
            logger.info(f'Admin changed password for user: {user[1]}')
            return {'ok': True, 'username': user[1]}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('update_user_password failed: %s', e)
        raise HTTPException(status_code=500, detail='Failed to update password')


@app.delete('/admin/users/{user_id}')
async def delete_user(user_id: int, _admin=Depends(require_role('admin'))):
    """Delete a user (cascades to user_roles)"""
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT username FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail='User not found')
            
            cur.execute('DELETE FROM users WHERE id = %s', (user_id,))
            conn.commit()
            
            logger.info(f'Admin deleted user: {user[0]}')
            return {'ok': True, 'username': user[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('delete_user failed: %s', e)
        raise HTTPException(status_code=500, detail='Failed to delete user')


# ============================================================
# ADMIN ENDPOINTS: SYSTEM CONFIGURATION
# ============================================================

@app.get('/admin/config')
async def get_system_config(_admin=Depends(require_role('admin'))):
    """Get all system configuration key-value pairs"""
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT key, value FROM system_config')
            rows = cur.fetchall()
        config = {row[0]: row[1] for row in rows}
        return {'config': config}
    except Exception as e:
        logger.exception('get_system_config failed: %s', e)
        raise HTTPException(status_code=500, detail='Failed to get system config')


@app.post('/admin/config')
async def update_system_config(key: str = Form(...), value: str = Form(...), _admin=Depends(require_role('admin'))):
    """Update a system configuration value"""
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO system_config (key, value, updated_at) 
                VALUES (%s, %s, NOW()) 
                ON CONFLICT (key) DO UPDATE 
                SET value = EXCLUDED.value, updated_at = NOW()
            ''', (key, value))
            conn.commit()
            logger.info(f'Admin updated system config: {key} = {value}')
        return {'ok': True, 'key': key, 'value': value}
    except Exception as e:
        logger.exception('update_system_config failed: %s', e)
        raise HTTPException(status_code=500, detail='Failed to update config')


@app.get('/admin/ollama/models')
async def get_ollama_models(_admin=Depends(require_role('admin'))):
    """Fetch available Ollama embedding models from localhost:11434/api/tags
    Filters only models suitable for embeddings (contain 'embedding' in name or are known embedding models)
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get('http://localhost:11434/api/tags')
            response.raise_for_status()
            data = response.json()
            models = data.get('models', [])
            
            # Known embedding model patterns (not LLMs)
            embedding_keywords = ['embedding', 'embed', 'nomic', 'bge', 'e5']
            
            # Filter only embedding models
            embedding_models = []
            for m in models:
                name = m.get('name', '').lower()
                if name and any(keyword in name for keyword in embedding_keywords):
                    embedding_models.append(m.get('name', ''))
            
            return {'models': embedding_models, 'total': len(models), 'embedding_count': len(embedding_models)}
    except Exception as e:
        logger.exception('get_ollama_models failed: %s', e)
        raise HTTPException(status_code=500, detail=f'Failed to fetch Ollama models: {str(e)}')


@app.get('/folders/')
async def list_folders():
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM folders ORDER BY id DESC")
        rows = cur.fetchall()
    folders = [{'id': r[0], 'name': r[1]} for r in rows]
    return {'folders': folders}


@app.post('/admin/fill_hashes/')
async def admin_fill_hashes():
    """Admin endpoint: compute SHA-256 fingerprints for PDFs with NULL hash
    by concatenating stored chunks (openai/ollama tables) and updating the pdfs table.
    Returns a summary of updated rows.
    """
    updated = []
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM pdfs WHERE hash IS NULL")
        rows = cur.fetchall()

    for (pdf_id,) in rows:
        chunks = []
        with conn.cursor() as cur2:
            try:
                cur2.execute("SELECT chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id", (pdf_id,))
                chunks += [r[0] for r in cur2.fetchall()]
            except Exception:
                pass
            try:
                cur2.execute("SELECT chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id", (pdf_id,))
                chunks += [r[0] for r in cur2.fetchall()]
            except Exception:
                pass

        if not chunks:
            continue

        combined = ''.join([c or '' for c in chunks])
        file_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        with conn.cursor() as cur3:
            cur3.execute("UPDATE pdfs SET hash = %s WHERE id = %s", (file_hash, pdf_id))
            conn.commit()
        updated.append({'id': pdf_id, 'hash': file_hash})

    return {'updated': updated, 'count': len(updated)}


# ============================================================================
# Endpoints de conversaciones (historial de chat por usuario)
# ============================================================================

@app.get('/conversations/')
async def list_conversations(user = Depends(get_current_user)):
    """Lista todas las conversaciones del usuario autenticado"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.id, c.pdf_id, c.title, c.created_at, c.updated_at, p.filename
            FROM conversations c
            LEFT JOIN pdfs p ON c.pdf_id = p.id
            WHERE c.user_id = %s
            ORDER BY c.updated_at DESC
        """, (user['id'],))
        rows = cur.fetchall()
    
    conversations = []
    for row in rows:
        conversations.append({
            'id': row[0],
            'pdf_id': row[1],
            'title': row[2],
            'created_at': row[3].isoformat() if row[3] else None,
            'updated_at': row[4].isoformat() if row[4] else None,
            'pdf_filename': row[5]
        })
    
    return {'conversations': conversations}


@app.get('/conversations/{conversation_id}/messages')
async def get_conversation_messages(conversation_id: int, user = Depends(get_current_user)):
    """Obtiene todos los mensajes de una conversación"""
    # Verificar que la conversación pertenece al usuario
    with conn.cursor() as cur:
        cur.execute("SELECT user_id, pdf_id FROM conversations WHERE id = %s", (conversation_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        if row[0] != user['id']:
            raise HTTPException(status_code=403, detail="No tienes permiso para acceder a esta conversación")
        pdf_id = row[1]
    
    # Obtener mensajes
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, role, content, sources, page_number, created_at
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        """, (conversation_id,))
        rows = cur.fetchall()
    
    messages = []
    for row in rows:
        import json
        sources = json.loads(row[3]) if row[3] else []
        messages.append({
            'id': row[0],
            'role': row[1],
            'content': row[2],
            'sources': sources,
            'page_number': row[4],
            'created_at': row[5].isoformat() if row[5] else None
        })
    
    return {
        'conversation_id': conversation_id,
        'pdf_id': pdf_id,
        'messages': messages
    }


@app.delete('/conversations/{conversation_id}')
async def delete_conversation(conversation_id: int, user = Depends(get_current_user)):
    """Elimina una conversación y todos sus mensajes"""
    # Verificar que la conversación pertenece al usuario
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM conversations WHERE id = %s", (conversation_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        if row[0] != user['id']:
            raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta conversación")
    
    # Eliminar conversación (los mensajes se eliminan en cascada)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        conn.commit()
    
    return {'success': True, 'message': 'Conversación eliminada correctamente'}

