# Dokumentace AI session – Mini Cloud Storage

## 1. Použité AI nástroje
- **ChatGPT (GPT-5-mini)** – generování Python/FastAPI kódu, Pydantic modelů, SQLAlchemy integrace, debugging.

## 2. Příklady promptů
- „změnit ukládání dat z JSON na SQLAlchemy“
- „create_file(db, file_data) db není definována“
- „finalni main.py s FastAPI“
- „http://127.0.0.1:8000/docs neexistuje“
- „implementovat validaci dat pomocí Pydantic“

## 3. Co AI vygenerovala správně
- SQLAlchemy modely a `database.py`
- CRUD endpoints v `main.py` s DB integrací
- Pydantic response modely (`schemas.py`)
- Použití `Depends(get_db)` místo `db` global
- Tipy na debugging a virtuální prostředí

## 4. Co bylo nutné opravit
- Explicitní předání `db` do funkcí (`create_file`, `get_file`, apod.)
- Spuštění serveru přes `python -m uvicorn main:app --reload`
- Instalace `python-multipart` pro upload souborů
- Návrat Pydantic modelů místo dictů
- Download endpoint nemá `response_model`

## 5. Chyby AI
- Nepředvídala chybějící `python-multipart`
- Používala deprecated `@app.on_event`
- Nedefinovala db ve všech voláních
- Nezdůraznila, že `FileResponse` nevyužívá Pydantic