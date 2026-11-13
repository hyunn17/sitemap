# my-agent — 텔레그램으로 부리는 개인 비서 (Claude 구독 사용)

Pickle처럼 **실제 사람이 컴퓨터를 쓰듯** 맥의 Chrome을 직접 조작해서 일을 처리하는 비서입니다.
API 키 없이 **Claude Pro/Max 구독**으로 돌아갑니다.

```
휴대폰 텔레그램 ──▶ 맥에서 실행 중인 Claude Code ──▶ Chrome(내가 로그인해 둔 그대로)
       ▲                    │  CLAUDE.md(규칙) + 스킬 5개 + tracker(이력 DB)
       └──── 답장·승인 요청 ─┘
```

| 하는 일 | 스킬 |
|---|---|
| 블로그 글 작성(4유형) → 승인 → 티스토리 발행/예약 | `blog-post` |
| 네이버·구글 색인 요청 | `index-request` |
| 스타일씨 체험단 찾기·신청 | `stylec` |
| 리뷰통 이력 동기화·마감 알림 | `reviewtong` |
| 쿠팡 리뷰 초안 → 승인 → 등록 | `coupang-review` |
| 매일 아침 현황 요약 | `scripts/daily-summary.sh` |

## 맥에 설치하기

### 1. 준비물
- Claude **Max 구독 추천** (브라우저 작업은 사용량이 많아서 Pro는 한도에 금방 닿을 수 있어요)
- Chrome + [Claude in Chrome 확장](https://claude.ai/chrome) 설치 후 같은 Claude 계정으로 로그인
- 터미널에서:
  ```bash
  curl -fsSL https://claude.ai/install.sh | bash   # Claude Code
  curl -fsSL https://bun.sh/install | bash          # 텔레그램 플러그인에 필요
  brew install tmux                                 # 백그라운드 실행용 (Homebrew 필요)
  ```
- 이 저장소를 받고 폴더로 이동: `git clone <저장소 주소> && cd sitemap/my-agent`

### 2. Chrome에서 직접 로그인해 두기
비서는 비밀번호를 받지 않고, **내가 로그인해 둔 Chrome**을 그대로 씁니다.
티스토리, 네이버(서치어드바이저), 구글(서치콘솔), 쿠팡, 쿠팡 파트너스, 스타일씨, 리뷰통에 로그인해 두세요.

### 3. 텔레그램 봇 연결
1. 텔레그램에서 **@BotFather** → `/newbot` → 이름 정하기 → 토큰 복사
2. 이 폴더에서 `claude` 실행 후:
   ```
   /plugin install telegram@claude-plugins-official
   /telegram:configure <토큰>
   ```
   (설치 범위는 user 선택. "/reload-plugins" 안내가 나오면 실행)
3. `/exit`로 나간 뒤 `claude --channels plugin:telegram@claude-plugins-official` 로 다시 실행
4. 텔레그램에서 내 봇에게 아무 말이나 보내면 페어링 코드가 옴 → Claude에서:
   ```
   /telegram:access pair <코드>
   /telegram:access policy allowlist
   ```
5. 아침 요약용으로 내 텔레그램 ID 저장: 텔레그램 **@userinfobot**에게 말 걸면 숫자 ID를 알려 줘요.
   ```bash
   echo 123456789 > data/telegram_chat_id
   tools/notify.sh "테스트"   # 텔레그램에 '테스트'가 오면 성공
   ```

### 4. 비서 켜기
```bash
scripts/start.sh            # tmux 백그라운드에서 실행
tmux attach -t agent        # 화면 보기 (빠져나오기: Ctrl+b 누르고 d)
```
**처음 며칠은 맥 앞에서** 텔레그램으로 일을 시켜 보고, 뜨는 권한 확인에 "항상 허용"을 눌러 쌓아 두세요.
맥 앞에 없을 때 권한 확인이 뜨면 거기서 멈춥니다. 익숙해지면 `PERMISSION_MODE=acceptEdits scripts/start.sh` 처럼 바꿀 수 있어요.

맥이 잠자기에 들어가면 비서도 멈춰요: **시스템 설정 → 배터리/에너지 → 디스플레이가 꺼져도 잠자기 방지** 켜기.

### 5. 매일 아침 요약 (선택)
```bash
sed "s#__AGENT_DIR__#$PWD#" scripts/com.my-agent.daily.plist > ~/Library/LaunchAgents/com.my-agent.daily.plist
launchctl load ~/Library/LaunchAgents/com.my-agent.daily.plist
```
매일 08:37에 마감·발표·색인 현황이 텔레그램으로 옵니다 (Claude 사용량 안 씀).
스타일씨 새 캠페인 확인처럼 브라우저가 필요한 정기 작업은 텔레그램으로
"매일 오전 10시에 스타일씨 새 캠페인 확인해줘"라고 시키면 실행 중인 세션이 일정을 잡습니다.

## 텔레그램으로 이렇게 시키면 돼요
- `카본매트 vs 온수매트 비교글 써줘. 내일 아침 8시 예약발행`
- `어제 올린 글 색인 등록해줘`
- `스타일씨에 주방용품 체험단 있나 봐줘`
- `리뷰통 이력 정리하고 이번 주 마감 알려줘`
- `쿠팡 리뷰 쓸 거 있어?` → 목록 받고 → `2번, 별 4개` + 사진 → 체크리스트에 `1,3,4`
- `전기요 실사용 후기 써줘` + 사진 → 체크리스트에 `다 맞아`

## 원칙 (CLAUDE.md에 들어 있음)
- 발행·신청·리뷰 등록·결제는 **텔레그램 승인 후에만** 합니다.
- 실사용 후기는 경험을 직접 적지 않아도 됩니다. 비서가 상품평에서 뽑은 **경험 체크리스트**를 보내면
  맞는 번호만 고르세요("다 맞아" / "1,3,5"). 고른 항목만 내 경험으로 씁니다.
- 쿠팡 파트너스 문구, 체험단 협찬 문구를 자동으로 넣습니다.
- 비밀번호는 저장하지 않고, 캡차·본인인증은 사람에게 넘깁니다.

## 이력 직접 보기
```bash
python3 tools/tracker.py summary
python3 tools/tracker.py posts
python3 tools/tracker.py campaigns --platform stylec
```
