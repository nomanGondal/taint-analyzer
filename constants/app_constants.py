from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = "benchmarks"
REPORTS_DIR = "reports"

PYRE_COMMAND = ["pyre", "check"]

SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"

ISSUE_TYPE_PYRE = "pyre"
ISSUE_TYPE_PYSA = "pysa"
ISSUE_TYPE_MCP = "mcp_vulnerability"

DANGEROUS_SINKS = {
    "os.system": ("COMMAND_INJECTION", SEVERITY_HIGH),
    "os.popen": ("COMMAND_INJECTION", SEVERITY_HIGH),
    "os.execv": ("COMMAND_INJECTION", SEVERITY_HIGH),
    "os.execve": ("COMMAND_INJECTION", SEVERITY_HIGH),
    "os.spawnv": ("COMMAND_INJECTION", SEVERITY_HIGH),
    "subprocess.run": ("COMMAND_INJECTION", SEVERITY_HIGH),
    "subprocess.call": ("COMMAND_INJECTION", SEVERITY_HIGH),
    "subprocess.Popen": ("COMMAND_INJECTION", SEVERITY_HIGH),
    "eval": ("CODE_INJECTION", SEVERITY_HIGH),
    "exec": ("CODE_INJECTION", SEVERITY_HIGH),
    "compile": ("CODE_INJECTION", SEVERITY_MEDIUM),
    "open": ("FILE_SYSTEM_ACCESS", SEVERITY_MEDIUM),
    "io.open": ("FILE_SYSTEM_ACCESS", SEVERITY_MEDIUM),
    "os.remove": ("FILE_SYSTEM_ACCESS", SEVERITY_MEDIUM),
    "os.unlink": ("FILE_SYSTEM_ACCESS", SEVERITY_MEDIUM),
    "os.rmdir": ("FILE_SYSTEM_ACCESS", SEVERITY_MEDIUM),
    "shutil.rmtree": ("FILE_SYSTEM_ACCESS", SEVERITY_HIGH),
    "shutil.move": ("FILE_SYSTEM_ACCESS", SEVERITY_MEDIUM),
    "socket.socket": ("NETWORK_EXPOSURE", SEVERITY_MEDIUM),
    "socket.create_connection": ("NETWORK_EXPOSURE", SEVERITY_MEDIUM),
    "os.environ.get": ("SENSITIVE_DATA_ACCESS", SEVERITY_LOW),
    "pickle.load": ("DESERIALIZATION", SEVERITY_HIGH),
    "pickle.loads": ("DESERIALIZATION", SEVERITY_HIGH),
    "marshal.loads": ("DESERIALIZATION", SEVERITY_HIGH),
    "ctypes.CDLL": ("NATIVE_CODE_LOAD", SEVERITY_HIGH),
    "ctypes.cast": ("MEMORY_UNSAFE", SEVERITY_MEDIUM),
}

MCP_TOOL_DECORATORS = ['tool']
