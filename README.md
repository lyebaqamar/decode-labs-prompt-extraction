Zero-Shot & Few-Shot Structured Data Extraction Engine

This is my implementation of Project 1: Zero-Shot & Few-Shot Data Extraction (DecodeLabs - Batch 2026). I have developed a deterministic extraction compiler that forces Large Language Models (LLMs) to ingest messy customer service text and return structured, production-grade JSON records matching a strict 5-field schema.

My Architecture & Implementation Choices

System Prompt (Static Prefix): I engineered a prompt (prompts/extraction_system_prompt.txt) containing precise operational boundaries and 2 high-quality few-shot scenarios. I placed static constraints first to make full use of prefix-caching mechanisms.

XML Security Fencing: I wrapped dynamic inputs in <unstructured_data> XML tags. This isolates incoming customer emails and safely ignores any adversarial commands (like prompt injections) hidden inside the data.

Double Verification Pipeline: I built a verification pipeline in src/extractor.py. First, I verify key completeness, and then I use pydantic to validate enums, range bounds, and typings.

Self-Correction (Repair Loop): I implemented a simulation loop to gracefully trap parsing/schema validation errors and return rectified payloads.

File Directory Map

decode-labs-prompt-extraction/
├── requirements.txt
├── README.md
├── prompts/
│   └── extraction_system_prompt.txt
├── schemas/
│   └── ticket_schema.py
├── src/
│   └── extractor.py
└── tests/
    └── test_extraction.py


Workspace Setup & Execution Guide

1. Configure the Virtual Environment

I run the following commands in my terminal to set up a clean Python environment and load dependencies:

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt


2. Verify Output Behavior with My Test Suite

I execute my automated checks using pytest to verify the robustness of my validation and parser logic:

pytest -v

