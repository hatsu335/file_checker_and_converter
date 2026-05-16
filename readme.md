# 設計支援アプリ 操作説明書

---

# 1. アプリ概要

本アプリは、CAD / NC データの確認および EPS 変換を行うための設計支援アプリです。

主な用途：

* DXF 図面確認
* NC(Gコード)形状確認
* 大R検出
* 微小円弧検出
* DXF → EPS 変換
* 加工前チェック
* DTP / 印刷用 EPS 作成

---

# 2. 主な機能

## R-CHECKER モード

DXF / NC データを解析し、以下を検出します。

### 検出項目

| 項目     | 内容                |
| ------ | ----------------- |
| 大R検出   | YAMLで設定したR値以上の円弧  |
| 微小円弧検出 | YAMLで設定した円弧長以下の円弧 |
| NC形状表示 | Gコード形状を可視化        |
| DXF表示  | CAD図形表示           |

---

## EPS-CONVERT モード

DXF ファイルを EPS ファイルへ変換します。

変換エンジン：

```text
Inkscape CLI
```

を使用。

---

# 3. 動作環境

| 項目     | 内容            |
| ------ | ------------- |
| OS     | Windows 11 推奨 |
| Python | 3.11 以上推奨     |
| GUI    | PySide6       |
| CAD読込  | ezdxf         |
| 描画     | matplotlib    |
| EPS変換  | Inkscape      |

---

# 4. 必要ライブラリ

```bash
pip install pyside6 matplotlib ezdxf pyyaml
```

---

# 5. Inkscape

EPS変換には Inkscape が必要です。

例：

```text
C:\Program Files\Inkscape\bin\inkscape.exe
```

---

# 6. 対応ファイル

| 拡張子  | 内容            |
| ---- | ------------- |
| .dxf | CAD図面         |
| .dat | NCデータ         |
| .nc  | NCデータ（拡張対応可能） |

---

# 7. モード切替

画面下部の VSCode風ステータスバーをクリックすることで切替可能です。

---

## R-CHECKER

解析モード。

対象：

* DXF
* NC

---

## EPS-CONVERT

EPS変換モード。

対象：

* DXFのみ

---

# 8. ファイル操作

## ドラッグ＆ドロップ

対象ファイルをウィンドウへドラッグ＆ドロップします。

---

# 9. R-CHECKER 詳細

---

# 9-1. DXF解析

以下を解析します。

| 要素     | 対応 |
| ------ | -- |
| LINE   | ○  |
| ARC    | ○  |
| CIRCLE | ○  |

---

# 9-2. NC解析

以下に対応。

| 項目      | 内容    |
| ------- | ----- |
| G00     | 早送り   |
| G01     | 直線補間  |
| G02     | CW円弧  |
| G03     | CCW円弧 |
| I/J円弧   | 対応    |
| G90/G91 | 対応    |

---

# 9-3. 独自NC対応

本アプリは、特定企業向け独自NC形式を考慮しています。

対応内容：

* 増分座標
* 独自スケール
* 独自Mコード混在

---

# 9-4. NCスケール

独自NCで：

```text
100 = 1.00mm
```

形式に対応。

YAML設定：

```yaml
gcode:
  scale: 0.01
```

---

# 9-5. 大R検出

設定R以上を赤表示。

例：

```yaml
threshold: 100
```

↓

```text
R100以上
```

を検出。

---

# 9-6. 微小円弧検出

短すぎる円弧を検出。

例：

```yaml
gcode:
  arc_length_threshold: 0.1
```

↓

```text
円弧長0.1mm以下
```

を検出。

---

# 9-7. 警告表示

異常検出時：

* 赤表示
* R値表示
* 円弧長表示

を行います。

---

# 10. EPS変換

---

# 10-1. 変換方式

```text
DXF
↓
Inkscape
↓
EPS
```

---

# 10-2. 使用オプション

```bash
--export-type=eps
--export-area-drawing
--export-ps-level=2
```

---

# 10-3. 出力先

ステータスバー左側に表示。

クリックで変更可能。

---

# 10-4. 変換中表示

複数ファイル時：

```text
EPS変換中... (1/5)
```

表示。

---

# 11. YAML設定

---

# 11-1. 設定ファイル例

```yaml
# 半径の閾値
threshold: 4000

# ウィンドウサイズ
window_size:
  x: 650
  y: 500

# Inkscape
inkscape: "C:\\Program Files\\Inkscape\\bin\\inkscape.exe"

# 保存先
folder: "C:\\Users\\******\\OneDrive\\Desktop"

# EPS version
eps_ver: "--export-ps-level=2"
# eps_ver: "--export-ps-level=3"

# EPS margin
eps_margin: "--export-margin=20"

# G-code
gcode:
  scale: 0.01
  default_absolute_mode: false
  arc_length_threshold: 0.1
```

---

# 11-2. 設定内容

| 項目                    | 内容         |
| --------------------- | ---------- |
| threshold             | 大R判定       |
| scale                 | NC倍率       |
| default_absolute_mode | G90/G91初期値 |
| arc_length_threshold  | 微小円弧判定     |

---

# 12. EPS寸法について

EPS内部単位は：

```text
point
```

です。

そのため DTPソフトでは：

```text
inch / pt
```

表示される場合があります。

ただし実寸は保持されています。

検証結果：

```text
70.0 → 70.00028
```

であり、実務上十分高精度です。

---

# 13. 注意事項

---

# 13-1. NC互換性

本アプリは汎用NCビューアではありません。

特定NC仕様向けに最適化されています。

---

# 13-2. Inkscape依存

EPS変換は Inkscape バージョンに依存します。

---

# 13-3. DXF互換性

一部特殊DXF：

* SPLINE
* BLOCK複雑構造
* 3D要素

は未対応または簡易表示です。

---

# 14. 今後の拡張候補

| 機能    | 内容     |
| ----- | ------ |
| ズーム   | 拡大縮小   |
| 検出一覧  | 警告一覧   |
| ジャンプ  | 問題箇所移動 |
| ログ    | 詳細ログ   |
| PDF出力 | レポート生成 |
| SVG出力 | DTP連携  |
| NC統計  | 加工情報分析 |

---

# 15. 開発構成

| 項目    | 内容           |
| ----- | ------------ |
| GUI   | PySide6      |
| 描画    | matplotlib   |
| CAD   | ezdxf        |
| 設定    | YAML         |
| EPS変換 | Inkscape CLI |

---

# 16. アプリの特徴

本アプリは：

```text
現場向け軽量設計支援ツール
```

として設計されています。

特に：

* 独自NC対応
* 微小円弧検出
* EPS変換
* YAML設定

を重視しています。
