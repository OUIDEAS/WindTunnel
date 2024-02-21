# IMPORTING MODULES
import usb_cdc
import board
import DFR_lwlp
import adafruit_bmp3xx
import adafruit_ahtx0
import time
import pwmio

def init_sensors(i2c):
    """
    Connects to the boards i2c and initializes the i2C connections with all 3 sensors.
    :param i2c: the board's i2c object
    :return: True if successful, otherwise returns an error message
    """

    # initialize bmp
    bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)
    bmp.pressure_oversampling = 8
    bmp.temperature_oversampling = 2

    if bmp:
        print("Successfully Connected:", bmp)
    else:
        print("Issue Connecting to BMP")

    # initialize aht
    aht = adafruit_ahtx0.AHTx0(i2c)

    if aht:
        print("Successfully Connected:", aht)
    else:
        print("Issue Connecting to AHT")

    # initialize lwlp
    lwlp = DFR_lwlp.lwlp(0x00)

    if lwlp:
        print("Successfully Connected:", lwlp)
    else:
        print("Issue Connecting to LWLP")

    lwlp.i2c.unlock()

    if bmp and aht and lwlp:
        return bmp, aht, lwlp
    else:
        return "Error connecting to one or more of the sensors"


def receive_command(port):
    """
    Receives a command from the pc over the specified port. Command is sent bit by bit but will be of form <TYPE, VAL>

    :param port: the port the pc is writing to
    :return: the command in the form <type, val>
    """

    # Ensure Port Connection
    if port is None:
        return "Trouble connecting to port"

    # Receive command from PC
    command_received = False  # start with assuming no command has been received yet
    value = ""  # empty string to contain each value for the command
    # e.g. this lets me store '11' in the list rather than '1','1'
    while True:  # loop indefinitely
        byte_read = port.read(1)  # read 1 byte from computer

        if not command_received:  # if command hasn't yet been received
            if byte_read == b"<":  # start message
                command = []
                command_received = True
                continue  # do not record the "<"

        if command_received:  # if command has started to be recieved
            if byte_read == b">":  # if command ended break loop
                command.append(value)
                break
            elif byte_read == b",":  # skip if byte is ','
                command.append(value)
                value = ""
            else:
                value = value + byte_read.decode('utf-8')
    return command


def handle_command(command):
    """
    Interprets and acts on the command from receive_command().
    :param command: the command in form "type, val"
    :return: True when finished
    """

    if command[0] == 'D':  # command requesting data
        num_samples = int(command[1])
        send_data(data_port, num_samples)

    elif command[0] == 'P':  # command updating pwm value
        pwm_val = int(command[1])
        send_pwm(pwm_val)


def get_data(bmp, aht, lwlp):
    """
    Fetches data from each of the sensors and returns it in the form of a list
    :param bmp: bmp sensor object
    :param aht: aht sensor object
    :param lwlp: lwlp sensor object
    :return: list of data in form [bmp pressure, bmp temp, aht hum, aht temp, lwlp pressure, lwlp temp]
    """

    data = [bmp.pressure, bmp.temperature, aht.relative_humidity, aht.temperature]

    # get data from lwlp
    lwlp.i2c.try_lock()
    lwlp_data = lwlp.get_filter_data()

    data.append(lwlp_data[0])
    data.append(lwlp_data[1])
    lwlp.i2c.unlock()

    return data


def send_pwm(duty_cycle):
    """
    TODO
    :param pwm_val:
    :param fan_pin:
    :return:
    """

    pwm.duty_cycle = duty_cycle
    
    
def send_data(port, num_samples):
    """
    Sends data to PC
    :param port: port to send to. should be data port of pc
    :param num_samples: number of samples to send
    :return: True when finished
    """

    sample_count = 0
    while sample_count < num_samples:
        port.write(bytes("<", "ascii"))
        sample = get_data(bmp, aht, lwlp)

        for value in sample:
            port.write(bytes(f"{value}", "ascii"))
            if value != sample[-1]:  # put commas between all  but the final
                port.write(bytes(",", "ascii"))
        port.write(bytes(">", "ascii"))
        sample_count += 1
    return True



# connect to i2c
i2c = board.STEMMA_I2C()

# init pwm 
pwm = pwmio.PWMOut(board.D10)  # pwm sent to pin 10
pwm.duty_cycle = 0  # start at lowest duty cycle

# init sensors
sensors = init_sensors(i2c)
bmp = sensors[0]
aht = sensors[1]
lwlp = sensors[2]

# initializing ports
console_port = usb_cdc.console
data_port = usb_cdc.data

while True:
    command = receive_command(console_port)
    handle_command(command)
 