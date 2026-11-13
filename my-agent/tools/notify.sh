#!/usr/bin/env bash
# 텔레그램으로 메시지 보내기 (Claude 세션이 꺼져 있어도 동작).
# 사용: tools/notify.sh "메시지"   또는   echo "메시지" | tools/notify.sh
# 토큰: TELEGRAM_BOT_TOKEN 환경변수, 없으면 ~/.claude/channels/telegram/.env 에서 읽음.
# 대화 ID: TELEGRAM_CHAT_ID 환경변수, 없으면 data/telegram_chat_id 파일.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] && [ -f "$HOME/.claude/channels/telegram/.env" ]; then
  TELEGRAM_BOT_TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$HOME/.claude/channels/telegram/.env" | head -1 | cut -d= -f2- | tr -d '"'"'")
fi
if [ -z "${TELEGRAM_CHAT_ID:-}" ] && [ -f data/telegram_chat_id ]; then
  TELEGRAM_CHAT_ID=$(tr -d '[:space:]' < data/telegram_chat_id)
fi
: "${TELEGRAM_BOT_TOKEN:?텔레그램 봇 토큰이 없어요 (README 3단계)}"
: "${TELEGRAM_CHAT_ID:?data/telegram_chat_id 파일에 내 텔레그램 ID를 넣어 주세요 (README 3단계)}"

if [ $# -gt 0 ]; then MSG="$*"; else MSG=$(cat); fi

curl -sS --fail -o /dev/null \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${MSG}"
echo "보냄"
