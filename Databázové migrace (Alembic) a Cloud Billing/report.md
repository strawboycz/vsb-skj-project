AI REPORT: IMPLEMENTACE IMAGE PROCESSORU (ÚKOL 6)
PROMPTY A REÁLNÝ KONTEXT
1. Řešení počátečního timeoutu
Prompt: "FAILED tests_worker.py::test_worker_processes_10_tasks - Failed: Worker nestihl zpracovat úlohy včas (Timeout)."

Kontext: Na začátku vývoje integrační test odesílal 10 zpráv příliš rychle. AI analyzovala, že SQLite nezvládá souběžné zamykání při zápisu zpráv a ACK potvrzení zároveň.

Řešení: AI navrhla přepsat test do sekvenční podoby, kde se každá zpráva pošle, zpracuje a potvrdí (ACK) samostatně, což eliminovalo zamykání databáze.

2. Přechod na Vanilla JS (Klientské UI)
Prompt: "vytvoříme úplně jednoduchou react aplikaci" -> "hej vis co, napisme to ciste v js"

Kontext: Rozhodnutí zjednodušit technologický stack vedlo k vytvoření index.html. Zde se objevil problém s CORS a bezpečností prohlížeče při otevírání souboru přímo z disku (file:///).

Řešení: AI doplnila implementaci CORSMiddleware na backendu a doporučila spuštění frontendu přes lokální server python -m http.server 3000.

3. Debugging WebSocket komunikace (Blob vs. Text)
Prompt: "[WS] PŘIJATA ZPRÁVA: Blob ... Unexpected token 'o', '[object Blob]' is not valid JSON"

Kontext: Tato technická překážka spočívala v tom, že FastAPI Broker odesílal byty, které prohlížeč interpretoval jako binární Blob. Pokus o JSON.parse() na tomto objektu způsoboval pád aplikace.

Řešení: AI upravila kód o asynchronní čtení await event.data.text() a balení odchozích zpráv do new Blob(), aby byla zajištěna kompatibilita s receive_bytes() na straně FastAPI.

4. Oprava logiky ořezu (Crop)
Prompt: "mas tam spatne jak se pocitaji ty souradnice, zamysli se nad tim"

Kontext: AI původně navrhla ořez pomocí absolutních indexů matice (NumPy slicing), což bylo pro uživatele nepraktické a vyžadovalo manuální výpočet souřadnic.

Řešení: AI přepracovala logiku na okraje (margins). Uživatel nyní zadává, kolik pixelů chce uříznout z každé strany (Top, Bottom, Left, Right), což je intuitivnější.

CHYBY AI A JEJICH OPRAVY (V TÉTO KONVERZACI)
Chyba v datovém typu (The Blob Fail): AI v prvním návrhu index.html opomněla, že prohlížeč neumí automaticky parsovat binární WebSocket zprávy jako JSON.

Oprava: Na základě chyby v konzoli AI kód doplnila o detekci instanceof Blob a následnou konverzi na text.

Ghosting starých zpráv: AI podcenila přítomnost nevyřízených zpráv v perzistentní frontě (SQLite) z předchozích neúspěšných testů. To způsobovalo zobrazení chyb (404) u neexistujících testovacích souborů.

Oprava: AI doplnila ACK logiku do frontendu, aby se i chybové zprávy z fronty korektně vyčistily.

Špatná implementace ořezu: Původní návrh ořezu byl matematicky funkční pro NumPy, ale uživatelsky nevyhovující (např. vyžadoval záporná čísla pro ořez zdola).

Oprava: Po upozornění uživatele AI logiku ve Workeru i v UI přepsala na srozumitelný systém odsazení od hran.

Absence CORS konfigurace: AI navrhla frontendový kód, ale původně neupozornila na nutnost úpravy backendu pro povolení Cross-Origin požadavků z prohlížeče.

Oprava: AI dodatečně vygenerovala potřebnou konfiguraci CORSMiddleware pro FastAPI aplikaci.