#**PROMPTY**
##*Implementace Brokera*
1. "I currently have endpoints for buckets and files, this is the first task in our assignment about asynchronnous programming, and the assignment is about a pub/sub relationship done by a msg broker, how do I firstly create the broker endpoint?? and the broadcast method will be done by running through all the sockets related to the topic and using send_bytes(), yes?"

AI spravne doplnila broadcast metodu v sablone ConnectionManager, vysvetlila rovnez ze **asyncio.gather()** by se mohlo taky pouzit ale for loop bohate staci.
Vytvorila endpoint pro broker, spravne pouzila asynchronismus.

##*Klient a podpora více formátů zpráv*
2. "second task, can you please explain a little further what he means by the fact that it could work in the two modes?"

AI vysvetlila, ze skript se ma chovat bud jako odesilatel nebo prijimatel, podle toho jak se skript spusti. Navrhla **import argparse**, vygenerovala skript s metodami pro sub/pub logiku.

##*Zátěžové testy a měření propustnosti (benchmarking)*
3. "we are supposed to create a script that creates 5 concurrent subscribers and 5 concurrent publishers with asyncio.gather and have the publishers send 10000 messages, measure the total time in which all subscribers accept all messages and calculate throughput in msg/s... in both json and msgpack, how would you go about the calculations?"

AI vysvetlila, jak bude pocitat throughput, 5 publisheru * 10000 zprav = 50000 zprav, 50000 zprav dorucenych 5 subscriberum je 250000 zprav.
AI definovala throughput jako: *Throughput (msg/s) = Total Delivered / Elapsed Time in seconds*.
Vysvetlila, ze budeme testovat na pevne danem poctu zprav, takze budeme iterovat pres prijate zpravy v while loopu dokud nedostaneme 50000.
AI taky navrhla uziti **asyncio.Event** aby publisheri pockali, dokud nebude aspon 5 subscriberu pripojeno k brokeru.


##*Automatizované testy (pytest)*
4. "how do I test successful connection and whether the message really arrives?"
AI vysvetlila ze pri pouziti *FastAPI TestClientu* staci napsat synchronni testy. Vygenerovala testovy soubor pro 3 scenare.

##*Garantované doručení a perzistence (Durable Queues)*
5. "regarding the first subtask in task number 5, how do I create payload that can have two datatypes?"

AI navrhla pouzit jen LargeBinary, s tim ze v pripade JSONu se data zakoduji.
Pri ukladani do databaze chybelo generovani UUID, coz crashovalo server.

AI vysvetlila rozdil mezi *run_in_threadpool* a *AsyncSession*, implementovala run_in_threadpool.

Pri testovani rychlosti SQLite nestihalo soubezny zapis zprav a ACK -> pro testovaci zamery se *snizil pocet zprav*.










