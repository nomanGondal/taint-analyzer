import ast
import logging
import re
from dataclasses import dataclass

from constants.app_constants import (
    DANGEROUS_SINKS,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)

logger = logging.getLogger(__name__)


@dataclass
class Vulnerability:
    rule: str
    severity: str
    line: int
    description: str
    fix: str


class MCPASTSCANNER:
    """AST-based heuristics for MCP agent / tool code (complements Pyre/Pysa)."""

    def scan(self, code: str) -> list[Vulnerability]:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [
                Vulnerability(
                    rule="SYNTAX_ERROR",
                    severity=SEVERITY_LOW,
                    line=e.lineno or 0,
                    description=str(e),
                    fix="Fix the syntax error before static analysis can run.",
                )
            ]

        vulnerabilities: list[Vulnerability] = []
        vulnerabilities += self._check_dangerous_calls(tree)
        vulnerabilities += self._check_prompt_injection(tree)
        vulnerabilities += self._check_mcp_tool_scope(tree)
        vulnerabilities += self._check_tool_trust_boundary(tree)
        vulnerabilities += self._check_ssrf(tree)
        vulnerabilities += self._check_hardcoded_secrets(code)
        vulnerabilities += self._check_schema_exposure(tree)
        vulnerabilities += self._check_eval_exec(tree)
        vulnerabilities += self._check_subprocess_shell_true(tree)
        vulnerabilities += self._check_dynamic_import(tree)
        vulnerabilities += self._check_deserialization(tree)
        return vulnerabilities

    def _is_mcp_tool(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        return any(self._decorator_indicates_mcp_tool(d) for d in node.decorator_list)

    def _decorator_indicates_mcp_tool(self, d: ast.expr) -> bool:
        if isinstance(d, ast.Name) and d.id == "tool":
            return True
        if isinstance(d, ast.Attribute) and d.attr == "tool":
            return True
        if isinstance(d, ast.Call):
            func = d.func
            if isinstance(func, ast.Attribute) and func.attr == "tool":
                return True
        return False

    def _tool_functions(self, tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        out: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self._is_mcp_tool(node):
                    out.append(node)
        return out

    def _param_names(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
        names: set[str] = set()
        for a in node.args.args:
            names.add(a.arg)
        for a in node.args.kwonlyargs:
            names.add(a.arg)
        if node.args.vararg:
            names.add(node.args.vararg.arg)
        if node.args.kwarg:
            names.add(node.args.kwarg.arg)
        return names

    def _check_dangerous_calls(self, tree: ast.AST) -> list[Vulnerability]:
        found: list[Vulnerability] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = self._get_call_name(node)
            if name in DANGEROUS_SINKS:
                rule, severity = DANGEROUS_SINKS[name]
                found.append(
                    Vulnerability(
                        rule=rule,
                        severity=severity,
                        line=getattr(node, "lineno", 0) or 0,
                        description=f"Dangerous call '{name}' — risky in an MCP tool or agent context.",
                        fix=f"Remove, sandbox, or strictly validate inputs before calling '{name}'.",
                    )
                )
        return found

    def _fstring_uses_params(self, node: ast.JoinedStr, params: set[str]) -> bool:
        for part in node.values:
            if isinstance(part, ast.FormattedValue):
                if self._expr_uses_names(part.value, params):
                    return True
        return False

    def _expr_uses_names(self, expr: ast.expr, names: set[str]) -> bool:
        for child in ast.walk(expr):
            if isinstance(child, ast.Name) and child.id in names:
                return True
        return False

    def _check_prompt_injection(self, tree: ast.AST) -> list[Vulnerability]:
        """Flag f-strings inside MCP tools that interpolate tool parameters (LLM / prompt risk)."""
        found: list[Vulnerability] = []
        for fn in self._tool_functions(tree):
            params = self._param_names(fn)
            if not params:
                continue
            for inner in ast.walk(fn):
                if isinstance(inner, ast.JoinedStr):
                    if self._fstring_uses_params(inner, params):
                        found.append(
                            Vulnerability(
                                rule="PROMPT_INJECTION",
                                severity=SEVERITY_HIGH,
                                line=inner.lineno or fn.lineno,
                                description=(
                                    "f-string in MCP tool interpolates tool parameters — "
                                    "untrusted content may reach prompts or tool output."
                                ),
                                fix="Structure prompts explicitly; validate, allowlist, or escape user-controlled segments.",
                            )
                        )
        return found

    def _check_mcp_tool_scope(self, tree: ast.AST) -> list[Vulnerability]:
        found: list[Vulnerability] = []
        for fn in self._tool_functions(tree):
            danger_count = sum(
                1
                for n in ast.walk(fn)
                if isinstance(n, ast.Call) and self._get_call_name(n) in DANGEROUS_SINKS
            )
            if danger_count >= 2:
                found.append(
                    Vulnerability(
                        rule="EXCESSIVE_TOOL_SCOPE",
                        severity=SEVERITY_MEDIUM,
                        line=fn.lineno or 0,
                        description=(
                            f"Tool '{fn.name}' contains {danger_count} dangerous operations — "
                            "scope may be too broad for safe MCP exposure."
                        ),
                        fix="Split into smaller single-purpose tools; narrow filesystem and process access.",
                    )
                )
        return found

    def _check_tool_trust_boundary(self, tree: ast.AST) -> list[Vulnerability]:
        mcp_tool_names: set[str] = {fn.name for fn in self._tool_functions(tree)}
        found: list[Vulnerability] = []
        for fn in self._tool_functions(tree):
            for inner in ast.walk(fn):
                if not isinstance(inner, ast.Call):
                    continue
                name = self._get_call_name(inner)
                if name in mcp_tool_names and name != fn.name:
                    found.append(
                        Vulnerability(
                            rule="TOOL_TRUST_BOUNDARY",
                            severity=SEVERITY_MEDIUM,
                            line=inner.lineno or 0,
                            description=(
                                f"Tool '{fn.name}' calls another MCP tool '{name}' directly — "
                                "weakens composability and audit boundaries."
                            ),
                            fix="Use shared plain Python helpers instead of calling other tools internally.",
                        )
                    )
        return found

    def _check_ssrf(self, tree: ast.AST) -> list[Vulnerability]:
        network_calls = {
            "requests.get",
            "requests.post",
            "requests.put",
            "requests.delete",
            "requests.request",
            "httpx.get",
            "httpx.post",
            "httpx.put",
            "httpx.delete",
            "httpx.request",
            "urllib.request.urlopen",
            "aiohttp.ClientSession.get",
            "aiohttp.ClientSession.post",
        }
        found: list[Vulnerability] = []
        for fn in self._tool_functions(tree):
            params = self._param_names(fn)
            for inner in ast.walk(fn):
                if not isinstance(inner, ast.Call):
                    continue
                call_name = self._get_call_name(inner)
                if call_name not in network_calls:
                    continue
                first = inner.args[0] if inner.args else None
                if first is not None and self._expr_uses_names(first, params):
                    found.append(
                        Vulnerability(
                            rule="SSRF",
                            severity=SEVERITY_HIGH,
                            line=inner.lineno or 0,
                            description=(
                                f"Tool parameter may flow into network call '{call_name}' (SSRF / "
                                "unintended egress)."
                            ),
                            fix="Allowlist hosts and schemes; block private IPs; do not pass raw user strings as URLs.",
                        )
                    )
        return found

    def _check_hardcoded_secrets(self, code: str) -> list[Vulnerability]:
        patterns: list[tuple[str, str, str, str, str]] = [
            (
                r"(?i)(api_key|apikey|secret|token|password|passwd)\s*=\s*[\"'][^\"']{8,}[\"']",
                "HARDCODED_SECRET",
                SEVERITY_HIGH,
                "Possible hardcoded secret assignment.",
                "Use environment variables or a secrets manager; rotate exposed credentials.",
            ),
            (
                r"sk-[a-zA-Z0-9]{20,}",
                "HARDCODED_OPENAI_KEY",
                SEVERITY_HIGH,
                "Possible hardcoded OpenAI-style API key.",
                "Remove from source; rotate the key; load from secure configuration.",
            ),
            (
                r"(?i)bearer\s+[a-zA-Z0-9\-_\.]{20,}",
                "HARDCODED_BEARER_TOKEN",
                SEVERITY_HIGH,
                "Possible hardcoded bearer token.",
                "Never commit tokens; use short-lived tokens from environment or vault.",
            ),
        ]
        found: list[Vulnerability] = []
        for lineno, line in enumerate(code.splitlines(), start=1):
            for pattern, rule, severity, desc, fix in patterns:
                if re.search(pattern, line):
                    found.append(
                        Vulnerability(
                            rule=rule,
                            severity=severity,
                            line=lineno,
                            description=desc,
                            fix=fix,
                        )
                    )
        return found

    def _check_schema_exposure(self, tree: ast.AST) -> list[Vulnerability]:
        dangerous_returns = {
            "os.listdir",
            "os.walk",
            "os.scandir",
            "glob.glob",
            "pathlib.Path.glob",
            "pathlib.Path.rglob",
        }
        found: list[Vulnerability] = []
        for fn in self._tool_functions(tree):
            for inner in ast.walk(fn):
                if isinstance(inner, ast.Call):
                    name = self._get_call_name(inner)
                    if name in dangerous_returns:
                        found.append(
                            Vulnerability(
                                rule="SCHEMA_EXPOSURE",
                                severity=SEVERITY_MEDIUM,
                                line=inner.lineno or 0,
                                description=(
                                    f"Tool uses '{name}' — may leak filesystem layout or sensitive paths to the model."
                                ),
                                fix="Return minimal filtered results; avoid full directory trees or system paths.",
                            )
                        )
        return found

    def _check_eval_exec(self, tree: ast.AST) -> list[Vulnerability]:
        found: list[Vulnerability] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = self._get_call_name(node)
                if name in ("eval", "exec", "compile"):
                    found.append(
                        Vulnerability(
                            rule="ARBITRARY_CODE_EXECUTION",
                            severity=SEVERITY_HIGH,
                            line=node.lineno or 0,
                            description=f"'{name}' can execute arbitrary code if untrusted input reaches it.",
                            fix=f"Remove '{name}'; use safe parsers or strictly validated DSLs instead.",
                        )
                    )
        return found

    def _check_subprocess_shell_true(self, tree: ast.AST) -> list[Vulnerability]:
        found: list[Vulnerability] = []
        for fn in self._tool_functions(tree):
            params = self._param_names(fn)
            for inner in ast.walk(fn):
                if not isinstance(inner, ast.Call):
                    continue
                name = self._get_call_name(inner)
                if name not in ("subprocess.run", "subprocess.call", "subprocess.Popen"):
                    continue
                shell_true = False
                for kw in inner.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        shell_true = True
                if not shell_true:
                    continue
                risky = False
                if inner.args and self._expr_uses_names(inner.args[0], params):
                    risky = True
                for kw in inner.keywords:
                    if kw.arg in ("args", "input") and self._expr_uses_names(kw.value, params):
                        risky = True
                if risky:
                    found.append(
                        Vulnerability(
                            rule="SHELL_INJECTION",
                            severity=SEVERITY_HIGH,
                            line=inner.lineno or 0,
                            description="subprocess with shell=True and user-influenced input — command injection risk.",
                            fix="Use shell=False with argument lists; never pass user strings through a shell.",
                        )
                    )
        return found

    def _check_dynamic_import(self, tree: ast.AST) -> list[Vulnerability]:
        found: list[Vulnerability] = []
        for fn in self._tool_functions(tree):
            params = self._param_names(fn)
            for inner in ast.walk(fn):
                if isinstance(inner, ast.Call):
                    name = self._get_call_name(inner)
                    if name == "__import__" and inner.args and self._expr_uses_names(inner.args[0], params):
                        found.append(
                            Vulnerability(
                                rule="DYNAMIC_IMPORT",
                                severity=SEVERITY_HIGH,
                                line=inner.lineno or 0,
                                description="User-influenced __import__ inside MCP tool — arbitrary module load risk.",
                                fix="Use static imports and an explicit allowlist of operations.",
                            )
                        )
        return found

    def _check_deserialization(self, tree: ast.AST) -> list[Vulnerability]:
        sinks = {"pickle.load", "pickle.loads", "marshal.loads", "shelve.open", "yaml.load"}
        found: list[Vulnerability] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = self._get_call_name(node)
                if name in sinks:
                    found.append(
                        Vulnerability(
                            rule="UNSAFE_DESERIALIZATION",
                            severity=SEVERITY_HIGH,
                            line=node.lineno or 0,
                            description=f"'{name}' on untrusted data can lead to remote code execution.",
                            fix="Use json or yaml.safe_load; never unpickle untrusted bytes.",
                        )
                    )
        return found

    def _get_call_name(self, node: ast.Call) -> str:
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            parts: list[str] = []
            cur: ast.expr = func
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            parts.reverse()
            return ".".join(parts) if parts else ""
        return ""
