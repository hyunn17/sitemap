"""Claude 구조화 출력용 스키마."""
from typing import Literal

from pydantic import BaseModel, Field

HookType = Literal[
    "질문형", "결과선공개", "충격·반전", "경고·금지", "공감·고통", "숫자·리스트",
    "비교·대결", "권위·증거", "호기심갭", "도발·논쟁", "스토리", "기타",
]


# ---- 영상 분석 ---------------------------------------------------------------

class HookLine(BaseModel):
    text: str = Field(description="영상에서 실제로 쓰인 후킹 문장 (원문 그대로)")
    hook_type: HookType
    pattern: str = Field(description="다른 제품에도 재사용할 수 있게 빈칸화한 공식. 예: '[제품] [기간] 써보니 [의외의 결과]'")
    why_it_works: str
    language: Literal["ko", "en", "ja", "other"]


class Section(BaseModel):
    section: str = Field(description="예: 훅, 문제제기, 재후킹, 증거, 반전, 결론, CTA")
    start_sec: float
    purpose: str
    technique: str
    example_line: str


class OpeningHook(BaseModel):
    first_line: str
    hook_type: HookType
    visual_hook: str = Field(description="첫 1~2초 화면/자막/동작에서 시선을 잡는 요소")
    why_it_works: str


class VideoAnalysis(BaseModel):
    summary: str
    format_type: str = Field(description="예: 솔직후기, 비교, 언박싱, 꿀팁, 스토리텔링")
    opening_hook: OpeningHook
    hook_lines: list[HookLine] = Field(description="오프닝 훅 + 중간 재후킹 + 결말 직전 긴장 유지 멘트")
    structure: list[Section]
    retention_devices: list[str]
    cta: str
    pacing_notes: str
    reusable_lessons: list[str]


# ---- 대본 템플릿 ---------------------------------------------------------------

class TemplateSection(BaseModel):
    name: str
    time_range: str = Field(description="예: 0-3s")
    goal: str
    instructions: str
    example_line: str


class ScriptTemplate(BaseModel):
    name: str
    description: str
    best_for: list[str] = Field(description="이 템플릿이 잘 맞는 제품/여론 상황")
    target_length_sec: int
    hook_formula: str
    sections: list[TemplateSection]
    hook_examples: list[str]
    cta_formula: str
    do: list[str]
    dont: list[str]


class TemplateSet(BaseModel):
    templates: list[ScriptTemplate]


# ---- 제품 반응 리서치 -------------------------------------------------------------

class Point(BaseModel):
    point: str
    frequency: Literal["상", "중", "하"]
    evidence_quotes: list[str]
    sources: list[str] = Field(description="출처 커뮤니티명 또는 URL")


class Quote(BaseModel):
    quote: str
    source: str
    language: Literal["ko", "en", "ja", "other"]


class Comparison(BaseModel):
    competitor: str
    verdict: str


class ResearchReport(BaseModel):
    product_summary: str
    overall_sentiment: str
    positive_pct: int = Field(description="긍정 반응 비율 추정(0-100)")
    top_praises: list[Point]
    top_complaints: list[Point]
    controversies: list[str] = Field(description="사람들이 갈리는 논쟁 포인트")
    common_questions: list[str] = Field(description="구매 전 사람들이 자주 묻는 질문")
    surprising_insights: list[str] = Field(description="의외의 사실, 잘 알려지지 않은 장단점")
    target_audience: list[str]
    comparisons: list[Comparison]
    korea_vs_global: str = Field(description="국내 반응과 해외 반응의 차이")
    real_quotes: list[Quote] = Field(description="대본에 인용하기 좋은 실제 반응")
    angle_ideas: list[str] = Field(description="쇼츠 기획 각도 아이디어")
    coverage_notes: str = Field(description="조사된 출처 범위와 한계")


# ---- 쇼츠 대본 -----------------------------------------------------------------

class HookOption(BaseModel):
    text: str
    hook_type: HookType
    reason: str


class ScriptBeat(BaseModel):
    time: str = Field(description="예: 0-3s")
    section: str
    narration: str
    on_screen_text: str
    visual: str = Field(description="촬영 컷/B롤/소품 지시")


class ShortsScript(BaseModel):
    template_name: str
    template_reason: str = Field(description="리서치 결과를 보고 이 템플릿을 고른 이유")
    angle: str
    title_options: list[str]
    hook_options: list[HookOption]
    beats: list[ScriptBeat]
    full_narration: str
    cta: str
    estimated_length_sec: int
    hashtags: list[str]
    pinned_comment: str = Field(description="댓글 참여를 유도하는 고정 댓글")
    research_used: list[str] = Field(description="대본에 반영한 리서치 포인트")
    fact_check_notes: list[str] = Field(description="촬영 전 직접 확인해야 할 사실/주장")
