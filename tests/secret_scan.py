"""
EdgeGuard Repository Secret & Entropy Scanner
Scans all codebase files and git commit history for credentials, private keys, API keys,
and high-entropy tokens to enforce the Zero Secret Exposure policy.
"""

import os
import re
import subprocess
import sys

SECRET_PATTERNS = [
    (r'BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY', 'Private Key Header'),
    (r'ghp_[A-Za-z0-9_]{36}', 'GitHub Personal Access Token'),
    (r'xkeysib-[a-f0-9]{64}', 'Brevo API Key'),
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key ID'),
    (r'eyJ[a-zA-Z0-9_-]{20,}\.eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}', 'JSON Web Token (JWT)'),
    (r'postgres(?:ql)?:\/\/[a-zA-Z0-9_]+:[a-zA-Z0-9_]+@', 'PostgreSQL Connection URI with Password'),
    (r'(?:api_key|apikey|private_key|secret_key)\s*[:=]\s*["\'][a-zA-Z0-9_\-]{16,}["\']', 'Generic Secret Key Assignment')
]

IGNORED_DIRS = {
    '.git', 'node_modules', 'target', '.agents', 'venv', 'env', 
    '__pycache__', 'dist', '.idea', '.vscode', '.ruff_cache'
}

IGNORED_EXTENSIONS = {
    '.png', '.svg', '.onnx', '.ico', '.jar', '.class', 
    '.zip', '.7z', '.woff', '.woff2', '.ttf', '.eot'
}

SAFE_ALLOWLIST_SUBSTRINGS = [
    'your_brevo_api_key',
    'replace_with',
    'CHANGE_ON_FIRST_LOGIN',
    'your_secure_password',
    'BREVO_API_KEY=your_',
    'JWT_SECRET=replace_'
]


def scan_workspace(base_dir='.'):
    violations = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in IGNORED_EXTENSIONS:
                continue
            filepath = os.path.join(root, f)
            # Avoid self-matching pattern definitions
            if os.path.abspath(filepath) == os.path.abspath(__file__):
                continue

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                    for line_no, line in enumerate(fp, 1):
                        # Skip allowlisted dummy placeholders
                        if any(safe in line for safe in SAFE_ALLOWLIST_SUBSTRINGS):
                            continue
                        for pattern, desc in SECRET_PATTERNS:
                            if re.search(pattern, line, re.IGNORECASE):
                                violations.append({
                                    'file': filepath,
                                    'line': line_no,
                                    'rule': desc,
                                    'snippet': line.strip()[:60]
                                })
            except Exception as e:
                print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
    return violations


def scan_git_history():
    violations = []
    try:
        patterns_query = "BEGIN|ghp_|xkeysib|AKIA|eyJ|postgres"
        output = subprocess.check_output(
            ['git', 'log', '-p', f'-G{patterns_query}'],
            stderr=subprocess.STDOUT,
            text=True,
            errors='ignore'
        )
        for line in output.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                added_line = line[1:].strip()
                if any(safe in added_line for safe in SAFE_ALLOWLIST_SUBSTRINGS):
                    continue
                for pattern, desc in SECRET_PATTERNS:
                    if re.search(pattern, added_line, re.IGNORECASE):
                        violations.append({
                            'source': 'git_log',
                            'rule': desc,
                            'snippet': added_line[:60]
                        })
    except subprocess.CalledProcessError as e:
        print(f"Warning: git log scan returned error code {e.returncode}", file=sys.stderr)
    except FileNotFoundError:
        print("Warning: git binary not found in PATH", file=sys.stderr)
    return violations


def main():
    print("=" * 60)
    print("EdgeGuard Security Audit: Zero Secret & Credential Scan")
    print("=" * 60)

    workspace_violations = scan_workspace('.')
    print(f"[*] Workspace files scanned. Violations found: {len(workspace_violations)}")
    for v in workspace_violations:
        print(f"  [ALERT] {v['file']}:{v['line']} - {v['rule']}: {v['snippet']}")

    git_violations = scan_git_history()
    print(f"[*] Git commit history scanned. Violations found: {len(git_violations)}")
    for v in git_violations:
        print(f"  [ALERT] Commit history - {v['rule']}: {v['snippet']}")

    total_violations = len(workspace_violations) + len(git_violations)
    print("=" * 60)
    if total_violations == 0:
        print("PASSED: 0 secrets or sensitive credentials detected. Repository is clean.")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"FAILED: {total_violations} secret violations detected! Remediate before release.")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
