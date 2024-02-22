# WindTunnel

This repository contains all the neccesary files to run the GUI and testing system on any machine.
All contained within the repo are all backup files for setting up and running the Adafruit Feather.

The directory 'python_files" contains the .py scripts to run on the PC. The main python script is 
TunnelGUI.py, this script sets up the user interface to allow for control of the wind tunnel. 
feathercom.py sets up a communication link between the TunnelGUI.py script and the Adafruit Feather.

All code was written for Python version 3.8.10. But any python version should suffice.
Neccessary python libraries are listed in requirements.txt and can be all pip installed at once by 
typing "pip install -r requirements.txt" when located inside its host directory.
