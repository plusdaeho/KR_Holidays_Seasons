#!/usr/bin/env python3
"""
한국천문연구원 특일 정보 API → iCal (.ics) 생성기
- 24절기 (solarTerm)
- 잡절 (miscDay)
- 공휴일 (publicHoliday)
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, date, timezone, timedelta
import re

# ── 설정 ──────────────────────────────────────────────────────────────────────
API_KEY   = os.environ.get("DATA_GO_KR_API_KEY", "")
BASE_URL  = "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService"
OUT_DIR   = os.environ.get("OUTPUT_DIR", "dist")
OUT_FILE  = os.path.join(OUT_DIR, "korean_calendar.ics")
# 몇 년치 데이터를 가져올지 (현재 연도 ± YEAR_RANGE)
YEAR_RANGE = int(os.environ.get("YEAR_RANGE", "2"))

KST = timezone(timedelta(hours=9))

# ── 카테고리별 메타데이터 ─────────────────────────────────────────────────────
CATEGORIES = {
    "holiday":    {"name": "공휴일",  "color": "RED",    "prefix": "🎌"},
    "solarTerm":  {"name": "24절기", "color": "GREEN",  "prefix": "🌿"},
    "miscDay":    {"name": "잡절",   "color": "BLUE",   "prefix": "📅"},
}

ENDPOINT_MAP = {
    "holiday":   "getRestDeInfo",
    "solarTerm": "get24DivisionsInfo",
    "miscDay":   "getSundryDayInfo",
}

# ── API 호출 ──────────────────────────────────────────────────────────────────
def fetch_items(endpoint: str, year: int, month: int) -> list[dict]:
    """data.go.kr API 한 달치 호출 → item 목록 반환"""
    params = {
        "serviceKey": API_KEY,
        "solYear":    str(year),
        "solMonth":   f"{month:02d}",
        "numOfRows":  "100",
        "pageNo":     "1",
        "_type":      "json",
    }
    url = f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  [WARN] {endpoint} {year}-{month:02d} 호출 실패: {e}", file=sys.stderr)
        return []

    try:
        body = raw["response"]["body"]
        items = body.get("items") or {}
        if not items:
            return []
        item = items.get("item", [])
        return item if isinstance(item, list) else [item]
    except (KeyError, TypeError):
        return []


def fetch_year(year: int) -> list[dict]:
    """1~12월 전체 수집 → 통합 이벤트 목록"""
    events = []
    for cat_key, endpoint in ENDPOINT_MAP.items():
        print(f"  [{year}] {CATEGORIES[cat_key]['name']} 수집 중...", file=sys.stderr)
        for month in range(1, 13):
            items = fetch_items(endpoint, year, month)
            for item in items:
                # 날짜 파싱
                locdate = str(item.get("locdate", ""))
                if len(locdate) != 8:
                    continue
                name = item.get("dateName", "").strip()
                is_holiday = str(item.get("isHoliday", "N")).upper() == "Y"

                # 공휴일 카테고리는 isHoliday=Y 인 것만
                if cat_key == "holiday" and not is_holiday:
                    continue

                events.append({
                    "date":       locdate,          # "YYYYMMDD"
                    "name":       name,
                    "category":   cat_key,
                    "is_holiday": is_holiday,
                })
    return events


# ── iCal 생성 ─────────────────────────────────────────────────────────────────
def make_uid(evt: dict) -> str:
    return f"{evt['date']}-{re.sub(r'[^a-z0-9]', '', evt['name'].lower())}-{evt['category']}@korean-calendar"


def escape_ical(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(events: list[dict], generated_at: datetime) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Korean Calendar//KR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:한국 공휴일 & 절기",
        "X-WR-CALDESC:공휴일·24절기·잡절 (한국천문연구원 데이터)",
        "X-WR-TIMEZONE:Asia/Seoul",
        f"X-WR-RELCALID:korean-calendar-ics",
    ]

    # 중복 제거 (같은 날짜+이름+카테고리)
    seen = set()
    unique_events = []
    for e in events:
        key = (e["date"], e["name"], e["category"])
        if key not in seen:
            seen.add(key)
            unique_events.append(e)

    unique_events.sort(key=lambda e: (e["date"], e["category"]))

    dtstamp = generated_at.strftime("%Y%m%dT%H%M%SZ")

    for evt in unique_events:
        cat  = evt["category"]
        meta = CATEGORIES[cat]
        suffix = " 🎌" if evt["is_holiday"] else ""
        summary = f"{evt['name']}{suffix}"

        # 다음날 (DTEND for all-day events)
        d = date(int(evt["date"][:4]), int(evt["date"][4:6]), int(evt["date"][6:]))
        dtend = (d + timedelta(days=1)).strftime("%Y%m%d")

        lines += [
            "BEGIN:VEVENT",
            f"UID:{make_uid(evt)}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;VALUE=DATE:{evt['date']}",
            f"DTEND;VALUE=DATE:{dtend}",
            f"SUMMARY:{escape_ical(summary)}",
            f"CATEGORIES:{escape_ical(meta['name'])}",
            f"COLOR:{meta['color']}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    if not API_KEY:
        print("❌ 환경변수 DATA_GO_KR_API_KEY 가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    now  = datetime.now(tz=KST)
    base = now.year
    years = list(range(base - YEAR_RANGE, base + YEAR_RANGE + 1))

    print(f"📅 수집 연도: {years}", file=sys.stderr)

    all_events: list[dict] = []
    for year in years:
        all_events.extend(fetch_year(year))

    print(f"✅ 총 {len(all_events)}개 이벤트 수집 완료", file=sys.stderr)

    os.makedirs(OUT_DIR, exist_ok=True)
    ics_content = build_ics(all_events, now)

    with open(OUT_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(ics_content)

    print(f"💾 저장 완료: {OUT_FILE}", file=sys.stderr)

    # 메타 JSON (구독 페이지에서 활용)
    meta = {
        "generated_at": now.isoformat(),
        "years":        years,
        "event_count":  len(set((e["date"], e["name"], e["category"]) for e in all_events)),
        "by_category": {
            cat: sum(1 for e in all_events if e["category"] == cat)
            for cat in CATEGORIES
        },
    }
    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
