# QRCodec Glossary

| Term | Definition |
|------|-----------|
| **QRT** | QR Transfer の略。本ツール独自のワイヤーフォーマットのプレフィックス |
| **SID** | Session ID。1回のエンコード操作に対して生成される6桁の数値識別子（crypto.getRandomValues使用）。複数セッションのQRが混在しても分離可能にする |
| **SEQ** | Sequence Number。チャンクの連番（1始まり、ゼロパディング3桁）|
| **TOTAL** | 総チャンク数（ゼロパディング3桁）。SEQと合わせて `001/012` の形式で表記 |
| **チャンク (Chunk)** | gzip圧縮→Base64変換後のデータを一定サイズで分割した断片。1チャンク = 1QRコード |
| **chunkSize** | チャンク分割時のサイズ（バイト単位）。Base64文字列の分割長であり、圧縮前のデータサイズではない |
| **クワイエットゾーン (Quiet Zone)** | QRコード周囲に必要な白い余白領域（仕様上4モジュール以上）。これがないとスキャナがQRの境界を認識できない |
| **ECC** | Error Correction Capacity。QRコードのエラー訂正レベル。L(7%), M(15%), Q(25%), H(30%) の4段階。本ツールはQ |
| **モジュール (Module)** | QRコードを構成する最小の黒/白セル単位 |
| **バージョン (Version)** | QRコードのサイズ規格。1(21x21)〜40(177x177)。データ量が増えるとバージョンが上がりモジュールが小さくなる |
| **ファインダーパターン (Finder Pattern)** | QRコードの左上・右上・左下にある3つの大きな四角。スキャナの位置検出に使用 |
| **BarcodeDetector API** | Web標準のバーコード検出API。Chrome Android等で利用可能。ネイティブ実装のため高速 |
| **jsQR** | Pure JavaScriptのQRコード検出ライブラリ。BarcodeDetector非対応環境でのフォールバック |
| **pako** | JavaScriptのzlib実装ライブラリ。gzip圧縮(deflate)と展開(inflate)に使用 |
| **セキュアコンテキスト (Secure Context)** | HTTPS、localhost、file://（一部）等、ブラウザがセキュアと判断する実行環境。getUserMedia等のAPIに必要 |
| **Base64** | バイナリデータをASCII文字列で表現するエンコーディング方式。元データの約133%のサイズになる |
