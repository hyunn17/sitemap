# 티스토리 HTML 조각

## 공정위 문구 박스 (본문 맨 위)
```html
<blockquote data-ke-style="style1" style="background:#f8f9fa; border-left:4px solid #346aff; padding:15px; margin:20px 0;">
  <p style="color:#666; font-size:14px; margin:0;">※ (style-guide.md 5번 문구 중 하나, 어휘 변주)</p>
</blockquote>
```

## 제품 전용 구매 버튼 (3단 배치: 도입부 직후 1회 / 각 제품 섹션 끝 / 결론 직후 1회)
```html
<p align="center" style="margin: 25px 0;">
  <a href="https://link.coupang.com/a/..." target="_blank" rel="noopener noreferrer sponsored" style="display:inline-block; padding:14px 28px; background-color:#346aff; color:#ffffff; font-weight:bold; font-size:16px; border-radius:8px; text-decoration:none; box-shadow: 0 4px 12px rgba(52,106,255,0.3);">
    👉 [제품 모델명] 로켓배송 최저가 & 할인 혜택 보러가기
  </a>
</p>
```
링크는 쿠팡 파트너스(`partners.coupang.com`) → 간편 링크 만들기 → 상품 URL → 단축 URL(`https://link.coupang.com/a/...`).

## 이미지
```html
<p align="center" style="margin: 20px 0;">
  <img src="이미지URL" alt="구체적인 설명" style="max-width:100%; height:auto; border-radius:8px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);" />
</p>
```
실사진은 티스토리 에디터 기본모드의 사진 첨부로 올린 뒤 위치를 맞춥니다.

## 유튜브
```html
<p align="center" style="margin: 25px 0;">
  <iframe width="100%" height="360" src="https://www.youtube.com/embed/영상ID" title="제품 비교 영상" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen style="max-width:640px; border-radius:8px;"></iframe>
</p>
```

## 경고 박스 (지금 사면 손해인 경우)
```html
<div style="background:#fff4e5; border:2px solid #ffae33; border-radius:10px; padding:16px; margin:20px 0;">
  <p style="margin:0; font-weight:bold;">⚠️ 지금 이 모델 사면 손해인 이유</p>
  <p style="margin:8px 0 0;">(이유 + 대안 모델)</p>
</div>
```
