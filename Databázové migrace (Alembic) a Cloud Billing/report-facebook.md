# 🛠️ Report projektu: Implementace distribuované architektury Haystack

## 1. Účel a vize projektu
Cílem bylo postavit moderní cloudové úložiště obrázků, které se nenechá zpomalit velkým množstvím malých souborů. Inspirovali jsme se architekturou **Facebook Haystack**, která místo tisíců jednotlivých souborů na disku používá jeden velký binární svazek.

## 2. Co jsme dělali (Architektura systému)

### A. Haystack Node (Fyzické úložiště)
Vytvořili jsme dedikovanou službu (`haystack_node.py`), která spravuje soubory `.dat`.
- **Jak:** Místo `open("foto.jpg", "w")` používáme asynchronní zápis na konec jednoho velkého souboru. Každá fotka má svou adresu definovanou jako `(offset, size)`.
- **Proč:** Eliminujeme režii operačního systému při hledání metadat tisíců malých souborů.

### B. Event-Driven Gateway (Mozek systému)
Upravili jsme hlavní API (`main.py`) na plně asynchronní model.
- **Jak:** Gateway přijme fotku, uloží ji do fronty (Broker) a okamžitě vrátí uživateli odpověď. O skutečný zápis se postará až potvrzení z Haystacku.
- **Proč:** Uživatel nemusí čekat, až se data fyzicky zapíší na disk. Systém je díky tomu extrémně škálovatelný.

### C. Image Worker (Zpracování obrazu)
Vytvořili jsme konzumenta (`worker.py`), který provádí výpočetně náročné operace.
- **Jak:** Pomocí knihovny **NumPy** provádí maticové operace (negativ, překlopení, jas) přímo v paměti bez nutnosti ukládání dočasných souborů.
- **Proč:** Oddělení procesoru (CPU-bound úloh) od hlavního serveru, aby nahrávání fotek zůstalo rychlé.

### D. Kompaktor (Údržba a defragmentace)
Napsali jsme skript `compact.py` pro čištění disku.
- **Jak:** Skript projde svazek, vynechá "díry" po smazaných souborech a platná data přeskládá těsně za sebe.
- **Proč:** V Haystacku se soubory fyzicky nemažou (pouze logicky v DB), kompakce vrací volné místo zpět systému.

## 3. Jaké chyby se staly a jak jsme je vyřešili

### 🔴 Chyba 404 při kompakci
- **Problém:** Skript `compact.py` nemohl najít endpointy pro seznam souborů a aktualizaci souřadnic.
- **Příčina:** Tyto administrativní funkce nebyly původně v `main.py` implementovány.
- **Řešení:** Doplnili jsme administrativní endpointy `/admin/volume/{id}/files` a `/admin/files/{id}/relocate`.

### 🔴 Worker Error: Status Code 202
- **Problém:** Worker po nahrání upravené fotky nahlásil chybu, přestože nahrávání proběhlo.
- **Příčina:** Gateway v nové architektuře vracela kód `202 Accepted` (přijato do fronty), ale starý kód Workera očekával striktně `200 OK`.
- **Řešení:** Upravili jsme validaci v `worker.py`, aby akceptovala kódy `200`, `201` i `202`.

### 🔴 SQLITE_BUSY (Při zátěžových testech)
- **Problém:** Při velkém počtu zpráv v Brokeru došlo k uzamčení databáze.
- **Příčina:** SQLite nepodporuje vysokou míru souběžných zápisů z více vláken najednou.
- **Řešení:** Pro produkční nasazení by bylo nutné přejít na PostgreSQL, v našem případě jsme optimalizovali frekvenci ACK zpráv.

## 4. Instrukce pro spuštění

1. **Gateway:** `uvicorn main:app --reload` (port 8000)
2. **Haystack Node:** `python haystack_node.py` (port 8001)
3. **Worker:** `python worker.py` (naslouchá brokeru)
4. **Web:** `python -m http.server 3000` (přístup přes prohlížeč)

## 5. Závěr
Tento projekt demonstruje přechod od jednoduchého monolitického ukládání k **distribuovanému systému**. Nejdůležitějším poznatkem je, že v cloudu není nejdůležitější rychlost zápisu jednoho souboru, ale celková propustnost systému a schopnost obsloužit tisíce požadavků najednou bez blokování.
