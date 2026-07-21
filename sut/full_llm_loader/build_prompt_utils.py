from __future__ import annotations

import random
import argparse
from pathlib import Path
from typing import Literal, TypedDict

# Run with python build_parser_prompts.py ./csvstorm_files \ --version both

PromptVersion = Literal["naive", "guided"]      # two options for prompt
CSV_PLACEHOLDER = "{{CSV_TEXT}}"                # this is where the CSV will go
BASE_DIR = Path(__file__).resolve().parent      # go to directory full_llm_loader/
PROMPTS_DIR = BASE_DIR / "prompts"              # full_llm_loader/prompts/


class PromptMessages(TypedDict):
    system: str
    user: str


def parse_args() -> argparse.Namespace:
    # Parse command-line arguments for the script.
    parser = argparse.ArgumentParser(
        description=(
            "Construct naive and/or guided LLM prompts for one "
            "explicitly specified CSV file."
        )
    )

    parser.add_argument(
        "csv_path",
        type=Path,
        help="Exact path to the CSV file.",
    )
    parser.add_argument(
        "--version",
        choices=("naive", "guided", "both"),
        default="both",
        help="Prompt version to test. Default: both.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="CSV file encoding. Default: utf-8.",
    )

    return parser.parse_args()


def get_prompt_paths(version: PromptVersion,) -> tuple[Path, Path]:
    """
    Return the system- and user-prompt paths for a prompt version.

    Expected files:
        prompts/naive_system_prompt.txt
        prompts/naive_user_prompt.txt
        prompts/guided_system_prompt.txt
        prompts/guided_user_prompt.txt
    """
    system_prompt_path = PROMPTS_DIR / f"{version}_system_prompt.txt"
    user_prompt_path = PROMPTS_DIR / f"{version}_user_prompt.txt"

    return system_prompt_path, user_prompt_path


def read_text_file(path: Path, encoding: str = "utf-8",) -> str:
    """Read a text file with useful validation and error messages."""
    if not path.is_file():
        raise FileNotFoundError(f"Required file does not exist: {path}")

    selected_encoding = ("utf-8-sig" if encoding.lower() == "utf-8" else encoding)

    try:
        return path.read_text(encoding=selected_encoding)
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Could not decode {path} using encoding "
            f"{selected_encoding!r}."
            ) from exc


def load_prompt_templates(version: PromptVersion,) -> PromptMessages:
    """
    Load the system and user prompt templates for one parser version.
    """
    system_prompt_path, user_prompt_path = get_prompt_paths(version)

    system_prompt = read_text_file(system_prompt_path)
    user_prompt = read_text_file(user_prompt_path)

    placeholder_count = user_prompt.count(CSV_PLACEHOLDER)

    if placeholder_count != 1:
        raise ValueError(
            f"{user_prompt_path} must contain exactly one "
            f"{CSV_PLACEHOLDER!r} placeholder, but contains "
            f"{placeholder_count}."
        )

    if CSV_PLACEHOLDER in system_prompt:
        raise ValueError(
            f"{system_prompt_path} must not contain "
            f"{CSV_PLACEHOLDER!r}. The CSV belongs in the user prompt."
        )

    return {
        "system": system_prompt.strip(),
        "user": user_prompt,
    }


def read_csv_file(csv_path: str | Path, encoding: str = "utf-8",) -> str:
    """
    Read a CSV artifact as raw text.

    The file is deliberately not parsed here because malformed CSV input
    must be preserved exactly for the LLM.
    """
    path = Path(csv_path)

    if not path.is_file():
        raise FileNotFoundError(f"CSV file does not exist: {path.resolve()}")

    return read_text_file(path, encoding=encoding)


def build_prompts(csv_path: str | Path, version: PromptVersion, encoding: str = "utf-8",) -> PromptMessages:
    """
    Load the selected system/user templates and insert the CSV contents
    into the user prompt.
    """
    templates = load_prompt_templates(version)
    csv_text = read_csv_file(csv_path, encoding=encoding)

    combined_user_prompt = templates["user"].replace(
        CSV_PLACEHOLDER,
        csv_text,
        1,
    )

    return {
        "system": templates["system"],
        "user": combined_user_prompt,
    }


def build_messages(csv_path: str | Path, version: PromptVersion, encoding: str = "utf-8",) -> list[dict[str, str]]:
    """
    Return OpenAI-compatible chat messages.
    """
    prompts = build_prompts(
        csv_path=csv_path,
        version=version,
        encoding=encoding,
    )

    return [
        {
            "role": "system",
            "content": prompts["system"],
        },
        {
            "role": "user",
            "content": prompts["user"],
        },
    ]


def test_prompt_construction() -> None:
    """
    Small smoke test for both prompt variants.

    Creates a temporary CSV file, constructs the prompts, and checks that:
    - both prompt files can be loaded;
    - the CSV placeholder is replaced;
    - the CSV content appears in the user prompt;
    - the system and user messages have the expected roles.
    """
    from tempfile import TemporaryDirectory

    sample_csv = (
        "name,age,city\n"
        "Alice,31,Nuremberg\n"
        "Bob,28,Berlin\n"
    )

    with TemporaryDirectory() as temporary_directory:
        csv_path = Path(temporary_directory) / "sample.csv"
        csv_path.write_text(sample_csv, encoding="utf-8")

        for version in ("naive", "guided"):
            messages = build_messages(
                csv_path=csv_path,
                version=version,
            )

            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"

            system_prompt = messages[0]["content"]
            user_prompt = messages[1]["content"]

            assert system_prompt.strip()
            assert user_prompt.strip()
            assert CSV_PLACEHOLDER not in user_prompt
            assert sample_csv in user_prompt

            print(f"\n{'=' * 70}")
            print(f"{version.upper()} PROMPT TEST PASSED")
            print(f"{'=' * 70}")
            print(f"System prompt length: {len(system_prompt)} characters")
            print(f"User prompt length:   {len(user_prompt)} characters")
            print("\nUser-prompt preview:")
            print(user_prompt[-300:])

    print("\nAll prompt-construction tests passed.")


def test_real_csv(
    csv_path: str | Path,
    version: PromptVersion | Literal["both"] = "both",
    encoding: str = "utf-8",
) -> None:
    """
    Construct and validate prompts for a specific CSV file.

    Args:
        csv_path:
            Exact path of the CSV file to insert into the prompt.
        version:
            "naive", "guided", or "both".
        encoding:
            Encoding used to read the CSV file.
    """
    path = Path(csv_path).expanduser().resolve()

    if not path.is_file():
        raise FileNotFoundError(f"CSV file does not exist: {path}")

    if path.suffix.lower() != ".csv":
        raise ValueError(f"Expected a .csv file, received: {path}")

    versions: tuple[PromptVersion, ...]

    if version == "both":
        versions = ("naive", "guided")
    else:
        versions = (version,)

    original_csv = read_csv_file(path, encoding=encoding)

    for prompt_version in versions:
        messages = build_messages(
            csv_path=path,
            version=prompt_version,
            encoding=encoding,
        )

        assert len(messages) == 2, (
            f"{prompt_version}: expected exactly two messages"
        )
        assert messages[0]["role"] == "system", (
            f"{prompt_version}: first message must be the system prompt"
        )
        assert messages[1]["role"] == "user", (
            f"{prompt_version}: second message must be the user prompt"
        )

        system_prompt = messages[0]["content"]
        user_prompt = messages[1]["content"]

        assert system_prompt.strip(), (
            f"{prompt_version}: system prompt is empty"
        )
        assert user_prompt.strip(), (
            f"{prompt_version}: user prompt is empty"
        )
        assert CSV_PLACEHOLDER not in user_prompt, (
            f"{prompt_version}: CSV placeholder was not replaced"
        )
        assert original_csv in user_prompt, (
            f"{prompt_version}: CSV content is missing from the user prompt"
        )

        print(f"\n{'=' * 70}")
        print(f"{prompt_version.upper()} PROMPT TEST PASSED")
        print(f"{'=' * 70}")
        print(f"CSV file:             {path}")
        print(f"CSV length:           {len(original_csv)} characters")
        print(f"System prompt length: {len(system_prompt)} characters")
        print(f"User prompt length:   {len(user_prompt)} characters")

        print("\nBeginning of user prompt:\n")
        print(user_prompt[:400])

        print("\n...\n")

        print("End of user prompt:\n")
        print(user_prompt[-400:])

    print("\nAll requested prompt-construction tests passed.")


if __name__ == "__main__":
    args = parse_args()

    test_real_csv(
        csv_path=args.csv_path,
        version=args.version,
        encoding=args.encoding,
    )


    # run ... to test
    # python sut/full_llm_loader/build_prompt_utils.py \ /home/neubauer/src/pollock-offsite/results/source.csv \ --version guided