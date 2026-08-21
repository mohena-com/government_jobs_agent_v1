import hashlib, requests
from pathlib import Path
from urllib.parse import urlparse
HEADERS={'User-Agent':'GovernmentJobsAgent/1.0 (+responsible automated monitoring)'}
def get(url,timeout=30): return requests.get(url,headers=HEADERS,timeout=timeout,allow_redirects=True)
def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def is_pdf_response(r): return 'application/pdf' in (r.headers.get('content-type') or '').lower() or r.url.lower().endswith('.pdf')
def safe_filename(url):
    n=Path(urlparse(url).path).name or 'document.pdf'; return ''.join(c if c.isalnum() or c in '._-' else '_' for c in n)
