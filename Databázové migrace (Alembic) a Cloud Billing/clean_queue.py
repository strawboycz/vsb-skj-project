import sqlite3

# Připojí se k tvojí databázi
conn = sqlite3.connect("storage.db")
cursor = conn.cursor()

# Všem zprávám ve frontě nastaví, že jsou doručené (broker je bude ignorovat)
cursor.execute("UPDATE queued_messages SET is_delivered = 1")

conn.commit()
conn.close()
print("Fronta zpráv byla úspěšně vyčištěna!")