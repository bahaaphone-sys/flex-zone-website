#!/usr/bin/env python3
"""Find possible higher-resolution local image replacements for small catalog sources.

Produces suggestions only; never swaps pictures automatically. Perceptual hashes
are approximate and must be visually verified before any use.
"""
import json
from pathlib import Path
from PIL import Image, ImageOps
ROOT=Path(__file__).resolve().parent
products=json.loads((ROOT/"products.json").read_text(encoding="utf-8"))
extensions={".jpg",".jpeg",".png",".webp"}
candidates=[]
for p in ROOT.rglob("*"):
    if not p.is_file() or p.suffix.lower() not in extensions:
        continue
    if "meta-images" in p.relative_to(ROOT).parts or ".git" in p.relative_to(ROOT).parts:
        continue
    try:
        with Image.open(p) as im:
            w,h=im.size
            if min(w,h)<500: continue
            im=ImageOps.exif_transpose(im).convert("RGB")
            thumb=im.resize((9,8),Image.Resampling.LANCZOS).convert("L")
            px=list(thumb.getdata())
            dhash=sum((1<<((y*8)+x)) for y in range(8) for x in range(8) if px[y*9+x]>px[y*9+x+1])
        candidates.append((p.relative_to(ROOT).as_posix(),w,h,dhash))
    except Exception:
        pass

def imagehash(path):
    with Image.open(path) as im:
        im=ImageOps.exif_transpose(im).convert("RGB").resize((9,8),Image.Resampling.LANCZOS).convert("L")
        px=list(im.getdata())
        return sum((1<<((y*8)+x)) for y in range(8) for x in range(8) if px[y*9+x]>px[y*9+x+1])

small=[]
for i,p in enumerate(products,1):
    if p.get("available") is False:continue
    rel=str(p.get("image","")).lstrip("/")
    src=ROOT/rel
    if not src.is_file():continue
    with Image.open(src) as im:
        dims=list(im.size)
    if min(dims)>=500:continue
    h=imagehash(src)
    matched=sorted([(int((h^other).bit_count()),path,w,ht) for path,w,ht,other in candidates if path!=rel])
    # Low difference suggests visually related images, but is not proof.
    suggested=[{"path":path,"dimensions":[w,ht],"hash_distance":dist} for dist,path,w,ht in matched[:5] if dist<=8]
    small.append({"id":f"FZ-{i:04d}","name":p.get("name"),"current":rel,"current_dimensions":dims,
                  "possible_larger_files":suggested,"needs_visual_review":bool(suggested)})
report={"small_source_images":len(small),"larger_image_files_scanned":len(candidates),
        "with_possible_matches":sum(bool(x["possible_larger_files"]) for x in small),
        "notice":"Matches are approximate and may be wrong. Do not replace images without visual inspection.",
        "products":small}
(ROOT/"meta-larger-image-candidates.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k!="products"},indent=2,ensure_ascii=False))
