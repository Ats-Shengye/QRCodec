#!/usr/bin/env python3
"""QRCodec HTTPS development server.

Serves only HTML/JS/CSS files. Denies access to .pem and .py files
to prevent accidental exposure of private keys and source code.
"""
import argparse
import http.server
import os
import posixpath
import ssl
from pathlib import Path
from typing import Optional
from urllib.parse import unquote


PORT: int = 8443
DIR: Path = Path(__file__).resolve().parent

# サーブを拒否する拡張子
DENIED_EXTENSIONS: frozenset[str] = frozenset({'.pem', '.py'})


def _is_denied_path(url_path: str) -> bool:
    """URL-decode and normalize the path, then check extension against deny list.

    Handles URL-encoded dots (%2E/%2e) and path normalization (e.g., /key.pem/.)
    to prevent bypass of extension checks.
    Query strings and fragments are stripped before checking.
    """
    clean = unquote(url_path.split('?', 1)[0].split('#', 1)[0])
    clean = posixpath.normpath(clean)
    ext = os.path.splitext(clean)[1].lower()
    return ext in DENIED_EXTENSIONS


class SecureHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """証明書ファイルとPythonファイルへのアクセスを拒否するハンドラ。"""

    def do_GET(self) -> None:
        """GETリクエストを処理する。拒否対象の拡張子は403を返す。"""
        if _is_denied_path(self.path):
            self.send_error(403, 'Forbidden')
            return
        super().do_GET()

    def do_HEAD(self) -> None:
        """HEADリクエストを処理する。拒否対象の拡張子は403を返す。"""
        if _is_denied_path(self.path):
            self.send_error(403, 'Forbidden')
            return
        super().do_HEAD()

    def end_headers(self) -> None:
        """レスポンスにセキュリティヘッダーを付与する。"""
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header(
            'Content-Security-Policy',
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval' "
            "https://cdn.tailwindcss.com "
            "https://cdnjs.cloudflare.com "
            "https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "media-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'"
        )
        self.send_header(
            'Permissions-Policy',
            'camera=(self), microphone=(), geolocation=()'
        )
        super().end_headers()


def create_ssl_context(cert_path: Path, key_path: Path) -> Optional[ssl.SSLContext]:
    """SSL証明書を読み込んでSSLContextを返す。

    失敗した場合はエラーメッセージを表示してNoneを返す。

    Args:
        cert_path: 証明書ファイルのパス
        key_path: 秘密鍵ファイルのパス

    Returns:
        ssl.SSLContext または None（読み込み失敗時）
    """
    if not cert_path.exists():
        print(f'[ERROR] 証明書が見つかりません: {cert_path}')
        print('  以下のコマンドで自己署名証明書を生成してください:')
        print('  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem'
              ' -days 365 -nodes -subj "/CN=localhost"')
        return None

    if not key_path.exists():
        print(f'[ERROR] 秘密鍵が見つかりません: {key_path}')
        print('  以下のコマンドで自己署名証明書を生成してください:')
        print('  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem'
              ' -days 365 -nodes -subj "/CN=localhost"')
        return None

    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(cert_path), str(key_path))
        return ctx
    except ssl.SSLError as e:
        print(f'[ERROR] SSL証明書の読み込みに失敗しました: {e}')
        print('  証明書ファイルが破損しているか、形式が正しくない可能性があります。')
        print('  以下のコマンドで再生成してください:')
        print('  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem'
              ' -days 365 -nodes -subj "/CN=localhost"')
        return None


def main() -> None:
    """サーバーを起動する。"""
    parser = argparse.ArgumentParser(description='QRCodec HTTPS development server')
    parser.add_argument(
        '--bind', default='0.0.0.0',
        help='Bind address (default: 0.0.0.0)',
    )
    parser.add_argument(
        '--port', type=int, default=PORT,
        help=f'Port number (default: {PORT})',
    )
    args = parser.parse_args()

    os.chdir(DIR)

    cert_path = DIR / 'cert.pem'
    key_path = DIR / 'key.pem'

    ctx = create_ssl_context(cert_path, key_path)
    if ctx is None:
        raise SystemExit(1)

    if args.bind == '0.0.0.0':
        print('[WARN] Listening on all interfaces — '
              'LAN上の全デバイスからアクセス可能です。'
              ' --bind 127.0.0.1 でローカル限定にできます。')

    server = http.server.HTTPServer(
        (args.bind, args.port), SecureHTTPRequestHandler,
    )
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print(f'QRCodec server running on https://{args.bind}:{args.port}')
    server.serve_forever()


if __name__ == '__main__':
    main()
