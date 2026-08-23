from datetime import date
from pathlib import Path


def load_selector():
    root = Path(__file__).resolve().parents[1]
    script = root / 'scripts' / 'select_future_jobs.py'
    namespace = {'__file__': str(script), '__name__': 'not_main'}
    code = compile(script.read_text(encoding='utf-8'), str(script), 'exec')
    exec(code, namespace)
    return namespace


def test_selector_has_no_history_or_duplicate_filtering():
    ns = load_selector()
    assert 'get_last_date' in ns
    assert 'read_history' not in ns
    assert 'used_yesterday' not in ns


def test_future_date_is_selected_and_today_is_not():
    ns = load_selector()
    get_last_date = ns['get_last_date']
    today = date(2026, 8, 23)
    assert get_last_date({'application_end': '2026-08-25'}) > today
    assert not (get_last_date({'application_end': '2026-08-23'}) > today)
    assert not (get_last_date({'application_end': '2026-08-22'}) > today)


def test_daily_script_uses_future_date_selector():
    root = Path(__file__).resolve().parents[1]
    script = (root / 'scripts' / 'generate_today_instagram.sh').read_text(encoding='utf-8')
    assert 'select_future_jobs.py' in script
    assert '--published-today' not in script
    assert 'agent_usage_history' not in script
    assert 'duplicate_filtering' in script
