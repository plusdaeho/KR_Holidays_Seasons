# 🗓️ 한국 절기·공휴일 iCal 자동 생성

한국천문연구원 특일 정보 API (data.go.kr)로 **24절기 · 잡절 · 공휴일**을 `.ics` 파일로 만들고  
GitHub Pages에 자동 배포하는 저장소입니다.

## 📁 구조

```
.
├── .github/
│   └── workflows/
│       └── generate.yml      # Actions 워크플로우
├── scripts/
│   └── generate_ics.py       # ICS 생성 스크립트
├── index.html                # 구독 랜딩 페이지
└── README.md
```

## 🚀 셋업 가이드

### 1. API 키 발급

1. [data.go.kr](https://www.data.go.kr) 로그인
2. **한국천문연구원_특일 정보** 검색 → 활용 신청
3. 마이페이지 → 인증키 확인 (일반 인증키)

### 2. GitHub Secrets 등록

```
저장소 → Settings → Secrets and variables → Actions → New repository secret

Name : DATA_GO_KR_API_KEY
Value: (발급받은 인증키)
```

### 3. GitHub Pages 활성화

```
Settings → Pages → Source: Deploy from a branch
Branch: gh-pages / (root) → Save
```

### 4. 첫 실행

```
Actions 탭 → "Generate Korean Calendar ICS" → Run workflow
```

---

## 🔄 자동 실행 시점

| 트리거 | 시점 |
|--------|------|
| `schedule` | 매주 수요일 KST 03:00 (UTC 화요일 18:00) |
| `workflow_dispatch` | 수동 실행 |
| `push` | `scripts/` 또는 `.github/workflows/` 변경 시 |

### 수동 트리거 방법

**GitHub UI:**  
`Actions` 탭 → `Generate Korean Calendar ICS` → `Run workflow` 버튼 클릭

**GitHub CLI:**
```bash
gh workflow run generate.yml
# 연도 범위 지정 (현재 연도 ± 3년)
gh workflow run generate.yml -f year_range=3
```

**REST API:**
```bash
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/{owner}/{repo}/actions/workflows/generate.yml/dispatches \
  -d '{"ref":"main","inputs":{"year_range":"2"}}'
```

---

## 📅 캘린더 구독

배포 후 `https://{username}.github.io/{repo}/` 에서 구독 URL 확인

두 개의 캘린더로 분리 제공됩니다:

| 파일 | 내용 |
|------|------|
| `korean_holidays.ics` | 법정 공휴일·대체공휴일 |
| `korean_solar_terms.ics` | 24절기·잡절 |

| 앱 | 구독 방법 |
|----|-----------|
| Apple 캘린더 | `webcal://...` 링크 클릭 |
| Google 캘린더 | 다른 캘린더 추가 → URL로 추가 |
| Outlook | 캘린더 추가 → 인터넷에서 구독 |

---

## ⚙️ 환경변수 (Actions)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DATA_GO_KR_API_KEY` | (필수) | data.go.kr 인증키 |
| `YEAR_RANGE` | `2` | 현재 연도 ± N년 수집 |
| `OUTPUT_DIR` | `dist` | 출력 디렉터리 |

---

## 📦 포함 데이터

| 카테고리 | API 엔드포인트 | 설명 |
|----------|---------------|------|
| 공휴일 | `getRestDeInfo` | 법정 공휴일·대체공휴일 (`isHoliday=Y` 만 포함) |
| 24절기 | `get24DivisionsInfo` | 입춘~대한 |
| 잡절 | `getSundryDayInfo` | 한식·단오·칠석 등 |
