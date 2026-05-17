# PySide6統合版 設計支援アプリ
import sys
import os
import re
import math
import subprocess

import ezdxf
import yaml

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.patches import Arc

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)
from PySide6.QtGui import QIcon

# =========================================================
# Main Window
# =========================================================
class IntegratedCADApp(QMainWindow):

    MODE_RCHECK = "R-CHECKER"
    MODE_EPS = "DXF → EPS CONVERTER"

    def __init__(self):
        super().__init__()

        # --------------------------------------------
        # YAML Load
        # --------------------------------------------
        self.config = self.load_yaml(r"c:\checker.yaml")

        self.threshold = self.config["threshold"]

        window = self.config["window_size"]

        self.resize(window["x"], window["y"])

        self.setWindowTitle("CAD Support Tool")
        
        # =========================================================
        # Inkscape Path
        # =========================================================
        self.INKSCAPE_PATH = self.config["inkscape"]

        # --------------------------------------------
        # Current Mode
        # --------------------------------------------
        self.current_mode = self.MODE_RCHECK

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
                background-color: #252526;
                color: white;
                border: 2px dashed #555;
                font-size: 14px;
                font-weight: bold;
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
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # --------------------------------------------
        # Output Directory Label
        # --------------------------------------------
        
        folder = self.config["folder"]
        
        self.output_dir = os.path.expanduser(folder)
        
        self.output_label = QLabel()
        self.output_label.setCursor(Qt.PointingHandCursor)
        
        self.output_label.setStyleSheet(
            """
            QLabel {
                background-color: #3c3c3c;
                color: white;
                padding: 4px 12px;
                border-right: 1px solid #555;
            }
            """
        )
        
        self.output_label.mousePressEvent = self.select_output_directory
        
        self.status.addWidget(self.output_label)
        
        # --------------------------------------------
        # Model Label
        # --------------------------------------------
        self.status_label = QLabel()
        self.status_label.setCursor(Qt.PointingHandCursor)

        self.status_label.setStyleSheet(
            """
            QLabel {
                background-color: #007acc;
                color: white;
                padding: 4px 12px;
                font-weight: bold;
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

    # =====================================================
    # Mode Switch
    # =====================================================
    def toggle_mode(self, event):

        if self.current_mode == self.MODE_RCHECK:
            self.current_mode = self.MODE_EPS
        else:
            self.current_mode = self.MODE_RCHECK

        self.update_mode_ui()

    def update_mode_ui(self):

        self.status_label.setText(f"MODE : {self.current_mode}")
        
        self.output_label.setText(f"OUTPUT : {self.output_dir}")

        if self.current_mode == self.MODE_RCHECK:

            self.drop_label.setText(
                "DXF または NC(.dat) をドラッグ＆ドロップしてください"
            )

        else:

            self.drop_label.setText(
                "DXF をドラッグ＆ドロップしてください（EPS変換）"
            )
            
    # =====================================================
    # Output Directory Select
    # =====================================================
    def select_output_directory(self, event):
        
        folder = QFileDialog.getExistingDirectory(self, "EPS 出力先を選択", self.output_dir)
        
        if folder:
            self.output_dir = folder
            self.output_label.setText(f"OUTPUT : {self.output_dir}")

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

        for file_path in files:

            ext = os.path.splitext(file_path)[1].lower()

            # ----------------------------------------
            # R Checker Mode
            # ----------------------------------------
            if self.current_mode == self.MODE_RCHECK:

                if ext == ".dxf":
                    self.process_dxf(file_path)

                elif ext == ".dat":
                    self.process_gcode(file_path)

            # ----------------------------------------
            # EPS Convert Mode
            # ----------------------------------------
            else:

                if ext == ".dxf":
                    self.convert_dxf_to_eps(file_path)

            break

    # =====================================================
    # DXF PROCESS
    # =====================================================
    def process_dxf(self, file_path):

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

        except Exception as e:

            self.show_error(
                f"DXFエラー : {str(e)}"
            )

    # =========================================================
    # GCODE PROCESS
    # =========================================================
    def process_gcode(self, file_path):

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

        except Exception as e:

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
                    background-color: #4b1c1c;
                    color: #ff8080;
                    border: 2px solid red;
                    font-weight: bold;
                }
                """
            )

            # title += f"  【警告 : {self.threshold}R以上検出】"
            title += f"  【警告 : ファイルの修正が必要です】"

        else:

            self.drop_label.setStyleSheet(
                """
                QLabel {
                    background-color: #1c3b1c;
                    color: #90ee90;
                    border: 2px solid green;
                    font-weight: bold;
                }
                """
            )

        self.drop_label.setText(title)

    # =====================================================
    # EPS Convert
    # =====================================================
    def convert_dxf_to_eps(self, dxf_path):

        if not os.path.exists(self.INKSCAPE_PATH):

            self.show_error("Inkscape が見つかりません")
            return

        
        # -----------------------------
        # 出力ファイル名生成
        # -----------------------------
        base_name = os.path.splitext(
            os.path.basename(dxf_path)
        )[0]
        
        eps_path = os.path.join(
            self.output_dir,
            f"{base_name}.eps"
        )

        # -----------------------------
        # Inkscape Command
        # -----------------------------    
        
        cmd = [
            self.INKSCAPE_PATH,
            dxf_path,
            "--export-type=eps",
            f"--export-filename={eps_path}",
            "--export-area-drawing", # DXF の全範囲を出力
            "--export-margin=20",
            self.config["eps_ver"], # EPS のバージョン(yaml で setting)
        ]

        try:

            self.drop_label.setStyleSheet(
                """
                QLabel {
                    background-color: #1f3b5c;
                    color: #8ecfff;
                    border: 2px solid #007acc;
                    font-weight: bold;
                }
                """
            )

            self.drop_label.setText(
                "EPS変換中..."
            )

            QApplication.processEvents()

            subprocess.run(cmd, check=True)

            self.drop_label.setStyleSheet(
                """
                QLabel {
                    background-color: #1c3b1c;
                    color: #90ee90;
                    border: 2px solid green;
                    font-weight: bold;
                }
                """
            )

            self.drop_label.setText(
                f"EPS変換完了 : {os.path.basename(eps_path)}"
            )

        except Exception as e:

            self.show_error(f"EPS変換失敗 : {str(e)}")

    # =====================================================
    # Error Display
    # =====================================================
    def show_error(self, message):

        self.drop_label.setStyleSheet(
            """
            QLabel {
                background-color: #4b1c1c;
                color: #ff8080;
                border: 2px solid red;
                font-weight: bold;
            }
            """
        )

        self.drop_label.setText(message)

    # =====================================================
    # YAML Loader
    # =====================================================
    def load_yaml(self, file_path):

        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


# =========================================================
# Main
# =========================================================
if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = IntegratedCADApp()

    window.show()

    sys.exit(app.exec())
