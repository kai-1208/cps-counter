from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QStackedWidget
from PySide6.QtCore import QTimer, Qt, QElapsedTimer
from PySide6.QtGui import QMouseEvent, QPainter, QBrush, QColor
import sys

class SettingScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        layout = QVBoxLayout()

        self.label = QLabel("測定時間を選択:")
        self.combo_box = QComboBox()
        self.combo_box.addItems([str(i) for i in range(1, 61)])
        self.start_button = QPushButton("開始")
        self.start_button.clicked.connect(self.start_measurement)

        layout.addWidget(self.label)
        layout.addWidget(self.combo_box)
        layout.addWidget(self.start_button)
        self.setLayout(layout)

    def start_measurement(self):
        duration = int(self.combo_box.currentText())
        self.main_app.start_cps_measurement(duration)

class CPSMeasurementScreen(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.click_count = 0
        self.max_cps = 0
        self.elapsed_timer = QElapsedTimer()
        self.ripple_x = None
        self.ripple_y = None
        self.ripple_alpha = 255
        self.ripples = []

        layout = QVBoxLayout()
        self.label = QLabel("画面をクリックして測定してください")
        self.cps_label = QLabel("CPS: 0")
        self.max_cps_label = QLabel("最大 CPS: 0")

        layout.addWidget(self.label)
        layout.addWidget(self.cps_label)
        layout.addWidget(self.max_cps_label)
        self.setLayout(layout)

    def start_measurement(self, duration):
        self.click_count = 0
        self.max_cps = 0
        self.elapsed_timer = QElapsedTimer()
        self.duration = duration * 1000
        self.cps_history = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_cps)
        self.timer.start(100)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.elapsed_timer.isValid():
            self.elapsed_timer.start()  # 最初のクリック時に測定開始
            QTimer.singleShot(self.duration, self.finish_measurement)
        self.click_count += 1

        self.ripples.append({
            "x": event.position().x(),
            "y": event.position().y(),
            "alpha": 255
        })
        # self.ripple_x, self.ripple_y = event.position().x(), event.position().y()
        # self.ripple_alpha = 255
        self.update()   

    def update_cps(self):
        if not self.elapsed_timer.isValid():
            return

        elapsed_time = self.elapsed_timer.elapsed() / 1000  # 秒単位
        if elapsed_time > 0:
            current_cps = self.click_count / elapsed_time
            self.cps_history.append(current_cps)

            # 直近1秒間の CPS を計算
            if len(self.cps_history) >= 10:  # 1秒ごとに記録
                last_10_intervals = self.cps_history[-10:]  # 最新10個取得
                avg_last_1s_cps = sum(last_10_intervals) / len(last_10_intervals)
                self.max_cps = max(self.max_cps, avg_last_1s_cps)

            self.cps_label.setText(f"CPS: {current_cps:.2f}")
            self.max_cps_label.setText(f"最大 CPS: {self.max_cps:.2f}")

        for ripple in self.ripples:
            ripple["alpha"] -= 10
            if ripple["alpha"] <= 0:
                self.ripples.remove(ripple)
        self.update()

        # if self.ripple_alpha > 0:
        #     self.ripple_alpha -= 10
        #     self.update()

    
    def paintEvent(self, event):
        # if self.ripple_x is not None and self.ripple_y is not None:
        #     painter = QPainter(self)
        #     painter.setBrush(QBrush(QColor(0, 150, 255, self.ripple_alpha)))
        #     painter.setPen(Qt.NoPen)
        #     radius = (255 - self.ripple_alpha) * 2
        #     painter.drawEllipse(int(self.ripple_x - radius / 2), int(self.ripple_y - radius / 2), radius, radius)

        painter = QPainter(self)
        painter.setPen(Qt.NoPen)

        # すべての波紋を描画
        for ripple in self.ripples:
            painter.setBrush(QBrush(QColor(0, 150, 255, ripple["alpha"])))
            radius = (255 - ripple["alpha"]) * 2
            painter.drawEllipse(int(ripple["x"] - radius / 2), int(ripple["y"] - radius / 2), radius, radius)

    def finish_measurement(self):
        self.timer.stop()
        self.ripples.clear()
        self.update()
        self.main_app.show_result_screen(self.click_count, self.max_cps, self.duration / 1000, self.cps_history)

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

    def start_cps_measurement(self, duration):
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
