# Dokumentace AI session – Mini Cloud Storage

## 1. Použité AI nástroje
- **ChatGPT (GPT-5-mini)** – generování Python/FastAPI kódu, Pydantic modelů, SQLAlchemy integrace, debugging.

## 2. Příklady promptů
- „[main.py] ukolem je zmenit stavajici ukladani dat do JSON souboru na ukladani do databaze pomoci sqlalchemy, vytvor soubor ktery bude toto resit“
- „create_file(db, file_data) db není definována“
- „@app.on_event je depricated“
- „http://127.0.0.1:8000/docs nenacita“
- „Pro všechny vstupy a výstupy, tedy parametry endpointů a návratové hodnoty z nich, budeme pužívat Pydantic modely. Nadefinuj si jednotlivé modely pro requesty i response a ne jen obyčejné "raw" slovníky (dict) jako návratové hodnoty.“

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
