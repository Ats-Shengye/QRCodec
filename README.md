# QRCodec

テキストやソースコードをQRコード経由でデバイス間転送するツールキット。
PC側でテキストをQRコードにエンコードし、スマホのカメラで読み取ってデコードする。

## 構成

| ファイル | 役割 |
|----------|------|
| `qr-generator.html` | エンコーダー（PC側）。テキストをgzip圧縮→Base64→チャンク分割→QRコード生成 |
| `qr-reconstructor.html` | デコーダー（スマホ側）。カメラでQR読み取り→チャンク再結合→展開→テキスト復元 |
| `serve.py` | HTTPS開発サーバー（カメラAPIにHTTPS必須のため） |

## 使い方

```bash
# HTTPS開発サーバーを起動（初回は自己署名証明書を生成）
python3 serve.py

# PC: https://localhost:4443/qr-generator.html を開いてテキストを入力
# スマホ: 同じネットワークから https://<PCのIP>:4443/qr-reconstructor.html を開いてカメラで読み取り
```

## 仕組み

長いテキストを1枚のQRに収めず、独自のQRTフォーマットでチャンク分割する。

```
QRT|{SID}|{SEQ}/{TOTAL}|{base64_gzip_chunk}
```

- gzip圧縮でペイロードを縮小
- チャンクサイズ調整で読み取り精度と枚数のトレードオフを制御
- セッションID（SID）で複数転送を区別
- エラー訂正レベルQ（25%）で多少の歪みに耐える

詳細は [SPEC.md](SPEC.md) を参照。
