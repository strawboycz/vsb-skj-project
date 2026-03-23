#  Report o využití AI: Mini Cloud Storage

###  Jaké nástroje AI byly použity
* **Hlavní asistent:** Gemini Pro (Google)
* **Využití:** Generování základní kostry aplikace, vysvětlování chybových hlášek, návrh struktury pro práci se soubory a pomoc s testováním přes cURL.

###  Příklady promptů
Během vývoje byly použity například tyto prompty (postupný přístup):
1. *"mame za ukol tohle implementovat a pracovat s AI pomoz mi nejak pochopit a udelat kod ktery by to mohl splnovat postupne popisuj kroky"*
2. *[Zkopírovaná chybová hláška z terminálu]* *"TypeError: the 'package' argument is required to perform a relative import for '../projekt/main'"*
3. *"chci pridat users"* (Spolu s vložením stávajícího kódu pro úpravu).

###  Co AI vygenerovala správně
* **Základní kostru FastAPI aplikace:** Inicializace serveru a routování.
* **Práci se soubory:** Správné použití `python-multipart` (třída `UploadFile`) a asynchronní zápis na disk pomocí `aiofiles`.
* **Generování ID:** Správné zapojení knihovny `uuid` pro prevenci kolizí názvů souborů.
* **Strukturu metadat:** Ukládání informací do JSON slovníku v požadovaném formátu.
* **HTTP odpovědi:** Správné nastavení status kódů (404, 403) přes `HTTPException` a vrácení souboru přes `FileResponse`.

###  Co bylo nutné opravit a pochopit
* **Spouštění Uvicornu:** Pokus o spuštění serveru z nadřazené složky s relativní cestou (`uvicorn ../projekt/main:app`) vyhazoval chybu `TypeError` kvůli způsobu, jakým Uvicorn interpretuje moduly. Bylo nutné přejít přímo do složky projektu a spouštět lokálně.
* **Zastínění názvu (Name Shadowing):** Došlo k nedorozumění ohledně importu. Vytvořil jsem si omylem vlastní prázdný soubor `FileResponse.py`, což mátlo Python při snaze importovat originální nástroj z knihovny FastAPI. Soubor bylo nutné smazat, aby import `from fastapi.responses import FileResponse` fungoval.
* **Testování ve Windows:** Příkazy `curl` ze zadání (linuxové) bylo nutné v PowerShellu upravit na `curl.exe`, jinak by kolidovaly s vestavěným aliasem PowerShellu.

### Jaké chyby AI udělala
* **Zjednodušení na úkor zadání:** V prvním kroku AI navrhla řešit ukládání uživatelů přes statickou proměnnou `MOCK_USER_ID` rovnou v kódu. Kód sice fungoval, ale pro reálnou ukázku oddělení uživatelů to nestačilo. Musel jsem AI explicitně vyzvat k přidání uživatelů, načež kód přepsala tak, aby přijímal ID dynamicky přes HTTP hlavičku `X-User-ID`.
