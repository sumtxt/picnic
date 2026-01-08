"""
OpenAI API client for article classification

Ported from fun.R:314-344
"""

import logging
import time
from typing import Optional

from openai import OpenAI, OpenAIError, RateLimitError, APITimeoutError

from .config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TIMEOUT,
    PROMPT_SOCSCI_CLASSIFIER,
    FILTER_PASS,
    FILTER_ERROR,
    FILTER_AI_REJECT,
    CROSSREF_RETRY_BACKOFF
)


def create_openai_client() -> OpenAI:
    """
    Create and configure OpenAI client

    Returns:
        Configured OpenAI client
    """
    return OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT)


def classify_article(
    journal: str,
    title: str,
    abstract: Optional[str],
    client: Optional[OpenAI] = None,
    system_prompt: str = PROMPT_SOCSCI_CLASSIFIER,
    model: str = OPENAI_MODEL,
    max_retries: int = 5,
    backoff_factor: int = CROSSREF_RETRY_BACKOFF
) -> int:
    """
    Classify article as social science using OpenAI API with exponential backoff

    Uses same retry logic as Crossref API (5 retries with backoff_factor=5).
    Backoff times: 5s, 10s, 20s, 40s, 80s

    Ported from fun.R:314-344 and add_multidisciplinary_filter logic

    Args:
        journal: Journal name
        title: Article title
        abstract: Article abstract (may be None)
        client: OpenAI client (creates new one if None)
        system_prompt: System prompt for classification
        model: Model to use (default: gpt-4o-mini)
        max_retries: Maximum number of retry attempts (default: 5)
        backoff_factor: Exponential backoff factor (default: 5 from config)

    Returns:
        FILTER_PASS (0) if social science
        FILTER_AI_REJECT (2) if not social science
        FILTER_ERROR (-1) on error
    """
    if client is None:
        client = create_openai_client()

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
                logging.warning(f"Unexpected OpenAI response: '{answer}' for article: {title}")
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
                logging.error(f"OpenAI rate limit exceeded for '{title}' after {max_retries} attempts")
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
                logging.error(f"OpenAI API timeout for '{title}' after {max_retries} attempts")
                return FILTER_ERROR

        except OpenAIError as e:
            # Don't retry on other OpenAI errors (e.g., invalid API key, bad request)
            logging.error(f"OpenAI API error for article '{title}': {e}")
            return FILTER_ERROR

        except Exception as e:
            logging.error(f"Unexpected error in OpenAI classification for '{title}': {e}")
            return FILTER_ERROR

    # Should not reach here, but just in case
    return FILTER_ERROR
