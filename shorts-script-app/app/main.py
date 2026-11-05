"""FastAPI 서버 + 웹 UI.  실행: uvicorn app.main:app --reload"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, db, llm, pipeline, youtube

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("shorts")
STATIC = Path(__file__).parent / "static"


async def _auto_collect_loop():
    """AUTO_COLLECT_HOURS 마다 키워드별로 떡상 영상을 수집해 후킹 멘트를 꾸준히 쌓는다."""
    while True:
        for kw in config.AUTO_COLLECT_KEYWORDS:
            try:
                r = await asyncio.to_thread(pipeline.collect, kw)
                log.info("자동수집 '%s': 영상 %d, 분석 %d, 새 후킹 %d",
                         kw, r["found"], r["analyzed"], r["new_hooks"])
            except Exception:
                log.exception("자동수집 실패: %s", kw)
        await asyncio.sleep(config.AUTO_COLLECT_HOURS * 3600)


@asynccontextmanager
async def lifespan(_: FastAPI):
    pipeline.init()
    task = None
    if config.AUTO_COLLECT_HOURS > 0 and config.AUTO_COLLECT_KEYWORDS:
        task = asyncio.create_task(_auto_collect_loop())
    yield
    if task:
        task.cancel()


app = FastAPI(title="Shorts Script Studio", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (llm.LLMError, youtube.YouTubeError, ValueError) as e:
        raise HTTPException(400, str(e)) from e


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    return {
        "anthropic": bool(config.ANTHROPIC_API_KEY),
        "youtube": bool(config.YOUTUBE_API_KEY),
        "naver": bool(config.NAVER_CLIENT_ID and config.NAVER_CLIENT_SECRET),
        "model": config.CLAUDE_MODEL,
        "auto_collect": {"hours": config.AUTO_COLLECT_HOURS, "keywords": config.AUTO_COLLECT_KEYWORDS},
        "counts": {
            "videos": db.one("SELECT COUNT(*) n FROM videos")["n"],
            "analyses": db.one("SELECT COUNT(*) n FROM analyses")["n"],
            "hooks": db.one("SELECT COUNT(*) n FROM hooks")["n"],
            "templates": db.one("SELECT COUNT(*) n FROM templates")["n"],
            "scripts": db.one("SELECT COUNT(*) n FROM scripts")["n"],
        },
    }


# ---- 1. 떡상 영상 ------------------------------------------------------------------------

class CollectIn(BaseModel):
    keyword: str
    days: int = 14
    region: str = "KR"
    language: str = "ko"
    min_views: int = 50_000
    analyze_top: int = 5


@app.post("/api/collect")
def collect(body: CollectIn):
    return _run(pipeline.collect, **body.model_dump())


@app.get("/api/videos")
def videos():
    return db.list_videos()


@app.get("/api/videos/{video_id}/analysis")
def video_analysis(video_id: str):
    a = db.get_analysis(video_id)
    if not a:
        raise HTTPException(404, "아직 분석되지 않은 영상입니다")
    return {"video": db.get_video(video_id), "analysis": a}


class AnalyzeIn(BaseModel):
    transcript: str | None = None


@app.post("/api/videos/{video_id}/analyze")
def analyze(video_id: str, body: AnalyzeIn):
    return _run(pipeline.analyze_video, video_id, body.transcript)


# ---- 후킹 라이브러리 ------------------------------------------------------------------------

@app.get("/api/hooks")
def hooks(type: str | None = None, q: str | None = None):
    return {"hooks": db.list_hooks(type, q), "types": db.hook_types()}


@app.post("/api/hooks/{hook_id}/favorite")
def favorite(hook_id: int):
    db.toggle_favorite(hook_id)
    return {"ok": True}


@app.delete("/api/hooks/{hook_id}")
def delete_hook(hook_id: int):
    db.delete_hook(hook_id)
    return {"ok": True}


# ---- 2. 템플릿 ---------------------------------------------------------------------------

@app.get("/api/templates")
def templates():
    return db.list_templates()


@app.post("/api/templates/rebuild")
def rebuild_templates():
    return _run(pipeline.rebuild_templates)


@app.delete("/api/templates/{tid}")
def delete_template(tid: int):
    db.delete_template(tid)
    return {"ok": True}


# ---- 3. 리서치 / 4. 대본 -------------------------------------------------------------------

class ResearchIn(BaseModel):
    product: str


@app.post("/api/research")
def research(body: ResearchIn):
    return _run(pipeline.research, body.product.strip())


@app.get("/api/research")
def research_list():
    return db.list_research()


@app.get("/api/research/{rid}")
def research_get(rid: int):
    r = db.get_research(rid)
    if not r:
        raise HTTPException(404, "리서치를 찾을 수 없습니다")
    return r


class ScriptIn(BaseModel):
    product: str
    research_id: int | None = None
    notes: str = ""
    length_sec: int = 45
    template_id: int | None = None


@app.post("/api/scripts")
def make_script(body: ScriptIn):
    return _run(pipeline.generate_script, body.product.strip(), body.research_id, body.notes,
                body.length_sec, body.template_id)


@app.get("/api/scripts")
def scripts():
    return db.list_scripts()
