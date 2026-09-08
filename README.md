# AskHR - FrontEnd

## 준비 (uv 설치)
```powershell
pip install uv
```
```powershell
uv --version
```

## 실행
```powershell
uv sync
```

```powershell
uv run streamlit run streamlit_app.py
```

## 로그 및 데이터 분석

로그인한 뒤 사이드바의 **로그 및 데이터 분석**을 선택한다.
`render_dashboard()`가 본문에 대시보드를 표시하며 자체 사이드바는 생성하지 않는다.

- 전체 사용자 응답 수, 평균·p95 지연시간, 입력·출력·전체 토큰
- 최근 5회 응답 시간 및 입력·출력 토큰 비교
- 최신순 로그와 대화별 통계 (50건씩 페이지 이동)
- 한국 시간 기준 오늘을 포함한 최근 30일의 전체 대화 조회

기존 `BACKEND_URL` 설정과 로그인 세션의 Bearer 토큰으로
`/analytics/summary`, `/analytics/logs`,
`/analytics/conversations`를 호출한다. 관리자 등록은 필요하지 않다.
로그 표시 시각은 한국 시간으로 변환한다.
대화별 최근 50건만 보관하므로 전체 누적 통계와 다를 수 있다.
토큰 미수집 값은 로그에서 `—`로 표시하고 합계에는 확인된 값만 포함한다.

```powershell
uv run python -m unittest discover -s tests -v
```
