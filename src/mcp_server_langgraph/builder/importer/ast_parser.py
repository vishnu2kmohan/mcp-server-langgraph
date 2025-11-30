"""
AST Parser for Python Code Import

Parses Python source code into Abstract Syntax Tree for analysis.

Key capabilities:
- Parse Python code safely
- Extract function definitions
- Find class definitions
- Identify LangGraph API calls
- Extract configuration values

Example:
    from mcp_server_langgraph.builder.importer import PythonCodeParser

    parser = PythonCodeParser()
    ast_tree = parser.parse_file("agent.py")

    # Extract all function calls
    calls = parser.find_function_calls(ast_tree, "add_node")
"""

import ast
from typing import Any


class PythonCodeParser:
    """
    Parser for Python source code using AST.

    Safely analyzes Python code to extract structure without execution.
    """

    def __init__(self) -> None:
        """Initialize parser."""
        self.ast_tree: ast.Module | None = None

    def parse_code(self, code: str) -> ast.Module:
        """
        Parse Python code string into AST.

        Args:
            code: Python source code

        Returns:
            AST Module

        Raises:
            SyntaxError: If code is invalid Python

        Example:
            >>> parser = PythonCodeParser()
            >>> tree = parser.parse_code("def foo(): pass")
            >>> isinstance(tree, ast.Module)
            True
        """
        self.ast_tree = ast.parse(code)
        return self.ast_tree

    def parse_file(self, file_path: str) -> ast.Module:
        """
        Parse Python file into AST.

        Args:
            file_path: Path to Python file

        Returns:
            AST Module

        Example:
            >>> parser = PythonCodeParser()
            >>> tree = parser.parse_file("agent.py")
        """
        with open(file_path) as f:
            code = f.read()

        return self.parse_code(code)

    def find_function_calls(self, tree: ast.Module | None = None, function_name: str | None = None) -> list[dict[str, Any]]:
        """
        Find all function calls in AST.

        Args:
            tree: AST tree (uses self.ast_tree if None)
            function_name: Optional filter for specific function name

        Returns:
            List of function call information

        Example:
            >>> calls = parser.find_function_calls(tree, "add_node")
            >>> len(calls)
            3
        """
        tree = tree or self.ast_tree
        if not tree:
            return []

        calls = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Get function name
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                else:
                    continue

                # Filter if function_name specified
                if function_name and func_name != function_name:
                    continue

                # Extract arguments
                args = []
                for arg in node.args:
                    args.append(self._extract_value(arg))

                # Extract keyword arguments
                kwargs = {}
                for keyword in node.keywords:
                    if keyword.arg:
                        kwargs[keyword.arg] = self._extract_value(keyword.value)

                calls.append({"function": func_name, "args": args, "kwargs": kwargs, "lineno": node.lineno})

        return calls

    def find_class_definitions(self, tree: ast.Module | None = None) -> list[dict[str, Any]]:
        """
        Find all class definitions.

        Args:
            tree: AST tree

        Returns:
            List of class information

        Example:
            >>> classes = parser.find_class_definitions(tree)
            >>> [c["name"] for c in classes]
            ['AgentState', 'MyClass']
        """
        tree = tree or self.ast_tree
        if not tree:
            return []

        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Extract base classes
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)

                # Extract class docstring
                docstring = ast.get_docstring(node)

                classes.append({"name": node.name, "bases": bases, "docstring": docstring, "lineno": node.lineno})

        return classes

    def find_variable_assignments(
        self, tree: ast.Module | None = None, variable_name: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Find variable assignments.

        Args:
            tree: AST tree
            variable_name: Optional filter for specific variable

        Returns:
            List of assignments

        Example:
            >>> assignments = parser.find_variable_assignments(tree, "graph")
            >>> assignments[0]["value"]
            'StateGraph(...)'
        """
        tree = tree or self.ast_tree
        if not tree:
            return []

        assignments = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id

                        # Filter if variable_name specified
                        if variable_name and var_name != variable_name:
                            continue

                        value = self._extract_value(node.value)

                        assignments.append({"variable": var_name, "value": value, "lineno": node.lineno})

        return assignments

    def _extract_value(self, node: ast.AST) -> Any:
        """
        Extract value from AST node.

        Handles constants, names, lists, dicts, calls, etc.

        Args:
            node: AST node

        Returns:
            Extracted value (str representation for complex types)
        """
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return [self._extract_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            return {
                self._extract_value(k): self._extract_value(v)
                for k, v in zip(node.keys, node.values, strict=False)
                if k is not None
            }
        elif isinstance(node, ast.Call):
            # Return string representation of call
            if isinstance(node.func, ast.Name):
                return f"{node.func.id}(...)"
            elif isinstance(node.func, ast.Attribute):
                return f"{node.func.attr}(...)"
            return "call(...)"
        else:
            # Return string representation for complex types
            return ast.unparse(node) if hasattr(ast, "unparse") else "..."

    def get_imports(self, tree: ast.Module | None = None) -> list[str]:
        """
        Extract all imports from code.

        Args:
            tree: AST tree

        Returns:
            List of imported modules

        Example:
            >>> imports = parser.get_imports(tree)
            >>> "langgraph" in imports
            True
        """
        tree = tree or self.ast_tree
        if not tree:
            return []

        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        return imports


# ==============================================================================
# Example Usage
# ==============================================================================

if __name__ == "__main__":
    # Example Python code
    sample_code = """
from langgraph.graph import StateGraph

class MyState(TypedDict):
    query: str
    result: str

graph = StateGraph(MyState)
graph.add_node("search", search_function)
graph.add_node("summarize", summarize_function)
graph.add_edge("search", "summarize")
graph.set_entry_point("search")

app = graph.compile()
"""

    # Parse code
    parser = PythonCodeParser()
    tree = parser.parse_code(sample_code)

    print("=" * 80)
    print("AST PARSER - TEST RUN")
    print("=" * 80)

    # Find imports
    imports = parser.get_imports(tree)
    print(f"\nImports found: {imports}")

    # Find add_node calls
    add_node_calls = parser.find_function_calls(tree, "add_node")
    print(f"\nadd_node calls: {len(add_node_calls)}")
    for call in add_node_calls:
        print(f"  - Line {call['lineno']}: add_node({call['args']})")

    # Find add_edge calls
    add_edge_calls = parser.find_function_calls(tree, "add_edge")
    print(f"\nadd_edge calls: {len(add_edge_calls)}")
    for call in add_edge_calls:
        print(f"  - Line {call['lineno']}: add_edge({call['args']})")

    # Find class definitions
    classes = parser.find_class_definitions(tree)
    print(f"\nClasses found: {len(classes)}")
    for cls in classes:
        print(f"  - {cls['name']} (bases: {cls['bases']})")

    print("\n" + "=" * 80)
