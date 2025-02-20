import sys
import time
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer

class CPSCounter(QWidget):
    def __init__(self):
        super().__init__()

        self.click_count = 0
        self.max_cps = 0
        self.last_time = 0

        self.cps_label = QLabel("CPS: 0", self)
        self.max_cps_label = QLabel("Max CPS: 0", self)
        self.timer_label = QLabel("Timer: 0", self)

        layout = QVBoxLayout()
        layout.addWidget(self.cps_label)
        layout.addWidget(self.max_cps_label)
        layout.addWidget(self.timer_label)
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_cps)
        self.timer.start(10)  # 0.01秒ごと

    def mousePressEvent(self, event):
        if self.click_count == 0:
            self.last_time = time.time()
        self.click_count += 1

    def update_cps(self):
        current_time = time.time()
        elapsed_time = current_time - self.last_time
        cps = self.click_count / elapsed_time
        self.cps_label.setText(f"CPS: {cps:.2f}")
        self.timer_label.setText(f"Timer: {elapsed_time:.2f}")

        if cps > self.max_cps:
            self.max_cps = cps
            self.max_cps_label.setText(f"Max CPS: {self.max_cps:.2f}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CPSCounter()
    window.show()
    sys.exit(app.exec())
