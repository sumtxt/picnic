"""
Tests for openrouter_client module
"""

from unittest.mock import MagicMock

import pytest
from openai import APITimeoutError, RateLimitError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from src.config import FILTER_AI_REJECT, FILTER_ERROR, FILTER_PASS
from src.openrouter_client import classify_article, create_openrouter_client


def make_completion(content: str, finish_reason: str = "stop") -> ChatCompletion:
    return ChatCompletion(
        id="chatcmpl-test",
        object="chat.completion",
        created=0,
        model="gpt-4o-mini",
        choices=[
            Choice(
                index=0,
                finish_reason=finish_reason,
                message=ChatCompletionMessage(role="assistant", content=content),
            )
        ],
    )


def make_client(*side_effects):
    client = MagicMock()
    client.chat.completions.create.side_effect = side_effects
    return client


class TestCreateOpenrouterClient:
    def test_points_at_openrouter_base_url(self):
        client = create_openrouter_client()
        assert str(client.base_url) == "https://openrouter.ai/api/v1/"


class TestClassifyArticle:
    def test_yes_returns_pass(self):
        client = make_client(make_completion("Yes"))
        result = classify_article("Journal", "Title", "Abstract", client=client)
        assert result == FILTER_PASS

    def test_no_returns_ai_reject(self):
        client = make_client(make_completion("No"))
        result = classify_article("Journal", "Title", "Abstract", client=client)
        assert result == FILTER_AI_REJECT

    def test_response_is_case_insensitive(self):
        client = make_client(make_completion("YES"))
        result = classify_article("Journal", "Title", "Abstract", client=client)
        assert result == FILTER_PASS

    def test_unexpected_answer_returns_error(self):
        client = make_client(make_completion("Maybe"))
        result = classify_article("Journal", "Title", "Abstract", client=client)
        assert result == FILTER_ERROR

    def test_non_stop_finish_reason_returns_error(self):
        client = make_client(make_completion("Yes", finish_reason="length"))
        result = classify_article("Journal", "Title", "Abstract", client=client)
        assert result == FILTER_ERROR

    def test_missing_abstract_is_handled(self):
        client = make_client(make_completion("Yes"))
        result = classify_article("Journal", "Title", None, client=client)
        assert result == FILTER_PASS

    def test_retries_on_rate_limit_then_succeeds(self, monkeypatch):
        monkeypatch.setattr("src.openrouter_client.time.sleep", lambda _: None)
        error = RateLimitError("rate limited", response=MagicMock(status_code=429), body=None)
        client = make_client(error, make_completion("Yes"))
        result = classify_article(
            "Journal", "Title", "Abstract", client=client, backoff_factor=1
        )
        assert result == FILTER_PASS
        assert client.chat.completions.create.call_count == 2

    def test_rate_limit_exhausts_retries_returns_error(self, monkeypatch):
        monkeypatch.setattr("src.openrouter_client.time.sleep", lambda _: None)
        error = RateLimitError("rate limited", response=MagicMock(status_code=429), body=None)
        client = make_client(error, error, error)
        result = classify_article(
            "Journal", "Title", "Abstract", client=client, max_retries=3, backoff_factor=1
        )
        assert result == FILTER_ERROR
        assert client.chat.completions.create.call_count == 3

    def test_timeout_returns_error_after_retries(self, monkeypatch):
        monkeypatch.setattr("src.openrouter_client.time.sleep", lambda _: None)
        error = APITimeoutError(request=MagicMock())
        client = make_client(error, error)
        result = classify_article(
            "Journal", "Title", "Abstract", client=client, max_retries=2, backoff_factor=1
        )
        assert result == FILTER_ERROR
        assert client.chat.completions.create.call_count == 2

    def test_creates_default_client_when_none_given(self, monkeypatch):
        default_client = make_client(make_completion("Yes"))
        monkeypatch.setattr(
            "src.openrouter_client.create_openrouter_client", lambda: default_client
        )
        result = classify_article("Journal", "Title", "Abstract")
        assert result == FILTER_PASS
        default_client.chat.completions.create.assert_called_once()


@pytest.mark.integration
class TestClassifyArticleLive:
    """
    Hits the real OpenRouter API. Requires OPENROUTER_APIKEY to be set
    (e.g. in a local .env file) and is skipped otherwise.
    """

    def test_classifies_a_clear_social_science_article(self):
        from src.config import OPENROUTER_API_KEY

        if not OPENROUTER_API_KEY:
            pytest.skip("OPENROUTER_APIKEY not set")

        result = classify_article(
            journal="American Political Science Review",
            title="Voter Turnout and Political Trust in Democracies",
            abstract=(
                "This article examines the relationship between institutional trust "
                "and voter turnout across 30 democracies using panel survey data."
            ),
        )
        assert result in (FILTER_PASS, FILTER_AI_REJECT)
