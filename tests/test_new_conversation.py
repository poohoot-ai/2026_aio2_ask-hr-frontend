import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


class NewConversationTests(unittest.TestCase):
    def setUp(self):
        self.rows = []
        self.messages = {}
        self.api_patch = patch("common.api", side_effect=self.response)
        self.api = self.api_patch.start()
        self.addCleanup(self.api_patch.stop)

    def response(self, method, path, **kwargs):
        if method == "POST":
            row = {"id": f"c{len(self.rows)}", "title": "새 대화"}
            self.rows.insert(0, row)
            return row
        if path == "/me/conversations":
            return self.rows
        return self.messages.get(path.split("/")[2], [])

    def app(self):
        app = AppTest.from_file(PAGE, default_timeout=20).run()
        app.session_state.access_token = "test"
        return app.run()

    def click_new(self, app):
        next(button for button in app.button if button.label == "새 대화").click().run()
        self.assertEqual(len(app.exception), 0)

    def test_repeated_click_reuses_empty_conversation(self):
        app = self.app()
        self.click_new(app)
        self.click_new(app)
        self.click_new(app)
        self.assertEqual(len(self.rows), 1)
        self.assertEqual(app.session_state.conversation_id, "c0")
        self.assertEqual(len([c for c in self.api.call_args_list if c.args[0] == "POST"]), 1)

    def test_conversation_with_messages_allows_new(self):
        self.rows.append({"id": "existing", "title": "새 대화"})
        self.messages["existing"] = [{"role": "user", "content": "연차 문의"}]
        app = self.app()
        self.click_new(app)
        self.assertEqual(len(self.rows), 2)
        self.assertEqual(app.session_state.conversation_id, "c1")

    def test_existing_empty_conversation_is_reused(self):
        self.rows.append({"id": "existing", "title": "이전 빈 대화"})
        app = self.app()
        self.click_new(app)
        self.assertEqual(len(self.rows), 1)
        self.assertEqual(app.session_state.conversation_id, "existing")
