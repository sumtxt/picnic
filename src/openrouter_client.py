"""
OpenRouter API client for article classification

Uses a decision model via OpenRouter's Decisions API: the article is sent as
`state` together with a "choice" question, and the model returns the chosen
option ("Yes" / "No") rather than generated text.
"""

import logging
import time
from typing import Optional

import httpx
from openrouter import OpenRouter
from openrouter.errors import NoResponseError, OpenRouterError

from .config import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENROUTER_TIMEOUT,
    OPENROUTER_RETRY_BACKOFF,
    SOCSCI_QUESTION_NAME,
    SOCSCI_QUESTION,
    FILTER_PASS,
    FILTER_ERROR,
    FILTER_AI_REJECT,
)

# Status codes worth retrying (besides 5xx); other 4xx won't go away on retry
RETRYABLE_STATUS = {408, 429}


def create_openrouter_client() -> OpenRouter:
    """
    Create and configure OpenRouter client

    SDK-level retries are disabled (by default the SDK retries 5xx for up to
    an hour); classify_article handles retries itself.

    Returns:
        Configured OpenRouter client
    """
    return OpenRouter(
        api_key=OPENROUTER_API_KEY,
        timeout_ms=OPENROUTER_TIMEOUT * 1000,
        retry_config=None
    )


def classify_article(
    journal: str,
    title: str,
    abstract: Optional[str],
    client: Optional[OpenRouter] = None,
    question: dict = SOCSCI_QUESTION,
    model: str = OPENROUTER_MODEL,
    max_retries: int = 5,
    backoff_factor: int = OPENROUTER_RETRY_BACKOFF
) -> int:
    """
    Classify article as social science using OpenRouter Decisions API with exponential backoff

    Uses same retry logic as Crossref API (5 retries with backoff_factor=5).
    Backoff times: 5s, 10s, 20s, 40s, 80s

    Args:
        journal: Journal name
        title: Article title
        abstract: Article abstract (may be None)
        client: OpenRouter client (creates new one if None)
        question: "choice" question with options "Yes" / "No"
        model: Decision model to use (default: openai/gpt-6-luna-decisions)
        max_retries: Maximum number of retry attempts (default: 5)
        backoff_factor: Exponential backoff factor (default: 5 from config)

    Returns:
        FILTER_PASS (0) if social science
        FILTER_AI_REJECT (2) if not social science
        FILTER_ERROR (-1) on error
    """
    if client is None:
        client = create_openrouter_client()

    # Build state (same layout as the former chat user prompt)
    abstract_text = abstract if abstract else ""
    state = f"Journal Name: {journal}\nTitle: {title}\n{abstract_text}"

    # Retry loop with exponential backoff
    for attempt in range(max_retries):
        try:
            response = client.alpha.decisions.create(
                model=model,
                questions={SOCSCI_QUESTION_NAME: question},
                state=state
            )

            # Classify based on chosen option
            answer = response.answers[SOCSCI_QUESTION_NAME].choice.strip().lower()
            if answer == "no":
                return FILTER_AI_REJECT
            elif answer == "yes":
                return FILTER_PASS
            else:
                logging.warning(f"Unexpected OpenRouter choice: '{answer}' for article: {title}")
                return FILTER_ERROR

        except (OpenRouterError, NoResponseError, httpx.TransportError) as e:
            # Don't retry on client errors (e.g., invalid API key, bad request, unknown model)
            status = getattr(e, "status_code", None)
            if status is not None and status < 500 and status not in RETRYABLE_STATUS:
                logging.error(f"OpenRouter API error for article '{title}': {status}: {e}")
                return FILTER_ERROR

            if attempt < max_retries - 1:
                # Calculate backoff time: backoff_factor * (2 ** attempt)
                wait_time = backoff_factor * (2 ** attempt)
                logging.warning(
                    f"OpenRouter error for '{title}' ({status or type(e).__name__}). "
                    f"Retry {attempt + 1}/{max_retries} after {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logging.error(
                    f"OpenRouter request failed for '{title}' after {max_retries} attempts: {e}"
                )
                return FILTER_ERROR

        except Exception as e:
            logging.error(f"Unexpected error in OpenRouter classification for '{title}': {e}")
            return FILTER_ERROR

    # Should not reach here, but just in case
    return FILTER_ERROR
