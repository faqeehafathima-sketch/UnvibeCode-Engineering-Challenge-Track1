from __future__ import annotations
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import zipfile

from unvibecode import cli

JOB = "b" * 32
TRUNCATED_BODY = b"PK\x03\x04partial"
DECLARED_CONTENT_LENGTH = 256

def valid_zip_bytes():
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("site/report-unvibecode-full.html", "<html>ok</html>")
    return data.getvalue()

class Handler(BaseHTTPRequestHandler):
    mode = "truncated"
    def log_message(self, *args):
        pass
    def send_body(self, body: bytes, content_length: int | None = None):
        self.send_response(200)
        self.send_header("Content-Type", "application/json" if self.path.endswith("/jobs") else "application/zip")
        self.send_header("Content-Length", str(len(body) if content_length is None else content_length))
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()
    def do_POST(self):
        remaining = int(self.headers.get("Content-Length", "0"))
        while remaining:
            chunk = self.rfile.read(min(65536, remaining))
            if not chunk: break
            remaining -= len(chunk)
        self.send_body(json.dumps({"job_id": JOB}).encode())
    def do_GET(self):
        if self.path.startswith(f"/analysis/jobs/{JOB}/download"):
            if self.mode == "truncated":
                self.send_body(TRUNCATED_BODY, content_length=DECLARED_CONTENT_LENGTH)
                try: self.connection.shutdown(socket.SHUT_WR)
                except OSError: pass
            else:
                self.send_body(valid_zip_bytes())
        elif self.path.startswith(f"/analysis/jobs/{JOB}?"):
            payload = {"status": "completed", "interim_ready": False, "presentation": [{"id": 1, "kind": "text", "text": "COMPLETE", "final": True}], "has_more": False}
            self.send_body(json.dumps(payload).encode())
        else:
            self.send_error(404)


def worker(port: int, repo: Path, output: Path):
    os.environ["UNVIBECODE_API_URL"] = f"http://127.0.0.1:{port}/analysis"
    return cli.main(["review", "--repository", str(repo), "--output", str(output), "--no-open-browser"])

def parent():
    records = []
    for mode in ("truncated", "truncated", "truncated", "valid"):
        Handler.mode = mode
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="unvibecode-truncated-download-") as td:
                base = Path(td)
                repo = base / "repo"
                repo.mkdir()
                (repo / "ordinary.py").write_text("print('ok')\n", encoding="utf-8")
                output = base / "results"
                env = os.environ.copy()
                env.pop("UNVIBECODE_API_URL", None)
                command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(server.server_port), str(repo), str(output)]
                cp = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
                stdout = cp.stdout.replace(str(base), "<TEMP>")
                stderr = cp.stderr.replace(str(base), "<TEMP>")
                root = str(Path(__file__).resolve().parents[1])
                stdout = stdout.replace(root, "<WORKSPACE>")
                stderr = stderr.replace(root, "<WORKSPACE>")
                appdata = os.environ.get("APPDATA", "")
                if appdata:
                    stdout = stdout.replace(appdata, "<APPDATA>")
                    stderr = stderr.replace(appdata, "<APPDATA>")
                records.append((mode, cp.returncode, stdout, stderr))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
    lines = [f"Python: {sys.version.split()[0]}", f"UnvibeCode: {__import__('unvibecode').__version__}", "Network: loopback mock HTTP only; no external requests", "Test: real Client/CLI upload, status, and result-download flow against a local HTTP mock", f"MOCK_CONTENT_LENGTH={DECLARED_CONTENT_LENGTH}", f"MOCK_BODY_LENGTH={len(TRUNCATED_BODY)}", f"MOCK_CONTENT_LENGTH_SHORTFALL={DECLARED_CONTENT_LENGTH - len(TRUNCATED_BODY)}"]
    for i, (mode, code, stdout, stderr) in enumerate(records, 1):
        lines.extend([f"\nCASE {i} mode={mode} OS_EXIT_CODE={code}", "STDOUT:", stdout.rstrip(), "STDERR:", stderr.rstrip() or "<empty>"])
    truncated_failed = all(code != 0 and "BadZipFile" in stderr for mode, code, stdout, stderr in records if mode == "truncated")
    valid_passed = records[-1][0] == "valid" and records[-1][1] == 0
    lines.extend([f"\nTRUNCATED_RESPONSE_REPEATED_UNHANDLED_BADZIPFILE={truncated_failed}", f"VALID_DOWNLOAD_CONTROL_EXIT_ZERO={valid_passed}"])
    report = "\n".join(lines) + "\n"
    print(report, end="")
    (Path(__file__).with_name("truncated-download-followup.log")).write_text(report, encoding="utf-8")
    return 0 if truncated_failed and valid_passed else 1

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        raise SystemExit(worker(int(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])))
    raise SystemExit(parent())
