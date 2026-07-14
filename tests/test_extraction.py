import pytest

from src.extractor import ExtractionEngine, ExtractionError
from schemas.ticket_schema import SupportTicket

VALID_JSON = """{
"customer_name": "Sarah Jenkins",
"order_number": "99218-A",
"complaint_type": "Product Quality",
"severity_level": 4,
"contact_phone": "555-0192"
}"""


@pytest.fixture
def engine():
    return ExtractionEngine()


def test_extraction_prompt_formatting(engine):
    """I verify that my prefix-caching alignment and boundary fencing render perfectly."""
    test_input = "My order #123 is broken."
    full_prompt = engine.format_extraction_prompt(test_input)

    assert full_prompt.startswith("You are a highly disciplined")
    assert "<unstructured_data>" in full_prompt
    assert "My order #123 is broken." in full_prompt
    assert "</unstructured_data>" in full_prompt


def test_clean_raw_llm_response_with_fences(engine):
    """I confirm that markdown formatting wrappers are successfully neutralized."""
    dirty_response = f"```json\n{VALID_JSON}\n```"
    cleaned = engine.clean_raw_llm_response(dirty_response)

    assert cleaned == VALID_JSON
    assert "```" not in cleaned


def test_clean_raw_llm_response_without_fences(engine):
    """I confirm plain JSON with no markdown wrapper passes through untouched."""
    cleaned = engine.clean_raw_llm_response(f"  {VALID_JSON}  ")
    assert cleaned == VALID_JSON


def test_parse_and_validate_success(engine):
    """I confirm a well-formed response parses into a valid SupportTicket."""
    ticket, error = engine.parse_and_validate(VALID_JSON)

    assert error is None
    assert isinstance(ticket, SupportTicket)
    assert ticket.customer_name == "Sarah Jenkins"
    assert ticket.complaint_type == "Product Quality"
    assert ticket.severity_level == 4


def test_parse_and_validate_invalid_json(engine):
    """I confirm malformed JSON is caught and reported, not raised."""
    ticket, error = engine.parse_and_validate("{not valid json")

    assert ticket is None
    assert "Invalid JSON" in error


def test_parse_and_validate_missing_keys(engine):
    """I confirm missing required schema keys are caught before pydantic runs."""
    incomplete = """{
"customer_name": "Sarah Jenkins",
"complaint_type": "Billing",
"severity_level": 3
}"""
    ticket, error = engine.parse_and_validate(incomplete)

    assert ticket is None
    assert "Missing required keys" in error


def test_parse_and_validate_bad_severity(engine):
    """I confirm out-of-range severity values fail pydantic bounds validation."""
    bad_severity = VALID_JSON.replace('"severity_level": 4', '"severity_level": 9')
    ticket, error = engine.parse_and_validate(bad_severity)

    assert ticket is None
    assert "Schema validation failed" in error


def test_parse_and_validate_bad_enum(engine):
    """I confirm an invalid complaint_type value is rejected by the enum."""
    bad_enum = VALID_JSON.replace(
        '"complaint_type": "Product Quality"', '"complaint_type": "Not A Real Type"'
    )
    ticket, error = engine.parse_and_validate(bad_enum)

    assert ticket is None
    assert "Schema validation failed" in error


def test_empty_string_normalized_to_none(engine):
    """I confirm blank optional fields are normalized to null instead of ''."""
    blank_phone = VALID_JSON.replace('"contact_phone": "555-0192"', '"contact_phone": "   "')
    ticket, error = engine.parse_and_validate(blank_phone)

    assert error is None
    assert ticket.contact_phone is None


def test_extract_succeeds_on_first_try(engine):
    """I confirm the end-to-end pipeline returns a ticket when the model gets it right immediately."""
    calls = []

    def fake_llm(prompt: str) -> str:
        calls.append(prompt)
        return VALID_JSON

    ticket = engine.extract("My order #123 is broken.", fake_llm)

    assert isinstance(ticket, SupportTicket)
    assert len(calls) == 1


def test_extract_self_corrects_after_bad_first_attempt(engine):
    """I confirm the repair loop feeds the error back and recovers on a later attempt."""
    responses = iter(["not json at all", VALID_JSON])

    def fake_llm(prompt: str) -> str:
        return next(responses)

    ticket = engine.extract("My order #123 is broken.", fake_llm, max_retries=2)

    assert isinstance(ticket, SupportTicket)


def test_extract_raises_after_exhausting_retries(engine):
    """I confirm extraction raises ExtractionError once every repair attempt fails."""

    def always_broken(prompt: str) -> str:
        return "still not valid json"

    with pytest.raises(ExtractionError):
        engine.extract("My order #123 is broken.", always_broken, max_retries=1)
