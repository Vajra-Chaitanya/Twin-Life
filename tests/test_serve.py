from fastapi.testclient import TestClient

from serve import create_server


def make_dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log('x');" * 200)
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "face.json").write_text("{}")
    (tmp_path / "index.html").write_text("<!doctype html><div id=root></div>")
    return tmp_path


def test_production_server_serves_spa_api_and_cached_assets(tmp_path):
    client = TestClient(create_server(make_dist(tmp_path)))

    # Client routes, including ones that share a name with API routes, return the app shell.
    for route in ("/", "/history", "/twin/health", "/chat"):
        page = client.get(route)
        assert page.status_code == 200 and "id=root" in page.text
        assert page.headers["cache-control"] == "no-cache"

    assert client.get("/api/health").json()["status"] == "ok"

    asset = client.get("/assets/index-abc123.js", headers={"Accept-Encoding": "gzip"})
    assert "immutable" in asset.headers["cache-control"]
    assert asset.headers["content-encoding"] == "gzip"
    assert client.get("/models/face.json").headers["cache-control"] == "public, max-age=86400"
    # Paths outside the build folder are never served.
    assert "id=root" in client.get("/../api.py").text
