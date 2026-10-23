"""
Tests for openrouter_client module
"""

from unittest.mock import MagicMock

import httpx
import pytest
from openrouter.components import DecisionsResponse
from openrouter.errors import OpenRouterError

from src.config import FILTER_AI_REJECT, FILTER_ERROR, FILTER_PASS, SOCSCI_QUESTION_NAME
from src.openrouter_client import classify_article, create_openrouter_client


def make_decision(choice: str) -> DecisionsResponse:
    return DecisionsResponse.model_validate({
        "answers": {
            SOCSCI_QUESTION_NAME: {
                "type": "choice",
                "choice": choice,
                "probabilities": {"Yes": 0.9, "No": 0.1},
                "confidence": 0.8,
            }
        },
        "model": "openai/gpt-6-luna-decisions",
        "usage": {"input_tokens": 10, "output_tokens": 0},
    })


def make_error(status_code: int) -> OpenRouterError:
    request = httpx.Request("POST", "https://openrouter.ai/api/alpha/decisions")
    return OpenRouterError("error", httpx.Response(status_code, request=request))


def make_client(*side_effects):
    client = MagicMock()
    client.alpha.decisions.create.side_effect = side_effects
    return client


class TestCreateOpenrouterClient:
    def test_points_at_openrouter_base_url(self):
        client = create_openrouter_client()
        server_url, _ = client.sdk_configuration.get_server_details()
        assert server_url == "https://openrouter.ai/api/v1"

    def test_disables_sdk_retries(self):
        client = create_openrouter_client()
        assert client.sdk_configuration.retry_config is None


class TestClassifyArticle:
    def test_yes_returns_pass(self):
        client = make_client(make_decision("Yes"))
        result = classify_article("Journal", "Title", "Abstract", client=client)
        assert result == FILTER_PASS

    def test_no_returns_ai_reject(self):
        client = make_client(make_decision("No"))
        result = classify_article("Journal", "Title", "Abstract", client=client)
        assert result == FILTER_AI_REJECT

    def test_response_is_case_insensitive(self):
        client = make_client(make_decision("YES"))
        result = classify_article("Journal", "Title", "Abstract", client=client)
        assert result == FILTER_PASS

    def test_unexpected_answer_returns_error(self):
        client = make_client(make_decision("Maybe"))
        result = classify_article("Journal", "Title", "Abstract", client=client)
        assert result == FILTER_ERROR

    def test_sends_article_as_state_with_choice_question(self):
        client = make_client(make_decision("Yes"))
        classify_article("Journal", "Title", "Abstract", client=client)
        kwargs = client.alpha.decisions.create.call_args.kwargs
        assert kwargs["model"] == "openai/gpt-6-luna-decisions"
        assert kwargs["state"] == "Journal Name: Journal\nTitle: Title\nAbstract"
        question = kwargs["questions"][SOCSCI_QUESTION_NAME]
        assert question["type"] == "choice"
        assert set(question["criteria"]) == {"Yes", "No"}

    def test_missing_abstract_is_handled(self):
        client = make_client(make_decision("Yes"))
        result = classify_article("Journal", "Title", None, client=client)
        assert result == FILTER_PASS

    def test_retries_on_rate_limit_then_succeeds(self, monkeypatch):
        monkeypatch.setattr("src.openrouter_client.time.sleep", lambda _: None)
        error = make_error(429)
        client = make_client(error, make_decision("Yes"))
        result = classify_article(
            "Journal", "Title", "Abstract", client=client, backoff_factor=1
        )
        assert result == FILTER_PASS
        assert client.alpha.decisions.create.call_count == 2

    def test_rate_limit_exhausts_retries_returns_error(self, monkeypatch):
        monkeypatch.setattr("src.openrouter_client.time.sleep", lambda _: None)
        error = make_error(429)
        client = make_client(error, error, error)
        result = classify_article(
            "Journal", "Title", "Abstract", client=client, max_retries=3, backoff_factor=1
        )
        assert result == FILTER_ERROR
        assert client.alpha.decisions.create.call_count == 3

    def test_retries_on_server_error_then_succeeds(self, monkeypatch):
        monkeypatch.setattr("src.openrouter_client.time.sleep", lambda _: None)
        client = make_client(make_error(502), make_decision("No"))
        result = classify_article(
            "Journal", "Title", "Abstract", client=client, backoff_factor=1
        )
        assert result == FILTER_AI_REJECT
        assert client.alpha.decisions.create.call_count == 2

    def test_client_error_is_not_retried(self, monkeypatch):
        monkeypatch.setattr("src.openrouter_client.time.sleep", lambda _: None)
        client = make_client(make_error(401))
        result = classify_article(
            "Journal", "Title", "Abstract", client=client, backoff_factor=1
        )
        assert result == FILTER_ERROR
        assert client.alpha.decisions.create.call_count == 1

    def test_timeout_returns_error_after_retries(self, monkeypatch):
        monkeypatch.setattr("src.openrouter_client.time.sleep", lambda _: None)
        error = httpx.ReadTimeout("timed out")
        client = make_client(error, error)
        result = classify_article(
            "Journal", "Title", "Abstract", client=client, max_retries=2, backoff_factor=1
        )
        assert result == FILTER_ERROR
        assert client.alpha.decisions.create.call_count == 2

    def test_creates_default_client_when_none_given(self, monkeypatch):
        default_client = make_client(make_decision("Yes"))
        monkeypatch.setattr(
            "src.openrouter_client.create_openrouter_client", lambda: default_client
        )
        result = classify_article("Journal", "Title", "Abstract")
        assert result == FILTER_PASS
        default_client.alpha.decisions.create.assert_called_once()


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
