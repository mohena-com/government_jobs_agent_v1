from src.verify_official import _classify, reconcile

JA_TEXT = '''
RAJASTHAN RAJYA VIDYUT UTPADAN NIGAM LTD.
August 04, 2026
Common Recruitment of Junior Accountant and Junior Assistant/ Commercial Assistant-II
(Advertisement No. RVUN/Rectt.-2026-27/03)
(i) Name of Post:- Junior Accountant
In Non-TSP Areas
RVUN\nTotal 41\nRVPN\nTotal 28\nJVVN\nTotal 116\nAVVN\nTotal 30\nJDVVN\nTotal 134
HORIZONTAL RESERVATION
In TSP Areas
RVUN\nTotal 3\nAVVN\nTotal 18\nJDVVN\nTotal 1
HORIZONTAL RESERVATION
(ii) Name of Post:- Junior Assistant/ Commercial Assistant-II
In Non-TSP Areas
RVUN\nTotal 43\nRVPN\nTotal 41\nJVVN\nTotal 288\nAVVN\nTotal 126\nJDVVN\nTotal 186
HORIZONTAL RESERVATION
In TSP Areas
RVUN\nTotal 2\nAVVN\nTotal 75\nJDVVN\nTotal 4
HORIZONTAL RESERVATION
5th August, 2026 (10.00 AM)
25th August, 2026 (12.00 Midnight)
'''

JE_TEXT = '''
RAJASTHAN RAJYA VIDYUT UTPADAN NIGAM LTD.
August 04, 2026
Common Recruitment of Junior Engineers-I
(Advertisement No. RVUN/Rectt.-2026-27/02)
(i) Name of Post:- Junior Engineer-I (Electrical)
In Non-TSP Areas
RVUN\nTotal 108\nRVPN\nTotal 156\nJVVN\nTotal 189\nAVVN\nTotal 122\nJDVVN\nTotal 119
HORIZONTAL RESERVATION
In TSP Areas
RVUN\nTotal 1\nRVPN\nTotal 6\nAVVN\nTotal 22\nJDVVN\nTotal 4
HORIZONTAL RESERVATION
(ii) Name of Post:- Junior Engineer-I (Mechanical)
In Non-TSP Areas
RVUN\nTotal 108
HORIZONTAL RESERVATION
In TSP Areas
RVUN\nTotal 2
HORIZONTAL RESERVATION
(iii) Name of Post:- Junior Engineer-I (Civil)
In Non-TSP Areas
RVPN\n31\n0\n31
HORIZONTAL RESERVATION
In TSP Areas
RVPN\n1\n0\n1
HORIZONTAL RESERVATION
5th August, 2026 (10.00 AM)
25th August, 2026 (12.00 Midnight)
'''

SHORT_TEXT = '''
RAJASTHAN RAJYA VIDYUT UTPADAN NIGAM LTD.
RVUN/P&A/Rectt.2026-27/F.103/D.172 July 30, 2026
NOTICE
A short advertisement bearing no. RVUN/Rectt.-2026-27/01 for recruitment against 2005 vacancies of Junior Engineer-I, Junior Accountant and Junior Assistant/Commercial Assistant-II in five Power Companies of Rajasthan.
5th August, 2026 (10:00 AM)
25th August, 2026 (12:00 Midnight)
'''

def test_classify_ja_totals_and_dates():
    d = _classify(JA_TEXT, 'https://example/ja.pdf')
    assert d['advertisement_number'] == 'RVUN/Rectt.-2026-27/03'
    assert [p['total'] for p in d['post_sections']] == [371, 765]
    assert d['application_start'] == '2026-08-05'
    assert d['application_end'] == '2026-08-25'

def test_classify_je_total_from_sections_fixture():
    d = _classify(JE_TEXT, 'https://example/je.pdf')
    assert d['advertisement_number'] == 'RVUN/Rectt.-2026-27/02'
    assert [p['total'] for p in d['post_sections']] == [727, 110, 32]

def test_short_notice_2005_is_preserved():
    d = _classify(SHORT_TEXT, 'https://example/short.pdf')
    assert d['document_type'] == 'SHORT_NOTICE'
    assert d['advertisement_number'] == 'RVUN/Rectt.-2026-27/01'
    assert d['short_notice_total'] == 2005

def test_reconcile_detailed_total_matches_short_notice():
    short = _classify(SHORT_TEXT, 'https://example/short.pdf')
    ja = _classify(JA_TEXT, 'https://example/ja.pdf')
    je = _classify(JE_TEXT, 'https://example/je.pdf')
    r = reconcile([short, ja, je], [])
    assert r['combined_vacancies'] == 2005
    assert r['short_notice_total'] == 2005
    assert r['vacancy_reconciliation']['difference'] == 0
    assert r['vacancy_reconciliation']['status'] == 'CONSISTENT'
    assert r['status'] == 'PASS'

def test_v192_repairs_rvunl_pdf_extraction_losses_and_reconciles_to_2005():
    short = _classify(SHORT_TEXT, 'https://example/short.pdf')
    ja = _classify(JA_TEXT, 'https://example/ja.pdf')
    je = _classify(JE_TEXT, 'https://example/je.pdf')
    r = reconcile([short, ja, je], [])
    assert r['combined_vacancies'] == 2005
    assert sorted(x['vacancies'] for x in r['post_vacancies']) == [32, 110, 371, 727, 765]
    assert r['vacancy_reconciliation']['status'] == 'CONSISTENT'
    assert r['status'] == 'PASS'


def test_v192_never_passes_when_authoritative_total_does_not_reconcile():
    short = _classify(SHORT_TEXT, 'https://example/short.pdf')
    ja = _classify(JA_TEXT.replace('Total 186', 'Total 100'), 'https://example/ja.pdf')
    je = _classify(JE_TEXT, 'https://example/je.pdf')
    # Remove one post entirely. A missing authoritative post must never PASS.
    ja['post_sections'] = ja['post_sections'][:1]
    r = reconcile([short, ja, je], [])
    assert r['status'] == 'FAIL'
