---
name: index-request
description: 발행된 블로그 글 URL을 네이버 서치어드바이저(웹페이지 수집 요청)와 구글 서치콘솔(URL 검사 → 색인 생성 요청)에 브라우저로 등록하고 이력을 남긴다. "색인 등록", "수집 요청", "검색 노출" 요청이나 글 발행 직후에 사용.
---

# 색인 등록

대상 URL: 요청에 있으면 그것, 없으면 `python3 tools/tracker.py posts --not-indexed`로 미등록 글 목록.

## 네이버 서치어드바이저
1. `https://searchadvisor.naver.com/console/board` → 사이트 `https://todayshopping.tistory.com` 선택
2. 요청 → **웹페이지 수집** → URL 입력 → 확인
3. 하루 요청 한도가 있으니 "한도 초과"가 뜨면 멈추고 남은 URL은 내일로 미룹니다.
4. 성공하면 `python3 tools/tracker.py post-indexed <ID> --engine naver`

## 구글 서치콘솔
1. `https://search.google.com/search-console` → 속성 선택
2. 상단 **URL 검사**에 URL 입력 → 결과가 나오면 **색인 생성 요청**
3. 1~2분 걸리는 검사 화면은 기다립니다. 할당량 초과 메시지가 뜨면 멈춥니다.
4. 성공하면 `python3 tools/tracker.py post-indexed <ID> --engine google`

## 사이트맵
처음 한 번 또는 강현님이 요청할 때만: 네이버는 요청 → 사이트맵 제출(`/sitemap.xml`),
구글은 Sitemaps 메뉴에 `sitemap.xml` 제출. 티스토리는 사이트맵을 자동 생성합니다.

## 보고
텔레그램으로 "네이버 ✅ / 구글 ✅ (또는 실패 이유)" 한 줄 보고.
캡차나 보안절차가 뜨면 화면을 캡처해 보내고 강현님이 처리하도록 기다립니다.
