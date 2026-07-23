"""
OpenRouter API client for article classification
"""

import logging
import time
from typing import Optional

from openai import OpenAI, OpenAIError, RateLimitError, APITimeoutError

from .config import (
    OPENROUTER_API_KEY,
    OPENROUTER_API_BASE,
    OPENROUTER_MODEL,
    OPENROUTER_TIMEOUT,
    OPENROUTER_RETRY_BACKOFF,
    PROMPT_SOCSCI_CLASSIFIER,
    FILTER_PASS,
    FILTER_ERROR,
    FILTER_AI_REJECT,
)


def create_openrouter_client() -> OpenAI:
    """
    Create and configure OpenRouter client

    Returns:
        Configured OpenAI client pointing to OpenRouter
    """
    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_API_BASE,
        timeout=OPENROUTER_TIMEOUT
    )


def classify_article(
    journal: str,
    title: str,
    abstract: Optional[str],
    client: Optional[OpenAI] = None,
    system_prompt: str = PROMPT_SOCSCI_CLASSIFIER,
    model: str = OPENROUTER_MODEL,
    max_retries: int = 5,
    backoff_factor: int = OPENROUTER_RETRY_BACKOFF
) -> int:
    """
    Classify article as social science using OpenRouter API with exponential backoff

    Uses same retry logic as Crossref API (5 retries with backoff_factor=5).
    Backoff times: 5s, 10s, 20s, 40s, 80s

    Args:
        journal: Journal name
        title: Article title
        abstract: Article abstract (may be None)
        client: OpenAI client configured for OpenRouter (creates new one if None)
        system_prompt: System prompt for classification
        model: Model to use (default: openai/gpt-4o-mini)
        max_retries: Maximum number of retry attempts (default: 5)
        backoff_factor: Exponential backoff factor (default: 5 from config)

    Returns:
        FILTER_PASS (0) if social science
        FILTER_AI_REJECT (2) if not social science
        FILTER_ERROR (-1) on error
    """
    if client is None:
        client = create_openrouter_client()

    # Build user prompt
    abstract_text = abstract if abstract else ""
    user_prompt = f"Journal Name: {journal}\nTitle: {title}\n{abstract_text}"

    # Retry loop with exponential backoff
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Check finish reason
            if response.choices[0].finish_reason != "stop":
                logging.warning(
                    f"Non-stop finish reason: {response.choices[0].finish_reason} "
                    f"for article: {title}"
                )
                return FILTER_ERROR

            # Get response content
            answer = response.choices[0].message.content.strip().lower()

            # Classify based on response
            if answer == "no":
                return FILTER_AI_REJECT
            elif answer == "yes":
                return FILTER_PASS
            else:
                logging.warning(f"Unexpected OpenRouter response: '{answer}' for article: {title}")
                return FILTER_ERROR

        except RateLimitError:
            if attempt < max_retries - 1:
                # Calculate backoff time: backoff_factor * (2 ** attempt)
                wait_time = backoff_factor * (2 ** attempt)
                logging.warning(
                    f"Rate limit hit for '{title}'. "
                    f"Retry {attempt + 1}/{max_retries} after {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logging.error(f"OpenRouter rate limit exceeded for '{title}' after {max_retries} attempts")
                return FILTER_ERROR

        except APITimeoutError:
            if attempt < max_retries - 1:
                wait_time = backoff_factor * (2 ** attempt)
                logging.warning(
                    f"Timeout for '{title}'. "
                    f"Retry {attempt + 1}/{max_retries} after {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logging.error(f"OpenRouter API timeout for '{title}' after {max_retries} attempts")
                return FILTER_ERROR

        except OpenAIError as e:
            # Don't retry on other errors (e.g., invalid API key, bad request)
            logging.error(f"OpenRouter API error for article '{title}': {e}")
            return FILTER_ERROR

        except Exception as e:
            logging.error(f"Unexpected error in OpenRouter classification for '{title}': {e}")
            return FILTER_ERROR

    # Should not reach here, but just in case
    return FILTER_ERROR
