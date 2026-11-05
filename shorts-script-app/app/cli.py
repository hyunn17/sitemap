"""명령줄 실행 (cron 등록용).

  python -m app.cli collect 리뷰 언박싱 --days 7
  python -m app.cli templates
  python -m app.cli research "갤럭시 버즈3 프로"
  python -m app.cli script "갤럭시 버즈3 프로" --notes "노캔은 만족, 착용감 애매" --length 40
"""
import argparse
import json

from . import pipeline


def main():
    p = argparse.ArgumentParser(prog="shorts")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="떡상 쇼츠 수집 + 후킹 분석")
    c.add_argument("keywords", nargs="+")
    c.add_argument("--days", type=int, default=14)
    c.add_argument("--region", default="KR")
    c.add_argument("--language", default="ko")
    c.add_argument("--min-views", type=int, default=50_000)
    c.add_argument("--analyze-top", type=int, default=5)

    sub.add_parser("templates", help="분석 결과로 템플릿 재구성")

    r = sub.add_parser("research", help="제품 반응 리서치")
    r.add_argument("product")

    s = sub.add_parser("script", help="쇼츠 대본 생성")
    s.add_argument("product")
    s.add_argument("--research-id", type=int)
    s.add_argument("--notes", default="")
    s.add_argument("--length", type=int, default=45)

    a = p.parse_args()
    pipeline.init()

    if a.cmd == "collect":
        for kw in a.keywords:
            r = pipeline.collect(kw, a.days, a.region, a.language, a.min_views, a.analyze_top)
            print(f"[{kw}] 영상 {r['found']}개, 분석 {r['analyzed']}개, 새 후킹 {r['new_hooks']}개"
                  + (f", 오류 {len(r['errors'])}개" if r["errors"] else ""))
    elif a.cmd == "templates":
        for t in pipeline.rebuild_templates():
            print(f"- {t['name']}: {t['description']}")
    elif a.cmd == "research":
        r = pipeline.research(a.product)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif a.cmd == "script":
        r = pipeline.generate_script(a.product, a.research_id, a.notes, a.length)
        s = r["script"]
        print(f"템플릿: {s['template_name']} — {s['template_reason']}\n")
        print("제목 후보:", *s["title_options"], sep="\n  ")
        print("\n대본:")
        for b in s["beats"]:
            print(f"  [{b['time']}] {b['section']}: {b['narration']}  (자막: {b['on_screen_text']})")
        print("\n확인 필요:", *s["fact_check_notes"], sep="\n  ")


if __name__ == "__main__":
    main()
