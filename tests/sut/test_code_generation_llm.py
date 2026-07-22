from __future__ import annotations

from pathlib import Path

from sut.code_generation_llm import solution


FAKE_LLM_CODE = """
def repair_csv(raw_csv: str) -> str:
    lines = raw_csv.splitlines()
    if (
        len(lines) >= 4
        and lines[0].startswith("DATE,TIME,Qty")
        and lines[1].startswith("PRODUCTID,Price,ProductType")
        and lines[2].startswith("ProductDescription,URL,Comments")
    ):
        header = [
            "DATE",
            "TIME",
            "Qty",
            "PRODUCTID",
            "Price",
            "ProductType",
            "ProductDescription",
            "URL",
            "Comments",
        ]
        return ",".join(header) + "\n" + "\n".join(lines[3:])
    return raw_csv
"""


def test_parse_csv_with_validation_normal_csv(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "simple.csv"
    csv_path.write_text("name,city,amount\nAlice,Berlin,10\nBob,Munich,20\n", encoding="utf-8")
    monkeypatch.setattr(solution, "_query_llm", lambda prompt: FAKE_LLM_CODE)

    df, malformed = solution.parse_csv_with_validation(str(csv_path), llm_repair=True)

    assert list(df.columns) == ["name", "city", "amount"]
    assert df.shape == (2, 3)
    assert malformed


def test_parse_csv_with_validation_multiline_header(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "multiline.csv"
    csv_path.write_text(
        "DATE,TIME,Qty\n"
        "PRODUCTID,Price,ProductType\n"
        '"ProductDescription","URL",Comments\n'
        "2024-01-01,00:00,1,SKU-1,$9.99,Widget,Small widget,https://example.com,ok\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(solution, "_query_llm", lambda prompt: FAKE_LLM_CODE)

    df, malformed = solution.parse_csv_with_validation(str(csv_path), llm_repair=True)

    assert len(df.columns) == 9
    assert list(df.columns)[:3] == ["DATE", "TIME", "Qty"]
    assert list(df.columns)[6:9] == ["ProductDescription", "URL", "Comments"]
    assert df.shape == (1, 9)
    assert len(malformed) >= 3
