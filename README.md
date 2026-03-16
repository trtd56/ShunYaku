# ShunYaku

`LiquidAI/LFM2-350M-ENJP-MT` を使った、英語から日本語専用の常駐翻訳アプリです。常駐中に `Ctrl+C` を短時間で 2 回押すと、クリップボード内の英語テキストを翻訳してポップアップ表示します。macOS では実用上 `Cmd+C` 2 回でも同じように動作します。

## 構成

- UI: `PySide6`
- グローバルキー監視: `pynput`
- 推論: `llama-cpp-python`
- モデル: `LiquidAI/LFM2-350M-ENJP-MT-GGUF`

## 前提

- macOS
- Python 3.11 以上
- アクセシビリティ権限
  - `Ctrl+C` のグローバル監視に必要

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

1. 英文を選択して `Ctrl+C` または `Cmd+C` でコピーする
2. 続けてもう一度同じキー操作を押す
3. ポップアップに日本語訳が表示される

## 動作仕様

- 英語テキストのみを対象とします
- 連打判定の既定値は 0.75 秒です
- クリップボードが空、または英字比率が低い場合は翻訳しません
- 翻訳中はポップアップに進捗を表示します

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

`システム設定 > プライバシーとセキュリティ > アクセシビリティ` で有効化してください。

## 今後の拡張候補

- `py2app` で `.app` 化
- 自動起動登録
- 翻訳履歴
