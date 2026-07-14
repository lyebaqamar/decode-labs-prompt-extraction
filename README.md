# Zero-Shot & Few-Shot Structured Data Extraction Engine

A deterministic extraction compiler that constrains Large Language Models (LLMs) to convert messy customer-service text into strict, production-grade JSON records that follow a 5-field schema. This repository contains an implementation for Project 1 Zero-Shot & Few-Shot Data Extraction (DecodeLabs - Batch 2026).

## Highlights / Goals
- Produce reliable, schema-compliant JSON from noisy, adversarial, or ambiguous customer messages.
- Enforce deterministic behavior through a carefully engineered system prompt and fenced input.
- Validate and auto-repair outputs to produce production-ready records.

## Key Features
- System Prompt (Static Prefix)
- A static system prompt (prompts/extraction_system_prompt.txt) with strong operational constraints and two high-quality few-shot examples to improve consistency and leverage prefix-caching.
- XML Security Fencing
- Dynamic inputs are wrapped in `<unstructured_data>` tags to isolate data and mitigate prompt-injection or adversarial payloads.
- Double Verification Pipeline
- A two-stage verification in `src/extractor.py`: 
    1) Key completeness checks, then
    2) Pydantic-based validation for enums, ranges, and types (schemas/ticket_schema.py).
- Self-Correction (Repair Loop)
- A simulation/repair loop that traps parsing or schema validation errors and attempts deterministic rectification before returning a final payload.
- Deterministic Extraction Compiler
- Forces consistent output shapes from LLMs so results can be consumed by downstream systems without additional manual cleanup.

## Repository Structure

decode-labs-prompt-extraction/
- requirements.txt
- README.md
- prompts/
  - extraction_system_prompt.txt
- schemas/
  - ticket_schema.py
- src/
  - extractor.py
- tests/
  - test_extraction.py

## Getting Started

Prerequisites
- Python 3.10+ (or the project's specified Python version)
- Git (for cloning)

Setup (recommended)
```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Running the project
- The core extraction logic lives in `src/extractor.py`. Configure any required environment variables or API keys (if integration with an LLM is enabled) before running.

Run tests
```bash
pytest -v
```

## Usage overview
1. Place the raw, unstructured customer text into the input wrapper used by the system prompt — the code uses XML fencing (`<unstructured_data> ... </unstructured_data>`).
2. The extraction compiler issues the constrained prompt to the LLM (or simulated LLM in tests) and receives a JSON response.
3. The double verification pipeline checks that all required keys are present and validates each field with Pydantic models (see `schemas/ticket_schema.py`).
4. If validation fails, the repair loop attempts to correct formatting/typing issues and re-validate the response.
5. The final validated JSON record is returned for downstream processing.

## Design & Implementation Notes
- Static Prompting: Static constraints and few-shot examples are placed at the top of the system prompt to maximize their effect regardless of dynamic input size.
- Security-by-Design: XML fencing ensures any embedded instructions inside customer text cannot escape the data context or override the system prompt.
- Determinism: The prompt and post-processing enforce deterministic outputs to minimize variance and make the outputs automatable.
- Validation: Pydantic models define strict typing, allowed enums, and numeric bounds. This avoids silent acceptance of malformed values.

## Tests
- Tests are located in `tests/test_extraction.py`. They exercise parsing, validation, and the repair loop.
- Use `pytest -v` to run the suite. Add new unit tests for edge cases (adversarial inputs, missing fields, type coercion) when changing extraction logic.

## Troubleshooting & Tips
- If tests fail due to environment differences, ensure Python version and dependency versions match `requirements.txt`.
- When integrating a live LLM, start with a small subset of inputs and enable verbose logging to trace prompt/response cycles.
- Keep the system prompt file (`prompts/extraction_system_prompt.txt`) under version control and avoid runtime modifications that could affect determinism.

## Contributing
- Open issues for bugs or feature requests.
- For code changes, follow the repo's contribution guidelines (create feature branches, add tests for new behavior, and open a PR for review).

## Contact
- Author: lyebaqamar  
- For questions about the implementation or to request collaboration, open an issue or contact the author directly via GitHub.
