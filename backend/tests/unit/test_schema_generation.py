import json
import os
import subprocess
import sys
from pathlib import Path

from tests.conftest import EXAMPLE_ENV_FILE, read_env_file


def test_schema_generation_without_oauth_credentials_or_network(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output = tmp_path / "openapi.json"
    environment = {**os.environ, **read_env_file(EXAMPLE_ENV_FILE)}
    environment.update(
        SIP_AUTH_OIDC_TOKEN_ENDPOINT="",
        SIP_AUTH_OIDC_CLIENT_ID="",
        SIP_AUTH_OIDC_CLIENT_SECRET="",
    )
    # Block sockets in the subprocess: schema generation must only import the
    # app and build its schema, never start clients or fetch a token.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import runpy
import socket
import sys

def block_network(*args, **kwargs):
    raise AssertionError("Schema generation attempted network access")

socket.socket.connect = block_network
socket.socket.connect_ex = block_network
socket.getaddrinfo = block_network
sys.argv = ["scripts/extract_docs.py", sys.argv[1]]
runpy.run_path(sys.argv[0], run_name="__main__")
""",
            str(output),
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    schema = json.loads(output.read_text())
    assert "/api/auth/register" in schema["paths"]
    assert schema["components"]["schemas"]
