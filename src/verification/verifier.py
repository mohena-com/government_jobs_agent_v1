from src.verification.domain import domain_of,is_trusted_domain
def verify(r,domains,suffixes):
    u=r.official_source_url or r.notification_url; r.source_verified=is_trusted_domain(u,domains,suffixes) if u else False; r.official_domain=domain_of(u) if u else ''; return r
