import ast
import operator as op
from typing import Any, Dict

from resource_agent.tools.base import BaseTool, ToolResult

class CalculatorTool(BaseTool):
    name = "calculator"
    description = "A simple calculator that can evaluate basic arithmetic expressions."
    timeout_seconds = 2

    allowed_operators = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.Pow: op.pow,
        ast.USub: op.neg,
    }

    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        """Evaluate a basic arithmetic expression safely.

        Args:
            arguments: Tool payload containing the `expression` to evaluate.

        Returns:
            ToolResult: Result payload containing either the computed value or
                an error message.
        """
        expression = arguments.get("expression")

        if not isinstance(expression, str) or not expression.strip():
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message="No arithmetic expression provided.",
            )

        try:
            result = self._safe_eval(expression)

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "expression": expression,
                    "result": result,
                },
            )

        except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as error:
            return ToolResult(
                success=False,
                tool_name=self.name,
                data={
                    "expression": expression,
                },
                error_message=str(error),
            )

    def _safe_eval(self, expression: str):
        """Parse an arithmetic expression and evaluate its AST body.

        Args:
            expression: Arithmetic expression to parse.

        Returns:
            Any: Numeric result of the evaluated expression.
        """
        node = ast.parse(expression, mode="eval").body
        return self._eval_node(node)

    def _eval_node(self, node):
        """Recursively evaluate a supported arithmetic AST node.

        Args:
            node: AST node produced from a parsed expression.

        Returns:
            Any: Numeric value represented by the node.
        """
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numeric values are allowed.")

        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            operator_type = type(node.op)

            if operator_type not in self.allowed_operators:
                raise ValueError("Operator is not allowed.")

            return self.allowed_operators[operator_type](left, right)

        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            operator_type = type(node.op)

            if operator_type not in self.allowed_operators:
                raise ValueError("Unary operator is not allowed.")

            return self.allowed_operators[operator_type](operand)

        raise ValueError("Invalid expression.")
