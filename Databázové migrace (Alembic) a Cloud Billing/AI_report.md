# 🧠 Report o využití AI: Projekt Mini Cloud Storage

## 🛠  Základní informace a nástroje
* **Použitý AI asistent:** Gemini (Google)
* **Hlavní přínos AI:** Generování kostry aplikace, návrh relačních databázových modelů v moderním standardu (SQLAlchemy 2.0), vysvětlování chybových hlášení (Tracebacks), konfigurace Alembicu pro bezpečné migrace a pochopení logiky cloudového účtování (Ingress/Egress).

---

## 💬 Příklady použitých promptů
Vývoj probíhal iterativně. Zde jsou ukázky klíčových promptů, které formovaly projekt:

1. *"Máme za úkol tohle implementovat a pracovat s AI, pomoz mi nějak pochopit a udělat kód, který by to mohl splňovat, postupně popisuj kroky."*
2. *"TypeError: the 'package' argument is required to perform a relative import for '../projekt/main'"* (Řešení chyby při spouštění serveru).
3. *"Použij při práci s databází podobnou strukturu jako je tady [ukázka kódu]. Tohle jsme si zkoušeli na cvičení."* (Zajištění použití správné a moderní verze SQLAlchemy 2.0).
4. *"V minulém cvičení jsme naimplementovali perzistenci... Řešením jsou databázové migrace... Pomoz mi s tím a velice detailně a pomalu mě naváděj, co mám udělat."* (Start Fáze 3 s Alembicem a Billingem).
5. *"Traceback... AttributeError: type object 'bool' has no attribute '_set_parent_with_dispatch'"* (Řešení pádu Alembicu při Soft Delete).

---

## ☁️ Databázové migrace (Alembic) a Cloud Billing

### ✅ Co AI vygenerovala správně:
* **Architektura migrací:** AI vysvětlila rozdíl mezi `Base.metadata.create_all()` (které může způsobit ztrátu dat) a bezpečnými migracemi přes Alembic. Správně mě navedla k vymazání generování tabulek z `main.py`.
* **Ekonomika cloudu (Billing):** Navrhla elegantní řešení pro odlišení interního a externího provozu pomocí boolean HTTP hlavičky `X-Internal-Source`.
* **Soft Delete:** Pomohla mi pochopit koncept, kde operace `DELETE` ve skutečnosti soubor nemaže, ale pouze mu v databázi změní příznak `is_deleted = True`. Zaručila také, že i přesto se klientovi nadále účtuje zabrané místo (`current_storage_bytes`), protože data na serveru fyzicky existují.

### 🔧 Jaké chyby bylo nutné řešit s Alembicem:
* **Slepý Alembic (env.py):** Při prvním spuštění `--autogenerate` Alembic nenašel žádné tabulky a vyhodil chybu. AI mi vysvětlila, že je nutné do `env.py` nejen vložit kořenovou cestu projektu, ale také **explicitně importovat všechny modely** (`User`, `Bucket`, `FileMetadata`), jinak je SQLAlchemy nenačte do paměti a Alembic nemá metadata s čím porovnat.
* **Spouštění Uvicornu:** Zjistil jsem, že Uvicorn bere parametr před dvojtečkou jako Python modul, nikoliv jako cestu ke složce.
* **Typová chyba v SQLAlchemy (mapped_column):** Při implementaci Soft Delete mi AI v modelu původně navrhla zápis `is_deleted: Mapped[bool] = mapped_column(bool, default=False)`. To vedlo k chybě `ArgumentError` při generování migrace. Funkce `mapped_column()` totiž striktně vyžaduje databázový typ (`Boolean` ze SQLAlchemy), nikoliv čistý Python typ `bool`. Po poskytnutí Tracebacku AI chybu okamžitě opravila.
