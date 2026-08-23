from src.verify_official import _rvunl_post_fact_blocks, _clean_fee

def test_rvunl_je_post_boundaries():
    text = """
    Electrical The candidate must hold Full Time four years’ Graduation Degree in Engineering as a regular student or AMIE in Electrical/ Electrical & Electronics/ Electrical, Instrumentation & Control/ Power Systems & High Voltage/Power Electronics/ Power Engineering or equivalent from a University/Institution established by Law in India and recognized equivalent to full time Graduation Degree in Engineering by AICTE, New Delhi. Mechanical The candidate must hold Full Time four years’ Graduation Degree in Engineering as a regular student or AMIE in Mechanical/ Production/ Industrial Engineering/ Production & Industrial/ Thermal/ Mechanical & Automation/ Power Engineering or equivalent from a University/Institution established by Law in India and recognized equivalent to full time Graduation Degree in Engineering by AICTE, New Delhi. Civil The candidate must hold Full Time four years’ Graduation Degree in Engineering as a regular student or AMIE in Structural/Civil Construction/Civil Engineering or equivalent from a University/Institution established by Law in India and recognized equivalent to full time Graduation Degree in Engineering by AICTE, New Delhi. (b) Candidates must possess working knowledge of Hindi written in Devnagri script and knowledge of Rajasthani culture.
    """
    rows=_rvunl_post_fact_blocks(text,'RVUN/Rectt.-2026-27/02')
    assert [r['post'] for r in rows]==['Junior Engineer-I (Electrical)','Junior Engineer-I (Mechanical)','Junior Engineer-I (Civil)']
    assert 'Mechanical/' not in rows[0]['qualification']
    assert 'Civil Construction' not in rows[1]['qualification']
    assert 'Structural/Civil Construction/Civil Engineering' in rows[2]['qualification']

def test_fee_cleaning():
    text='Application Fees General /: 1000/- EWS / BC / MBC SC / ST / PH: 500/- Pay the Examination Fee Through Debit Card / Credit Card / Net Banking / Online Only.'
    out=_clean_fee(text)
    assert out=='General: ₹1000; EWS/BC/MBC/SC/ST/PwBD: ₹500; payment: online.'
