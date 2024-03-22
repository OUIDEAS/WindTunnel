from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

class LEDWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create a label to represent the LED
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        
        # Add the label to the widget's layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        # Set default properties
        self.led_state = False
        self.update_led()
        
    def turnOn(self):
        self.led_state = True
        self.update_led()
        
    def turnOff(self):
        self.led_state = False
        self.update_led()
        
    def update_led(self):
        color = Qt.green if self.led_state else Qt.red
        if isinstance(color, QColor):  # Check if color is a QColor object
            self.label.setStyleSheet("background-color: {}; border-radius: 5px; border: 1px solid black;".format(color.name()))
        else:
            # Convert integer color value to QColor
            color = QColor(color)
            if color.isValid():
                self.label.setStyleSheet("background-color: {}; border-radius: 5px; border: 1px solid black;".format(color.name()))
            else:
                print("Invalid color object:", color)
            
    # Dummy setText method
    def setText(self, text):
        pass
