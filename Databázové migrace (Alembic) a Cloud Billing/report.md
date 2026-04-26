# **PROMPTY A REPORT O POUŽITÍ AI**

## *Implementace Brokera*
1. "I currently have endpoints for buckets and files, this is the first task in our assignment about asynchronnous programming, and the assignment is about a pub/sub relationship done by a msg broker, how do I firstly create the broker endpoint?? and the broadcast method will be done by running through all the sockets related to the topic and using send_bytes(), yes?"

AI správně doplnila broadcast metodu v šabloně ConnectionManager, vysvětlila rovněž, že **asyncio.gather()** by se mohlo taky použít, ale for loop bohatě stačí. Vytvořila endpoint pro broker, správně použila asynchronismus.

## *Klient a podpora více formátů zpráv*
2. "second task, can you please explain a little further what he means by the fact that it could work in the two modes?"

AI vysvětlila, že skript se má chovat buď jako odesílatel, nebo přijímatel, podle toho jak se skript spustí. Navrhla **import argparse**, vygenerovala skript s metodami pro sub/pub logiku.

## *Zátěžové testy a měření propustnosti (benchmarking)*
3. "we are supposed to create a script that creates 5 concurrent subscribers and 5 concurrent publishers with asyncio.gather and have the publishers send 10000 messages, measure the total time in which all subscribers accept all messages and calculate throughput in msg/s... in both json and msgpack, how would you go about the calculations?"

AI vysvětlila, jak se bude počítat throughput: 5 publisherů * 10000 zpráv = 50000 zpráv. 50000 zpráv doručených 5 subscriberům je celkem 250000 zpráv.
AI definovala throughput jako: *Throughput (msg/s) = Total Delivered / Elapsed Time in seconds*.
Vysvětlila, že se bude testovat na pevně daném počtu zpráv, takže se bude iterovat přes přijaté zprávy ve while loopu dokud se nedosáhne hodnoty 50000.
AI také navrhla užití **asyncio.Event**, aby publisheři počkali, dokud nebude alespoň 5 subscriberů připojeno k brokeru.

## *Automatizované testy (pytest)*
4. "how do I test successful connection and whether the message really arrives?"

AI vysvětlila, že při použití *FastAPI TestClientu* stačí napsat synchronní testy. Vygenerovala testovací soubor pro 3 scénáře.

**Chyby AI a jejich opravy v této části:**
* **Chybějící inicializace databáze:** AI do testů nepřidala logiku pro vytvoření testovací databáze, kvůli čemuž testy padaly na neexistenci tabulky. Bylo nutné přidat automatické vytvoření a promazání tabulek (`Base.metadata.create_all` a `drop_all`) přes pytest `@fixture`.
* **Souběžné zamykání v testech:** AI navrhla testy, ve kterých se otevíralo více asynchronních spojení souběžně (např. spuštění Publishera i Subscribera ve stejném bloku `with`). `TestClient` ale interně vytváří oddělená vlákna, což ve spojení se synchronní SQLite databází vedlo ke smrtelnému uváznutí (deadlock) a testy se donekonečna zasekávaly. Kód testů musel být přepsán do **sekvenční** podoby – Publisher nejprve zprávu odešle a odpojí se (čímž se zpráva bezpečně uloží do perzistentní fronty) a až poté se připojí Subscriber, kterému broker zprávu zpětně doručí.

## *Garantované doručení a perzistence (Durable Queues)*
5. "regarding the first subtask in task number 5, how do I create payload that can have two datatypes?"

AI navrhla použít datový typ `LargeBinary`, s tím, že v případě JSONu se data před uložením zakódují.
AI vysvětlila rozdíl mezi `run_in_threadpool` a `AsyncSession` a zvolila implementaci pomocí `run_in_threadpool` pro odstínění blokujících databázových operací.

**Chyby AI a jejich opravy v této části:**
* **Absence Pydantic modelů:** AI zcela ignorovala požadavek v zadání na zavedení jednotného protokolu zpráv pomocí Pydantic modelů. Přijatá data pouze parsovala pomocí `json.loads` a četla jako slovníky. Bylo nutné manuálně do souboru `schemas.py` přidat modely (`WSPublishMessage`, `WSAckMessage`) a do `main.py` implementovat logiku, která přijatou zprávu přes tyto modely zvaliduje.
* **Deadlock kvůli globální injekci databáze:** Původní kód vkládal databázovou session do WebSocket endpointu přes závislost `Depends(get_db)`. Protože WebSocket spojení může trvat velmi dlouho (běží v nekonečné smyčce), databázová transakce zůstávala celou dobu otevřená a uzamkla SQLite pro všechny ostatní klienty. Bylo nutné závislost `Depends(get_db)` zcela odstranit z hlavičky a otevírat `Session` výhradně lokálně (přes `with Session(engine):`) uvnitř jednotlivých pomocných funkcí na pouhý zlomek sekundy.
* **DetachedInstanceError:** Po výše zmíněné opravě se začala objevovat chyba odpojené instance. Databáze se ihned zavřela, avšak kód se následně pokoušel přistoupit k atributu `new_message.id` již uloženého objektu. Oprava spočívala v ručním vygenerování UUID předem do proměnné a jejím následném použití namísto čtení z ORM modelu.
* **Logická chyba v Broadcast routingu:** Ačkoliv AI správně vytvořila nový tvar zprávy (obsahující `message_id` pod klíčem `deliver`), do finální metody `manager.broadcast()` omylem předávala proměnnou obsahující původní neupravená data zadaná uživatelem. Bylo nutné proměnnou v kódu ručně přepsat, aby se odběratelům odesílala upravená data s přiděleným ID potřebným pro úspěšné ACK potvrzení.