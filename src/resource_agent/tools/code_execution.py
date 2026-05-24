import ast
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from resource_agent.tools.base import BaseTool, ToolResult

DEFAULT_TIMEOUT_SECONDS = 5
MAX_TIMEOUT_SECONDS = 10

class CodeExecutionTool(BaseTool):
    """
    Executes Python snippets in a temporary working directory with
    basic AST-based safety checks and a hard timeout.

    This is a restricted execution helper, not a true security sandbox.
    """

    name = "code_execution_tool"
    description = (
        "Executes Python code snippets in a temporary subprocess with basic "
        "AST-based restrictions and a hard timeout. Returns stdout, stderr, "
        "and the exit status."
    )
    
    blocked_imports = {"os", "sys", "subprocess", "shutil", "socket", "requests", "urllib", "http"}

    blocked_calls = {"open", "exec", "eval", "compile", "globals", "locals", "__import__", "input"}

    def run(self, arguments: Dict[str, Any]) ->ToolResult:
        code = arguments.get("code", "")
        language = arguments.get("language", "python")
        timeout = arguments.get("timeout", DEFAULT_TIMEOUT_SECONDS)

        if not isinstance(timeout, int):
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message="Timeout must be an integer number of seconds.",
            )

        if timeout < 1 or timeout > MAX_TIMEOUT_SECONDS:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"Timeout must be between 1 and {MAX_TIMEOUT_SECONDS} seconds.",
            )

        if not code:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message="No code provided for execution."
            )
        
        if language.lower() != "python":
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"Unsupported language: {language}. Only Python is supported."
            )
        
        validation_error = self._validate_code(code)

        if validation_error:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=validation_error
            )
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = Path(temp_dir)/"snippet.py"
                file_path.write_text(code, encoding="utf-8")

                result = subprocess.run(
                    [sys.executable, str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=temp_dir,
                )

                execution_data = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }

                if result.returncode != 0:
                    return ToolResult(
                        success=False,
                        tool_name=self.name,
                        data=execution_data,
                        error_message=result.stderr.strip() or f"Process exited with code {result.returncode}",
                    )

                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    data=execution_data,
                )
                
        
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"Code execution exceeded the timeout of {timeout} seconds."
            )
        
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"An error occurred during code execution: {str(exc)}"
            )
        
    def _validate_code(self, code: str) -> str:
        try:
            tree = ast.parse(code)

        except SyntaxError as exc:
            return f"Syntax error in code: {str(exc)}"
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_module = alias.name.split(",")[0]
                    if root_module in self.blocked_imports:
                        return f"Import of module '{root_module}' is not allowed."
            
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    root_module = node.module.split(",")[0]
                    if root_module in self.blocked_imports:
                        return f"Import from module '{root_module}' is not allowed."
                
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in self.blocked_calls:
                    return f"Use of function '{node.func.id}' is not allowed."
                elif isinstance(node.func, ast.Attribute) and node.func.attr in self.blocked_calls:
                    return f"Use of function '{node.func.attr}' is not allowed."
        
        return ""

