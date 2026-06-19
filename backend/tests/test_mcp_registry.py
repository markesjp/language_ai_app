from app.mcp_servers.registry import list_mcp_modules


def test_required_mcp_modules_are_registered():
    modules = list_mcp_modules()

    assert "conversation" in modules
    assert "admin-rag" in modules
    assert "usage-audit" in modules
    assert "latency-audit" in modules
    assert "analytics" in modules
