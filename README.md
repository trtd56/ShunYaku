# ShunYaku

`LiquidAI/LFM2-350M-ENJP-MT` を使った、英語から日本語専用の常駐翻訳アプリです。常駐中にコピー操作を短時間で 2 回押すと、クリップボード内の英語テキストを翻訳して、選択位置付近にポップアップ表示します。macOS では `Cmd+C` を、その他の環境では `Ctrl+C` を使います。

## 構成

- UI: `PySide6`
- グローバルキー監視: `pynput`
- 推論: `llama-cpp-python`
- モデル: `LiquidAI/LFM2-350M-ENJP-MT-GGUF`

## 前提

- macOS
- Python 3.11 以上
- アクセシビリティ権限
  - コピー操作のグローバル監視に必要

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

初回起動時に Hugging Face からモデルを取得します。デフォルトでは公式 GGUF の `Q8_0` 量子化を選びます。

## 起動

```bash
shunyaku
```

または:

```bash
python3 -m shunyaku.app
```

## 使い方

1. 英文を選択してコピーする
   - macOS: `Cmd+C`
   - その他: `Ctrl+C`
2. 続けてもう一度同じキー操作を押す
3. マウスカーソル付近に、日本語訳の長さに応じたサイズのポップアップが表示される

## 動作仕様

- 英語テキストのみを対象とします
- 連打判定の既定値は 0.75 秒です
- クリップボードが空、または英字比率が低い場合は翻訳しません
- 翻訳中は選択位置付近のポップアップに進捗を表示します

## 環境変数

- `SHUNYAKU_MODEL_REPO`
  - デフォルト: `LiquidAI/LFM2-350M-ENJP-MT-GGUF`
- `SHUNYAKU_MODEL_QUANT`
  - デフォルト: `Q8_0`
- `SHUNYAKU_DOUBLE_COPY_WINDOW_MS`
  - デフォルト: `750`
- `SHUNYAKU_MAX_TOKENS`
  - デフォルト: `256`
- `SHUNYAKU_CTX`
  - デフォルト: `2048`
- `SHUNYAKU_GPU_LAYERS`
  - デフォルト: `0`

## macOS 権限

`pynput` によるグローバルキー監視のため、ターミナルまたは実行バイナリにアクセシビリティ権限が必要です。

macOS ではターミナルの `Ctrl+C` が割り込みシグナルと衝突するため、アプリのトリガーには `Cmd+C` のみを使います。

`システム設定 > プライバシーとセキュリティ > アクセシビリティ` で有効化してください。

## macOS アプリとしてビルド

`PyInstaller` で `.app` バンドルを生成できます。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[build]"
./scripts/build_macos_app.sh
```

生成物:

- `dist/ShunYaku.app`
- `dist/ShunYaku-mac.zip`

このアプリはメニューバー常駐アプリとして配布する前提なので、Dock には常駐しません。

## 署名と公証

社内配布やローカル利用なら未署名でも起動できますが、一般配布するなら Apple Developer 証明書で署名し、公証まで通すべきです。

```bash
export CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export APPLE_NOTARY_PROFILE="notarytool-profile-name"
./scripts/build_macos_app.sh
```

`APPLE_NOTARY_PROFILE` を使う場合は、事前に以下で認証情報を登録してください。

```bash
xcrun notarytool store-credentials "notarytool-profile-name" \
  --apple-id "you@example.com" \
  --team-id "TEAMID" \
  --password "app-specific-password"
```

## 今後の拡張候補

- 自動起動登録
- 翻訳履歴
