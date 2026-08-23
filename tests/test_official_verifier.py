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


def test_v194_deep_extraction_from_official_ad_text():
    text = '''
    Rajasthan Rajya Vidyut Utpadan Nigam Ltd. (RVUNL)
    August 04, 2026
    Advertisement No. RVUN/Rectt.-2026-27/03
    Name of Post:- Junior Accountant
    In Non-TSP Areas
    RVUN
    Total 371
    Educational Qualification: Bachelor Degree in Commerce OR IPCC / Intermediate Exam Passed OR MBA / PG Diploma in Business Management OR M.Com.
    Experience: Relevant experience not required.
    Name of Post:- Junior Assistant/ Commercial Assistant-II
    In Non-TSP Areas
    RVUN
    Total 765
    Educational Qualification: 10+2 Intermediate Exam from Any Recognized Board in India and computer qualification.
    Selection Process: Written Examination followed by document verification.
    Application Fee: General / EWS: Rs. 1000/-; SC / ST / PH: Rs. 500/-.
    How to Apply: Apply online through the official recruitment portal.
    '''
    d = _classify(text, 'https://example/ja.pdf')
    assert d['selection_process']
    assert d['application_fee_official']
    assert d['how_to_apply']
    assert len(d['post_eligibility']) >= 1


def test_v194_deep_extraction_is_conservative():
    text = '''
    Rajasthan Rajya Vidyut Utpadan Nigam Ltd. (RVUNL)
    Advertisement No. RVUN/Rectt.-2026-27/03
    Junior Accountant
    Read the notification for eligibility and selection procedure.
    '''
    d = _classify(text, 'https://example/ja.pdf')
    assert d['post_eligibility'] == []


def test_rvunl_how_to_apply_contamination_is_cleared():
    from src.verify_official import apply_to_job

    verification = {
        'advertisements': [{
            'advertisement_number': 'RVUN/Rectt.-2026-27/02',
            'organisation': 'Rajasthan Rajya Vidyut Utpadan Nigam Ltd. (RVUNL)',
            'published_date': '2026-08-04',
            'age_limit': '21–43 years',
            'pay_scale': 'Level-10',
            'application_start': '2026-08-05',
            'application_end': '2026-08-25',
            'url': 'https://example.gov.in/notification.pdf',
            'post_eligibility': [],
            'post_sections': [],
            'selection_process': 'CBT',
            'how_to_apply': 'Name of Company Field Area of Operation Rajasthan RVUN...',
            'application_fee_official': '',
            'experience_official': '',
        }],
        'combined_vacancies': 727,
        'application_start': '2026-08-05',
        'application_end': '2026-08-25',
        'post_vacancies': [],
        'raw_post_vacancies': [],
        'status': 'PASS',
    }
    facts, _ = apply_to_job({}, verification)
    assert facts['how_to_apply'] == ''
    assert 'how_to_apply_verification_note' in facts
