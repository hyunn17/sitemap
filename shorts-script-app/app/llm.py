"""Claude 호출: 영상 후킹 분석, 템플릿 구조화, 제품 반응 웹리서치/종합, 대본 작성."""
import json
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from . import config
from .schemas import ResearchReport, ShortsScript, TemplateSet, VideoAnalysis

T = TypeVar("T", bound=BaseModel)

FALLBACK_BETA = "server-side-fallback-2026-07-01"
_client: anthropic.Anthropic | None = None


class LLMError(RuntimeError):
    pass


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise LLMError("ANTHROPIC_API_KEY가 설정되지 않았습니다 (.env 확인)")
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


# ---- 공통 헬퍼 -------------------------------------------------------------------

def strict_schema(model: type[BaseModel]) -> dict:
    """pydantic 스키마를 구조화 출력용(모든 필드 required, additionalProperties=false)으로 변환."""
    schema = model.model_json_schema()

    def fix(node):
        if isinstance(node, list):
            for v in node:
                fix(v)
            return
        if not isinstance(node, dict):
            return
        node.pop("default", None)
        if isinstance(node.get("title"), str):
            node.pop("title")
        if "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"].keys())
            for v in node["properties"].values():  # 속성 이름 자체는 건드리지 않음
                fix(v)
        for k, v in node.items():
            if k != "properties":
                fix(v)

    fix(schema)
    return schema


def _stream(**kwargs) -> anthropic.types.beta.BetaMessage:
    try:
        with client().beta.messages.stream(
            model=config.CLAUDE_MODEL,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            thinking={"type": "adaptive"},
            **kwargs,
        ) as s:
            msg = s.get_final_message()
    except anthropic.AuthenticationError as e:
        raise LLMError("Claude API 키가 올바르지 않습니다") from e
    except anthropic.RateLimitError as e:
        raise LLMError("Claude API 요청 한도 초과. 잠시 후 다시 시도하세요") from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"Claude API 오류 ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise LLMError("Claude API 연결 실패. 네트워크를 확인하세요") from e
    if msg.stop_reason == "refusal":
        detail = getattr(msg.stop_details, "explanation", None) if msg.stop_details else None
        raise LLMError(f"Claude가 요청을 거절했습니다: {detail or '사유 미제공'}")
    return msg


def ask_json(model: type[T], system: str, user: str, effort: str = "high",
             max_tokens: int = 32000) -> T:
    msg = _stream(
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort,
                       "format": {"type": "json_schema", "schema": strict_schema(model)}},
    )
    if msg.stop_reason == "max_tokens":
        raise LLMError("응답이 너무 길어 잘렸습니다. 입력을 줄여 다시 시도하세요")
    text = "".join(b.text for b in msg.content if b.type == "text")
    return model.model_validate_json(text)


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1)


# ---- 1. 떡상 영상 분석 ---------------------------------------------------------------

ANALYSIS_SYSTEM = """당신은 유튜브 쇼츠 리텐션 분석가다. 조회수가 폭발한 쇼츠의 대본을 해부해서,
다른 크리에이터가 다른 제품에도 그대로 가져다 쓸 수 있는 '후킹 구조'를 뽑아낸다.

- 첫 1~3초의 오프닝 훅이 왜 스와이프를 멈추게 하는지 구체적으로 설명한다.
- 오프닝 훅뿐 아니라 중간 재후킹(이탈 방지 멘트), 결말 직전 긴장 유지 멘트도 hook_lines에 모은다.
- pattern은 고유명사를 [제품], [기간], [가격], [결과] 같은 빈칸으로 바꾼 재사용 공식으로 쓴다.
- 자막이 없으면 제목·설명·통계만으로 추정하고, 추정임을 summary에 밝힌다.
- 출력은 한국어. 단 text 필드의 원문 문장은 원어 그대로 둔다."""


def analyze_video(video: dict) -> VideoAnalysis:
    transcript = video.get("transcript") or "(자막 없음)"
    user = f"""다음 쇼츠를 분석해줘.

제목: {video.get('title')}
채널: {video.get('channel_title')} (구독자 {video.get('subscribers'):,}명)
조회수: {video.get('views'):,} / 좋아요 {video.get('likes'):,} / 댓글 {video.get('comments'):,}
구독자 대비 조회수 배율: {video.get('viral_score')}배, 시간당 조회수: {video.get('views_per_hour')}
길이: {video.get('duration_sec')}초
설명: {(video.get('description') or '')[:1000]}

대본(타임스탬프 자막):
{transcript[:15000]}"""
    return ask_json(VideoAnalysis, ANALYSIS_SYSTEM, user, effort="high")


# ---- 2. 템플릿 구조화 ------------------------------------------------------------------

TEMPLATE_SYSTEM = """당신은 쇼츠 대본 템플릿 설계자다. 여러 떡상 쇼츠의 분석 결과를 비교해
반복적으로 등장하는 구조를 묶어 '제품 리뷰 쇼츠'용 대본 템플릿으로 만든다.

- 서로 확실히 구분되는 템플릿만 만든다(같은 구조를 이름만 바꿔 중복 생성하지 않는다).
- best_for에는 '어떤 여론 상황의 제품'에 맞는지 적는다. 예: 단점 논란이 큰 제품, 가성비로 화제인 제품,
  비싼데 만족도가 높은 제품, 경쟁 제품과 자주 비교되는 제품, 사용법을 몰라 불만이 많은 제품.
  이 정보는 나중에 제품 리서치 결과를 보고 템플릿을 고르는 기준이 된다.
- 각 섹션 instructions는 처음 보는 사람이 바로 대본을 쓸 수 있을 만큼 구체적으로 쓴다.
- 기존 템플릿 목록이 주어지면 그것과 겹치지 않는 새 구조만 추가하거나, 같은 구조라면 같은 name으로
  더 나은 버전을 만든다."""


def build_templates(analyses: list[dict], existing: list[dict], max_templates: int = 5) -> TemplateSet:
    slim_existing = [{"name": t["name"], "description": t["description"],
                      "best_for": t["best_for"]} for t in existing]
    user = f"""떡상 쇼츠 분석 결과 {len(analyses)}개를 보고 템플릿을 최대 {max_templates}개 만들어줘.

기존 템플릿:
{_dump(slim_existing)}

분석 결과:
{_dump(analyses)}"""
    return ask_json(TemplateSet, TEMPLATE_SYSTEM, user, effort="high")


# ---- 3. 제품 반응 리서치 -----------------------------------------------------------------

WEB_RESEARCH_SYSTEM = """당신은 소비자 여론 리서처다. 웹검색으로 특정 제품에 대한 '실제 사용자 반응'을 조사한다.
광고·보도자료·공식 스펙 소개가 아니라 사람들이 직접 쓴 후기, 불만, 질문, 논쟁을 찾는다.

반드시 아래 출처를 골고루 검색한다(site: 연산자 활용):
- 국내 커뮤니티: 네이트판(pann.nate.com), 디시인사이드(dcinside.com), 더쿠(theqoo.net),
  에펨코리아(fmkorea.com), 클리앙(clien.net), 뽐뿌(ppomppu.co.kr), 루리웹(ruliweb.com),
  인스티즈(instiz.net), 네이버 카페/블로그
- SNS: X/트위터, 인스타그램, 스레드, 틱톡
- 해외: Reddit, 아마존 리뷰, 해외 포럼

각 출처마다 찾은 대표 반응을 짧게 인용하고 URL을 함께 적는다. 찾지 못한 출처는 '없음'으로 표시한다.
결과는 출처별로 정리한 한국어 메모로 작성한다."""


def web_research(product: str, max_searches: int = 15) -> dict:
    """Claude 웹검색으로 API 없는 커뮤니티/SNS 반응 조사. {'notes': str, 'urls': [...]} 반환."""
    messages = [{"role": "user", "content": f"제품: {product}\n이 제품에 대한 사람들의 반응을 조사해줘."}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches}]
    urls: list[str] = []
    notes: list[str] = []
    for _ in range(5):  # pause_turn 재개 최대 횟수
        msg = _stream(max_tokens=32000, system=WEB_RESEARCH_SYSTEM, messages=messages,
                      tools=tools, output_config={"effort": "medium"})
        for b in msg.content:
            if b.type == "text":
                notes.append(b.text)
            elif b.type == "web_search_tool_result" and isinstance(b.content, list):
                urls += [r.url for r in b.content if getattr(r, "url", None)]
        if msg.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": msg.content})
    return {"notes": "".join(notes), "urls": list(dict.fromkeys(urls))}


SYNTH_SYSTEM = """당신은 쇼츠 기획자를 돕는 리서치 분석가다. 여러 출처에서 모은 제품 반응을
종합해 '쇼츠 대본에 바로 쓸 수 있는' 인사이트 리포트를 만든다.

- 빈도(상/중/하)는 여러 출처에서 반복되는 정도로 판단한다.
- evidence_quotes와 real_quotes는 수집 자료에 실제로 있는 문장만 쓴다. 지어내지 않는다.
- 광고성/체험단 글로 보이는 반응은 가중치를 낮춘다.
- 국내와 해외 반응이 다르면 korea_vs_global에 분명히 적는다.
- 출처가 부족하면 coverage_notes에 솔직히 적는다."""


def synthesize_research(product: str, collected: dict, web: dict) -> ResearchReport:
    user = f"""제품: {product}

[API 수집 자료: Reddit / 네이버 블로그·카페·지식iN / 유튜브 리뷰 댓글]
{_dump(collected)[:60000]}

[웹검색 조사 메모: 국내 커뮤니티 / SNS / 해외]
{web.get('notes', '')[:40000]}

참고 URL: {_dump(web.get('urls', [])[:60])}"""
    return ask_json(ResearchReport, SYNTH_SYSTEM, user, effort="high")


# ---- 4. 대본 작성 ----------------------------------------------------------------------

SCRIPT_SYSTEM = """당신은 조회수 높은 한국어 제품 리뷰 쇼츠 대본 작가다.

작업 순서:
1. 제품 리서치 리포트를 보고 이 제품의 여론 상황을 판단한다(논란형/가성비형/고만족형/비교형 등).
2. 주어진 템플릿 중 그 상황에 가장 맞는 것 하나를 고르고 이유를 template_reason에 쓴다.
3. 후킹 멘트 라이브러리의 공식(pattern)을 참고해 오프닝 훅 후보 3개를 만든다. 문장을 그대로 베끼지 말고
   이 제품에 맞게 변형한다.
4. 선택한 템플릿 섹션 순서대로 beats를 쓴다. 실제 사람들의 반응(인용, 불만, 질문)을 근거로 쓴다.

규칙:
- 말하듯 짧은 문장. 한 문장 15자 안팎. 읽었을 때 길이가 목표 길이를 넘지 않게 한다.
- 장점만 나열하지 않는다. 신뢰를 주는 단점/주의점을 최소 하나 넣는다.
- 리서치에 없는 수치나 사실을 지어내지 않는다. 직접 확인이 필요한 주장은 fact_check_notes에 적는다.
- 리뷰어(사용자)가 실제로 써본 경험이 들어갈 자리는 [직접 사용 경험: ...] 처럼 표시한다.
- full_narration은 beats의 narration을 이어붙인 최종 낭독본이다."""


def write_script(product: str, report: dict, templates: list[dict], hooks: list[dict],
                 notes: str = "", length_sec: int = 45) -> ShortsScript:
    slim_hooks = [{"text": h["text"], "hook_type": h["hook_type"], "pattern": h["pattern"]}
                  for h in hooks]
    slim_templates = [{k: t[k] for k in t if k not in ("id", "source", "created_at")}
                      for t in templates]
    user = f"""제품: {product}
목표 길이: 약 {length_sec}초
리뷰어 메모(직접 써본 느낌, 강조하고 싶은 점 등): {notes or '없음'}

[제품 반응 리서치 리포트]
{_dump(report)}

[사용 가능한 대본 템플릿]
{_dump(slim_templates)}

[수집된 후킹 멘트 라이브러리 (떡상 영상에서 추출)]
{_dump(slim_hooks)}"""
    return ask_json(ShortsScript, SCRIPT_SYSTEM, user, effort="high")
