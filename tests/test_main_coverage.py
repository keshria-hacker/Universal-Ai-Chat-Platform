"""
Tests for main.py branch coverage - targeting uncovered lines.
"""
import os
import sys
import unittest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ["TEST_MODE"] = "1"
os.environ["MASTER_KEY"] = "7nQheyKjedj1oYnZhCq3PqxMRCl9E5rdteunHkQzGBQ="

import importlib


class LifespanTests(unittest.TestCase):
    """Tests for lifespan manager (lines 100-114)."""

    @patch("main.logger")
    def test_lifespan_startup(self, mock_logger):
        """Test lifespan startup sequence (lines 101-106)."""
        import asyncio
        from main import lifespan
        from fastapi import FastAPI

        mock_app = MagicMock(spec=FastAPI)

        with patch("main.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = MagicMock()
            mock_settings.UPLOAD_DIR.mkdir = MagicMock()

            with patch("main.init_db", new_callable=AsyncMock) as mock_init_db:
                async def run():
                    async with lifespan(mock_app):
                        pass

                asyncio.run(run())

                mock_settings.UPLOAD_DIR.mkdir.assert_called()
                mock_init_db.assert_called_once()
                mock_logger.info.assert_any_call("Application startup complete")

    @patch("main.logger")
    def test_lifespan_shutdown(self, mock_logger):
        """Test lifespan shutdown sequence (lines 108-114)."""
        import asyncio
        from main import lifespan
        from fastapi import FastAPI

        mock_app = MagicMock(spec=FastAPI)

        with patch("main.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = MagicMock()
            mock_settings.UPLOAD_DIR.mkdir = MagicMock()

            # Patch where the imports happen (inside the function)
            with patch("llm._cleanup_ollama") as mock_cleanup_ollama:
                with patch("ratelimit_redis.close_rate_limit_store", new_callable=AsyncMock) as mock_close_redis:
                    with patch("main.init_db", new_callable=AsyncMock):
                        async def run():
                            async with lifespan(mock_app):
                                pass

                        asyncio.run(run())

                        mock_cleanup_ollama.assert_called_once()
                        mock_close_redis.assert_called_once()
                        mock_logger.info.assert_any_call("Application shutdown")


class HealthCheckTests(unittest.TestCase):
    """Tests for enhanced health check endpoint (lines 202-238)."""

    def _parse_response_body(self, result):
        """Parse JSONResponse body from bytes to dict."""
        return json.loads(result.body.decode())

    @patch("database.engine")
    @patch("httpx.AsyncClient")
    def test_health_check_database_connected(self, mock_client_class, mock_engine):
        """Test health check with database connected (lines 218-221)."""
        import asyncio
        from main import health_check

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_resp
        mock_client_class.return_value.__aenter__.return_value = mock_client_instance

        async def run():
            return await health_check()

        result = asyncio.run(run())

        self.assertEqual(result.status_code, 200)
        body = self._parse_response_body(result)
        self.assertEqual(body.get("database"), "connected")

    @patch("database.engine")
    def test_health_check_database_error(self, mock_engine):
        """Test health check with database error (lines 222-224)."""
        import asyncio
        from main import health_check

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("DB connection failed"))
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            async def run():
                return await health_check()

            result = asyncio.run(run())

            self.assertEqual(result.status_code, 503)
            body = self._parse_response_body(result)
            self.assertIn("error:", body.get("database"))

    @patch("database.engine")
    def test_health_check_ollama_connected(self, mock_engine):
        """Test health check with Ollama connected (lines 227-231)."""
        import asyncio
        from main import health_check

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            async def run():
                return await health_check()

            result = asyncio.run(run())

            body = self._parse_response_body(result)
            self.assertEqual(body.get("ollama"), "connected")

    @patch("database.engine")
    def test_health_check_ollama_http_error(self, mock_engine):
        """Test health check with Ollama HTTP error (lines 232-233)."""
        import asyncio
        from main import health_check

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            async def run():
                return await health_check()

            result = asyncio.run(run())

            body = self._parse_response_body(result)
            self.assertEqual(body.get("ollama"), "http_500")

    @patch("database.engine")
    def test_health_check_ollama_unreachable(self, mock_engine):
        """Test health check with Ollama unreachable (lines 234-235)."""
        import asyncio
        from main import health_check

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = Exception("Connection refused")
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            async def run():
                return await health_check()

            result = asyncio.run(run())

            body = self._parse_response_body(result)
            self.assertEqual(body.get("ollama"), "unreachable")


class SecurityHeadersTests(unittest.TestCase):
    """Tests for security headers middleware (lines 124-157)."""

    @patch.dict("os.environ", {"ENV": "production"})
    def test_security_headers_production_includes_hsts(self):
        """Test security headers in production includes HSTS (lines 154-155)."""
        import config
        import main

        importlib.reload(config)
        importlib.reload(main)
        from main import SecurityHeadersMiddleware

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.headers = {}

        async def call_next(request):
            return mock_response

        middleware = SecurityHeadersMiddleware(None)
        import asyncio

        async def run():
            return await middleware.dispatch(mock_request, call_next)

        result = asyncio.run(run())

        self.assertIn("Strict-Transport-Security", result.headers)
        self.assertEqual(result.headers["Strict-Transport-Security"], "max-age=31536000; includeSubDomains; preload")


class CSRFMiddlewareTests(unittest.TestCase):
    """Tests for CSRF middleware (lines 181-190)."""

    @patch("main.verify_csrf")
    def test_csrf_middleware_valid(self, mock_verify_csrf):
        """Test CSRF middleware passes when valid."""
        import asyncio
        from main import csrf_middleware

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_verify_csrf.return_value = None

        async def call_next(request):
            return mock_response

        async def run():
            return await csrf_middleware(mock_request, call_next)

        result = asyncio.run(run())
        self.assertEqual(result, mock_response)

    @patch("main.verify_csrf")
    def test_csrf_middleware_invalid(self, mock_verify_csrf):
        """Test CSRF middleware returns JSONResponse on failure (lines 186-189)."""
        import asyncio
        from main import csrf_middleware
        from fastapi import HTTPException

        mock_request = MagicMock()
        mock_verify_csrf.side_effect = HTTPException(status_code=403, detail="CSRF validation failed")

        async def call_next(request):
            return MagicMock()

        async def run():
            return await csrf_middleware(mock_request, call_next)

        result = asyncio.run(run())
        self.assertEqual(result.status_code, 403)
        body = json.loads(result.body.decode())
        self.assertEqual(body.get("detail"), "CSRF validation failed")


class RootEndpointTests(unittest.TestCase):
    """Tests for root endpoint (lines 241-243)."""

    def test_root_endpoint(self):
        """Test root endpoint returns basic info."""
        import asyncio
        from main import root

        async def run():
            return await root()

        result = asyncio.run(run())
        self.assertIn("app", result)
        self.assertIn("status", result)
        self.assertIn("docs", result)


if __name__ == "__main__":
    unittest.main()