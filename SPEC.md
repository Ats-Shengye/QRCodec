# QRCodec Specification

## Overview
テキスト/ソースコードをQRコード経由で別デバイスに転送するためのツールセット。
エンコーダー（PC）とデコーダー（スマホ）の2つのHTMLで構成される。

## QRT Wire Format
```
QRT|{SID}|{SEQ}/{TOTAL}|{base64_gzip_chunk}
```

| Field | Format | Description |
|-------|--------|-------------|
| Prefix | `QRT` | 固定プレフィックス |
| SID | 数字6桁 | セッション識別子（ランダム生成） |
| SEQ | ゼロパディング3桁、1始まり | チャンク連番（例: 001, 002） |
| TOTAL | ゼロパディング3桁 | 総チャンク数（例: 012） |
| Payload | Base64文字列 | gzip圧縮済みデータの分割チャンク |

### Example
```
QRT|663312|001/001|H4sIAAAAAAAAAytJLS4BAAx+f9gEAAAA
```

## Processing Pipeline

### Encode (PC → QR)
1. 入力テキストをUTF-8バイト列に変換
2. pako.gzipで圧縮
3. 圧縮バイト列をBase64エンコード
4. Base64文字列をchunkSizeバイト単位で分割
5. 各チャンクにQRTヘッダーを付与
6. QRコード生成（ECC=Q）

### Decode (QR → テキスト)
1. カメラ/画像からQRコードを検出
2. QRTフォーマットをパース（SID/SEQ/TOTAL/Payload分離）
3. SID単位でチャンクを蓄積
4. 全チャンク揃ったらBase64を結合
5. Base64デコード → Uint8Array
6. pako.inflateでgzip展開
7. UTF-8テキストとして復元

## Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| chunkSize | 300 byte | 100-2000 | Base64分割サイズ。大きいほど枚数減るが読み取り困難に |
| ECC | Q (25%) | - | QRエラー訂正レベル |
| QR Size | 600px | - | QRコード描画サイズ |
| Scan Interval | 300ms | - | デコーダーのスキャン間隔 |

### Chunk Size Tuning
- 1500 byte: 動作確認済み上限（Pixel 10 Pro Fold + MUGA5画面）
- 300 byte: 安全マージン込みのデフォルト
- QRコードのクワイエットゾーン（白余白）がないと読み取り精度が大幅に低下する

## Components

| File | Role | Runtime |
|------|------|---------|
| qr-generator.html | エンコーダー | ブラウザ（file://可） |
| qr-reconstructor.html | デコーダー | ブラウザ（HTTPS必須、カメラ使用） |
| serve.py | HTTPSサーバー | Python 3 + ssl |
| cert.pem / key.pem | 自己署名証明書 | 有効期限365日 |

## QR Detection Engines (Decoder)
1. **BarcodeDetector API** (優先) — Chrome Android ネイティブ、高速
2. **jsQR** (フォールバック) — Pure JS、BarcodeDetector非対応環境用

## Libraries (CDN)
- pako 2.1.0 — gzip圧縮/展開
- qrcode.js 1.0.0 — QRコード生成（エンコーダー側）
- jsQR 1.4.0 — QRコード検出（デコーダー側フォールバック）
- Tailwind CSS — UI

## Known Issues / Constraints
- デコーダーはgetUserMedia (カメラAPI) を使うためセキュアコンテキスト（HTTPS/localhost）が必須
- file://からはカメラが使えない → serve.pyでHTTPSサーバーを立てて回避
- Androidクリップボードの文字数上限により、QRリーダーアプリ経由の手動コピーは大きなペイロードで途切れる場合がある
- ダークテーマUI上でクワイエットゾーンなしのQRはスキャン精度が著しく低下する → padding: 16px で白余白を確保
