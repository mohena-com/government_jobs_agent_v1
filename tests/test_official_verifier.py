from src.verify_official import _classify, reconcile

JA_TEXT = '''
RAJASTHAN RAJYA VIDYUT UTPADAN NIGAM LTD.
August 04, 2026
Common Recruitment of Junior Accountant and Junior Assistant/ Commercial Assistant-II
(Advertisement No. RVUN/Rectt.-2026-27/03)
(i) Name of Post:- Junior Accountant
In Non-TSP Areas
RVUN\nTotal 41\nRVPN\nTotal 28\nJVVN\nTotal 116\nAVVN\nTotal 30\nJDVVN\nTotal 134
In TSP Areas
RVUN\nTotal 3\nAVVN\nTotal 18\nJDVVN\nTotal 1
HORIZONTAL RESERVATION
(ii) Name of Post:- Junior Assistant/ Commercial Assistant-II
In Non-TSP Areas
RVUN\nTotal 43\nRVPN\nTotal 41\nJVVN\nTotal 288\nAVVN\nTotal 126\nJDVVN\nTotal 186
In TSP Areas
RVUN\nTotal 2\nAVVN\nTotal 75\nJDVVN\nTotal 4
HORIZONTAL RESERVATION
Age Candidates must have attained the age of 18 years and must have not attained 40 years. upper age ... 43 years.
IMPORTANT DATES
Date of opening Website Link for submission of Online Application Form
5th August, 2026 (10.00 AM)
Last Date of submission of Online Application Form
25th August, 2026 (12.00 Midnight)
'''

JE_TEXT = """
RAJASTHAN RAJYA VIDYUT UTPADAN NIGAM LTD.
August 04, 2026
Common Recruitment of Junior Engineers-I
(Advertisement No. RVUN/Rectt.-2026-27/02)
(i) Name of Post:- Junior Engineer-I (Electrical)
In Non-TSP Areas
RVUN\nTotal 108\nRVPN\nTotal 156\nJVVN\nTotal 189\nAVVN\nTotal 122\nJDVVN\nTotal 119
In TSP Areas
RVUN\nTotal 1\nRVPN\nTotal 6\nAVVN\nTotal 22\nJDVVN\nTotal 4
HORIZONTAL RESERVATION
(ii) Name of Post:- Junior Engineer-I (Mechanical)
In Non-TSP Areas
RVUN\nTotal 108
In TSP Areas
RVUN\nTotal 2
HORIZONTAL RESERVATION
(iii) Name of Post:- Junior Engineer-I (Civil)
In Non-TSP Areas
RVPN\nTotal 31
In TSP Areas
RVPN\nTotal 1
HORIZONTAL RESERVATION
IMPORTANT DATES
5th August, 2026 (10.00 AM)
25th August, 2026 (12.00 Midnight)
"""

def test_classify_ja_totals_and_dates():
    d = _classify(JA_TEXT, 'https://example/ja.pdf')
    assert d['advertisement_number'] == 'RVUN/Rectt.-2026-27/03'
    assert sum(p['total'] for p in d['post_sections']) == 1136
    assert d['application_start'] == '2026-08-05'
    assert d['application_end'] == '2026-08-25'

def test_classify_je_total_from_sections_fixture():
    d = _classify(JE_TEXT, 'https://example/je.pdf')
    assert d['advertisement_number'] == 'RVUN/Rectt.-2026-27/02'
    assert sum(p['total'] for p in d['post_sections']) == 869

def test_reconcile_combined_rvunl():
    ja = _classify(JA_TEXT, 'https://example/ja.pdf')
    je = _classify(JE_TEXT, 'https://example/je.pdf')
    r = reconcile([ja, je], [])
    assert r['combined_vacancies'] == 2005
    assert r['application_start'] == '2026-08-05'
    assert r['application_end'] == '2026-08-25'
    assert r['status'] == 'PASS'
