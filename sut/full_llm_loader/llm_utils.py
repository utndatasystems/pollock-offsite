from __future__ import annotations

import json
import os
import re

import requests

try:
    from .llm_config import (
        get_openai_api_base,
        get_openai_api_key,
        get_openai_model,
    )
except ImportError:
    from llm_config import (
        get_openai_api_base,
        get_openai_api_key,
        get_openai_model,
    )


def _get_openai_api_base() -> str:
    return os.environ.get(OPENAI_API_BASE_ENV, "https://api.openai.com/v1")


def _get_openai_model() -> str:
    return os.environ.get(OPENAI_MODEL_ENV, OPENAI_DEFAULT_MODEL)


def _query_llm(messages: list[dict[str, str]]) -> str:
    api_key = get_openai_api_key()
    api_base = get_openai_api_base()
    model = get_openai_model()

    url = f"{api_base}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 3000,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=300,
    )

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

        raise requests.HTTPError(
            f"{exc}\nOpenAI API error: {detail}",
            response=response,
        ) from exc

    body = response.json()

    if "choices" not in body or not body["choices"]:
        raise RuntimeError(
            "Unexpected LLM response: missing choices"
        )

    content = body["choices"][0]["message"].get("content")

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            "Unexpected LLM response: missing message content"
        )

    return content


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
