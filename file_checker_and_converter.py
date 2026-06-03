# PySide6統合版 設計支援アプリ
import sys
import os
import re
import math
import shutil
import subprocess
import datetime
import ezdxf
import yaml

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.patches import Arc

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)
from PySide6.QtGui import QIcon
from move_file_manager import MoveFileManager
from notepad_history_cleaner import NotepadHistoryCleaner
from logging_setup import logger

INKSCAPE_DXF_FORMATS = {
    "R12": "org.inkscape.output.dxf_twelve",
    "R14": "org.ekips.output.dxf_outlines",
}

# =========================================================
# Main Window
# =========================================================
class IntegratedCADApp(QMainWindow):

    def __init__(self):
        super().__init__()

        # --------------------------------------------
        # YAML Load
        # --------------------------------------------
        self.config = self.load_yaml(r"C:\checker.yaml")

        self.threshold = self.config["threshold"]

        window = self.config["window_size"]

        self.resize(window["x"], window["y"])

        self.setWindowTitle("設計支援ツール")
        
        self.mode_label_rcheck = self.config.get("mode_label_rcheck", "R-CHECKER")
        
        self.mode_label_eps = self.config.get("mode_label_eps", "DXF → EPS CONVERTER")

        self.mode_label_dxf_dxf = self.config.get("mode_label_dxf_dxf", "DXF → DXF")

        self.mode_label_dxf_pdf = self.config.get("mode_label_dxf_pdf", "DXF → PDF")

        self.mode_label_ai_dxf = self.config.get("mode_label_ai_dxf", "AI → DXF")

        self.modes = [
            self.mode_label_rcheck,
            self.mode_label_eps,
            self.mode_label_dxf_dxf,
            self.mode_label_dxf_pdf,
            self.mode_label_ai_dxf,
        ]

        self.mode_styles = {
            self.mode_label_rcheck: """
                QLabel {
                    background-color: #007bbb;
                    color: white;
                    padding: 4px 12px;
                    font-weight: bold;
                    border-radius: 4px;
                }
            """,
            self.mode_label_eps: """
                QLabel {
                    background-color: #e9546b;
                    color: black;
                    padding: 4px 12px;
                    font-weight: bold;
                    border-radius: 4px;
                }
            """,
            self.mode_label_dxf_dxf: """
                QLabel {
                    background-color: #f39800;
                    color: black;
                    padding: 4px 12px;
                    font-weight: bold;
                    border-radius: 4px;
                }
            """,
            self.mode_label_dxf_pdf: """
                QLabel {
                    background-color: #674598;
                    color: white;
                    padding: 4px 12px;
                    font-weight: bold;
                    border-radius: 4px;
                }
            """,
            self.mode_label_ai_dxf: """
                QLabel {
                    background-color: #ffea00;
                    color: black;
                    padding: 4px 12px;
                    font-weight: bold;
                    border-radius: 4px;
                }
            """,
        }

        self.dxf_downgrade_format = self.config.get(
            "dxf_downgrade_format",
            self.config.get("dxf_target_version", "ACAD2000"),
        ).upper()

        self.dxf_downgrade_inkscape_extension = INKSCAPE_DXF_FORMATS.get(
            self.dxf_downgrade_format,
        )

        self.ai_dxf_format = self.config.get(
            "ai_dxf_format",
            "R14",
        ).upper()

        self.ai_dxf_extension = INKSCAPE_DXF_FORMATS.get(
            self.ai_dxf_format,
            INKSCAPE_DXF_FORMATS["R14"],
        )

        # =========================================================
        # Inkscape Path
        # =========================================================
        self.INKSCAPE_PATH = self.config["inkscape"]

        self.ghostscript_path = (
            shutil.which("gswin64c")
            or shutil.which("gswin32c")
            or shutil.which("gs")
        )
        self.ghostscript_available = bool(self.ghostscript_path)

        oda_path = self.config.get("oda_file_converter")
        if oda_path:
            ezdxf.options.set("odafc-addon", "win_exec_path", oda_path)

        # --------------------------------------------
        # Current Mode
        # --------------------------------------------
        self.current_mode = self.mode_label_rcheck

        # --------------------------------------------
        # Central Widget
        # --------------------------------------------
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)
        
        # --------------------------------------------
        # Icon
        # --------------------------------------------
        self.setWindowIcon(QIcon("assets/tool_box.ico"))

        # --------------------------------------------
        # Drop Label
        # --------------------------------------------
        self.drop_label = QLabel()
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setFixedHeight(70)

        self.drop_label.setStyleSheet(
            """
            QLabel {
                background-color: #2b2b2b;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            """
        )

        self.layout.addWidget(self.drop_label)

        # --------------------------------------------
        # Matplotlib
        # --------------------------------------------
        self.figure, self.ax = plt.subplots()

        self.canvas = FigureCanvas(self.figure)

        self.layout.addWidget(self.canvas)

        # --------------------------------------------
        # Status Bar
        # --------------------------------------------
        # self.status = QStatusBar()
        # self.setStatusBar(self.status)
        self.status = self.statusBar()

        # --------------------------------------------
        # Output Directory Label
        # --------------------------------------------
        
        folder = self.config["folder"]
        
        self.output_dir = os.path.expanduser(folder)
        
        self.output_label = QLabel()
        self.output_label.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.output_label.setStyleSheet(
            """
            QLabel {
                background-color: #2b2b2b;
                color: white;
                padding: 4px 12px;
                border-right: 1px solid #555;
                border-radius: 4px;
            }
            """
        )
        
        self.output_label.mousePressEvent = self.select_output_directory
        
        self.status.addWidget(self.output_label)
        
        # --------------------------------------------
        # Notepad Cleaner
        # --------------------------------------------
        self.notepad_cleaner = NotepadHistoryCleaner()
        
        self.memo_label = QLabel("メモ帳履歴削除")

        self.memo_label.setCursor(Qt.CursorShape.PointingHandCursor)

        self.memo_label.setStyleSheet(
            """
            QLabel {
                background-color: #007bbb;
                color: white;
                padding: 4px 12px;
                font-weight: bold;
                border-radius: 4px;
            }

            QLabel:hover {
                background-color: #1e50a2;
            }
            """
        )
        
        self.status.addPermanentWidget(self.memo_label)
        
        self.memo_label.mousePressEvent = self.memo_label_mouse_event
        
        # --------------------------------------------
        # Move File Manager
        # --------------------------------------------
        self.move_manager = MoveFileManager(self.config)
        
        # 現在モード
        self.move_mode_index = 1
        
        # ステータスバーラベル

        self.move_label = QLabel()
        
        self.update_move_label()
        
        self.move_label.setCursor(Qt.CursorShape.PointingHandCursor)

        self.status.addPermanentWidget(self.move_label)
        
        # ワンクリックイベント
        self.move_label.mousePressEvent = self.move_label_mouse_event
        
        # ダブルクリックイベント
        self.move_label.mouseDoubleClickEvent = self.move_label_double_click_event
        
        # ワンクリック発火遅延用
        self.move_double_click = False
        
        # --------------------------------------------
        # Model Label
        # --------------------------------------------
        self.status_label = QLabel()
        self.status_label.setCursor(Qt.CursorShape.PointingHandCursor)

        self.status_label.setStyleSheet(
            """
            QLabel {
                background-color: #007bbb;
                color: white;
                padding: 4px 12px;
                font-weight: bold;
                border-radius: 4px;
            }
            """
        )

        self.status.addPermanentWidget(self.status_label)

        # Click Event
        self.status_label.mousePressEvent = self.toggle_mode

        # --------------------------------------------
        # Init UI
        # --------------------------------------------
        self.update_mode_ui()

        self.setAcceptDrops(True)

        logger.info(
            "アプリ初期化完了: mode=%s output_dir=%s dxf_downgrade=%s",
            self.current_mode,
            self.output_dir,
            self.dxf_downgrade_format,
        )
    
    # Notepad Cleaner クリックイベント
    def memo_label_mouse_event(self, event):

        if (
            event.button()
            != Qt.MouseButton.LeftButton
        ):
            return

        result = QMessageBox.question(

            self,

            "確認",

            "メモ帳履歴を削除しますか？\n\n""※ メモ帳は閉じてください",

            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,

            QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.No:

            logger.info("メモ帳履歴削除: ユーザーがキャンセル")
            return

        logger.info("メモ帳履歴削除: 実行開始")
        success, msg = (
            self.notepad_cleaner.clear_history()
        )

        if success:

            logger.info("メモ帳履歴削除: 成功 %s", msg)

            QMessageBox.information(
                self,
                "完了",
                msg,
            )

        else:

            logger.error("メモ帳履歴削除: 失敗 %s", msg)
            QMessageBox.critical(
                self,
                "エラー",
                msg,
            )
        
    # MoveFileManager ワンクリックイベント
    def move_label_mouse_event(self, event):
        
        # --------------------------------------------
        # RIGHT CLICK
        # --------------------------------------------
        if event.button() == Qt.MouseButton.RightButton:

            old_index = self.move_mode_index
            self.move_mode_index += 1
            
            if self.move_mode_index > 3:
                
                self.move_mode_index = 1

            logger.info(
                "ファイル移動モード切替: %s -> %s",
                old_index,
                self.move_mode_index,
            )
            
            self.update_move_label()
        
        # --------------------------------------------
        # LEFT CLICK
        # --------------------------------------------
        elif event.button() == Qt.MouseButton.LeftButton:
            
            self.move_double_click = False
            
            QTimer.singleShot(
                QApplication.doubleClickInterval(),
                lambda: self.execute_move_click()
            )
        
    # LEFT CLICK 処理
    def execute_move_click(self):
        
        if self.move_double_click:
            
            return

        # 処理
        key = (
            f"move_of_file_"
            f"{self.move_mode_index}"
        )
        
        count = self.move_manager.count_target_files(key)

        logger.info(
            "ファイル移動: 対象確認 key=%s count=%s",
            key,
            count,
        )
        
        if count == 0:
            
            QMessageBox.information(
                self,
                "確認",
                "移動対象ファイルはありません",
            )
            
            return
        
        # 実行確認
        result = QMessageBox.question(
            self,
            "確認",
            "ファイル移動を実行しますか",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        
        if result == QMessageBox.StandardButton.No:
            logger.info("ファイル移動: ユーザーがキャンセル")
            return

        logger.info("ファイル移動: 実行開始 key=%s", key)
        success, msg = self.move_manager.execute(
            key, overwrite_callback=self.confirm_overwrite)

        if success:
            logger.info("ファイル移動: 成功 %s", msg)
            QMessageBox.information(
                self,
                "完了",
                msg,
            )
        
        else:
            logger.error("ファイル移動: 失敗 %s", msg)
            QMessageBox.critical(
                self,
                "エラー",
                msg,
            )
        
        self.update_move_label()
        
    # =====================================================
    # OVERWRITE CHECK
    # =====================================================
    def confirm_overwrite(

        self,

        file_name,

        src_path,

        dst_path,
    ):

        # -----------------------------------------
        # UPDATE TIME
        # -----------------------------------------
        src_time = datetime.datetime.fromtimestamp(
            os.path.getmtime(src_path)
        )

        dst_time = datetime.datetime.fromtimestamp(
            os.path.getmtime(dst_path)
        )

        # -----------------------------------------
        # FORMAT
        # -----------------------------------------
        src_time_str = src_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        dst_time_str = dst_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # -----------------------------------------
        # NEWER CHECK
        # -----------------------------------------
        if src_time > dst_time:

            compare_msg = (
                "※ 移動元ファイルの方が新しいです"
            )

        elif src_time < dst_time:

            compare_msg = (
                "※ 移動先ファイルの方が新しいです"
            )

        else:

            compare_msg = (
                "※ 更新日時は同じです"
            )

        # -----------------------------------------
        # MESSAGE
        # -----------------------------------------
        msg = (

            "同名ファイルが存在します\n\n"

            f"{file_name}\n\n"

            "【移動元 更新日時】\n"
            f"{src_time_str}\n\n"

            "【移動先 更新日時】\n"
            f"{dst_time_str}\n\n"

            f"{compare_msg}\n\n"

            "上書きしますか？"
        )

        result = QMessageBox.question(

            self,

            "上書き確認",

            msg,

            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,

            QMessageBox.StandardButton.No,
        )

        overwrite = (
            result
            == QMessageBox.StandardButton.Yes
        )

        logger.info(
            "上書き確認: file=%s overwrite=%s",
            file_name,
            overwrite,
        )

        return overwrite
    
    # MoveFileManager ダブルクリックイベント
    def move_label_double_click_event(self, event):
        
        self.move_double_click = True
        
        if event.button() != Qt.MouseButton.LeftButton:
            
            return
        
        try:
            key = (f"move_of_file_"f"{self.move_mode_index}")
            
            move_config = self.config.get(key, {},)
            
            out_folder = move_config.get("out_of_folder", "",)
            
            # EXIST CHECK
            if not os.path.exists(out_folder):
                
                QMessageBox.warning(self, "フォルダエラー", ("移動元フォルダが存在しません\n\n"f"{out_folder}"),)

                return
            
            # OPEN FOLDER
            logger.info("移動元フォルダを開く: %s", out_folder)
            os.startfile(out_folder)
        
        except Exception as e:

            logger.exception("移動元フォルダを開く際にエラー")
            QMessageBox.critical(self, "エラー", str(e),)
            
    # =====================================================
    # Move Label color
    # =====================================================
    def update_move_label(self):
        
        key = (
                f"move_of_file_"
                f"{self.move_mode_index}"
            )
        
        move_config = self.config.get(key)
        
        label = move_config.get("label", "MOVE")
        
        bg = move_config.get("bg_color", "#00a3af")
        
        color = move_config.get("str_color", "white")
        
        count = self.move_manager.count_target_files(key)
        
        self.move_label.setText(f"ファイル移動 : {label} ({count})")
        
        self.move_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                color: {color};
                padding: 4px 12px;
                font-weight: bold;
                border-radius: 4px;
            }}
            """
        )

    # =====================================================
    # Mode Switch
    # =====================================================
    def toggle_mode(self, event):

        current_index = self.modes.index(self.current_mode)
        next_index = (current_index + 1) % len(self.modes)
        previous_mode = self.current_mode
        self.current_mode = self.modes[next_index]
        logger.info(
            "モード切替: %s -> %s",
            previous_mode,
            self.current_mode,
        )
        self.status_label.setStyleSheet(
            self.mode_styles[self.current_mode]
        )
        self.update_mode_ui()

    def _output_dir_label(self):

        if self.current_mode == self.mode_label_eps:
            return "EPS保存先"

        if self.current_mode in (
            self.mode_label_dxf_pdf,
        ):
            return "PDF保存先"

        if self.current_mode in (
            self.mode_label_dxf_dxf,
            self.mode_label_ai_dxf,
        ):
            return "DXF保存先"

        return "出力先"

    def update_mode_ui(self):

        self.status_label.setText(f"モード : {self.current_mode}")

        self.output_label.setText(
            f"{self._output_dir_label()} : {self.output_dir}"
        )

        drop_messages = {
            self.mode_label_rcheck: (
                "DXF または DAT をこの画面にドラッグ＆ドロップしてください（Ｒチェック）"
            ),
            self.mode_label_eps: (
                "DXF をこの画面にドラッグ＆ドロップしてください（EPS自動変換）"
            ),
            self.mode_label_dxf_dxf: (
                f"DXF をこの画面にドラッグ＆ドロップしてください（{self.dxf_downgrade_format} へ変換）"
            ),
            self.mode_label_dxf_pdf: (
                "DXF をこの画面にドラッグ＆ドロップしてください（PDF自動変換）"
            ),
            self.mode_label_ai_dxf: (
                f"AI をこの画面にドラッグ＆ドロップしてください（DXF {self.ai_dxf_format} 自動変換）"
            ),
        }

        self.drop_label.setText(
            drop_messages[self.current_mode]
        )
            
    # =====================================================
    # Output Directory Select
    # =====================================================
    def select_output_directory(self, event):

        dialog_titles = {
            self.mode_label_eps: "EPS 出力先を選択",
            self.mode_label_dxf_dxf: "DXF 出力先を選択",
            self.mode_label_dxf_pdf: "PDF 出力先を選択",
            self.mode_label_ai_dxf: "DXF 出力先を選択",
        }

        title = dialog_titles.get(
            self.current_mode,
            "出力先を選択",
        )
        
        folder = QFileDialog.getExistingDirectory(
            self,
            title,
            self.output_dir,
        )
        
        if folder:
            previous_dir = self.output_dir
            self.output_dir = folder
            logger.info(
                "出力先変更: %s -> %s (mode=%s)",
                previous_dir,
                self.output_dir,
                self.current_mode,
            )
            self.output_label.setText(
                f"{self._output_dir_label()} : {self.output_dir}"
            )

    # =====================================================
    # Drag & Drop
    # =====================================================
    def dragEnterEvent(self, event):

        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):

        files = [u.toLocalFile() for u in event.mimeData().urls()]

        logger.info(
            "ドロップ受信: mode=%s files=%s",
            self.current_mode,
            files,
        )

        for file_path in files:

            ext = os.path.splitext(file_path)[1].lower()
            logger.debug(
                "ドロップ処理: file=%s ext=%s",
                file_path,
                ext,
            )

            # ----------------------------------------
            # R Checker Mode
            # ----------------------------------------
            if self.current_mode == self.mode_label_rcheck:

                if ext == ".dxf":
                    self.process_dxf(file_path)

                elif ext == ".dat":
                    self.process_gcode(file_path)

            elif self.current_mode == self.mode_label_eps:

                if ext == ".dxf":
                    self.convert_dxf_to_eps(file_path)

            elif self.current_mode == self.mode_label_dxf_dxf:

                if ext == ".dxf":
                    self.convert_dxf_to_dxf(file_path)

            elif self.current_mode == self.mode_label_dxf_pdf:

                if ext == ".dxf":
                    self.convert_dxf_to_pdf(file_path)

            elif self.current_mode == self.mode_label_ai_dxf:

                if ext == ".ai":
                    self.convert_ai_to_dxf(file_path)
                else:
                    logger.warning(
                        "未対応ファイル: mode=%s ext=%s file=%s",
                        self.current_mode,
                        ext,
                        file_path,
                    )

            break

    # =====================================================
    # DXF PROCESS
    # =====================================================
    def process_dxf(self, file_path):

        logger.info("DXF解析開始: file=%s", file_path)

        try:

            doc = ezdxf.readfile(file_path)

            msp = doc.modelspace()

            self.ax.clear()

            found_large_r = False
            found_short_arc = False

            # -------------------------------------------------
            # CONFIG
            # -------------------------------------------------
            r_threshold = self.config.get(
                "threshold",
                100,
            )

            arc_length_threshold = (
                self.config.get("gcode", {})
                .get("arc_length_threshold", 0.1)
            )

            # =================================================
            # ENTITY LOOP
            # =================================================
            for e in msp:

                # =================================================
                # ARC / CIRCLE
                # =================================================
                if e.dxftype() in ("CIRCLE", "ARC"):

                    center = e.dxf.center

                    radius = e.dxf.radius

                    is_large_r = radius >= r_threshold

                    is_short_arc = False

                    arc_length = None

                    # =============================================
                    # ARC
                    # =============================================
                    if e.dxftype() == "ARC":

                        start_angle = e.dxf.start_angle
                        end_angle = e.dxf.end_angle

                        sweep_angle = end_angle - start_angle

                        if sweep_angle < 0:
                            sweep_angle += 360

                        arc_length = (
                            2
                            * math.pi
                            * radius
                            * sweep_angle
                            / 360
                        )

                        is_short_arc = (
                            arc_length <= arc_length_threshold
                        )

                    # =============================================
                    # FLAG
                    # =============================================
                    if is_large_r:
                        found_large_r = True

                    if is_short_arc:
                        found_short_arc = True

                    # =============================================
                    # DRAW
                    # =============================================
                    if is_large_r or is_short_arc:

                        self.draw_arc_highlight(
                            center.x,
                            center.y,
                            radius,
                            e,
                        )

                        # -----------------------------------------
                        # TEXT
                        # -----------------------------------------
                        text = f"R:{radius:.2f}"

                        if arc_length is not None:

                            text += (
                                f"\nL:{arc_length:.3f}"
                            )

                        self.ax.text(
                            center.x,
                            center.y,
                            text,
                            color="red",
                            fontsize=8,
                            fontweight="bold",
                        )

                    else:

                        self.draw_arc_normal(
                            center.x,
                            center.y,
                            radius,
                            e,
                        )

                # =================================================
                # LINE
                # =================================================
                elif e.dxftype() == "LINE":

                    self.ax.plot(
                        [
                            e.dxf.start.x,
                            e.dxf.end.x,
                        ],
                        [
                            e.dxf.start.y,
                            e.dxf.end.y,
                        ],
                        color="lightgray",
                        lw=0.5,
                    )

            # =====================================================
            # TITLE
            # =====================================================
            warning_text = []

            if found_large_r:

                warning_text.append(
                    f"{r_threshold}R以上"
                )

            if found_short_arc:

                warning_text.append(
                    f"円弧長{arc_length_threshold}mm以下"
                )

            title = (
                f"DXF解析完了 : "
                f"{os.path.basename(file_path)}"
            )

            if warning_text:

                title += "  【検出 : "
                title += " / ".join(warning_text)
                title += "】"

            # =====================================================
            # FINALIZE
            # =====================================================
            self.finalize_plot(
                title,
                found_large_r or found_short_arc,
            )

            logger.info(
                "DXF解析完了: file=%s large_r=%s short_arc=%s",
                file_path,
                found_large_r,
                found_short_arc,
            )

        except Exception as e:

            logger.exception("DXF解析エラー: file=%s", file_path)

            self.show_error(
                f"DXFエラー : {str(e)}"
            )

    # =========================================================
    # GCODE PROCESS
    # =========================================================
    def process_gcode(self, file_path):

        logger.info("Gコード解析開始: file=%s", file_path)

        try:

            # =================================================
            # CONFIG
            # =================================================
            gcode_config = self.config.get("gcode", {})

            NC_SCALE = gcode_config.get("scale", 0.01)

            absolute_mode = gcode_config.get(
                "default_absolute_mode",
                False,
            )

            # ---------------------------------------------
            # CHECK CONDITION
            # ---------------------------------------------
            r_threshold = self.config.get(
                "threshold",
                100,
            )

            arc_length_threshold = gcode_config.get(
                "arc_length_threshold",
                0.1,
            )

            # =================================================
            # INITIALIZE
            # =================================================
            self.ax.clear()

            found_large_r = False
            found_short_arc = False

            cur_x = 0.0
            cur_y = 0.0

            # =================================================
            # FILE READ
            # =================================================
            with open(file_path, "r", encoding="utf-8") as f:

                for line in f:

                    line = line.upper().strip()

                    if not line:
                        continue

                    # -----------------------------------------
                    # G90 / G91
                    # -----------------------------------------
                    if "G90" in line:
                        absolute_mode = True

                    if "G91" in line:
                        absolute_mode = False

                    # -----------------------------------------
                    # MOVE VALUE
                    # -----------------------------------------
                    move_x = (
                        float(
                            re.search(
                                r"X([-+]?\d*\.?\d+)",
                                line,
                            ).group(1)
                        ) * NC_SCALE
                        if "X" in line
                        else 0.0
                    )

                    move_y = (
                        float(
                            re.search(
                                r"Y([-+]?\d*\.?\d+)",
                                line,
                            ).group(1)
                        ) * NC_SCALE
                        if "Y" in line
                        else 0.0
                    )

                    # -----------------------------------------
                    # ABS / INC
                    # -----------------------------------------
                    if absolute_mode:

                        new_x = move_x if "X" in line else cur_x
                        new_y = move_y if "Y" in line else cur_y

                    else:

                        new_x = cur_x + move_x
                        new_y = cur_y + move_y

                    # =================================================
                    # ARC
                    # =================================================
                    if "G02" in line or "G03" in line:

                        clockwise = "G02" in line

                        # ---------------------------------------------
                        # I / J ARC
                        # ---------------------------------------------
                        if "I" in line or "J" in line:

                            i = (
                                float(
                                    re.search(
                                        r"I([-+]?\d*\.?\d+)",
                                        line,
                                    ).group(1)
                                ) * NC_SCALE
                                if "I" in line
                                else 0.0
                            )

                            j = (
                                float(
                                    re.search(
                                        r"J([-+]?\d*\.?\d+)",
                                        line,
                                    ).group(1)
                                ) * NC_SCALE
                                if "J" in line
                                else 0.0
                            )

                            # -----------------------------------------
                            # CENTER
                            # -----------------------------------------
                            center_x = cur_x + i
                            center_y = cur_y + j

                            # -----------------------------------------
                            # RADIUS
                            # -----------------------------------------
                            radius = math.sqrt(i**2 + j**2)

                            # -----------------------------------------
                            # START ANGLE
                            # -----------------------------------------
                            start_angle = math.degrees(
                                math.atan2(
                                    cur_y - center_y,
                                    cur_x - center_x,
                                )
                            )

                            # -----------------------------------------
                            # END ANGLE
                            # -----------------------------------------
                            end_angle = math.degrees(
                                math.atan2(
                                    new_y - center_y,
                                    new_x - center_x,
                                )
                            )
                            
                            # -----------------------------------------
                            # FULL CIRCLE CHECK
                            # -----------------------------------------
                            is_full_circle = (
                                abs(cur_x - new_x) < 0.000001
                                and
                                abs(cur_y - new_y) < 0.000001
                            )

                            # -----------------------------------------
                            # CW / CCW
                            # -----------------------------------------
                            if clockwise:

                                while start_angle < end_angle:
                                    start_angle += 360

                                theta1 = end_angle
                                theta2 = start_angle

                                sweep_angle = theta2 - theta1

                            else:

                                while end_angle < start_angle:
                                    end_angle += 360

                                theta1 = start_angle
                                theta2 = end_angle

                                sweep_angle = theta2 - theta1
                                
                            # -----------------------------------------
                            # FULL CIRCLE FIX
                            # -----------------------------------------
                            if is_full_circle:
                                
                                sweep_angle = 360

                            # -----------------------------------------
                            # ARC LENGTH
                            # -----------------------------------------
                            arc_length = (
                                2
                                * math.pi
                                * radius
                                * abs(sweep_angle)
                                / 360
                            )

                            # -----------------------------------------
                            # WARNING CHECK
                            # -----------------------------------------
                            is_large_r = radius >= r_threshold

                            is_short_arc = (
                                arc_length <= arc_length_threshold
                            )

                            # -----------------------------------------
                            # COLOR
                            # -----------------------------------------
                            if is_large_r or is_short_arc:

                                color = "red"
                                lw = 2

                            else:

                                color = "gray"
                                lw = 0.8

                            # -----------------------------------------
                            # FLAG
                            # -----------------------------------------
                            if is_large_r:
                                found_large_r = True

                            if is_short_arc:
                                found_short_arc = True

                            # -----------------------------------------
                            # ARC DRAW
                            # -----------------------------------------
                            if is_full_circle:
                                
                                circle = plt.Circle(
                                    (center_x, center_y),
                                    radius,
                                    fill=False,
                                    color=color,
                                    lw=lw,
                                )
                                
                                self.ax.add_patch(circle)
                            
                            else:
                            
                                arc = Arc(
                                    (center_x, center_y),

                                    radius * 2,
                                    radius * 2,

                                    angle=0,

                                    theta1=theta1,
                                    theta2=theta2,

                                    color=color,
                                    lw=lw,
                                )

                                self.ax.add_patch(arc)

                            # -----------------------------------------
                            # TEXT
                            # -----------------------------------------
                            if is_large_r or is_short_arc:

                                text = (
                                    f"R:{radius:.2f}\n"
                                    f"L:{arc_length:.3f}"
                                )

                                self.ax.text(
                                    center_x,
                                    center_y,
                                    text,
                                    color="red",
                                    fontsize=8,
                                    fontweight="bold",
                                )

                        # ---------------------------------------------
                        # R ARC (簡易)
                        # ---------------------------------------------
                        elif "R" in line:

                            radius = abs(
                                float(
                                    re.search(
                                        r"R([-+]?\d*\.?\d+)",
                                        line,
                                    ).group(1)
                                )
                            ) * NC_SCALE

                            is_large_r = radius >= r_threshold

                            if is_large_r:

                                color = "red"
                                lw = 2

                                found_large_r = True

                            else:

                                color = "gray"
                                lw = 0.8

                            self.ax.plot(
                                [cur_x, new_x],
                                [cur_y, new_y],
                                color=color,
                                lw=lw,
                            )

                    # =================================================
                    # LINE
                    # =================================================
                    elif "G00" in line or "G01" in line:

                        if "G00" in line:

                            color = "#808080"
                            lw = 0.5
                            alpha = 0.3

                        else:

                            color = "lightgray"
                            lw = 0.8
                            alpha = 1.0

                        self.ax.plot(
                            [cur_x, new_x],
                            [cur_y, new_y],
                            color=color,
                            lw=lw,
                            alpha=alpha,
                        )

                    # =================================================
                    # UPDATE
                    # =================================================
                    cur_x = new_x
                    cur_y = new_y

            # =========================================================
            # FINALIZE
            # =========================================================
            warning_text = []

            if found_large_r:
                warning_text.append(
                    f"{r_threshold}R以上"
                )

            if found_short_arc:
                warning_text.append(
                    f"円弧長{arc_length_threshold}mm以下"
                )

            title = (
                f"Gコード解析完了 : "
                f"{os.path.basename(file_path)}"
            )

            if warning_text:

                title += "  【検出 : "
                title += " / ".join(warning_text)
                title += "】"

            self.finalize_plot(
                title,
                found_large_r or found_short_arc,
            )

            logger.info(
                "Gコード解析完了: file=%s large_r=%s short_arc=%s",
                file_path,
                found_large_r,
                found_short_arc,
            )

        except Exception as e:

            logger.exception("Gコード解析エラー: file=%s", file_path)

            self.show_error(
                f"Gコードエラー : {str(e)}"
            )

    # # =====================================================
    # # Draw Normal Arc
    # # =====================================================
    def draw_arc_normal(self, cx, cy, r, e):

        if e.dxftype() == "CIRCLE":

            p = plt.Circle(
                (cx, cy),
                r,
                color="gray",
                fill=False,
                lw=0.5,
                alpha=0.3,
            )

        else:

            p = Arc(
                (cx, cy),
                r * 2,
                r * 2,
                angle=0,
                theta1=e.dxf.start_angle,
                theta2=e.dxf.end_angle,
                color="gray",
                lw=0.5,
                alpha=0.3,
            )

        self.ax.add_patch(p)

    # # =====================================================
    # # Draw Highlight Arc
    # # =====================================================
    def draw_arc_highlight(self, cx, cy, r, e):

        if e.dxftype() == "CIRCLE":

            p = plt.Circle(
                (cx, cy),
                r,
                color="red",
                fill=False,
                lw=2,
            )

        else:

            p = Arc(
                (cx, cy),
                r * 2,
                r * 2,
                angle=0,
                theta1=e.dxf.start_angle,
                theta2=e.dxf.end_angle,
                color="red",
                lw=2,
            )

        self.ax.add_patch(p)

        self.ax.text(
            cx,
            cy,
            f"R:{r:.1f}",
            color="red",
            fontsize=9,
            fontweight="bold",
        )

    # # =====================================================
    # # Finalize Plot
    # # =====================================================
    def finalize_plot(self, title, found_warning):

        self.ax.set_aspect("equal", adjustable="datalim")
        self.ax.autoscale_view()

        self.canvas.draw()

        if found_warning:

            self.drop_label.setStyleSheet(
                """
                QLabel {
                    background-color: #6c2c2f;
                    color: #ee827c;
                    border: 2px solid red;
                    font-weight: bold;
                    border-radius: 6px;
                }
                """
            )

            # title += f"  【警告 : {self.threshold}R以上検出】"
            title += f"  【警告 : ファイルの修正が必要です】"

        else:

            self.drop_label.setStyleSheet(
                """
                QLabel {
                    background-color: #274a78;
                    color: #a0d8ef;
                    border: 2px solid #0095d9;
                    font-weight: bold;
                    border-radius: 6px;
                }
                """
            )

        self.drop_label.setText(title)

    # =====================================================
    # Convert Helpers
    # =====================================================
    def _make_output_path(self, input_path, output_ext):

        base_name = os.path.splitext(
            os.path.basename(input_path)
        )[0]

        return os.path.join(
            self.output_dir,
            f"{base_name}{output_ext}",
        )

    def _show_converting(self, message):

        logger.info(message)
        self.drop_label.setStyleSheet(
            """
            QLabel {
                background-color: #005243;
                color: #98d98e;
                border: 2px solid green;
                font-weight: bold;
                border-radius: 6px;
            }
            """
        )
        self.drop_label.setText(message)
        QApplication.processEvents()

    def _show_convert_success(self, message):

        logger.info(message)
        self.drop_label.setStyleSheet(
            """
            QLabel {
                background-color: #274a78;
                color: #a0d8ef;
                border: 2px solid #0095d9;
                font-weight: bold;
                border-radius: 6px;
            }
            """
        )
        self.drop_label.setText(message)

    def _run_inkscape_export(
        self,
        input_path,
        output_path,
        export_type,
        extra_options=None,
        processing_text="変換中...",
        error_prefix="変換失敗",
        show_error_on_failure=True,
    ):

        if not os.path.exists(self.INKSCAPE_PATH):
            self.show_error("Inkscape が見つかりません")
            return False

        cmd = [
            self.INKSCAPE_PATH,
            input_path,
            f"--export-type={export_type}",
            f"--export-filename={output_path}",
        ]

        if extra_options:
            cmd.extend(extra_options)

        logger.info(
            "Inkscape変換開始: input=%s output=%s type=%s",
            input_path,
            output_path,
            export_type,
        )
        logger.debug("Inkscapeコマンド: %s", cmd)

        try:
            self._show_converting(processing_text)
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )

            if not os.path.exists(output_path):
                logger.error(
                    "Inkscapeは正常終了しましたが、出力ファイルが作成されませんでした: %s",
                    output_path,
                )
                logger.error("Inkscape stdout: %s", result.stdout)
                logger.error("Inkscape stderr: %s", result.stderr)
                if show_error_on_failure:
                    self.show_error(
                        f"{error_prefix} : 出力ファイルが作成されませんでした。"
                    )
                return False

            logger.debug("Inkscape stdout: %s", result.stdout)
            logger.debug("Inkscape stderr: %s", result.stderr)
            logger.info("Inkscape変換成功: output=%s", output_path)
            return True

        except Exception as e:
            logger.exception(
                "Inkscape変換失敗: input=%s output=%s",
                input_path,
                output_path,
            )
            if show_error_on_failure:
                self.show_error(f"{error_prefix} : {str(e)}")
            return False

    # =====================================================
    # EPS Convert
    # =====================================================
    def convert_dxf_to_eps(self, dxf_path):

        logger.info("EPS変換開始: file=%s", dxf_path)
        eps_path = self._make_output_path(dxf_path, ".eps")

        extra_options = [
            "--export-area-drawing",
            self.config.get("eps_margin", "--export-margin=20"),
            self.config["eps_ver"],
        ]

        if self._run_inkscape_export(
            dxf_path,
            eps_path,
            "eps",
            extra_options=extra_options,
            processing_text="EPS変換中...",
            error_prefix="EPS変換失敗",
        ):
            self._show_convert_success(
                f"EPS変換完了 : {os.path.basename(eps_path)}"
            )

    # =====================================================
    # DXF Convert
    # =====================================================
    def _export_dxf_via_inkscape(
        self,
        input_path,
        output_path,
        format_label,
        extension,
        extra_options=None,
        show_error_on_failure=True,
    ):

        if extra_options is None:
            extra_options = [
                "--export-area-drawing",
                f"--export-extension={extension}",
            ]

        if self._run_inkscape_export(
            input_path,
            output_path,
            "dxf",
            extra_options=extra_options,
            processing_text=f"DXF変換中... ({format_label})",
            error_prefix="DXF変換失敗",
            show_error_on_failure=show_error_on_failure,
        ):
            self._show_convert_success(
                f"DXF変換完了 : {os.path.basename(output_path)}"
            )
            return True

        return False

    def _convert_dxf_via_odafc(self, dxf_path, output_path):

        from ezdxf.addons import odafc

        if not odafc.is_installed():
            self.show_error(
                "ACAD2000 等形式への変換には ODA File Converter が必要です。"
                "checker.yaml に oda_file_converter を設定するか、"
                "dxf_downgrade_format を R12 / R14 に変更してください。"
            )
            return

        try:
            self._show_converting(
                f"DXF変換中... ({self.dxf_downgrade_format})"
            )

            logger.info(
                "ODA変換開始: input=%s output=%s version=%s",
                dxf_path,
                output_path,
                self.dxf_downgrade_format,
            )

            odafc.convert(
                dxf_path,
                output_path,
                version=self.dxf_downgrade_format,
                replace=True,
            )

            logger.info("ODA変換成功: output=%s", output_path)
            self._show_convert_success(
                f"DXF変換完了 : {os.path.basename(output_path)}"
            )

        except Exception as e:
            logger.exception(
                "ODA変換失敗: input=%s version=%s",
                dxf_path,
                self.dxf_downgrade_format,
            )
            self.show_error(f"DXF変換失敗 : {str(e)}")

    def convert_dxf_to_dxf(self, dxf_path):

        output_path = self._make_output_path(dxf_path, ".dxf")

        logger.info(
            "DXFダウングレード開始: file=%s format=%s output=%s",
            dxf_path,
            self.dxf_downgrade_format,
            output_path,
        )

        if self.dxf_downgrade_inkscape_extension:
            self._export_dxf_via_inkscape(
                dxf_path,
                output_path,
                self.dxf_downgrade_format,
                self.dxf_downgrade_inkscape_extension,
            )
            return

        self._convert_dxf_via_odafc(dxf_path, output_path)

    # =====================================================
    # PDF Convert
    # =====================================================
    def convert_dxf_to_pdf(self, dxf_path):

        logger.info("PDF変換開始(DXF): file=%s", dxf_path)
        pdf_path = self._make_output_path(dxf_path, ".pdf")

        extra_options = [
            "--export-area-drawing",
            self.config.get("pdf_margin", "--export-margin=20"),
        ]

        if self._run_inkscape_export(
            dxf_path,
            pdf_path,
            "pdf",
            extra_options=extra_options,
            processing_text="PDF変換中...",
            error_prefix="PDF変換失敗",
        ):
            self._show_convert_success(
                f"PDF変換完了 : {os.path.basename(pdf_path)}"
            )

    def convert_ai_to_dxf(self, ai_path):

        logger.info(
            "DXF変換開始(AI): file=%s format=%s",
            ai_path,
            self.ai_dxf_format,
        )
        dxf_path = self._make_output_path(ai_path, ".dxf")

        if self._export_dxf_via_inkscape(
            ai_path,
            dxf_path,
            self.ai_dxf_format,
            self.ai_dxf_extension,
            show_error_on_failure=False,
        ):
            return

        logger.info(
            "AIファイルのDXF変換を再試行します: アートボード領域指定(--export-area-page)"
        )
        if not self._export_dxf_via_inkscape(
            ai_path,
            dxf_path,
            self.ai_dxf_format,
            self.ai_dxf_extension,
            extra_options=["--export-area-page"],
        ):
            self.show_error(
                "AI→DXF変換に失敗しました。アートボードやアートボード外の要素を確認してください。"
            )

    # =====================================================
    # Error Display
    # =====================================================
    def show_error(self, message):

        logger.error(message)

        self.drop_label.setStyleSheet(
            """
            QLabel {
                background-color: #6c2c2f;
                color: #ee827c;
                border: 2px solid red;
                font-weight: bold;
                border-radius: 6px;
            }
            """
        )

        self.drop_label.setText(message)

    # =====================================================
    # YAML Loader
    # =====================================================
    def load_yaml(self, file_path):

        logger.info("設定読込: path=%s", file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.debug("設定読込完了: keys=%s", list(config.keys()))
        return config


# =========================================================
# Main
# =========================================================
if __name__ == "__main__":

    logger.info("アプリケーション起動")

    app = QApplication(sys.argv)

    window = IntegratedCADApp()

    window.show()

    exit_code = app.exec()
    logger.info("アプリケーション終了: exit_code=%s", exit_code)
    sys.exit(exit_code)
