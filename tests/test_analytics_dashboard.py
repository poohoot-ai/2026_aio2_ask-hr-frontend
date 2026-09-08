import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from analytics_dashboard import query_params, number
from common import ApiError, SessionExpired

PAGE = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")

def dashboard_app():
    app = AppTest.from_file(PAGE).run()
    app.session_state.current_page = "analytics"
    return app
METRICS = dict(request_count=2, prompt_tokens=100, response_tokens=20, total_tokens=120,
               missing_usage_count=1, avg_latency_ms=1500, p95_latency_ms=2000)
LOG = dict(requested_at="2026-09-08T03:00:00Z", latency_ms=1500, prompt_tokens=None,
           response_tokens=20, total_tokens=None, conversation_id="00000000-0000-0000-0000-000000000001",
           conversation_title="연차 문의")
COVERAGE = dict(max_logs_per_conversation=50, skipped_invalid_logs=0)


def response(method, path, **kwargs):
    if path.endswith("summary"):
        return dict(metrics=METRICS, coverage=COVERAGE, conversation_count=1)
    if path.endswith("logs"):
        return dict(items=[LOG], total=1)
    return dict(items=[dict(**METRICS, conversation_id=LOG["conversation_id"], conversation_title="연차 문의")], total=1)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        # 통합된 채팅 화면이 먼저 조회하는 본인 대화 목록.
        mock = patch("common.api", return_value=[])
        mock.start()
        self.addCleanup(mock.stop)

    def test_date_conversion_and_missing_tokens(self):
        params = query_params(date(2026, 9, 8), date(2026, 9, 8))
        self.assertEqual(params["start"], "2026-09-07T15:00:00+00:00")
        self.assertEqual(params["end"], "2026-09-08T15:00:00+00:00")
        self.assertEqual(number(None), "—")
        self.assertEqual(number(0), "0")

    @patch("analytics_dashboard.api", side_effect=response)
    def test_logged_in_renders_three_endpoints(self, mock):
        app = dashboard_app()
        app.session_state.access_token = "test-token"
        app.run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.dataframe), 2)
        self.assertEqual({call.args[1] for call in mock.call_args_list},
                         {"/analytics/summary", "/analytics/logs", "/analytics/conversations"})
        for call in mock.call_args_list:
            self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer test-token")
            self.assertNotIn("conversation_id", call.kwargs["params"])
        self.assertEqual(len(app.date_input), 0)
        self.assertFalse(any(item.label == "대화 ID (선택)" for item in app.text_input))

    @patch("analytics_dashboard.api")
    def test_logged_out_never_calls_backend(self, mock):
        app = dashboard_app().run()
        self.assertEqual(len(app.exception), 0)
        mock.assert_not_called()

    @patch("analytics_dashboard.api", side_effect=ApiError("저장소 연결 실패"))
    def test_error_does_not_render_fake_zero_metrics(self, mock):
        app = dashboard_app()
        app.session_state.access_token = "test-token"
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 1)
        self.assertEqual(len(app.dataframe), 0)

    @patch("analytics_dashboard.api", side_effect=SessionExpired("다시 로그인하세요"))
    def test_expired_session_cleared(self, mock):
        app = dashboard_app()
        app.session_state.access_token = "expired-token"
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertIsNone(app.session_state.access_token)

    @patch("analytics_dashboard.api")
    def test_empty_data(self, mock):
        def empty(method, path, **kwargs):
            if path.endswith("summary"):
                return dict(metrics={**METRICS, "request_count": 0, "avg_latency_ms": None,
                                     "p95_latency_ms": None, "prompt_tokens": 0, "response_tokens": 0,
                                     "total_tokens": 0, "missing_usage_count": 0},
                            coverage=COVERAGE, conversation_count=0)
            return dict(items=[], total=0)
        mock.side_effect = empty
        app = dashboard_app()
        app.session_state.access_token = "test-token"
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.info), 2)

    @patch("analytics_dashboard.api")
    def test_log_pagination(self, mock):
        def paged(method, path, **kwargs):
            result = response(method, path, **kwargs)
            if path.endswith("logs"):
                result["total"] = 51
            return result
        mock.side_effect = paged
        app = dashboard_app()
        app.session_state.access_token = "test-token"
        app.run()
        app.number_input(key="analytics_log_page").set_value(2).run()
        self.assertEqual(len(app.exception), 0)
        offsets = [call.kwargs["params"]["offset"] for call in mock.call_args_list
                   if call.args[1] == "/analytics/logs"]
        self.assertIn(50, offsets)


if __name__ == "__main__":
    unittest.main()

