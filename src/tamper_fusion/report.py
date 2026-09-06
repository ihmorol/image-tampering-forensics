from __future__ import annotations
import html, json
from pathlib import Path

def write_static_report(output_dir: Path, summary: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    rows = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>" for k,v in summary.items())
    page = "<!doctype html><meta charset='utf-8'><title>Tamper fusion report</title><h1>Tamper fusion report</h1><table>" + rows + "</table>"
    (output_dir / "report.html").write_text(page, encoding="utf-8")
