"""
This module contains functions to control communication between an Adafruit feather and a host pc

...
Functions:

    send_pwm(console_port, pwm_val)
        Sends a command to the feather telling it to send a pwm signal to the fan

    request_data(console_port, data_port, num_samples)
        Sends a command to the feather requesting lists containing all relevant sensor data

"""


def send_pwm(console_port, pwm_val):
    """
    Sends a command to the feather telling it to send a pwm signal to the fan

    ...
    The command is in bytes and is of the form <P, VALUE>, where P tells the feather what type of command it is
        receiving and VALUE is the information associated with that command

    :param console_port: the port of the pc to send the command. Should be a serial port object using pyserial
    :param pwm_val: a value between 0 and 65535 (16-bit resolution) corresponding to the duty cycle of the fan
    :return: None
    """
    console_port.write(bytes(f"<P,{pwm_val}>", "ascii"))  # write a command to the feather updating the fan duty cycle
    # print("Sending pwm value", pwm_val)


def request_data(console_port, data_port, num_samples):
    """
    Sends a command to the feather requesting 'num_samples' lists containing all relevant sensor data.

    ...
    In practice, it is ideal to only request 1 list and call request_data in the main program repeatedly as many times
        as needed. This makes timing more controlled.

    :param console_port: the port of the pc to send the command. Should be a serial port object using pyserial
    :param data_port: the port of the pc to receive the data over. Should be a serial port object using pyserial
    :param num_samples: the number of lists requested
    :return: data: a list containing 'num_samples' lists in the form:
                    [list, list, list, list ... ] where each list is of the form:
                        [bmp pressure, bmp temp, aht hum, aht temp, lwlp pressure, lwlp temp]
    """

    console_port.write(bytes(f"<D,{num_samples}>", "ascii"))  # write a command to the feather requesting data
    data = []  # list of lists that will contain all requested data
    value = ""  # str to temporarily contain each individual datapoint

    while len(data) < num_samples:  # loop until received requested number of samples
        sample = []  # reset sample container for each new sample
        data_port.read_until(b"<")  # wait until start of message
        byte_read = data_port.read_until(b">")  # read until end of message

        for byte in byte_read:  # iterate through all collected bytes
            if chr(byte) == ",":  # if byte is a comma, append prev value and reset placeholder
                sample.append(value)
                value = ""
            elif chr(byte) == ">":  # if byte is a '>', then message has ended. append prev value and end sample
                sample.append(value)
                value = ""
                continue
            else:
                value += chr(byte)

        data.append(sample)  # add each sensor readings sample to the complete list

    return data
