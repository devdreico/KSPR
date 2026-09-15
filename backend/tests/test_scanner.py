from kspr_engine.models import SourceFile
from kspr_engine.scanner import scan_files


def test_scanner_recovers_ui_events_routes_and_sql():
    result = scan_files([SourceFile(path="src/stock.js", content="""
    const button = document.getElementById('btnConfirmar');
    button.addEventListener('click', confirmar);
    app.post('/api/v1/stock', handler);
    const query = 'UPDATE Articulos SET stock = @stock';
    """)])
    assert any(item["kind"] == "element" for item in result.ui_elements)
    assert any(item["path"] == "/api/v1/stock" for item in result.routes)
    assert result.data_operations


def test_scanner_rejects_unsafe_path():
    import pytest
    with pytest.raises(ValueError):
        SourceFile(path="../secret.py", content="x")
