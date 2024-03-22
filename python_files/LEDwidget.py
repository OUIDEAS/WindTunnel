from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt

class LEDWidget(QWidget):
    def __init__(self, parent=None):
        super(LEDWidget, self).__init__(parent)
        self._color = Qt.green
        self._on = False

        # Create the label to represent the LED
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: gray; border-radius: 10px;")

        # Set up layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Update LED appearance
        self.update_led()

    def update_led(self):
        color = self._color if self._on else Qt.gray
        self.label.setStyleSheet("background-color: {}; border-radius: 10px;".format(color.name()))

    def setColor(self, color):
        self._color = color
        self.update_led()

    def turnOn(self):
        self._on = True
        self.update_led()

    def turnOff(self):
        self._on = False
        self.update_led()

    def toggle(self):
        self._on = not self._on
        self.update_led()

    def isOn(self):
        return self._on
