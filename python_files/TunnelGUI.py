import sys
import time
import serial
import os
import csv
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from pyqtgraph.Qt import QtCore
from feathercom import *

# setting pyqtgraph configuration options
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


ui_class, base_class = pg.Qt.loadUiType("python_files/desginer_ui.ui")


class MainWindow(ui_class, base_class):

    def __init__(self):
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
        self.console_port = serial.Serial('COM9', 115200)   # console port (write)
        self.data_port = serial.Serial('COM10', 115200)     # data port (read)

        # Other Settings
        self.setup_timer()  
        self.init_values() 
        self.density = 1.0
        self.vel_window = []                                # List to store velocity values
        self.vel_window_size = 10                           # Size of the moving average window                             
        self.sendDuty.clicked.connect(self.specific_entry)  # send button calls send duty% function
        self.manualDuty.editingFinished.connect(self.specific_entry) # value sent if 'enter'key hit
        self.tareVelocity.clicked.connect(self.tare_vel)    # tare button calls tare function
        self.initDP = 0.0                                   # initial diff. pressure for tare
        self.pwm_Range_Enabled = True                      # Ramps PWM 0-100% if True (for troubleshooting)  
        self.current_pwm = 0
        self.pwm_Range_Timer = QTimer()
        self.pwm_Range_Timer.timeout.connect(self.increase_pwm)
        
    def init_values(self):
        duration = 5
        dens_values = []

        start_time = time.time()
        while time.time() - start_time < duration:                    
            time.sleep(0.1)                                          
            data = self.get_data(self.console_port, self.data_port)  
            temp_K = data[1] + 273.15                                            
            press_Pa = data[0] * 100 
            dens = press_Pa / (287.0 * temp_K)
            dens_values.append(dens)                                                                              
            print("Initializing Density ...")

        if dens_values:    
            self.density = sum(dens_values) / len(dens_values) # takes the average density value and sets dense = to 
            print("Average Density Value:", self.density)
        


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

        self.recorded_data.append(recorded_data_point)


    def save_data(self):
        if not self.recorded_data:
            print("no data")
            return  # No data to save

        # Find the next available number for the filename
        record_counter = 1
        while True:
            filename = os.path.join(self.output_folder, f"recorded_data_{record_counter}.csv")
            if not os.path.exists(filename):
                break
            record_counter += 1

        # Write the recorded data to a CSV file, saves files with next available number
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
        
        if self.pwm_Range_Enabled:                                   # only active if pwm range is enabled, starts a 10s timer
            self.pwm_Range_Timer.start(10000)
            self.current_pwm = 0
            self.increase_pwm()

    def increase_pwm(self):                                          # function to increase the pwm by 5% every 10s
        if self.current_pwm <= 100:                                  # checks if current commanded pwm is under 100%
            self.current_pwm += 5                                    # if under, it adds 5% to current value
            self.desiredLCD.display(self.current_pwm)
            self.update_data
        else:
            self.pwm_Range_Time.stop()                               # stops timer when pwm reaches 100%


    def tare_vel(self):
       duration = 5
       dp_values = []
       start_time = time.time()
       while time.time() - start_time < duration:                    # 5 second while loop
            time.sleep(0.1)                                          # 0.1 second delay
            data = self.get_data(self.console_port, self.data_port)  # gets data
            dp = data[2]                                             # gets diff. pressure from get_data function
            dp_values.append(dp)                                     # saves the collected dp value
            print("Taring Velocity ...")

       if dp_values:    
            self.initDP = sum(dp_values) / len(dp_values)            # takes the average dp value and sets initDP = to 
            print("Average DP Value:", self.initDP)                  # initDP initially = 0 and is always being subtracted in data collection
      

    def setup_timer(self):                                           # timer setup for data collection and updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(200)                                         #200 ms delay on data collection (limited by sensor comm)


    def update_data(self):
        data = self.get_data(self.console_port, self.data_port)      # calls the get_data function
        self.update_lcds(data)                                       # calls the update_lcd function to update with new data
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
        press_Pa = data[0] * 100                                     # pressure converted into Pascals
        press_Kpa = press_Pa / 1000                                  # pressure converted into KPa
        dp = data[2]                         
        humidity = data[3]
        vel_MPS = (2 * max(dp-self.initDP, 0) / self.density)**0.5   # calculate velocity

        self.vel_window.append(vel_MPS)
        if len(self.vel_window) > self.vel_window_size:
            self.vel_window.pop(0)                                   # removes oldest velocity from window

        avg_vel = sum(self.vel_window) / len(self.vel_window) if self.vel_window else 0

        self.tempLCD.display(temp_C)                                 # display temp on LCD
        self.pressureLCD.display(press_Kpa)                          # display pressure on LCD
        self.humLCD.display(humidity)                                # display humidity on LCD
        self.actualLCD.display(avg_vel)                              # display avg velocity on LCD


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
