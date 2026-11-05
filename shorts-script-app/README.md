# Shorts Script Studio

떡상한 쇼츠의 후킹 구조를 분석해 쌓고, 리뷰할 제품에 대한 국내외 반응을 조사한 뒤,
가장 잘 맞는 템플릿으로 유튜브 쇼츠 대본을 써주는 앱입니다.

```
[1 떡상 영상 찾기] → [2 후킹 분석·수집] → [3 템플릿 구조화]
                                              ↓
[제품 입력] → [4 커뮤니티/SNS 반응 리서치] → [5 템플릿 선택 + 대본 작성]
```

## 각 단계가 하는 일

| 단계 | 방법 |
|---|---|
| **떡상 영상 찾기** | YouTube Data API로 키워드·기간·지역별 쇼츠(3분 이하) 검색. **떡상 점수 = 조회수 ÷ 구독자 수**(구독자 하한 1,000)로 정렬해, 큰 채널이라서가 아니라 영상 자체가 터진 경우를 찾습니다. 시간당 조회수도 함께 표시. |
| **후킹 분석** | 자막(자동 추출, 안 되면 직접 붙여넣기)을 Claude가 분석: 오프닝 훅, 중간 재후킹, 구조(타임라인), 이탈 방지 장치, CTA. |
| **후킹 멘트 수집** | 분석에서 나온 후킹 문장을 **유형(질문형/결과선공개/충격·반전/경고…)과 재사용 공식**(`[제품] [기간] 써보니 [결과]`)으로 DB에 누적. 중복 자동 제거, 즐겨찾기 가능. 자동수집을 켜면 주기적으로 계속 쌓입니다. |
| **템플릿 구조화** | 분석 결과 여러 개를 묶어 템플릿 생성. 각 템플릿엔 "어떤 여론 상황의 제품에 맞는지(best_for)"가 들어가 대본 작성 때 선택 기준이 됩니다. 기본 템플릿 5개(단점먼저 솔직후기, 결과 먼저, VS 비교, N가지 몰랐던 사실, 논란 정면돌파) 내장. |
| **제품 반응 리서치** | ① API 수집: Reddit, 네이버 블로그·카페·지식iN, 유튜브 리뷰 영상 댓글 ② Claude 웹검색: 네이트판, 디시, 더쿠, 에펨, 클리앙, 뽐뿌, 루리웹, 인스티즈, X, 인스타, 스레드, 틱톡, 해외 포럼/아마존 리뷰. 이를 종합해 칭찬·불만(빈도), 논쟁 포인트, 자주 묻는 질문, 국내 vs 해외 차이, 인용할 실제 반응, 기획 각도를 정리. |
| **대본 작성** | 리서치로 제품의 여론 유형을 판단 → 템플릿 자동 선택(이유 표시) → 후킹 라이브러리 공식을 변형한 훅 후보 3개 + 초 단위 대본(내레이션/자막/화면 지시) + 제목 후보, 고정 댓글, 해시태그, **촬영 전 사실 확인 목록**. |

## 설치 & 실행

```bash
cd shorts-script-app
pip install -r requirements.txt
cp .env.example .env        # 키 입력
uvicorn app.main:app --reload
# → http://localhost:8000
```

### 필요한 키

| 키 | 필수 | 발급 |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | https://console.anthropic.com |
| `YOUTUBE_API_KEY` | ✅ | Google Cloud Console → "YouTube Data API v3" 사용 설정 → 사용자 인증 정보 → API 키 |
| `NAVER_CLIENT_ID` / `SECRET` | 선택 | https://developers.naver.com → 애플리케이션 등록 → 검색 API |

YouTube API는 하루 10,000 유닛 무료이고, 검색 1회가 100 유닛입니다(키워드 1개 수집 ≈ 100~300 유닛).

## 후킹 멘트를 꾸준히 모으기

방법 1 — 서버에서 자동 수집 (`.env`):
```
AUTO_COLLECT_HOURS=12
AUTO_COLLECT_KEYWORDS=리뷰,언박싱,가성비,추천템,내돈내산
```

방법 2 — cron:
```bash
0 9 * * * cd /path/shorts-script-app && python -m app.cli collect 리뷰 언박싱 가성비 --days 3
```

## CLI

```bash
python -m app.cli collect 리뷰 언박싱 --days 7 --analyze-top 5
python -m app.cli templates
python -m app.cli research "갤럭시 버즈3 프로"
python -m app.cli script "갤럭시 버즈3 프로" --notes "노캔 만족, 착용감 애매" --length 40
```

## 구조

```
app/
  main.py           FastAPI 서버 + 자동수집 루프
  pipeline.py       수집 → 분석 → 템플릿 → 리서치 → 대본 오케스트레이션
  youtube.py        떡상 쇼츠 검색, 떡상 점수, 자막, 댓글
  communities.py    Reddit / 네이버 / 유튜브 댓글 수집
  llm.py            Claude 프롬프트 (분석, 템플릿, 웹검색 리서치, 종합, 대본)
  schemas.py        구조화 출력 스키마
  seed_templates.py 기본 템플릿 5개
  db.py             SQLite (data/shorts.db)
  static/index.html 웹 UI
tests/              외부 API를 가짜로 바꾼 전체 흐름 테스트 (python -m pytest tests)
```

## 알아둘 점

- **자막**: 쇼츠는 자막이 없거나 클라우드 서버 IP에서 자막 추출이 막히는 경우가 많습니다. 이때는 제목·설명으로 추정 분석하며, '분석' 버튼에서 대본을 직접 붙여넣으면 정확도가 올라갑니다.
- **커뮤니티 수집**: 네이트판·디시 등은 공식 API가 없어 직접 크롤링하지 않고 Claude 웹검색으로 조사합니다(사이트 이용약관 준수). 검색에 잡히지 않는 글은 빠질 수 있고, 리포트의 `coverage_notes`에 한계가 표시됩니다.
- **Reddit**: 공개 JSON 엔드포인트를 쓰며, 서버 IP에 따라 차단될 수 있습니다(실패해도 나머지 출처로 진행).
- **비용**: 기본 모델은 `claude-opus-5-5`. 영상 분석 1건, 리서치 1건, 대본 1건마다 Claude 호출이 발생합니다. `.env`의 `CLAUDE_MODEL`로 변경 가능.
- 대본의 `[직접 사용 경험: ...]` 자리와 '촬영 전 확인할 것' 목록은 꼭 직접 채우고 확인하세요.
