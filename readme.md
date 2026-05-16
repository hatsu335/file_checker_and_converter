# PySide6統合版 設計支援アプリ

以下は、

* `file_checker.py`
* `eps_convert.py`

を統合し、さらに以下の仕様を追加した PySide6 ベースの構成例です。

---

# 実装仕様

## 統合内容

### モード1

Rチェックモード

* DXF解析
* NC(.dat)解析
* 指定R以上を警告表示
* matplotlib描画

### モード2

DXF → EPS変換モード

* DXFファイルをドラッグ＆ドロップ
* Inkscape CLIで EPS 変換

---

# UI仕様

## VSCode風ステータスバー

画面下部のステータスバーをクリックするとモード切替。

表示例:

```text
MODE : R-CHECKER
MODE : DXF → EPS CONVERTER
```

---

# 必要ライブラリ

```bash
pip install pyside6 matplotlib ezdxf pyyaml
```


---

# 改善提案

今後このアプリはかなり発展可能です。

おすすめ構成:

## 1. モードをクラス分離

現在:

```text
IntegratedCADApp
 ├ Rチェック
 └ EPS変換
```

将来的には:

```text
modes/
 ├ r_checker.py
 ├ eps_converter.py
 ├ pdf_export.py
 ├ nesting_checker.py
 └ nc_simulator.py
```

のように分離すると保守性がかなり上がります。

---

## 2. StatusBarを本格VSCode風に

現在はクリック切替ですが、将来的には:

* 左: 現在モード
* 中央: ファイル名
* 右: 処理状態
* 右端: FPS / CPU / DXF数

などを表示できます。

---

## 3. matplotlib → pyqtgraph

DXF表示が大型化するなら pyqtgraph の方が高速です。

特に:

* 数万Line
* 数千Arc
* リアルタイムズーム

では差が大きくなります。

---

## 4. 将来的な構成

このアプリはかなり典型的な:

```text
CAD支援デスクトップアプリ
```

の構成になっています。

そのため将来的に:

* SQLite
* MySQL
* 設定画面
* ログ管理
* EXE化
* 自動アップデート
* ライセンス管理

まで拡張可能です。

かなり良い方向性です。
