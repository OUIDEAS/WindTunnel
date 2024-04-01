import sys
import time
import serial
import os
import csv
import argparse
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from pyqtgraph.Qt import QtCore
from feathercom import *
from LEDwidget import LEDWidget
import numpy as np
# setting pyqtgraph configuration options
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


ui_class, base_class = pg.Qt.loadUiType("python_files/desginer_ui.ui")


class MainWindow(ui_class, base_class):

    def __init__(self, fixed_mode=False, pwmRange_mode=False):
        super().__init__()

        # Plot Creation and Initialization
        self.setupUi(self)
        self.plot_start_time = None
        self.plot_timer = QTimer(self)
        self.livePlot.plot()  # create a pyqtgraph plot object
        self.livePlot.setTitle("Velocity vs Time")
        self.livePlot.addLegend()
        self.livePlot.showGrid(x=True, y=True)
        self.livePlot.setLabel('left', 'Velocity', 'm/s')
        self.livePlot.setLabel('bottom', 'Time', 's')

        # Plot Curve Drawing
        self.x_values = []
        self.y_actual = []
        self.y_desired = []
        self.pen1 = pg.mkPen("#e7b33c", width=2, style=pg.QtCore.Qt.SolidLine)
        self.pen2 = pg.mkPen("#5ea6bd", width=2, style=QtCore.Qt.DotLine)
        self.livePlot.actualCurve = self.livePlot.plot(self.x_values, self.y_actual)    # plot actual velocity
        self.livePlot.actualCurve.setPen(self.pen1)

        # Start, Stop, Pause, Resume plotting
        self.pushButton.clicked.connect(self.start_plot)
        self.pushButton_2.clicked.connect(self.reset_plot)
        self.pushButton_3.clicked.connect(self.pause_plot)
        self.pushButton_4.clicked.connect(self.resume_plot)

        # Data Recording: Set data recording of variables to False
        self.record_actual = False
        self.record_desired = False
        self.record_hum = False
        self.record_temp = False
        self.record_pressure = False
        self.output_folder = "data_output"
        self.recorded_data = []
        os.makedirs(self.output_folder, exist_ok=True)

        # Serial Port Settings
        self.console_port = serial.Serial('COM14', 115200)           # console port (write)
        self.data_port = serial.Serial('COM15', 115200)             # data port (read)

        # Mode Settings
        self.pwmRange_mode = pwmRange_mode                          # Ramps PWM 0-100% if True (for troubleshooting)                         
        self.pwmRange_Timer = QTimer()
        self.pwmRange_Timer.timeout.connect(self.increase_pwm)
        self.fixed_mode = fixed_mode                                # Determines Env.Cond. variable mode
        self.ledWidget = self.findChild(LEDWidget, "ledWidget")     # Adds custom ledWidget
        if self.fixed_mode:                                         # If Fixed Mode is selected, LED On.
            self.ledWidget.turnOn()
            self.label.setText("ON")
            self.label.setStyleSheet("text-transform: uppercase;")
        else:
            self.label.setText("OFF")
            self.label.setStyleSheet("text-transform: uppercase;")

        # Other Settings
        self.density = 1.0
        self.hum_window = []
        self.dens_window = []
        self.temp_window = []
        self.press_window = []
        self.vel_window = []  
        self.dp_window = []                                         # List to store velocity values
        self.window_size = 10                                       # Size of the moving average window                             
        self.sendDuty.clicked.connect(self.specific_entry)          # send button calls send duty% function
        self.manualDuty.editingFinished.connect(self.specific_entry)# value sent if 'enter'key hit
        self.tareVelocity.clicked.connect(self.tare_vel)            # tare button calls tare function
        self.current_pwm = 0
        self.setup_timer()  
        self.init_values()
        self.tare_vel() 


    def init_values(self):
        duration = 5
        dens_vals = []
        press_vals = []
        hum_vals = []
        temp_vals = []

        start_time = time.time()
        while time.time() - start_time < duration:                                                           
            data = self.get_data(self.console_port, self.data_port)  
            hum = data[3]
            temp_K = data[1] + 273.15                                            
            press_Pa = data[0] * 100 
            dens = press_Pa / (287.058 * temp_K)
            dens_vals.append(dens)
            press_vals.append(press_Pa)
            hum_vals.append(hum)
            temp_vals.append(temp_K - 273.15)
            print("Initializing Environmental Conditions ...")

        if dens_vals:    
            self.density = sum(dens_vals) / len(dens_vals) 
            self.pressure = sum(press_vals) / len(press_vals)
            self.humidity = sum(hum_vals) / len(hum_vals)
            self.temperature = sum(temp_vals) / len(temp_vals)
            print("Average Density: ", self.density)
            print("Average Pressure: ", self.pressure)
            print("Average Humidity: ", self.humidity)
            print("Average Temperature: ", self.temperature)

        self.tempLCD.display("{:.1f}".format(self.temperature))                        
        self.pressureLCD.display("{:.1f}".format(self.pressure/1000))                    
        self.humLCD.display("{:.0f}".format(self.humidity))                          
        self.densityLCD.display("{:.2f}".format(self.density))                                            
        

    def start_plot(self):
        ms = int((1/self.sampleRate.value())*1000)          # sets time delay based on user-set record Hz

        if not self.plot_timer.isActive():
            self.plot_start_time = time.time()
            self.plot_timer.start(ms)
            self.plot_timer.timeout.connect(self.update_plot)


    def resume_plot(self):
        self.plot_timer.start()


    def pause_plot(self):
        self.plot_timer.stop()


    def reset_plot(self):
        self.save_data()
        self.plot_timer.stop()
        self.x_values = []
        self.y_actual = []
        self.y_desired = []
        self.recorded_data = []
        self.livePlot.clear()
        

    def update_plot(self):
        elapsed_time = time.time() - self.plot_start_time
        temp = self.tempLCD.value()
        hum = self.humLCD.value()
        pressure = self.pressureLCD.value()
        density = self.densityLCD.value()
        actual_vel = self.actualLCD.value()
        duty_percent = self.desiredLCD.value()

        self.x_values.append(elapsed_time)
        self.y_actual.append(actual_vel)

        self.livePlot.clear()
        self.livePlot.plot(self.x_values, self.y_actual, pen=self.pen1)
        self.livePlot.setXRange(min(self.x_values), max(self.x_values))

        # Data Recording 
        recorded_data_point = {
            "time": elapsed_time,
            "velocity": actual_vel,
            "duty": duty_percent,
        }

        if self.checkBox.isChecked():
            recorded_data_point["humidity"] = hum

        if self.checkBox_2.isChecked():
            recorded_data_point["pressure"] = pressure

        if self.checkBox_3.isChecked():
            recorded_data_point["temp"] = temp

        if self.checkBox_4.isChecked():
            recorded_data_point["density"] = density

        self.recorded_data.append(recorded_data_point)


    def save_data(self):
        if not self.recorded_data:
            print("no data")
            return 
        
        record_counter = 1
        while True:
            filename = os.path.join(self.output_folder, f"recorded_data_{record_counter}.csv")
            if not os.path.exists(filename):
                break
            record_counter += 1

        with open(filename, mode='w', newline='') as file:
            fieldnames = ["time", "velocity", "duty", "pressure", "humidity", "temp"]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for data_point in self.recorded_data:
                writer.writerow(data_point)
        print(f"Data saved to: {filename}")


    def specific_entry(self):
        number = self.manualDuty.value()                             # saves the number that is input by the user for Duty Cycle
        self.desiredLCD.display(number)                              # sets manual numbered entered as the Duty Cycle LCD value        
        
        if self.pwmRange_mode:                                       # only active if pwm range is enabled, starts a 10s timer
            self.pwmRange_Timer.start(10000)
            self.current_pwm = 0
            self.increase_pwm()


    def increase_pwm(self):                                          # function to increase the pwm by 5% every 10s
        if self.current_pwm <= 95:                                   # checks if current commanded pwm is under 100%
            self.current_pwm += 5                                    # if under, it adds 5% to current value
            self.desiredLCD.display(self.current_pwm)
            self.update_data
        else:
            self.current_pwm = 0
            self.desiredLCD.display(self.current_pwm)
            self.update_data
            self.pwmRange_Timer.stop()                              # stops timer when pwm reaches 100%


    def tare_vel(self):
       duration = 10
       dp_values = []
       start_time = time.time()
       while time.time() - start_time < duration:                    # 10 second while loop
            data = self.get_data(self.console_port, self.data_port)  # gets data
            dp = data[2]                                             # gets diff. pressure from get_data function
            dp_values.append(dp)                                     # saves the collected dp value
            print("Taring Velocity ...")

       if dp_values:    
            self.initDP = sum(dp_values) / len(dp_values)            # takes the average dp value and sets initDP = to 
            print("Average DP Value:", self.initDP)                  
            self.dp_window = [self.initDP] * self.window_size


    def setup_timer(self):                                           # timer setup for data collection and updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(200)                                         #200 ms delay on data collection (limited by sensor comm)


    def update_data(self):
        data = self.get_data(self.console_port, self.data_port)      # calls the get_data function
        if self.fixed_mode:                                            # checks if fixed_mode is true/fale
            self.update_lcds_FIXED(data)                               # calls update_lcds_FIXED if true
        else:
            self.update_lcds(data)                                   # calls update_lcd if false

        signal = int((self.desiredLCD.value()/100) * 65535)          # calculates signal based on 12 bit reso.(65535 values)
        send_pwm(self.console_port, signal)                          # calls the send_pwm function to send pwm to fan


    def get_data(self,console_port,data_port):                       # get_data function
        data_packet = request_data(console_port, data_port, 1)       # requests data_packet from the feather via ports
        return (
            float(data_packet[0][0]),                                # pressure
            float(data_packet[0][3]),                                # temperature
            float(data_packet[0][4]),                                # diff_pressure
            float(data_packet[0][2]),                                # humidity
        )


    def update_lcds(self, data):                                     # update_lcds function
        temp_C = data[1]                                             # uses data from update_data update lcds
        temp_K = temp_C + 273.15                                     # temp converted into Kelvin
        press_Pa = data[0] * 100                                     # pressure converted into Pascals
        press_Kpa = press_Pa / 1000                                  # pressure converted into KPa
        dp = data[2]
        dens_kgm3 = press_Pa / (287.058 * temp_K)                   
        hum = data[3]
        
        self.dens_window.append(dens_kgm3)
        self.hum_window.append(hum)
        self.temp_window.append(temp_C)
        self.press_window.append(press_Kpa)
        self.dp_window.append(dp)

        if len(self.dens_window) > self.window_size:
            self.dens_window.pop(0)
        if len(self.hum_window) > self.window_size:
            self.hum_window.pop(0)
        if len(self.temp_window) > self.window_size:
            self.temp_window.pop(0)
        if len(self.press_window) > self.window_size:
            self.press_window.pop(0)
        if len(self.dp_window) > self.window_size:
            self.dp_window.pop(0)

        avg_dens = sum(self.dens_window) / len(self.dens_window) if self.dens_window else 0
        avg_hum = sum(self.hum_window) / len(self.hum_window) if self.hum_window else 0
        avg_temp = sum(self.temp_window) / len(self.temp_window) if self.temp_window else 0
        avg_press = sum(self.press_window) / len(self.press_window) if self.press_window else 0                           
        avg_dp = sum(self.dp_window) / len(self.dp_window) if self.dp_window else 0
                
        magnitude_vel = np.sqrt(abs(2 * (avg_dp-self.initDP) / avg_dens))
        is_neg_vel = (avg_dp-self.initDP) < 0
        if self.desiredLCD.value() == 0:
            avg_vel = 0
        else:
            avg_vel = magnitude_vel * (-1 if is_neg_vel else 1)

        self.tempLCD.display("{:.1f}".format(avg_temp))                               # display temp on LCD
        self.pressureLCD.display("{:.1f}".format(avg_press))                          # display pressure on LCD
        self.humLCD.display("{:.0f}".format(avg_hum))                                 # display humidity on LCD
        self.actualLCD.display("{:.2f}".format(avg_vel))                              # display avg velocity on LCD
        self.densityLCD.display("{:.2f}".format(avg_dens))                            # display density on LCD


    def update_lcds_FIXED(self, data):                               # function for fixed mode
        dens_kgm3 = self.density
        dp = data[2]
        self.dp_window.append(dp)
        if len(self.dp_window) > self.window_size:
            self.dp_window.pop(0)

        avg_dp = sum(self.dp_window) / len(self.dp_window) if self.dp_window else 0
        magnitude_vel = np.sqrt(abs(2 * (avg_dp-self.initDP) / dens_kgm3))
        is_neg_vel = (avg_dp-self.initDP) < 0
        if self.desiredLCD.value() == 0:
            avg_vel = 0
        else:
            avg_vel = magnitude_vel * (-1 if is_neg_vel else 1)

        self.actualLCD.display("{:.2f}".format(avg_vel))


    def quit(self):
        signal = 0
        send_pwm(self.console_port, signal)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--fixed_mode', action='store_true', help='Use average update')
    parser.add_argument('--pwmRange_mode', action='store_true', help='Ramps up PWM')
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = MainWindow(fixed_mode=args.fixed_mode, pwmRange_mode=args.pwmRange_mode)
    app.aboutToQuit.connect(window.quit)
    window.show()
    sys.exit(app.exec_())
