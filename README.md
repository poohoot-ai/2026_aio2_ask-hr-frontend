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

## UI 테마

Slack에서 영감을 받은 자주색 사이드바와 간결한 메시지 UI를 사용한다.
공통 헤더, 로그인 패널, 채팅 스타일은 `ui.py`, 라이트·다크 색상은
`.streamlit/config.toml`에 정의했다. 분석 페이지도 같은 스타일을 사용한다.
우측 상단 **⋮ → Settings → Theme**에서 라이트/다크 모드를 선택한다.
각 모드에 맞춰 본문, 사이드바, 입력창, 버튼, 글자와 테두리 색이 함께 바뀐다.

테마 설정을 읽도록 위 실행 명령은 `frontend` 디렉터리에서 실행한다.
설정이 반영되지 않으면 Streamlit 서버를 재시작하고 페이지를 새로고침한다.

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
