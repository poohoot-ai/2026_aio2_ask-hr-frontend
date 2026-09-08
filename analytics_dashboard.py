"""전체 사용자 사용량 대시보드. 기존 로그인 세션과 분석 API를 사용한다."""
from datetime import datetime, time, timedelta, timezone
from html import escape

import streamlit as st

from common import ApiError, SessionExpired, api, auth_headers
from ui import page_header

KST = timezone(timedelta(hours=9))
PAGE_SIZE = 50

CSS = """
<style>
/* 색상은 현재 Streamlit 테마에서 상속한다. */

.analytics-title {font-size:18px;font-weight:700;color:inherit;margin:0 0 6px;}
.analytics-subtitle {color:color-mix(in srgb, currentColor 72%, transparent);font-size:13px;margin-bottom:18px;}
.analytics-card {background:color-mix(in srgb, currentColor 4%, transparent);border:1px solid color-mix(in srgb, currentColor 18%, transparent);border-radius:8px;
 padding:18px 20px;min-height:130px;border-top:3px solid #87508F;}
.analytics-label {color:color-mix(in srgb, currentColor 80%, transparent);font-size:13px;font-weight:600;margin-bottom:16px;}
.analytics-value {color:inherit;font-size:25px;font-weight:650;}
.analytics-note {font-size:12px;color:color-mix(in srgb, currentColor 72%, transparent);margin-top:7px;}
.analytics-panel {background:color-mix(in srgb, currentColor 4%, transparent);border:1px solid color-mix(in srgb, currentColor 18%, transparent);border-radius:8px;
 padding:20px;min-height:320px;margin-top:12px;}
.analytics-panel-heading {display:flex;justify-content:space-between;gap:12px;
 color:color-mix(in srgb, currentColor 80%, transparent);font-size:15px;font-weight:600;margin-bottom:22px;}
.analytics-panel-heading span {font-size:12px;font-weight:400;}
.analytics-bars {height:190px;display:flex;align-items:flex-end;justify-content:space-around;
 border-left:2px solid color-mix(in srgb, currentColor 18%, transparent);border-bottom:2px solid color-mix(in srgb, currentColor 18%, transparent);gap:18px;padding:0 22px;margin:34px 12px 0;}
.analytics-bar {width:60px;max-width:100%;border-radius:8px 8px 0 0;background:color-mix(in srgb, currentColor 45%, transparent);}
.analytics-bar-labels {display:flex;justify-content:space-around;gap:18px;padding:12px 22px 0;
 margin:0 12px;color:color-mix(in srgb, currentColor 80%, transparent);font-size:13px;}
.analytics-token-row {display:flex;align-items:center;gap:18px;margin:40px 0;color:color-mix(in srgb, currentColor 80%, transparent);font-size:14px;}
.analytics-track {flex:1;background:color-mix(in srgb, currentColor 8%, transparent);height:16px;border-radius:20px;overflow:hidden;}
.analytics-fill {height:100%;background:currentColor;border-radius:20px;}
.analytics-callout {background:color-mix(in srgb, currentColor 8%, transparent);border-radius:10px;padding:13px 16px;color:inherit;font-size:12px;line-height:1.8;}
.analytics-empty {color:color-mix(in srgb, currentColor 72%, transparent);padding:60px 0;text-align:center;}
.st-key-analytics-logs, .st-key-analytics-conversations {
 background:color-mix(in srgb, currentColor 4%, transparent);border:1px solid color-mix(in srgb, currentColor 18%, transparent);border-radius:8px;padding:20px;margin-top:12px;}
@media(max-width:700px) {.analytics-card {padding:20px;min-height:125px;}
 .analytics-panel {padding:20px;} .analytics-title {font-size:26px;}}
</style>
"""


def number(value):
    return "—" if value is None else f"{value:,}"


def seconds(value):
    return "—" if value is None else f"{value / 1000:,.1f}초"


def local_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")


def query_params(start, end):
    """한국 날짜 기준 조회 기간을 UTC 반개구간으로 변환한다."""
    return {
        "start": datetime.combine(start, time.min, KST).astimezone(timezone.utc).isoformat(),
        "end": datetime.combine(end + timedelta(days=1), time.min, KST).astimezone(timezone.utc).isoformat(),
    }


def recent_chart(logs):
    rows = list(reversed(logs[:5]))
    heading = f'<div class="analytics-panel-heading">최근 응답 시간 추이<span>최근 {len(rows)}회 · 초</span></div>'
    if not rows:
        return f'<div class="analytics-panel">{heading}<div class="analytics-empty">선택한 기간의 응답 기록이 없습니다.</div></div>'
    maximum = max(max(row["latency_ms"] for row in rows), 1)
    bars, labels = [], []
    for index, row in enumerate(rows):
        height = row["latency_ms"] / maximum * 170
        color = "#87508F" if index == len(rows) - 1 else "color-mix(in srgb, #87508F 55%, transparent)"
        title = escape(f'{local_timestamp(row["requested_at"])} · {seconds(row["latency_ms"])}')
        bars.append(f'<div class="analytics-bar" title="{title}" style="height:{height}px;background:{color}"></div>')
        labels.append(f'<span>{seconds(row["latency_ms"])}</span>')
    return (f'<div class="analytics-panel">{heading}<div class="analytics-bars">{"".join(bars)}</div>'
            f'<div class="analytics-bar-labels">{"".join(labels)}</div></div>')


def token_comparison(metrics, coverage):
    prompt, response = metrics["prompt_tokens"], metrics["response_tokens"]
    total = max(prompt + response, 1)
    rows = []
    for label, value, color, background in (("입력", prompt, "#87508F", "color-mix(in srgb, currentColor 8%, transparent)"),
                                           ("출력", response, "#2A9D8F", "color-mix(in srgb, currentColor 8%, transparent)")):
        rows.append(f'<div class="analytics-token-row"><span>{label}</span>'
                    f'<div class="analytics-track" style="background:{background}">'
                    f'<div class="analytics-fill" style="width:{value / total * 100}%;background:{color}"></div>'
                    f'</div><span>{number(value)}</span></div>')
    return ('<div class="analytics-panel"><div class="analytics-panel-heading">입력·출력 토큰 비교</div>'
            + "".join(rows) + f'<div class="analytics-callout">대화별 완료된 응답 최신 {coverage["max_logs_per_conversation"]}건 보관<br>'
            f'토큰 미수집 {metrics["missing_usage_count"]}건 · 확인된 값만 합산</div></div>')


def fetch(endpoint, params):
    return api("GET", f"/analytics/{endpoint}", params=params, headers=auth_headers())


def render_dashboard():
    st.markdown(CSS, unsafe_allow_html=True)
    page_header("# 로그 및 데이터 분석", "워크스페이스 인사이트 · 최근 30일의 사용 현황")
    if not st.session_state.get("access_token"):
        st.info("로그인 후 전체 사용자의 사용량 대시보드를 볼 수 있습니다.")
        return

    today = datetime.now(KST).date()
    params = query_params(today - timedelta(days=29), today)

    st.markdown('<h2 class="analytics-title">워크스페이스 활동</h2>'
                '<div class="analytics-subtitle">전체 대화의 응답 현황을 확인하고, 사용 로그와 대화별 통계를 살펴보세요.</div>', unsafe_allow_html=True)
    try:
        with st.spinner("사용량을 불러오는 중입니다…"):
            summary = fetch("summary", params)
            recent = fetch("logs", {**params, "limit": PAGE_SIZE, "offset": 0})
        metrics, coverage = summary["metrics"], summary["coverage"]
        overview, logs_tab, conversations_tab = st.tabs(["활동 개요", "사용 로그", "대화별 통계"])
        with overview:
            st.caption(f"최근 30일 · {today - timedelta(days=29):%Y.%m.%d}–{today:%Y.%m.%d} · 한국 시간 기준")
            cards = [("응답 생성", f'{number(metrics["request_count"])}건', ""),
                     ("평균 지연시간", seconds(metrics["avg_latency_ms"]), f'p95 {seconds(metrics["p95_latency_ms"])}'),
                     ("입력 토큰", number(metrics["prompt_tokens"]), ""),
                     ("출력 토큰", number(metrics["response_tokens"]), f'전체 토큰 {number(metrics["total_tokens"])}')]
            for column, (label, value, note) in zip(st.columns(4), cards):
                with column:
                    st.markdown(f'<div class="analytics-card"><div class="analytics-label">{label}</div>'
                                f'<div class="analytics-value">{value}</div><div class="analytics-note">{note}</div></div>',
                                unsafe_allow_html=True)
            left, right = st.columns([2, 1], gap="large")
            with left:
                st.markdown(recent_chart(recent["items"]), unsafe_allow_html=True)
            with right:
                st.markdown(token_comparison(metrics, coverage), unsafe_allow_html=True)

        with logs_tab:
            with st.container(key="analytics-logs"):
                st.markdown("**최근 사용 로그**")
                page = page_control("로그", recent["total"], "analytics_log_page")
                logs = recent if page == 1 else fetch("logs", {**params, "limit": PAGE_SIZE, "offset": (page - 1) * PAGE_SIZE})
                st.caption(f'전체 {number(logs["total"])}건 · 페이지당 최대 50건 · 최신순')
                if logs["items"]:
                    st.dataframe([{"기록 시각 (KST)": local_timestamp(row["requested_at"]),
                                   "지연시간": seconds(row["latency_ms"]), "입력": number(row["prompt_tokens"]),
                                   "출력": number(row["response_tokens"]), "합계": number(row["total_tokens"]),
                                   "대화": row["conversation_title"], "대화 ID": row["conversation_id"]}
                                  for row in logs["items"]], hide_index=True, width="stretch")
                else:
                    st.info("선택한 기간에 저장된 로그가 없습니다.")

        with conversations_tab:
            with st.container(key="analytics-conversations"):
                st.markdown("**대화별 통계**")
                page = page_control("대화", summary["conversation_count"], "analytics_conversation_page")
                result = fetch("conversations", {**params, "limit": PAGE_SIZE, "offset": (page - 1) * PAGE_SIZE})
                st.caption(f'전체 {number(result["total"])}개 대화 · 응답 수 내림차순')
                if result["items"]:
                    st.dataframe([{"대화": row["conversation_title"], "응답 수": row["request_count"],
                                   "평균 지연시간": seconds(row["avg_latency_ms"]), "p95": seconds(row["p95_latency_ms"]),
                                   "입력": row["prompt_tokens"], "출력": row["response_tokens"], "합계": row["total_tokens"],
                                   "토큰 미수집": row["missing_usage_count"], "대화 ID": row["conversation_id"]}
                                  for row in result["items"]], hide_index=True, width="stretch")
                else:
                    st.info("표시할 대화가 없습니다.")

        st.caption(f'전체 사용자 · 대화별 최근 {coverage["max_logs_per_conversation"]}건 기준으로 전체 누적 이력과 다를 수 있습니다. '
                   '기록 시각은 응답 저장 시점입니다.')
        if coverage.get("skipped_invalid_logs"):
            st.warning(f'형식이 올바르지 않은 로그 {coverage["skipped_invalid_logs"]}건은 집계에서 제외되었습니다.')
    except SessionExpired as error:
        for key in ("access_token", "user_email", "conversation_id", "pending_question", "failed_question"):
            st.session_state[key] = None
        st.session_state.expired_notice = str(error)
        st.rerun()
    except ApiError as error:
        st.error(f"분석 데이터를 불러오지 못했습니다. {error}")
        st.caption("잠시 후 대시보드를 다시 열어 주세요.")


def page_control(label, total, key):
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    st.session_state[key] = min(st.session_state.get(key, 1), pages)
    return st.number_input(f"{label} 페이지 / {pages}", min_value=1, max_value=pages, step=1, key=key)
