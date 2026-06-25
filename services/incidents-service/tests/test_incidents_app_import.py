def test_incidents_app_imports_with_routes_registered():
    import sys
    from pathlib import Path

    service_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(service_root))

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    from app.main import app

    assert app.title == "Incidents Service"
