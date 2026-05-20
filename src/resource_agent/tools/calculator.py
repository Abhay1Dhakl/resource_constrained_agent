import ast
import operator as op

class CalculatorTool:
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

    def run(self, expression: str) -> dict:
        try:
            result = self._safe_eval(expression)

            return {
                "tool": self.name,
                "success": True,
                "input": expression,
                "result": result,
            }

        except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as error:
            return {
                "tool": self.name,
                "success": False,
                "input": expression,
                "error": str(error),
            }

    def _safe_eval(self, expression: str):
        node = ast.parse(expression, mode="eval").body
        return self._eval_node(node)

    def _eval_node(self, node):
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