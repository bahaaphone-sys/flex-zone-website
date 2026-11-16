#!/usr/bin/env python3
"""Create Meta-specific JPEG image copies and a validated catalog feed.

Original product files, images, prices and sizes are never modified.
JPEGs are padded to 600 x 600 on white, preserving the full source image.
Upscaling small images does not restore lost photographic detail.
"""
import csv
import io
import json
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
BASE = "https://bahaaphone-sys.github.io/flex-zone-website/"
PRODUCTS = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
OUTDIR = ROOT / "meta-images"
OUTDIR.mkdir(exist_ok=True)
FEED = ROOT / "meta-catalog-ready-review.csv"
REPORT = ROOT / "meta-image-conversion-report.json"
HEADERS = ["id", "title", "description", "availability", "condition",
           "price", "link", "image_link", "brand", "color"]
rows = []
results = []
failures = []

for index, p in enumerate(PRODUCTS, 1):
    if p.get("available") is False:
        continue
    product_id = f"FZ-{index:04d}"
    raw_path = str(p.get("image") or "").lstrip("/")
    image_path = (ROOT / raw_path).resolve()
    if not image_path.is_relative_to(ROOT.resolve()) or not image_path.is_file():
        failures.append(f"{product_id}: missing or unsafe image path {raw_path}")
        continue

    out_name = product_id + ".jpg"
    dest = OUTDIR / out_name
    try:
        with Image.open(image_path) as source:
            source.load()
            original_size = source.size
            original_format = source.format
            source = ImageOps.exif_transpose(source)
            if source.mode == "RGBA" or "transparency" in source.info:
                rgba = source.convert("RGBA")
                white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                white.alpha_composite(rgba)
                rgb = white.convert("RGB")
            else:
                rgb = source.convert("RGB")
            canvas = Image.new("RGB", (600, 600), "white")
            rgb.thumbnail((600, 600), Image.Resampling.LANCZOS)
            canvas.paste(rgb, ((600 - rgb.width) // 2, (600 - rgb.height) // 2))
            canvas.save(dest, "JPEG", quality=88, optimize=True, progressive=True)
        if dest.stat().st_size > 8 * 1024 * 1024:
            failures.append(f"{product_id}: generated image exceeds 8 MB")
            dest.unlink(missing_ok=True)
            continue
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        failures.append(f"{product_id}: {type(exc).__name__}: {exc}")
        dest.unlink(missing_ok=True)
        continue

    # Feed uses exact indexed products; IDs remain stable if product order doesn't change.
    title = str(p.get("name") or "").strip()
    price = p.get("price")
    if not title or not isinstance(price, (int, float)) or price <= 0:
        failures.append(f"{product_id}: invalid title or price")
        dest.unlink(missing_ok=True)
        continue
    rows.append({
        "id": product_id,
        "title": title,
        "description": str(p.get("description") or title).strip(),
        "availability": "in stock",
        "condition": "new",
        "price": f"{price:.2f} USD",
        "link": BASE + "product.html?id=" + product_id,
        "image_link": BASE + "meta-images/" + out_name,
        "brand": "FLEX ZONE",
        "color": str(p.get("colors") or "").strip(),
    })
    results.append({
        "id": product_id, "original_file": raw_path,
        "original_format": original_format,
        "original_dimensions": list(original_size),
        "catalog_image": "meta-images/" + out_name,
        "catalog_dimensions": [600, 600],
        "catalog_bytes": dest.stat().st_size,
        "upscaled": original_size[0] < 600 or original_size[1] < 600,
    })

with FEED.open("w", encoding="utf-8-sig", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(rows)

report = {
    "available_products": sum(p.get("available") is not False for p in PRODUCTS),
    "generated_images": len(results),
    "failed_products": len(failures),
    "upsampled_images": sum(r["upscaled"] for r in results),
    "failures": failures,
    "products": results,
    "note": "Source images remain untouched. Upscaling cannot restore lost detail. Brand field is the store name pending owner review."
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k!="products"}, indent=2, ensure_ascii=False))
if failures:
    raise SystemExit("Image conversions incomplete; review report before upload")
