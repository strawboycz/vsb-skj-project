## 1. konfigurace pocitace
 **os:** Ubuntu 24.04
 **cpu:** Intel Core Ultra 7 155H × 22
 **ram:** 32.0 GiB
 **python** Python 3.12

## 2. propustnost
s uzitim asyncio.gather()

# bez durable queues
*5 publisheru po 10000 zpravach, 5 subscriberu, celkovy pocet zprav 250000*

**JSON:** 69911 msgs/sec (čas: 3,58 s)
**MessagePack:** 72757 msgs/sec (čas: 3,44 s)

# s durable queues
*5 publisheru po 100 zpravach, 5 subscriberu, celkovy pocet zprav 2500*


**JSON:** 153 msgs/sec (čas: 16,32 s)
**MessagePack:** 235 msgs/sec (čas: 10,66s)

## 3. hodnoceni
bez durable queues byl MessagePack asi o 4% rychlejsi nez JSON, po pridani perzistence a ukladanim do databaze pri 50000 zpravach doslo k chybe *1011 keepalive ping timeout* a uzamceni databaze, protoze SQLite nestiha soubezny zapis, alternativou by bylo PostgreSQL, po snizeni zprav na 2500 byl MessagePack asi o 53% rychlejsi nez JSON
coz se ve vetsich skalach urcite vyplati, prenaseni mensich dat snizuje zatez, muze snizit i naklady (egress billing)
