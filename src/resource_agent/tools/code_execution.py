import ast
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from resource_agent.tools.base import BaseTool, ToolResult

class CodeExecutionTool(BaseTool):
    name = "code_execution_tool"
    description = ("This tool executes Python code snippets in a secure, sandboxed environment. "
                     "It accepts a code snippet as input and returns the output or any error messages.")
    
    blocked_imports = {"os", "sys", "subprocess", "shutil", "socket", "requests", "urllib", "http"}

    blocked_calls = {"open", "exec", "eval", "compile", "globals", "locals", "__import__", "input"}

    def run(self, arguments: Dict[str, Any]) ->ToolResult:
        code = arguments.get("code", "")
        language = arguments.get("language", "python")
        timeout = arguments.get("timeout", 5)

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
                    ["python", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=temp_dir,
                )

                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    data={
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    },
                    error = result.stderr if result.returncode != 0 else None
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

