# vsb-skj-project
AI slop 


📦 Object Storage Service

Jednoduchá backendová služba pro ukládání souborů (inspirovaná S3).

🚀 Funkce
upload souborů
stažení souborů
mazání souborů
správa metadat
📡 API
POST /files – upload
GET /files/{id} – download
GET /files/{id}/metadata – metadata
DELETE /files/{id} – smazání
🛠️ Stack (libovolný)
Node.js / Python / Java
lokální disk + metadata (JSON / DB)
