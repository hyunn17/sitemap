"""API로 직접 긁을 수 있는 커뮤니티 반응 수집기.

- Reddit: 공개 JSON 검색 (키 불필요)
- 네이버: 블로그 / 카페 검색 API (NAVER_CLIENT_ID/SECRET 필요)
- YouTube: 제품 리뷰 영상 상위 댓글

네이트판, 디시, 더쿠, 클리앙, 뽐뿌, X(트위터), 인스타 등 API가 없는 곳은
research.py 에서 Claude 웹검색으로 조사한다.
"""
import html
import re

import httpx2 as httpx

from . import config, youtube

TAG = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    return html.unescape(TAG.sub("", s or "")).strip()


def reddit(query: str, limit: int = 15, comments_per_post: int = 8) -> list[dict]:
    headers = {"User-Agent": config.USER_AGENT}
    try:
        r = httpx.get("https://www.reddit.com/search.json",
                      params={"q": query, "sort": "relevance", "t": "year", "limit": limit},
                      headers=headers, timeout=20, follow_redirects=True)
        r.raise_for_status()
        posts = r.json()["data"]["children"]
    except Exception as e:
        return [{"error": f"reddit 검색 실패: {e}"}]
    out = []
    for p in posts:
        d = p["data"]
        item = {
            "subreddit": d.get("subreddit"),
            "title": d.get("title"),
            "text": (d.get("selftext") or "")[:800],
            "score": d.get("score"),
            "url": "https://www.reddit.com" + d.get("permalink", ""),
            "comments": [],
        }
        try:
            cr = httpx.get(f"https://www.reddit.com{d['permalink']}.json",
                           params={"limit": comments_per_post, "sort": "top"},
                           headers=headers, timeout=20, follow_redirects=True)
            for c in cr.json()[1]["data"]["children"][:comments_per_post]:
                body = c.get("data", {}).get("body")
                if body:
                    item["comments"].append({"text": body[:400], "score": c["data"].get("score")})
        except Exception:
            pass
        out.append(item)
    return out


def naver(query: str, kind: str = "blog", display: int = 20) -> list[dict]:
    """kind: blog | cafearticle | kin(지식iN)"""
    if not (config.NAVER_CLIENT_ID and config.NAVER_CLIENT_SECRET):
        return []
    try:
        r = httpx.get(f"https://openapi.naver.com/v1/search/{kind}.json",
                      params={"query": query, "display": display, "sort": "sim"},
                      headers={"X-Naver-Client-Id": config.NAVER_CLIENT_ID,
                               "X-Naver-Client-Secret": config.NAVER_CLIENT_SECRET},
                      timeout=20)
        r.raise_for_status()
    except Exception as e:
        return [{"error": f"naver {kind} 검색 실패: {e}"}]
    return [{"title": _clean(i.get("title")), "text": _clean(i.get("description")),
             "url": i.get("link"), "date": i.get("postdate")} for i in r.json().get("items", [])]


def youtube_comments(product: str, videos: int = 4) -> list[dict]:
    if not config.YOUTUBE_API_KEY:
        return []
    out = []
    try:
        for q in (f"{product} 리뷰", f"{product} review"):
            for v in youtube.search_videos(q, max_results=videos // 2 or 1,
                                           language="ko" if "리뷰" in q else "en"):
                out.append({"video": v["title"], "video_id": v["video_id"],
                            "comments": youtube.top_comments(v["video_id"], 30)})
    except youtube.YouTubeError as e:
        out.append({"error": str(e)})
    return out


def collect_all(product: str) -> dict:
    return {
        "reddit": reddit(product),
        "naver_blog": naver(f"{product} 후기", "blog"),
        "naver_cafe": naver(f"{product} 후기", "cafearticle"),
        "naver_kin": naver(product, "kin", 10),
        "youtube_comments": youtube_comments(product),
    }
