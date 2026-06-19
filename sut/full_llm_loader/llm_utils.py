import json
import os
import re
import requests


OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
OPENAI_API_BASE_ENV = "OPENAI_API_BASE"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"


def _build_prompt(csv_text: str) -> str:
    return (
        "You are a CSV repair assistant.\n"
        "A corrupted CSV file is provided below. Your task is to produce a fully valid CSV file and a structured error report.\n\n"
        "Requirements:\n"
        "1) Return exactly two sections and nothing else.\n"
        "2) The first section is the fixed CSV text, including the original header row.\n"
        "3) The second section is a JSON error report describing the error types you fixed.\n"
        "4) Do not add markdown fences, analysis, or explanation outside the two sections.\n\n"
        "Format:\n"
        "--BEGIN FIXED CSV--\n"
        "<fixed CSV text>\n"
        "--END FIXED CSV--\n"
        "--BEGIN ERROR REPORT--\n"
        "<JSON object>\n"
        "--END ERROR REPORT--\n\n"
        "JSON schema for the error report:\n"
        "{\n"
        "  \"fixed_errors\": [\n"
        "    {\"type\": \"<error-type>\", \"description\": \"<what was fixed>\", \"rows\": [<example row numbers>] }\n"
        "  ],\n"
        "  \"summary\": \"<brief summary of the repair>\"\n"
        "}\n\n"
        "Corrupted CSV content:\n"
        f"{csv_text}\n"
    )


def _get_openai_api_base() -> str:
    return os.environ.get(OPENAI_API_BASE_ENV, "https://api.openai.com/v1")


def _get_openai_model() -> str:
    return os.environ.get(OPENAI_MODEL_ENV, OPENAI_DEFAULT_MODEL)


def _query_llm(prompt: str) -> str:
    api_key = os.environ.get(OPENAI_API_KEY_ENV)
    if not api_key:
        raise EnvironmentError(
            f"Missing {OPENAI_API_KEY_ENV}. Set it to a valid OpenAI API key to use the LLM repair path."
        )

    api_base = _get_openai_api_base().rstrip("/")
    model = _get_openai_model()
    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a meticulous CSV repair assistant. Fix broken CSV formatting, row length mismatch, quoting, delimiter issues, ``\n`` characters embedded inside cells, header corruption, and any common errors while preserving the original column semantics."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 3000,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=300)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        try:
            error = response.json().get("error", {})
            detail = error.get("message") or response.text
            error_type = error.get("type")
            if error_type:
                detail = f"{error_type}: {detail}"
        except ValueError:
            detail = response.text
        raise requests.HTTPError(f"{exc}\nOpenAI API error: {detail}", response=response) from exc
    body = response.json()
    if "choices" not in body or not body["choices"]:
        raise RuntimeError("Unexpected LLM response: missing choices")
    return body["choices"][0]["message"]["content"]


def _extract_sections(llm_output: str) -> tuple[str, dict]:
    csv_section = None
    json_section = None

    begin_csv = r"--BEGIN FIXED CSV--"
    end_csv = r"--END FIXED CSV--"
    begin_json = r"--BEGIN ERROR REPORT--"
    end_json = r"--END ERROR REPORT--"

    csv_match = re.search(
        f"{re.escape(begin_csv)}(.*?){re.escape(end_csv)}",
        llm_output,
        flags=re.S,
    )
    json_match = re.search(
        f"{re.escape(begin_json)}(.*?){re.escape(end_json)}",
        llm_output,
        flags=re.S,
    )

    if csv_match:
        csv_section = csv_match.group(1).strip()
    if json_match:
        json_text = json_match.group(1).strip()
        try:
            json_section = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Unable to parse JSON error report from LLM output: {exc}\n{json_text}"
            )

    if csv_section is None or json_section is None:
        if csv_section is None:
            csv_lines = []
            in_csv = False
            for line in llm_output.splitlines():
                stripped = line.strip()
                if stripped == begin_csv:
                    in_csv = True
                    continue
                if stripped == end_csv:
                    break
                if stripped == begin_json or stripped == end_json:
                    break
                if stripped == "" or stripped.startswith("Here is") or stripped.startswith("Fixed CSV"):
                    continue
                if in_csv:
                    csv_lines.append(line)
                elif stripped and not stripped.startswith("--"):
                    # If the markers are missing, accept plausible CSV lines.
                    csv_lines.append(line)
            csv_section = "\n".join(csv_lines).strip()

        if json_section is None:
            json_text = None
            json_match = re.search(r"(\{\s*\"fixed_errors\".*\})", llm_output, flags=re.S)
            if json_match:
                json_text = json_match.group(1)
            if json_text:
                try:
                    json_section = json.loads(json_text)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Unable to parse fallback JSON error report from LLM output: {exc}\n{json_text}"
                    )
            else:
                json_section = {
                    "fixed_errors": [
                        {
                            "type": "missing_error_report",
                            "description": "The LLM returned fixed CSV content but did not include a structured error report.",
                            "rows": [],
                        }
                    ],
                    "summary": "No structured error report was returned by the LLM.",
                }

    if csv_section is None:
        raise ValueError("Could not extract a fixed CSV section from the LLM output.")

    return csv_section, json_section
