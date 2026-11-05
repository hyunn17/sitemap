"""YouTube Data API v3 래퍼: 떡상 쇼츠 검색, 자막 추출, 댓글 수집."""
import re
from datetime import datetime, timedelta, timezone

import httpx2 as httpx

from . import config

API = "https://www.googleapis.com/youtube/v3"
MAX_SHORTS_SEC = 180  # 2024-10 이후 쇼츠는 최대 3분


class YouTubeError(RuntimeError):
    pass


def _get(path: str, **params) -> dict:
    if not config.YOUTUBE_API_KEY:
        raise YouTubeError("YOUTUBE_API_KEY가 설정되지 않았습니다 (.env 확인)")
    params["key"] = config.YOUTUBE_API_KEY
    r = httpx.get(f"{API}/{path}", params=params, timeout=30)
    if r.status_code != 200:
        try:
            msg = r.json()["error"]["message"]
        except Exception:
            msg = r.text[:300]
        raise YouTubeError(f"YouTube API 오류 ({r.status_code}): {msg}")
    return r.json()


def _iso_duration_to_sec(d: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    days, h, mi, s = (int(x or 0) for x in m.groups())
    return days * 86400 + h * 3600 + mi * 60 + s


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def search_viral_shorts(
    keyword: str,
    days: int = 14,
    region: str = "KR",
    language: str = "ko",
    max_results: int = 50,
    min_views: int = 50_000,
) -> list[dict]:
    """키워드로 최근 쇼츠를 찾고 '떡상 점수'(구독자 대비 조회수 배율) 순으로 정렬."""
    published_after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    ids: list[str] = []
    page_token = None
    while len(ids) < max_results:
        res = _get(
            "search", part="id", q=f"{keyword} #shorts", type="video", videoDuration="short",
            order="viewCount", publishedAfter=published_after, regionCode=region,
            relevanceLanguage=language, maxResults=min(50, max_results - len(ids)),
            **({"pageToken": page_token} if page_token else {}),
        )
        ids += [it["id"]["videoId"] for it in res.get("items", []) if it["id"].get("videoId")]
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    if not ids:
        return []

    videos = []
    for chunk in _chunks(ids, 50):
        res = _get("videos", part="snippet,statistics,contentDetails", id=",".join(chunk))
        videos += res.get("items", [])

    channel_ids = list({v["snippet"]["channelId"] for v in videos})
    subs: dict[str, int] = {}
    for chunk in _chunks(channel_ids, 50):
        res = _get("channels", part="statistics", id=",".join(chunk))
        for c in res.get("items", []):
            subs[c["id"]] = int(c["statistics"].get("subscriberCount", 0) or 0)

    now = datetime.now(timezone.utc)
    out = []
    for v in videos:
        sn, st = v["snippet"], v.get("statistics", {})
        dur = _iso_duration_to_sec(v["contentDetails"].get("duration", ""))
        views = int(st.get("viewCount", 0) or 0)
        if dur == 0 or dur > MAX_SHORTS_SEC or views < min_views:
            continue
        published = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
        hours = max((now - published).total_seconds() / 3600, 1)
        sub = subs.get(sn["channelId"], 0)
        out.append({
            "video_id": v["id"],
            "title": sn.get("title"),
            "channel_id": sn["channelId"],
            "channel_title": sn.get("channelTitle"),
            "description": sn.get("description", "")[:2000],
            "published_at": sn["publishedAt"],
            "duration_sec": dur,
            "views": views,
            "likes": int(st.get("likeCount", 0) or 0),
            "comments": int(st.get("commentCount", 0) or 0),
            "subscribers": sub,
            # 구독자 대비 조회수 배율. 구독자 수가 작은 채널의 과대평가를 막기 위해 하한 1,000
            "viral_score": round(views / max(sub, 1000), 2),
            "views_per_hour": round(views / hours, 1),
            "keyword": keyword,
        })
    out.sort(key=lambda x: x["viral_score"], reverse=True)
    return out


def fetch_transcript(video_id: str, languages=("ko", "en", "ja")) -> str | None:
    """자막(수동/자동)을 [초] 텍스트 형태로 반환. 자막이 없거나 차단되면 None."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        fetched = YouTubeTranscriptApi().fetch(video_id, languages=list(languages))
        return "\n".join(f"[{s.start:.1f}s] {s.text}" for s in fetched.snippets)
    except Exception:
        return None


def search_videos(query: str, max_results: int = 5, language: str = "ko") -> list[dict]:
    res = _get("search", part="snippet", q=query, type="video", order="relevance",
               relevanceLanguage=language, maxResults=max_results)
    return [{"video_id": it["id"]["videoId"], "title": it["snippet"]["title"]}
            for it in res.get("items", []) if it["id"].get("videoId")]


def top_comments(video_id: str, max_results: int = 40) -> list[dict]:
    try:
        res = _get("commentThreads", part="snippet", videoId=video_id, order="relevance",
                   maxResults=max_results, textFormat="plainText")
    except YouTubeError:
        return []  # 댓글 사용 중지된 영상 등
    out = []
    for it in res.get("items", []):
        c = it["snippet"]["topLevelComment"]["snippet"]
        out.append({"text": c["textDisplay"][:500], "likes": c.get("likeCount", 0)})
    return out
