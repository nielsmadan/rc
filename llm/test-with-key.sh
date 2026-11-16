#!/bin/bash
set -uo pipefail
set -a; . /etc/llm/llm.env; set +a
B=http://127.0.0.1:8000
code(){ curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$@"; }

echo "models with key:        $(code -H "Authorization: Bearer $VLLM_API_KEY" $B/v1/models)"
echo "--- chat completion"
curl -s --max-time 300 $B/v1/chat/completions \
  -H "Authorization: Bearer $VLLM_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.6-35b-a3b","messages":[{"role":"user","content":"What is 12*17? Answer with the number only."}],"max_tokens":800}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); m=d["choices"][0]["message"]; print("answer:", (m.get("content") or "").strip()); print("usage:", d.get("usage"))'
