from src.verify_official import _classify
from src.docx.quality_gate import quality_gate

JA_DEEP = '''
RAJASTHAN RAJYA VIDYUT UTPADAN NIGAM LTD.
Advertisement No. RVUN/Rectt.-2026-27/03
3. Educational qualification
1. Junior Accountant
(a) Candidate must hold a Graduation Degree in Commerce or Business Administration from a recognized University established by law in India; or Must have passed Intermediate examination of the Institute of Cost Accountants of India, Kolkata or the Integrated Professional Competence Course (IPCC/ intermediate) examination of the Institute of Chartered Accountants of India, New Delhi; or MBA from a recognized University established by law in India or equivalent; or M.Com. of minimum two (2) years from a recognized University established by law in India or equivalent. and (b) The candidate must be possessing O or Higher Level Certificate Course conducted by DOEACC; or Certificate course on Computer concept by NIELIT, New Delhi; or Degree/ Diploma/ Certificate in Computer Science/ Computer Application.
2. Junior Assistant/ Commercial Assistant-II
(a) Candidate must have passed Senior Secondary Examination from a recognized Board or its equivalent examination. and (b) The candidate must be possessing O or Higher Level Certificate Course conducted by DOEACC; or Certificate course on Computer concept by NIELIT, New Delhi; or Degree/ Diploma/ Certificate in Computer Science/Computer Application.
(b) Candidates must possess working knowledge of Hindi written in Devnagri script and knowledge of Rajasthani culture.
2. A person who has appeared or is appearing in the final year examination...
'''

def test_v198_extracts_both_ministerial_qualifications():
    d = _classify(JA_DEEP, 'https://example/ja.pdf')
    rows = {r['post']: r for r in d['post_eligibility']}
    assert 'Junior Accountant' in rows
    assert 'Junior Assistant/ Commercial Assistant-II' in rows
    assert 'Graduation Degree in Commerce' in rows['Junior Accountant']['qualification']
    assert 'Senior Secondary Examination' in rows['Junior Assistant/ Commercial Assistant-II']['qualification']
    assert rows['Junior Accountant']['source_method'] == 'RVUNL_EDUCATION_TABLE'
    assert rows['Junior Assistant/ Commercial Assistant-II']['source_method'] == 'RVUNL_EDUCATION_TABLE'
    assert 'Disqualification' not in rows['Junior Accountant']['qualification']
    assert 'Physical Fitness' not in rows['Junior Assistant/ Commercial Assistant-II']['qualification']

def test_v198_gate_blocks_missing_junior_accountant():
    posts = [
        {'post': 'Junior Engineer-I (Electrical)', 'qualification': 'verified'},
        {'post': 'Junior Engineer-I (Mechanical)', 'qualification': 'verified'},
        {'post': 'Junior Engineer-I (Civil)', 'qualification': 'verified'},
        {'post': 'Junior Assistant/ Commercial Assistant-II', 'qualification': 'verified'},
    ]
    facts = {
        'organisation':'RVUNL','post':'RVUNL','advertisement_number':'/02; /03','published_date':'2026-08-04',
        'total_vacancies':'2005','application_start':'2026-08-05','application_end':'2026-08-25',
        'age_limit':'18-43','eligibility':'verified','official_links':[{'url':'https://example/a.pdf'}],
        'post_facts':posts,'post_vacancies':[{'post':p,'vacancies':1} for p in [
            'Junior Engineer-I (Electrical)','Junior Engineer-I (Mechanical)','Junior Engineer-I (Civil)',
            'Junior Accountant','Junior Assistant/ Commercial Assistant-II']],
        'official_verification':{'authoritative_expected_total':5},
    }
    gate=quality_gate({},facts)
    assert gate['status']=='FAIL'
    assert gate['verification_required'] is True
    assert 'junior accountant' in ' '.join(gate['errors']).lower()
