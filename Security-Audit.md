# Security Report
updated: 2026-08-16

## Latest Review

- Date: 2026-08-16
- Reviewer: Security review agent
- Verdict: PASS
- ASVS L1 compliance: 80% (8/10 applicable items)
- Static analysis: bandit B104 x2 (hardcoded 0.0.0.0 — intentional, mitigated by M-2 --bind option + warning)
- Supply chain: pako@2.1.0, qrcode.js@1.0.0, jsQR@1.4.0, tailwindcss@3.4.17 (CDN with SRI) — no known CVEs (OSV API verified 2026-08-16)

## Finding History

### 2026-08-16 Review

#### Critical

- [C-1] serve.py extension check bypass via URL encoding — private key exposure
  - Location: serve.py:26-28 (`do_GET`), serve.py:34-36 (`do_HEAD`)
  - Type: Access Control Bypass (CWE-706: Use of Incorrectly-Resolved Name or Reference)
  - Description: Extension deny list checks `os.path.splitext(self.path)` on the raw URL path, but `SimpleHTTPRequestHandler.translate_path()` URL-decodes the path via `urllib.parse.unquote()` before resolving to filesystem. URL-encoding the dot (`%2E`) bypasses the extension check while the parent class resolves it to the actual file.
  - Exploit: `curl -k https://<host>:8443/key%2Epem` serves `key.pem` (private key). `curl -k https://<host>:8443/serve%2Epy` serves source code. Both lowercase (`%2e`) and uppercase (`%2E`) work.
  - Context: Absolute (environment-independent). Server binds 0.0.0.0, so any device on the network can exfiltrate the private key.
  - Impact: Private key exposure enables MITM on all HTTPS connections to this server. Source code disclosure reveals server implementation.
  - Fix cost: 1-line fix (URL-decode before extension check)
  - Fix:
    ```python
    from urllib.parse import unquote

    def _is_denied(self, url_path: str) -> bool:
        """URL-decode and check extension against deny list."""
        clean = unquote(url_path.split('?', 1)[0].split('#', 1)[0])
        ext = os.path.splitext(clean)[1].lower()
        return ext in DENIED_EXTENSIONS
    ```
    Then call `if self._is_denied(self.path)` in both `do_GET` and `do_HEAD`.
  - Reference: OWASP A01:2025 Broken Access Control, ASVS V5.3.1
  - Status: Fixed

#### High

- None

#### Medium

- [M-1] No HTTP security headers on serve.py responses
  - Location: serve.py (entire SecureHTTPRequestHandler class)
  - Type: Missing Security Headers (CWE-693)
  - Description: serve.py sets no security headers — no CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, HSTS. HTML files are served without any XSS or MIME-sniffing protection.
  - Context: Absolute. Any response from the server lacks headers.
  - Fix cost: Function 1 add (`end_headers` override or `send_response` wrapper)
  - Fix:
    ```python
    def end_headers(self) -> None:
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy',
            "default-src 'self'; "
            "script-src 'self' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "frame-ancestors 'none'")
        self.send_header('Permissions-Policy', 'camera=self, microphone=(), geolocation=()')
        super().end_headers()
    ```
  - Reference: OWASP HTTP Headers Cheat Sheet, ASVS V3.1.1
  - Status: Fixed (implementation adds `'unsafe-eval'` to `script-src` for Tailwind CSS CDN JIT — see Risk Acceptance)

- [M-2] Server binds to 0.0.0.0 without authentication or access control
  - Location: serve.py:93 (`('0.0.0.0', PORT)`)
  - Type: Insufficient Access Control (CWE-284)
  - Description: Server listens on all interfaces with no authentication. Any device on the network (or Tailscale mesh) can access served files. While 0.0.0.0 binding is functionally required (phone accesses server over LAN), there's no warning or opt-in.
  - Context: Mode-dependent. On trusted home network the risk is low; on public/corporate Wi-Fi the risk is elevated.
  - Fix cost: Function 1 add (configurable bind address + startup warning)
  - Fix:
    ```python
    import argparse

    # Add to main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', default='0.0.0.0',
                        help='Bind address (default: 0.0.0.0)')
    args = parser.parse_args()

    # Print warning when binding to all interfaces
    if args.bind == '0.0.0.0':
        print('[WARN] Listening on all interfaces. '
              'Use --bind 127.0.0.1 for localhost only.')
    ```
  - Reference: ASVS V14.1.1
  - Status: Fixed

- [M-3] No CSP meta tag in HTML files
  - Location: qr-generator.html, qr-reconstructor.html (both `<head>` sections)
  - Type: Missing CSP (CWE-1021)
  - Description: Neither HTML file includes a `<meta http-equiv="Content-Security-Policy">` tag. When opened via `file://` (generator supports this per SPEC.md), no server-side headers apply, leaving the page without any CSP protection.
  - Context: Mode-dependent. `file://` mode has no server headers; HTTPS mode could get headers from serve.py (if M-1 is fixed).
  - Fix cost: 1 line per file (add meta tag)
  - Fix: Add to both files' `<head>`:
    ```html
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'self'; script-src 'self' 'unsafe-eval' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; object-src 'none'">
    ```
    Note: `frame-ancestors` is intentionally omitted from meta CSP (ignored by browsers per spec; enforced in server-side header only). Reconstructor needs `media-src 'self'` for camera. Generator omits `cdn.jsdelivr.net` (jsQR not used).
  - Reference: ASVS V3.1.1
  - Status: Fixed (implementation adds `'unsafe-eval'` to `script-src` for Tailwind CSS CDN JIT — see Risk Acceptance)

#### Low

- [L-1] `.html` save feature writes decoded content as executable HTML without warning
  - Location: qr-reconstructor.html:482-487 (`btn-save-html` handler)
  - Type: Stored XSS vector (CWE-79)
  - Description: ".html保存" button saves decoded QR data as an HTML file. If an attacker controls the QR source (e.g., public display), victim could unknowingly save and open malicious HTML with embedded scripts.
  - Context: Mode-dependent. Requires attacker to control QR source AND victim to click save AND open the file. User can inspect content in textarea before saving.
  - Fix cost: 1 line (add confirm dialog)
  - Fix: Add confirmation before save:
    ```javascript
    if (!confirm('HTMLファイルとして保存します。信頼できるソースからのデータですか？')) return;
    ```
  - Status: Fixed

- [L-2] No decompression size limit in pako.inflate
  - Location: qr-reconstructor.html:274 (`pako.inflate(uint8Array, { to: 'string' })`)
  - Type: Decompression Bomb (CWE-409)
  - Description: pako.inflate has no output size limit. A crafted gzip stream could decompress to a large string, exhausting browser memory.
  - Context: Environment-specific. QR code data capacity (~1.6KB per code, max 999 chunks per format) limits compressed input to ~1.6MB, making a meaningful bomb impractical via QR. Browser tab crash, not system-level.
  - Fix cost: 1 function add (streaming inflate with size check)
  - Status: Accepted (QR capacity makes exploitation impractical)

- [L-3] Locally generated RSA-2048 cert (below recommended RSA-4096)
  - Location: cert.pem (not in codebase, .gitignore'd)
  - Type: Weak Cryptography (CWE-326)
  - Description: Generated certificate uses RSA-2048, while Security Guidelines recommend RSA-4096. serve.py's help text already suggests RSA-4096, so the code is correct; the locally generated cert was created with a different key size.
  - Context: Environment-specific. Self-signed development cert only; RSA-2048 is not broken but below guideline standard.
  - Fix cost: 1 command (regenerate cert with rsa:4096)
  - Status: Accepted (code recommends RSA-4096; local cert regeneration is user's choice)

- [L-4] Server header exposes Python version
  - Location: serve.py (inherited from `SimpleHTTPRequestHandler.server_version` / `sys_version`)
  - Type: Information Disclosure (CWE-200)
  - Description: `SimpleHTTPRequestHandler` sends `Server: SimpleHTTP/0.6 Python/3.12.x` header on all responses. Reveals server technology and exact Python version to any client.
  - Context: Environment-specific. Dev tool on local/Tailscale network only; minimal exposure surface.
  - Fix cost: 2 lines (add class attributes to `SecureHTTPRequestHandler`)
  - Fix:
    ```python
    class SecureHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        server_version = 'QRCodec'
        sys_version = ''
    ```
  - Status: Open (low priority — dev tool, non-public)

- [L-5] CDN-only dependency loading (no offline/vendored fallback)
  - Location: qr-generator.html:7-9, qr-reconstructor.html:7-9
  - Type: Availability Risk
  - Description: All JS libraries loaded exclusively from CDN. SRI hashes are present (good), but no offline fallback if CDN is unreachable. Generator works from `file://` but requires internet for CDN.
  - Context: Environment-specific. MUGA5 on home network is typically online; offline use at external locations would fail.
  - Fix cost: Structure change (vendor libraries locally)
  - Status: Accepted (SRI mitigates integrity risk; availability is acceptable trade-off)

## Risk Acceptance

### 2026-08-16 L-2: Decompression bomb via pako.inflate
- Category: Accepted
- Severity: Low
- Reason: QR code physical data capacity limits compressed input to ~1.6KB per code. Even with 999 chunks (format maximum) at 2000-byte chunk size, total compressed data is ~2MB. Gzip bomb ratio realistically caps at ~1000:1, yielding ~2GB — enough to crash a browser tab but impractical to deliver via 999 physical QR codes. Tab-level DoS only.
- Mitigation: Browser tab isolation limits blast radius. User must physically scan each QR code.
- Re-evaluate: If QR input source changes (e.g., file import of QR images)

### 2026-08-16 L-5: CDN-only dependency loading
- Category: Accepted
- Severity: Low
- Reason: SRI integrity hashes on all CDN resources prevent tampered delivery. CDN availability is sufficient for the tool's use context (home network, Tailscale). Vendoring adds maintenance burden for a dev tool.
- Mitigation: SRI hashes block compromised CDN responses
- Re-evaluate: If tool is used in air-gapped or unreliable network environments

### 2026-08-16 M-1/M-3: CSP unsafe-eval for Tailwind CSS CDN JIT
- Category: Accepted
- Severity: Medium (CSP weakening)
- Reason: Tailwind CSS CDN (Play CDN / JIT mode) requires `unsafe-eval` to compile utility classes in the browser at runtime using `new Function()`. Without `unsafe-eval`, Tailwind CSS classes are not applied and the UI is unstyled. Verified by reviewing Tailwind CDN v3.x JIT compiler behavior.
- Mitigation: XSS risk is limited — both HTML files use `textContent` for user data insertion (not `innerHTML`), and `script-src` is restricted to three specific CDN domains with SRI hashes. No user-controlled DOM injection points exist. `unsafe-eval` only enables code execution from scripts already permitted by the origin allowlist.
- Re-evaluate: If migrating from Tailwind CDN to build-time compilation (PostCSS + Tailwind CLI), `unsafe-eval` can be removed

## Applied Security Measures

### Transport
- Self-signed HTTPS (TLS 1.2+ via Python ssl.PROTOCOL_TLS_SERVER)
- Certificate and key excluded from git (.gitignore from initial commit)
- key.pem file permissions: 600 (owner-only)

### File Access Control
- DENIED_EXTENSIONS deny list for .pem and .py files (URL-decode + normpath aware)
- cert.pem and key.pem in .gitignore (never committed)
- .gitleaks.toml extends project PII rules

### Client-Side Security
- SRI (Subresource Integrity) hashes on all CDN-loaded scripts
- CSP deployed server-side (end_headers override) and client-side (meta tags for file:// mode)
  - `unsafe-eval` required for Tailwind CSS CDN JIT (accepted risk, see Risk Acceptance)
  - `frame-ancestors 'none'` in server header only (correctly omitted from meta tags per CSP spec)
- crypto.getRandomValues() for SID generation (CSPRNG)
- textContent used for DOM text insertion (not innerHTML with user data)
- IIFE scope isolation in generator
- QRT format validation (prefix, field count, sequence parsing)

### Supply Chain
- 4 CDN dependencies, all with SRI hashes and crossorigin="anonymous"
- No known CVEs in any dependency (OSV API verified 2026-08-16)
- gitleaks pre-push hook configured

## Conditional Application Decisions

- SQL injection: Not applicable (no database)
- Command injection: Not applicable (no subprocess execution)
- CSRF: Not applicable (no state-changing server endpoints)
- Authentication: Not applicable (static file server, no user accounts)
- Session management: Not applicable (no server-side sessions)
- Rate limiting: Not applicable (static file server, no API endpoints)
- SSRF: Not applicable (no server-side URL fetching)
- WebSocket: Not applicable (no WebSocket usage)
- Archive extraction: Not applicable (no archive handling)
- Path traversal: Applicable — serve.py serves files from directory → C-1 found

## Checklist

### Always Apply
- [x] No hardcoded credentials, API keys, or secrets in code
- [x] All external inputs validated with whitelist approach (QRT format + URL-decode-aware extension deny list)
- [x] Specific exception handling (no bare except)
- [x] Error messages without sensitive data (mostly — SSLError shows generic details)
- [ ] Audit logging for security-relevant events — no logging at all
- [x] Proper file permissions (key.pem: 600)
- [x] Dependencies verified and scanned for known vulnerabilities (OSV API: 0 CVEs)
- [x] Code generation tool output reviewed (both commits co-authored by Claude)

### Web Application Security (Conditional — applicable)
- [x] HTTP security headers set on all responses (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy)
- [x] CSP deployed (server-side header + meta tags for file:// mode)
- [x] X-XSS-Protection not set (correctly absent)
- [ ] Server header does not expose version info — L-4: `SimpleHTTP/0.6 Python/3.12.x` leaked via default `server_version`

### Supply Chain
- [x] CDN dependencies verified with SRI hashes
- [x] No AI-hallucinated packages (all well-known libraries)
- [x] cert.pem/key.pem excluded from version control

## ASVS L1 Compliance

- Applied chapters: V1 (Encoding), V2 (Validation), V3 (Web Frontend), V5 (File Handling), V11 (Crypto), V12 (Error/Logging), V14 (Config)
- Compliance: 80% (8/10 applicable items)
- Non-compliant:
  - V12.2.1 Audit logging: no logging exists (accepted for dev tool)
  - V14.3.3 Server header suppression: Python version exposed (L-4, low priority)
