#!/usr/bin/env python3
"""Read-only image audit for FLEX ZONE Meta catalog preparation."""
import json
from collections import Counter
from pathlib import Path
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
items = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
report = []
for idx, item in enumerate(items, 1):
    if item.get("available") is False:
        continue
    id_ = f"FZ-{idx:04d}"
    path = ROOT / str(item.get("image", "")).lstrip("/")
    row = {"id": id_, "name": item.get("name", ""), "image": item.get("image", ""),
           "exists": path.is_file(), "width": None, "height": None,
           "bytes": None, "format": None, "issues": []}
    if not path.is_file():
        row["issues"].append("missing_file")
    else:
        row["bytes"] = path.stat().st_size
        if row["bytes"] > 8 * 1024 * 1024:
            row["issues"].append("over_8mb")
        try:
            with Image.open(path) as image:
                row["width"], row["height"] = image.size
                row["format"] = image.format
                if image.width < 500 or image.height < 500:
                    row["issues"].append("under_500px")
                if image.format not in ("JPEG", "PNG"):
                    row["issues"].append("not_jpeg_or_png")
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            row["issues"].append("invalid_image")
            row["error"] = str(exc)[:160]
    report.append(row)

counts = Counter(issue for row in report for issue in row["issues"])
formats = Counter(row["format"] or "missing/invalid" for row in report)
summary = {"total_available": len(report), "with_issues": sum(bool(r["issues"]) for r in report),
           "without_detected_issues": sum(not r["issues"] for r in report),
           "image_formats": dict(formats), "issue_counts": dict(counts)}
out = ROOT / "meta-image-audit-report.json"
out.write_text(json.dumps({"summary": summary, "products": report}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print("META IMAGE AUDIT SUMMARY")
print(json.dumps(summary, indent=2))
print("Report:", out.name)
