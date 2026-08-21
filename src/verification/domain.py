from urllib.parse import urlparse
def domain_of(url): return urlparse(url).netloc.lower().split(':')[0]
def is_trusted_domain(url,domains,suffixes):
    d=domain_of(url)
    return any(d==x or d.endswith('.'+x) for x in domains) or any(d.endswith(s) for s in suffixes)
