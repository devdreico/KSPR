import pytest
from kspr_engine.analyzer import analyze
from kspr_engine.config import Settings
from kspr_engine.models import AnalysisRequest, SourceFile


@pytest.mark.asyncio
async def test_local_analysis_builds_markdown_package():
    request = AnalysisRequest(
        project_name="Inventario legado",
        files=[SourceFile(path="FrmInventario.cs", content="""
        private void btnConfirmarAjuste_Click(object sender, EventArgs e) { }
        string query = "SELECT id, nombre FROM Articulos WHERE codigo = @codigo";
        """)],
        iterations=3,
        provider="local",
    )
    result = await analyze(request, Settings())
    assert result.summary.status == "completed"
    assert result.summary.iterations_completed == 3
    assert {artifact.path for artifact in result.artifacts} >= {"README.md", "report.json"}
    assert result.report["riesgos"]
