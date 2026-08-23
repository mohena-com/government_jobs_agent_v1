from pathlib import Path
import hashlib
import requests

UA = "UPSC-Deep-Recruitment-Agent/1.0 (+research/monitoring)"

def download_pdf(url: str, out: str) -> tuple[str, str]:
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    if "pdf" not in (r.headers.get("content-type") or "").lower() and not url.lower().endswith(".pdf"):
        raise RuntimeError(f"Expected PDF but received {r.headers.get('content-type')}")
    p.write_bytes(r.content)
    return str(p), hashlib.sha256(r.content).hexdigest()
