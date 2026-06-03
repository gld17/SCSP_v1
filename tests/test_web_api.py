from __future__ import annotations

import unittest


class TestWebApi(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        try:
            from fastapi.testclient import TestClient
            from scsp.web_api import app
        except Exception:
            self.skipTest("fastapi or testclient not available")
            return

        client = TestClient(app)
        resp = client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("status"), "ok")


if __name__ == "__main__":
    unittest.main()
