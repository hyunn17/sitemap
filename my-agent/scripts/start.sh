#!/usr/bin/env bash
# 비서를 백그라운드(tmux)에서 켭니다. 맥을 켜 두는 동안 텔레그램으로 일을 시킬 수 있어요.
#   scripts/start.sh          # 켜기
#   tmux attach -t agent      # 화면 보기 (나올 땐 Ctrl+b 다음 d)
#   tmux kill-session -t agent  # 끄기
set -euo pipefail
cd "$(dirname "$0")/.."

SESSION=agent
# 권한 모드: default(매번 확인) | acceptEdits | auto. 처음엔 default로 맥 앞에서 '항상 허용'을 쌓는 걸 추천.
MODE="${PERMISSION_MODE:-default}"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "이미 켜져 있어요. 보려면: tmux attach -t $SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" -c "$PWD" \
  "claude --chrome --permission-mode $MODE --channels plugin:telegram@claude-plugins-official"
echo "비서를 켰어요. 화면 보기: tmux attach -t $SESSION"
