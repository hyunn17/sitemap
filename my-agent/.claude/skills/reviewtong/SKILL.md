---
name: reviewtong
description: 리뷰통(및 기타 체험단) 신청·선정·리뷰 마감 이력을 사이트에서 가져와 tracker DB와 맞추고, 마감 임박 건을 알린다. "리뷰통", "체험단 이력", "마감 언제야", "뭐 남았어" 요청에 사용.
---

# 리뷰통 이력 관리

## 1. 사이트와 동기화
1. 리뷰통 로그인 상태 확인 (안 돼 있으면 로그인 요청). 정확한 주소를 모르면 강현님께 물어 이 파일에 적어 둡니다.
2. 마이페이지의 신청 내역 / 선정 내역 / 리뷰 등록 내역을 확인합니다.
3. 각 건을 DB와 비교합니다: `python3 tools/tracker.py campaigns --platform reviewtong`
   - 없는 건 → `campaign-add --platform reviewtong ...`
   - 상태가 바뀐 건 → `campaign-update <ID> --status <applied|selected|rejected|posted|done>`
   - 리뷰 등록 완료 → `campaign-update <ID> --status posted --post-url <URL>`

## 2. 보고
`python3 tools/tracker.py summary` 결과를 바탕으로 텔레그램에 짧게:
- ⏰ 3일 안에 리뷰 마감: 목록
- 📢 발표 예정: 목록
- ✍️ 선정됐지만 글 미작성: 목록 → "글 쓸까요?" (`blog-post` 스킬로 연결)

## 3. 리뷰 등록 대행
선정 캠페인의 리뷰 URL 제출이 필요하면, 글 발행 후 리뷰통 마이페이지에서 URL 제출 화면을 찾아
**승인 받고** 제출합니다. 제출 후 `campaign-update <ID> --status posted --post-url <URL>`.
