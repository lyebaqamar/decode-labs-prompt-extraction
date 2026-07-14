import json
import os
import re
from typing import Any, Callable, Dict, Optional, Tuple

from pydantic import ValidationError

from schemas.ticket_schema import REQUIRED_KEYS, SupportTicket


class ExtractionError(Exception):
    """I raise this when extraction still fails after every repair attempt is exhausted."""


class ExtractionEngine:
    """
    My core processing engine. I handle loading the static system prompt from disk,
    formatting dynamic user inputs safely inside XML delimiters, cleaning markdown
    remnants from LLM output, and running a strict multi-stage parsing, validation,
    and self-correction pipeline.
    """

    def __init__(self, system_prompt_path: str = "prompts/extraction_system_prompt.txt"):
        if not os.path.exists(system_prompt_path):
            raise FileNotFoundError(
                f"I could not locate the system prompt file at: {system_prompt_path}"
            )

        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read().strip()

    def format_extraction_prompt(self, user_text: str) -> str:
        """
        I wrap raw input inside strict XML tags. This acts as a protective boundary
        against prompt injection attempts, isolating untrusted user input.
        """
        return (
            f"{self.system_prompt}\n\n"
            f"Input:\n<unstructured_data>\n{user_text}\n</unstructured_data>\n"
        )

    def clean_raw_llm_response(self, raw_response: str) -> str:
        """
        I strip any sneaky markdown code-fence wrappers (e.g. ```json ... ``` or
        ``` ... ```) and surrounding whitespace so only the raw, parseable JSON
        body remains.
        """
        cleaned = raw_response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    def _check_key_completeness(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        I verify that every required key from the schema is present in the parsed
        dictionary before handing it off to pydantic for deeper type/range checks.
        This is the first stage of my double verification pipeline.
        """
        missing = REQUIRED_KEYS - set(data.keys())
        if missing:
            return False, f"Missing required keys: {sorted(missing)}"
        return True, None

    def parse_and_validate(
        self, raw_response: str
    ) -> Tuple[Optional[SupportTicket], Optional[str]]:
        """
        I run the double verification pipeline:
          1. Clean the response, then parse it as JSON.
          2. Verify key completeness against the schema contract.
          3. Validate enums, types, and bounds using pydantic.

        I return (ticket, None) on success or (None, error_message) on failure.
        I never raise here -- the caller uses the error message to drive the
        self-correction repair loop.
        """
        cleaned = self.clean_raw_llm_response(raw_response)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            return None, f"Invalid JSON: {exc}"

        if not isinstance(data, dict):
            return None, "Parsed JSON is not an object."

        keys_ok, key_error = self._check_key_completeness(data)
        if not keys_ok:
            return None, key_error

        try:
            ticket = SupportTicket(**data)
        except ValidationError as exc:
            return None, f"Schema validation failed: {exc}"

        return ticket, None

    def build_repair_prompt(
        self, user_text: str, failed_response: str, error_message: str
    ) -> str:
        """
        I construct a follow-up prompt that shows the model its own broken output
        plus the exact validation error, and asks it to return a corrected JSON
        object that satisfies the schema this time.
        """
        return (
            f"{self.system_prompt}\n\n"
            f"Input:\n<unstructured_data>\n{user_text}\n</unstructured_data>\n\n"
            "Your previous response failed validation and could not be used.\n"
            f"Previous response:\n{failed_response}\n\n"
            f"Validation error:\n{error_message}\n\n"
            "Return ONLY a corrected, valid JSON object that fixes this error and "
            "strictly matches the schema. Do not include any commentary."
        )

    def extract(
        self,
        user_text: str,
        llm_call_fn: Callable[[str], str],
        max_retries: int = 2,
    ) -> SupportTicket:
        """
        I run the end-to-end extraction pipeline against a caller-supplied model
        function. `llm_call_fn` takes a prompt string and returns the model's raw
        text response, which keeps this engine provider-agnostic (OpenAI, Anthropic,
        a local model, or a test stub can all be plugged in).

        On a failed parse/validation, I trigger the self-correction repair loop:
        I feed the model its own error back and give it up to `max_retries`
        additional attempts to produce a rectified payload.
        """
        prompt = self.format_extraction_prompt(user_text)
        raw_response = llm_call_fn(prompt)

        ticket, error = self.parse_and_validate(raw_response)
        attempt = 0

        while ticket is None and attempt < max_retries:
            repair_prompt = self.build_repair_prompt(user_text, raw_response, error)
            raw_response = llm_call_fn(repair_prompt)
            ticket, error = self.parse_and_validate(raw_response)
            attempt += 1

        if ticket is None:
            raise ExtractionError(
                f"Extraction failed after {max_retries} repair attempt(s): {error}"
            )

        return ticket
