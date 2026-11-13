#!/usr/bin/env bash
# 매일 아침 체험단 마감·색인·예약 현황을 텔레그램으로 보냅니다 (Claude 사용량 0).
# launchd(scripts/com.my-agent.daily.plist)가 실행합니다.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/tracker.py summary --days 3 | tools/notify.sh
