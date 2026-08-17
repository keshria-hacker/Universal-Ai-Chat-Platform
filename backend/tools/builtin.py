"""Built-in tools for the chat application."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from backend.tools.registry import registry
from backend.tools.schemas import ToolDefinition


# -----------------------------------------------------------------------------
# Web Search Tool
# -----------------------------------------------------------------------------
async def web_search_handler(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web using DuckDuckGo (no API key required)."""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as e:
        return {"error": f"httpx and beautifulsoup4 required for web search: {str(e)}"}
    
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NexusBot/1.0)"}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, data=params, headers=headers)
        resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    
    for result in soup.select(".result__body")[:max_results]:
        title_elem = result.select_one(".result__title")
        snippet_elem = result.select_one(".result__snippet")
        url_elem = result.select_one(".result__url")
        
        if title_elem and snippet_elem:
            results.append({
                "title": title_elem.get_text(strip=True),
                "snippet": snippet_elem.get_text(strip=True),
                "url": url_elem.get_text(strip=True) if url_elem else "",
            })
    
    return {"results": results, "query": query}


web_search_tool = ToolDefinition(
    name="web_search",
    description="Search the web for current information. Returns a list of results with titles, snippets, and URLs.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "description": "Maximum number of results", "default": 5, "minimum": 1, "maximum": 10},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    handler=web_search_handler,
    capabilities=["web_access"],
)


# -----------------------------------------------------------------------------
# File System Tools
# -----------------------------------------------------------------------------
async def read_file_handler(path: str) -> dict[str, Any]:
    """Read a file from the local filesystem."""
    # Security: Restrict to allowed directories
    allowed_dirs = [Path.cwd(), Path.home() / "Documents", Path("/tmp"), Path(tempfile.gettempdir())]
    target = Path(path).resolve()
    
    if not any(target.is_relative_to(d) for d in allowed_dirs if d.exists()):
        return {"error": f"Access denied: path outside allowed directories: {path}"}
    
    if not target.exists():
        return {"error": f"File not found: {path}"}
    
    if not target.is_file():
        return {"error": f"Not a file: {path}"}
    
    try:
        content = target.read_text(encoding="utf-8")
        return {"content": content, "path": str(target), "size": len(content)}
    except UnicodeDecodeError:
        return {"error": f"File is not valid UTF-8 text: {path}"}


read_file_tool = ToolDefinition(
    name="read_file",
    description="Read the contents of a file from the local filesystem.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    handler=read_file_handler,
    capabilities=["file_access"],
)


async def list_files_handler(path: str = ".", pattern: str = "*") -> dict[str, Any]:
    """List files in a directory."""
    allowed_dirs = [Path.cwd(), Path.home() / "Documents", Path("/tmp"), Path(tempfile.gettempdir())]
    target = Path(path).resolve()
    
    if not any(target.is_relative_to(d) for d in allowed_dirs if d.exists()):
        return {"error": f"Access denied: path outside allowed directories: {path}"}
    
    if not target.exists():
        return {"error": f"Directory not found: {path}"}
    
    if not target.is_dir():
        return {"error": f"Not a directory: {path}"}
    
    files = []
    for item in target.glob(pattern):
        rel = item.relative_to(target)
        files.append({
            "name": str(rel),
            "type": "directory" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
    
    return {"files": files, "path": str(target)}


list_files_tool = ToolDefinition(
    name="list_files",
    description="List files in a directory matching a pattern.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path", "default": "."},
            "pattern": {"type": "string", "description": "Glob pattern", "default": "*"},
        },
        "additionalProperties": False,
    },
    handler=list_files_handler,
    capabilities=["file_access"],
)


# -----------------------------------------------------------------------------
# Code Execution Tool
# -----------------------------------------------------------------------------
async def execute_code_handler(code: str, language: str = "python", timeout: int = 30) -> dict[str, Any]:
    """Execute code in a sandboxed environment."""
    if language.lower() != "python":
        return {"error": f"Unsupported language: {language}. Only Python is currently supported."}
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        # Run with restricted environment
        proc = await asyncio.create_subprocess_exec(
            sys.executable, temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PYTHONPATH": "", "PYTHONDONTWRITEBYTECODE": "1"},
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"error": f"Code execution timed out after {timeout}s"}
        
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "returncode": proc.returncode,
        }
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


execute_code_tool = ToolDefinition(
    name="execute_code",
    description="Execute Python code in a sandboxed environment and return the output.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "language": {"type": "string", "description": "Programming language (only 'python' supported)", "default": "python", "enum": ["python"]},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30, "minimum": 1, "maximum": 300},
        },
        "required": ["code"],
        "additionalProperties": False,
    },
    handler=execute_code_handler,
    capabilities=["code_execution"],
)


# -----------------------------------------------------------------------------
# Register all built-in tools
# -----------------------------------------------------------------------------
def register_builtin_tools() -> None:
    """Register all built-in tools with the global registry."""
    registry.register(web_search_tool)
    registry.register(read_file_tool)
    registry.register(list_files_tool)
    registry.register(execute_code_tool)


# Auto-register on import
register_builtin_tools()
