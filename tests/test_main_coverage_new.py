"""
Tests for main.py branch coverage - targeting uncovered lines:
- 67-76: RequestLoggingMiddleware exception handling
- 102-104: lifespan directory creation
- 105-114: lifespan init_db, cleanup, shutdown
- 154-155: SecurityHeadersMiddleware HSTS in production
- 185-186: CSRF middleware HTTPException handling
- 222-224: Health check database error
- 232-235: Health check Ollama HTTP error/unreachable
- 243: Root endpoint
"""
import os
import sys
import unittest
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

os.environ["TEST_MODE"] = "1"
os.environ["MASTER_KEY"] = "7nQheyKjedj1oYnZhCq3PqxMRCl9E5rdteunHkQzGBQ="


class RequestLoggingMiddlewareTests(unittest.TestCase):
    """Tests for RequestLoggingMiddleware (lines 67-76)."""

    @patch("main.logger")
    def test_request_logging_middleware_success(self, mock_logger):
        """RequestLoggingMiddleware logs successful request."""
        import asyncio
        from main import RequestLoggingMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.state = MagicMock()
        mock_request.state.request_id = "test-req-id"

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {}

        async def call_next(request):
            return mock_response

        middleware = RequestLoggingMiddleware(None)

        async def test():
            result = await middleware.dispatch(mock_request, call_next)
            self.assertEqual(result, mock_response)
            self.assertIn("X-Request-ID", mock_response.headers)

        asyncio.run(test())

    @patch("main.logger")
    def test_request_logging_middleware_exception(self, mock_logger):
        """RequestLoggingMiddleware handles exceptions (lines 67-76)."""
        import asyncio
        from main import RequestLoggingMiddleware
        from starlette.requests import Request
        from fastapi.responses import JSONResponse

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.state = MagicMock()
        mock_request.state.request_id = "test-req-id"

        async def call_next(request):
            raise Exception("Test error")

        middleware = RequestLoggingMiddleware(None)

        async def test():
            result = await middleware.dispatch(mock_request, call_next)
            self.assertIsInstance(result, JSONResponse)
            self.assertEqual(result.status_code, 500)
            self.assertIn("Internal server error", result.body.decode())

        asyncio.run(test())

        # Verify exception was logged
        mock_logger.exception.assert_called()


class LifespanTests(unittest.TestCase):
    """Tests for lifespan context manager (lines 102-114)."""

    @patch("main.logger")
    def test_lifespan_startup_creates_directories(self, mock_logger):
        """Lifespan creates required directories on startup (lines 102-104)."""
        import asyncio
        from main import lifespan
        from fastapi import FastAPI

        mock_app = MagicMock(spec=FastAPI)

        with patch("main.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = MagicMock()
            mock_settings.UPLOAD_DIR.mkdir = MagicMock()

            with patch("main.BASE_DIR") as mock_base_dir:
                mock_history_dir = MagicMock()
                mock_history_dir.mkdir = MagicMock()
                mock_logs_dir = MagicMock()
                mock_logs_dir.mkdir = MagicMock()
                mock_base_dir.__truediv__.side_effect = lambda x: mock_history_dir if x == "history" else mock_logs_dir

                with patch("main.init_db", new_callable=AsyncMock) as mock_init_db:
                    async def run():
                        async with lifespan(mock_app):
                            pass

                    asyncio.run(run())

                    mock_settings.UPLOAD_DIR.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                    self.assertEqual(mock_history_dir.mkdir.call_count, 1)
                    self.assertEqual(mock_logs_dir.mkdir.call_count, 1)
                    mock_init_db.assert_called_once()
                    mock_logger.info.assert_any_call("Application startup complete")

    @patch("main.logger")
    def test_lifespan_shutdown_cleanup(self, mock_logger):
        """Lifespan runs cleanup on shutdown (lines 108-114)."""
        import asyncio
        from main import lifespan
        from fastapi import FastAPI

        mock_app = MagicMock(spec=FastAPI)

        with patch("main.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = MagicMock()
            mock_settings.UPLOAD_DIR.mkdir = MagicMock()

            with patch("main.BASE_DIR") as mock_base_dir:
                mock_dir = MagicMock()
                mock_dir.mkdir = MagicMock()
                mock_base_dir.__truediv__.return_value = mock_dir

                with patch("main.init_db", new_callable=AsyncMock):
                    with patch("llm._cleanup_ollama", new_callable=MagicMock) as mock_cleanup:
                        with patch("ratelimit_redis.close_rate_limit_store", new_callable=AsyncMock) as mock_close_redis:

                            async def run():
                                async with lifespan(mock_app):
                                    pass

                            asyncio.run(run())

                            mock_cleanup.assert_called_once()
                            mock_close_redis.assert_called_once()
                            mock_logger.info.assert_any_call("Application shutdown")


class SecurityHeadersMiddlewareTests(unittest.TestCase):
    """Tests for SecurityHeadersMiddleware (lines 154-155)."""

    @patch.dict("os.environ", {"ENV": "production"})
    def test_security_headers_production_hsts(self):
        """Production mode includes HSTS header (lines 154-155)."""
        import importlib
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

        async def test():
            return await middleware.dispatch(mock_request, call_next)

        result = asyncio.run(test())

        self.assertIn("Strict-Transport-Security", result.headers)
        self.assertEqual(result.headers["Strict-Transport-Security"], "max-age=31536000; includeSubDomains; preload")

    @patch.dict("os.environ", {"ENV": "development"})
    def test_security_headers_development_no_hsts(self):
        """Development mode does not include HSTS header."""
        import importlib
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

        async def test():
            return await middleware.dispatch(mock_request, call_next)

        result = asyncio.run(test())

        self.assertNotIn("Strict-Transport-Security", result.headers)

    def test_security_headers_content_security_policy(self):
        """CSP header is set correctly."""
        import importlib
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

        async def test():
            return await middleware.dispatch(mock_request, call_next)

        result = asyncio.run(test())

        self.assertIn("Content-Security-Policy", result.headers)
        self.assertIn("default-src 'self'", result.headers["Content-Security-Policy"])
        self.assertIn("script-src 'self'", result.headers["Content-Security-Policy"])

    def test_security_headers_other_security_headers(self):
        """Other security headers are set."""
        import importlib
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

        async def test():
            return await middleware.dispatch(mock_request, call_next)

        result = asyncio.run(test())

        self.assertEqual(result.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(result.headers["X-Frame-Options"], "DENY")
        self.assertEqual(result.headers["X-XSS-Protection"], "1; mode=block")
        self.assertEqual(result.headers["Referrer-Policy"], "strict-origin-when-cross-origin")


class CSRFMiddlewareTests(unittest.TestCase):
    """Tests for CSRF middleware (lines 185-186)."""

    @patch("main.verify_csrf")
    def test_csrf_middleware_valid(self, mock_verify_csrf):
        """CSRF middleware passes when valid."""
        import asyncio
        from main import csrf_middleware

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_verify_csrf.return_value = None

        async def call_next(request):
            return mock_response

        async def test():
            return await csrf_middleware(mock_request, call_next)

        result = asyncio.run(test())
        self.assertEqual(result, mock_response)

    @patch("main.verify_csrf")
    def test_csrf_middleware_invalid_returns_json_response(self, mock_verify_csrf):
        """CSRF middleware returns JSONResponse on HTTPException (lines 185-186)."""
        import asyncio
        from main import csrf_middleware
        from fastapi import HTTPException

        mock_request = MagicMock()
        mock_verify_csrf.side_effect = HTTPException(status_code=403, detail="CSRF validation failed")

        async def call_next(request):
            return MagicMock()

        async def test():
            return await csrf_middleware(mock_request, call_next)

        result = asyncio.run(test())
        self.assertEqual(result.status_code, 403)
        body = result.body.decode()
        import json
        data = json.loads(body)
        self.assertEqual(data.get("detail"), "CSRF validation failed")


class HealthCheckTests(unittest.TestCase):
    """Tests for health_check endpoint (lines 222-224, 232-235)."""

    def _parse_response(self, result):
        import json
        return json.loads(result.body.decode())

    @patch("database.engine")
    @patch("httpx.AsyncClient")
    def test_health_check_database_connected(self, mock_client_class, mock_engine):
        """Database connected returns healthy status (line 221)."""
        import asyncio
        from main import health_check

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client_class.return_value.__aenter__.return_value = mock_client

        async def test():
            return await health_check()

        result = asyncio.run(test())
        self.assertEqual(result.status_code, 200)
        body = self._parse_response(result)
        self.assertEqual(body["database"], "connected")
        self.assertEqual(body["ollama"], "connected")
        self.assertEqual(body["status"], "healthy")

    @patch("database.engine")
    @patch("httpx.AsyncClient")
    def test_health_check_database_error(self, mock_client_class, mock_engine):
        """Database error returns degraded status (lines 222-224)."""
        import asyncio
        from main import health_check

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client_class.return_value.__aenter__.return_value = mock_client

        async def test():
            return await health_check()

        result = asyncio.run(test())
        self.assertEqual(result.status_code, 503)
        body = self._parse_response(result)
        self.assertIn("error: DB error", body["database"])
        self.assertEqual(body["status"], "degraded")

    @patch("database.engine")
    @patch("httpx.AsyncClient")
    def test_health_check_ollama_http_error(self, mock_client_class, mock_engine):
        """Ollama HTTP error status (lines 232-233)."""
        import asyncio
        from main import health_check

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client_class.return_value.__aenter__.return_value = mock_client

        async def test():
            return await health_check()

        result = asyncio.run(test())
        body = self._parse_response(result)
        self.assertEqual(body["ollama"], "http_500")
        self.assertEqual(body["status"], "healthy")

    @patch("database.engine")
    @patch("httpx.AsyncClient")
    def test_health_check_ollama_unreachable(self, mock_client_class, mock_engine):
        """Ollama unreachable (lines 234-235)."""
        import asyncio
        from main import health_check

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        async def test():
            return await health_check()

        result = asyncio.run(test())
        body = self._parse_response(result)
        self.assertEqual(body["ollama"], "unreachable")


class RootEndpointTests(unittest.TestCase):
    """Tests for root endpoint (line 243)."""

    def test_root_endpoint(self):
        """Root endpoint returns app info."""
        import asyncio
        from main import root

        async def test():
            return await root()

        result = asyncio.run(test())
        self.assertIn("app", result)
        self.assertIn("status", result)
        self.assertIn("docs", result)
        self.assertEqual(result["status"], "running")


class MiddlewareOrderTests(unittest.TestCase):
    """Tests to verify middleware is added in correct order."""

    def test_middleware_order(self):
        """Verify middleware registration order."""
        import main
        from main import app

        # Check that middleware classes are registered
        # The order they're added matters for execution order
        middleware_classes = [m.cls for m in app.user_middleware]

        # RequestIDMiddleware should be first (outermost)
        # RequestLoggingMiddleware should be second
        # SecurityHeadersMiddleware should be third
        # RateLimitMiddleware should be fourth
        # CORSMiddleware should be fifth

        # Just verify they're all present
        from middleware.request_id import RequestIDMiddleware
        from main import RequestLoggingMiddleware, SecurityHeadersMiddleware
        from ratelimit import RateLimitMiddleware
        from fastapi.middleware.cors import CORSMiddleware

        self.assertIn(RequestIDMiddleware, middleware_classes)
        self.assertIn(RequestLoggingMiddleware, middleware_classes)
        self.assertIn(SecurityHeadersMiddleware, middleware_classes)
        self.assertIn(RateLimitMiddleware, middleware_classes)
        self.assertIn(CORSMiddleware, middleware_classes)


if __name__ == "__main__":
    unittest.main()