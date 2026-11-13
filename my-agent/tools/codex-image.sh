#!/usr/bin/env bash
# Codex CLI 이미지 생성($imagegen)을 호출하고 결과 PNG를 원하는 경로로 가져옵니다.
# 사용:
#   tools/codex-image.sh -o posts/x/use-1.png -p "거실 소파 위 카본매트, 따뜻한 저녁 조명, 실사 사진" [-i 참고상품.jpg ...]
# -i 로 상품 이미지를 주면 그 제품 모양을 참고해 실사 연출 컷을 만듭니다.
# 주의: codex exec 는 종료코드 0이어도 파일이 안 생기는 경우가 있어, 결과 파일을 직접 확인합니다.
set -euo pipefail

OUT="" PROMPT="" IMAGES=()
while getopts "o:p:i:" opt; do
  case $opt in
    o) OUT="$OPTARG" ;;
    p) PROMPT="$OPTARG" ;;
    i) IMAGES+=("$OPTARG") ;;
    *) echo "사용: $0 -o 출력.png -p \"프롬프트\" [-i 참고이미지]" >&2; exit 2 ;;
  esac
done
[ -n "$OUT" ] && [ -n "$PROMPT" ] || { echo "-o 와 -p 는 필수예요" >&2; exit 2; }
command -v codex >/dev/null || { echo "codex CLI가 설치돼 있지 않아요 (npm i -g @openai/codex)" >&2; exit 1; }

GEN_DIR="${CODEX_HOME:-$HOME/.codex}/generated_images"
mkdir -p "$(dirname "$OUT")"
MARK=$(mktemp); trap 'rm -f "$MARK"' EXIT
ABS_OUT="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"

IMG_ARGS=()
for f in ${IMAGES[@]+"${IMAGES[@]}"}; do IMG_ARGS+=(-i "$f"); done

FULL_PROMPT='$imagegen '"$PROMPT"'
요구사항: 실사 사진 스타일, 가로 4:3, 글자·워터마크·로고 넣지 않기, 참고 이미지가 있으면 제품의 모양·색을 그대로 유지.
완성된 PNG를 '"$ABS_OUT"' 에 저장해 주세요.'

codex exec --skip-git-repo-check ${IMG_ARGS[@]+"${IMG_ARGS[@]}"} "$FULL_PROMPT" >/tmp/codex-image.log 2>&1 || {
  echo "codex 실행 실패 (로그: /tmp/codex-image.log)" >&2; exit 1; }

# 1순위: 요청한 경로에 저장됐는지
if [ -s "$ABS_OUT" ] && [ "$ABS_OUT" -nt "$MARK" ]; then echo "생성: $OUT"; exit 0; fi
# 2순위: Codex 기본 저장 폴더에서 이번 실행 이후 생긴 가장 최근 이미지
NEW=""
while IFS= read -r f; do
  if [ -z "$NEW" ] || [ "$f" -nt "$NEW" ]; then NEW="$f"; fi
done < <(find "$GEN_DIR" -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.webp' \) -newer "$MARK" 2>/dev/null)
if [ -n "$NEW" ]; then cp "$NEW" "$ABS_OUT"; echo "생성: $OUT (원본 $NEW)"; exit 0; fi

echo "이미지 파일을 찾지 못했어요 (로그: /tmp/codex-image.log)" >&2
exit 1
