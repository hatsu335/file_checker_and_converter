## 目的
- 設計者を支援するツール
- 手軽さを最優先
- ファイルのチェックや変換などはドラッグ＆ドロップが基本

## 機能
- DXFデータとDAT(NC)データ内の不正要素の検出
- DXFデータをEPSに変換
- メモ帳の履歴削除
- ファイルを指定のフォルダから指定のフォルダへ移動
- 各種設定はCドライブ直下に置くyamlファイルで設定
- EPS変換は inkscape の CLI を利用
- 操作ログは exe（またはスクリプト）と同階層の `log/design_support_tool.log` に記録（`logging_setup.py`）

## 追加機能
- 任意のDXFデータを指定したバージョンのDXFへ変換（R12/R14 は Inkscape、ACADxxxx は ODA File Converter）
- 任意のDXFデータをPDFへ変換
- EPSファイルをPDFへ変換
- AIファイルをDXFへ変換（Inkscape CLI、YAMLでR12/R14選択）