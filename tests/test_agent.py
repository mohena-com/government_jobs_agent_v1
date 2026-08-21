from src.verification.domain import is_trusted_domain
def test_gov(): assert is_trusted_domain('https://x.gov.in/a',[],['.gov.in'])
def test_bad(): assert not is_trusted_domain('https://x.com/a',[],['.gov.in'])
