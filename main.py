from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QStackedWidget, QSlider
from PySide6.QtCore import QTimer, Qt, QElapsedTimer
from PySide6.QtGui import QMouseEvent, QPainter, QBrush, QColor
from numba import njit
import numpy as np
import sys
import pyqtgraph as pg

class SettingScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.setFixedSize(800, 600)

        layout = QVBoxLayout()
        self.label = QLabel("測定時間を選択してください:")
        layout.addWidget(self.label)
        self.combo_box = QComboBox()
        self.combo_box.addItems([str(i) for i in range(1, 61)])
        layout.addWidget(self.combo_box)

        self.ripple_color_label = QLabel("波紋の色を選択してください")
        layout.addWidget(self.ripple_color_label)

        self.r_slider_ripple = self.create_slider("R", layout)
        self.g_slider_ripple = self.create_slider("G", layout)
        self.b_slider_ripple = self.create_slider("B", layout)

        self.color_preview_ripple = QLabel()
        self.color_preview_ripple.setFixedSize(100, 50)
        self.update_color_preview(self.color_preview_ripple, self.r_slider_ripple, self.g_slider_ripple, self.b_slider_ripple)
        layout.addWidget(self.color_preview_ripple, alignment=Qt.AlignCenter)

        self.r_slider_ripple.valueChanged.connect(lambda: self.update_color_preview(self.color_preview_ripple, self.r_slider_ripple, self.g_slider_ripple, self.b_slider_ripple))
        self.g_slider_ripple.valueChanged.connect(lambda: self.update_color_preview(self.color_preview_ripple, self.r_slider_ripple, self.g_slider_ripple, self.b_slider_ripple))
        self.b_slider_ripple.valueChanged.connect(lambda: self.update_color_preview(self.color_preview_ripple, self.r_slider_ripple, self.g_slider_ripple, self.b_slider_ripple))

        self.start_button = QPushButton("測定開始")
        self.start_button.clicked.connect(self.start_measurement)
        layout.addWidget(self.start_button)

        self.setLayout(layout)

    def create_slider(self, label_text, layout):
        label = QLabel(f"{label_text}: 0")
        layout.addWidget(label)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(255)
        slider.valueChanged.connect(lambda: label.setText(f"{label_text}: {slider.value()}"))

        layout.addWidget(slider)
        return slider

    def update_color_preview(self, preview_label, r_slider, g_slider, b_slider):
        r = r_slider.value()
        g = g_slider.value()
        b = b_slider.value()
        preview_label.setStyleSheet(f"background-color: rgb({r}, {g}, {b});")

    def start_measurement(self):
        duration = int(self.combo_box.currentText())
        self.main_app.start_cps_measurement(duration, (self.r_slider_ripple.value(), self.g_slider_ripple.value(), self.b_slider_ripple.value()))

class CPSMeasurementScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.click_count = 0
        self.max_cps = 0
        self.elapsed_timer = QElapsedTimer()
        self.max_ripples = 20
        self.ripples = np.zeros((self.max_ripples, 4), dtype=np.float32)

        self.ripple_timer = QTimer()
        self.ripple_timer.timeout.connect(self.update_ripples)
        self.ripple_timer.start(30)

        layout = QVBoxLayout()
        self.label = QLabel("画面をクリックして測定してください")
        self.cps_label = QLabel("CPS: 0")
        self.max_cps_label = QLabel("最大 CPS: 0")

        layout.addWidget(self.label)
        layout.addWidget(self.cps_label)
        layout.addWidget(self.max_cps_label)

        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setTitle("CPS推移")
        self.graph_widget.setLabel("left", "CPS")
        self.graph_widget.setLabel("bottom", "時間 (秒)")
        self.graph_widget.setYRange(0, 10)
        self.cps_plot = self.graph_widget.plot([], [], pen="r")
        layout.addWidget(self.graph_widget)

        self.setLayout(layout)

    def start_measurement(self, duration):
        self.click_count = 0
        self.max_cps = 0
        self.elapsed_timer = QElapsedTimer()
        self.duration = duration * 1000
        self.cps_history = []
        self.time_history = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_cps)
        self.timer.start(100)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.elapsed_timer.isValid():
            self.elapsed_timer.start()  # 最初のクリック時に測定開始
            QTimer.singleShot(self.duration, self.finish_measurement)
        self.click_count += 1

        self.ripples[:-1] = self.ripples[1:]
        self.ripples[-1] = [event.position().x(), event.position().y(), 255, 5]

    def update_cps(self):
        if not self.elapsed_timer.isValid():
            return

        elapsed_time = self.elapsed_timer.elapsed() / 1000  # 秒単位
        if elapsed_time > 0:
            current_cps = self.click_count / elapsed_time
            self.cps_history.append(current_cps)
            self.time_history.append(elapsed_time)

            # 直近1秒間の CPS を計算
            if len(self.cps_history) >= 10:  # 1秒ごとに記録
                avg_last_1s_cps = sum(self.cps_history[-10:]) / len(self.cps_history[-10:])
                self.max_cps = max(self.max_cps, avg_last_1s_cps)

            self.cps_label.setText(f"CPS: {current_cps:.2f}")
            self.max_cps_label.setText(f"最大 CPS: {self.max_cps:.2f}")

            self.update_cps_graph()

    def update_cps_graph(self):
        self.cps_plot.setData(self.time_history, self.cps_history)
        self.graph_widget.setYRange(0, max(self.cps_history)+1)

    def update_ripples(self):
        self.ripples = expand(self.ripples, 70, 15)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Qt.NoPen)

        # すべての波紋を描画
        for x, y, alpha, radius in self.ripples:
            if alpha > 0:
                painter.setBrush(QBrush(QColor(self.ripple_color.red(), self.ripple_color.green(), self.ripple_color.blue(), int(alpha))))
                painter.drawEllipse(int(x - radius / 2), int(y - radius / 2), int(radius), int(radius))

    def finish_measurement(self):
        self.timer.stop()
        self.ripples.fill(0)
        self.update()
        self.main_app.show_result_screen(self.click_count, self.max_cps, self.duration / 1000, self.cps_history)

@njit
def expand(ripples, growth_rate, fade_rate):
    for i in range(len(ripples)):
        if ripples[i, 2] > 0:
            ripples[i, 3] += growth_rate
            ripples[i, 2] = max(0, ripples[i, 2] - fade_rate)
    return ripples

class ResultScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        layout = QVBoxLayout()

        self.result_label = QLabel("測定結果")
        self.total_clicks_label = QLabel("総クリック数: 0")
        self.avg_cps_label = QLabel("平均 CPS: 0")
        self.max_cps_label = QLabel("最大 CPS: 0")
        self.retry_button = QPushButton("再測定")
        self.retry_button.clicked.connect(self.main_app.show_setting_screen)

        layout.addWidget(self.result_label)
        layout.addWidget(self.total_clicks_label)
        layout.addWidget(self.avg_cps_label)
        layout.addWidget(self.max_cps_label)
        layout.addWidget(self.retry_button)
        self.setLayout(layout)

    def display_results(self, total_clicks, max_cps, duration, cps_history):
        avg_cps = total_clicks / duration if duration > 0 else 0
        if duration == 1:
            max_cps = avg_cps

        self.total_clicks_label.setText(f"総クリック数: {total_clicks}")
        self.avg_cps_label.setText(f"平均 CPS: {avg_cps:.2f}")
        self.max_cps_label.setText(f"最大 CPS: {max_cps:.2f}")

class CPSCounter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CPS 測定")
        self.layout = QVBoxLayout()

        self.stack = QStackedWidget()
        self.setting_screen = SettingScreen(self)
        self.measurement_screen = CPSMeasurementScreen(self)
        self.result_screen = ResultScreen(self)

        self.stack.addWidget(self.setting_screen)
        self.stack.addWidget(self.measurement_screen)
        self.stack.addWidget(self.result_screen)

        self.layout.addWidget(self.stack)
        self.setLayout(self.layout)

        self.show_setting_screen()

    def show_setting_screen(self):
        self.stack.setCurrentWidget(self.setting_screen)

    def start_cps_measurement(self, duration, ripple_color):
        self.measurement_screen.ripple_color = QColor(*ripple_color)
        self.stack.setCurrentWidget(self.measurement_screen)
        self.measurement_screen.start_measurement(duration)

    def show_result_screen(self, total_clicks, max_cps, duration, cps_history):
        self.result_screen.display_results(total_clicks, max_cps, duration, cps_history)
        self.stack.setCurrentWidget(self.result_screen)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CPSCounter()
    window.show()
    sys.exit(app.exec())
