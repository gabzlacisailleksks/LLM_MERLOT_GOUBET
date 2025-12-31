import argparse
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import src.app as entry


class EntrypointTests(unittest.TestCase):
    def test_main_routes_to_rag_track(self):
        args = SimpleNamespace(track="rag", question="What is LLM01?", k=2, max_steps=3)
        with mock.patch.object(argparse.ArgumentParser, "parse_args", return_value=args):
            with mock.patch("src.app.load_dotenv"):
                with mock.patch("src.app.genai.Client") as mock_client:
                    with mock.patch("src.app.run_rag", return_value={"answer": "ok"}) as mock_run_rag:
                        with mock.patch("builtins.print") as mock_print:
                            with mock.patch.dict(
                                os.environ,
                                {"GEMINI_API_KEY": "key", "MODEL_ID": "model"},
                                clear=True,
                            ):
                                entry.main()

        mock_run_rag.assert_called_once_with(
            "What is LLM01?",
            k=2,
            client=mock_client.return_value,
            model="model",
        )
        mock_print.assert_called_once()

    def test_main_routes_to_agent_track(self):
        args = SimpleNamespace(track="agent", question="Add numbers", k=3, max_steps=5)
        with mock.patch.object(argparse.ArgumentParser, "parse_args", return_value=args):
            with mock.patch("src.app.load_dotenv"):
                with mock.patch("src.app.genai.Client") as mock_client:
                    with mock.patch("src.app.run_agent", return_value={"answer": "ok"}) as mock_run_agent:
                        with mock.patch("builtins.print"):
                            with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "key"}, clear=True):
                                entry.main()

        mock_run_agent.assert_called_once_with(
            "Add numbers",
            client=mock_client.return_value,
            model="gemini-2.5-flash",
            max_steps=5,
        )


if __name__ == "__main__":
    unittest.main()
