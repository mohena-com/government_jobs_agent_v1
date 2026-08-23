from pathlib import Path


def test_future_selector_script_can_import_workspace_src():
    root = Path(__file__).resolve().parents[1]
    script = root / 'scripts' / 'select_future_jobs.py'
    namespace = {'__file__': str(script), '__name__': 'not_main'}
    code = compile(script.read_text(encoding='utf-8'), str(script), 'exec')
    exec(code, namespace)
    assert 'read_docx' in namespace


def test_daily_script_does_not_use_published_today_filter():
    root = Path(__file__).resolve().parents[1]
    script = (root / 'scripts' / 'generate_today_instagram.sh').read_text(encoding='utf-8')
    assert '--published-today' not in script
    assert 'select_future_jobs.py' in script
