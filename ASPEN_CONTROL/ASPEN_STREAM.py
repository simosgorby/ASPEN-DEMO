'''
(c) 2025 Politecnico di Milano

   ###       #####     #####      #######    #     # 
  #   #     #     #    #    #     #          ##    # 
 #     #    #          #    #     #          # #   # 
 #######     #####     #####      #####      #  #  # 
 #     #          #    #          #          #   # # 
 #     #    #     #    #          #          #    ## 
 #     #     #####     #          #######    #     #
 
  #####     #######    #####      #######      ###      #     # 
 #     #       #       #    #     #           #   #     ##   ## 
 #             #       #    #     #          #     #    # # # # 
  #####        #       #####      #####      #######    #  #  # 
       #       #       #   #      #          #     #    #     # 
 #     #       #       #    #     #          #     #    #     # 
  #####        #       #     #    #######    #     #    #     # 

'''

import sys
import os
import csv
import time
import numpy as np
import tkinter as tk
from tkinter import filedialog
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
from scipy.signal import butter, sosfilt, sosfilt_zi
import pyttsx3
import playsound
import threading
import socket

movement_count = 0 # Movement counter

SERVER_IP = "192.168.4.1"  # IP address of the Access Point created by Arduino
SERVER_PORT = 80           # Server port
BUFFER_SIZE = 1024         # Maximum buffer size for receiving messages

def send_trigger(client_socket, bit):
    try:
            message = f"bit={bit}" # Sending the bit to Arduino's server
            client_socket.sendall(message.encode())
            print(f"Sent to Arduino: {message}")
            response = client_socket.recv(BUFFER_SIZE).decode()
            print(f"Response from the server: {response}")
    except Exception as e:
        print(f"ERROR while sending the trigger: {e}")

# Create a unique filename with the creation timestamp
timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
csv_filename = f"trigger_timestamps_{timestamp}.csv"
sensor_data_csv_filename = f"sensor_data_{timestamp}.csv"

# Write the header in the CSV file for the triggers
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Trigger Type', 'Timestamp'])

# Write the header in the CSV file for the sensor data
with open(sensor_data_csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Timestamp', 'PosIsDeg', 'ForceIs', 'accX', 'accY', 'accZ', 'gyroX', 'gyroY', 'gyroZ'])

def write_trigger_to_csv(trigger_count, movement_count):
    # Get the current timestamp with millisecond precision
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    timestamp_with_ms = f"{timestamp}.{int((time.time() % 1) * 1000)}"  # Add milliseconds

    # Write the movement, trigger, and timestamp to the CSV
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([movement_count, trigger_count, timestamp_with_ms])

def add_header_as_first_row(filename, header):
    # Check if the file exists
    if os.path.exists(filename):
        # Create a temporary file
        temp_filename = f"temp_{filename}"
        
        with open(filename, mode='r', newline='') as file:
            reader = csv.reader(file)
            # Read all existing rows
            data = list(reader)

        # Write the header to the temporary file and then the existing data
        with open(temp_filename, mode='w', newline='') as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow(header)  # Add the header
            writer.writerows(data)  # Add the already existing data
        
        # Replace the original file with the temporary file
        os.replace(temp_filename, filename)

def receive_data(client_socket, writer):
    try:
        while True:
            try:
                data = client_socket.recv(BUFFER_SIZE).decode()
                if data:
                    data_parts = data.split(',')
                    posIsDeg = accX = accY = accZ = forceIs = gyroX = gyroY = gyroZ = None
                    for part in data_parts:
                        try:
                            key, value = part.split(':')
                            key = key.strip()
                            value = value.strip()
                            if key == "PosIsDeg":
                                posIsDeg = float(value)
                            elif key == "ForceIs":
                                forceIs = float(value)
                            elif key == "accX":
                                accX = float(value)
                            elif key == "accY":
                                accY = float(value)
                            elif key == "accZ":
                                accZ = float(value)
                            elif key == "gyroX":
                                gyroX = float(value)
                            elif key == "gyroY":
                                gyroY = float(value)
                            elif key == "gyroZ":
                                gyroZ = float(value)
                        except ValueError:
                            continue

                    if None not in [posIsDeg, forceIs, accX, accY, accZ, gyroX, gyroY, gyroZ]:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        timestamp_with_ms = f"{timestamp}.{int((time.time() % 1) * 1000)}"
                        writer.writerow([timestamp_with_ms, posIsDeg, forceIs, accX, accY, accZ, gyroX, gyroY, gyroZ])
                else:
                    print("ERROR: no data received from server..")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"ERROR in data reception: {e}")
                break
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Closing connection...")
    finally:
        client_socket.close()
        print("Connection closed.")

# Initialize the speech synthesis engine
tts_engine = pyttsx3.init()

# List of available voices
tts_engine.setProperty('voice', "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_EN-US_ZIRA_11.0")
tts_engine.say("Hi there! Let's get started and make this session amazing!")
tts_engine.runAndWait()

def play_audio_feedback(message, sound_file=None):
    if sound_file:
        try:
            playsound.playsound(sound_file, block=False)
        except Exception as e:
            print(f"Error during sound playback: {e}")
    tts_engine.say(message)
    tts_engine.runAndWait()

##. Function to create filters
def create_filters(Fs_EMG):
    fcutlow = 10  # Low cutoff frequency in Hz
    fcuthigh = 100  # High cutoff frequency in Hz
    sos_bandpass = butter(5, [fcutlow, fcuthigh], btype='bandpass', fs=Fs_EMG, output='sos')
    sos_lowpass = butter(5, 5, btype='low', fs=Fs_EMG, output='sos')
    bandpass_state = sosfilt_zi(sos_bandpass) * 0
    lowpass_state = sosfilt_zi(sos_lowpass) * 0
    return sos_bandpass, sos_lowpass, bandpass_state, lowpass_state

# Function to process data one by one
def process_batch(batch, state, filters):
    sos_bandpass, sos_lowpass = filters
    filtered_batch, state['bandpass'] = sosfilt(sos_bandpass, batch, zi=state['bandpass'])
    rectified_batch = np.abs(filtered_batch)
    envelope_batch, state['lowpass'] = sosfilt(sos_lowpass, rectified_batch, zi=state['lowpass'])
    return envelope_batch

###################### 1.FILE SELECTION
from os.path import join, dirname, realpath
MyTMSi_dir = dirname(realpath(__file__)) # directory of this file
modules_dir = join(MyTMSi_dir, '..') # directory with all modules
measurements_dir = join(MyTMSi_dir,"_myTMSi", '../ASPEN_EMG_MEASUREMENTS') # directory with all measurements
sys.path.append(modules_dir)

from TMSiFileFormats.file_readers import Poly5Reader, Xdf_Reader

# CSV Reader Class
class CSVReader:
    def __init__(self, filename=None):
        if filename is None:
            root = tk.Tk()
            filename = filedialog.askopenfilename(title='Select csv-file', filetypes=(('csv-files', '*.csv'), ('All files', '*.*')))
            root.withdraw()
        self.filename = filename
        print('Reading file ', filename)
        self._readFile(filename)

    def _readFile(self, filename):
        with open(filename, 'r', newline='', encoding='utf16') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            samples = []
            for i, row in enumerate(reader):
                if i == 0:
                    self.ch_names = row[:-1]
                    self.num_channels = len(self.ch_names)
                    continue
                if i == 1:
                    self.sample_rate = float(row[-1].replace(',', '.'))
                samples.append([float(val.replace(',', '.')) for val in row[:-1]])
        self.samples = np.array(samples)
        self.num_samples = i

# Supported formats dictionary
format_dict = {
    'poly5': {'reader': Poly5Reader, 'samples': lambda data: data.samples.T, 'sample_rate': lambda data: data.sample_rate},
    'xdf': {'reader': Xdf_Reader, 'samples': lambda data: data.data[0].get_data().T, 'sample_rate': lambda data: data.data[0].info['sfreq']},
    'csv': {'reader': CSVReader, 'samples': lambda data: data.samples, 'sample_rate': lambda data: data.sample_rate}
}

# File selection and data loading
root = tk.Tk()
file_path = filedialog.askopenfilename(filetypes=[("Supported files", "*.poly5 *.xdf *.csv")])
root.withdraw()
file_extension = os.path.splitext(file_path)[-1].lower().lstrip('.')
if file_extension in format_dict:
    Reader = format_dict[file_extension]['reader']
    data = Reader(filename=file_path)
    EMG_signal = format_dict[file_extension]['samples'](data)
    Fs_EMG = format_dict[file_extension]['sample_rate'](data)
else:
    raise NotImplementedError(f"File format '{file_extension}' not supported. Supported formats are {format_dict.keys()}.")

###################### 2.CHANNEL SELECTION
EMG_signal = EMG_signal[:, 0]

print(f"File read: {file_path}")
print(f"Number of samples: {len(EMG_signal)}")
print(f"Sampling frequency: {Fs_EMG} Hz")

###################### 3.PROCESSING
if __name__ == "__main__":

    while True:
        try:
            th_value = float(input("Enter the value of threshold th1: ")) # Threshold from ASPEN_CALIBRATION
            break
        except ValueError:
            print("ERROR: invalid input, insert a number.")

    # Double Thresholds
    th2 = 0.2 # Time threshold [ms]
    th_time = int(th2 * Fs_EMG) # Number of samples for the time treshold selected
    time_saved = []
    indices = [] # Idx that tracks starting and ending movement samples
    trigger = 0 # Initialize trigger flag to 0

    ##. Continuous updating plot parameters
    vis_time = 3 # [] Time window
    buffer_size = int(Fs_EMG*vis_time) # Samples time window
    x_data = np.linspace(0, vis_time, buffer_size) 
    envelope_data = np.zeros(buffer_size) # initialize envelope vector for update plot

    envelope_full = [] # Vector to visualize full plot

    update_interval = int(Fs_EMG*0.005) 
    last_update = 0

    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Movement Number', 'Trigger Type', 'Timestamp'])

    with open(sensor_data_csv_filename, mode='w', newline='') as sensor_file:
        sensor_writer = csv.writer(sensor_file)

        # Filters creation
        sos_bandpass, sos_lowpass, bandpass_state, lowpass_state = create_filters(Fs_EMG)
        state = {'bandpass': bandpass_state, 'lowpass': lowpass_state}
        filters = (sos_bandpass, sos_lowpass)

        app = QtGui.QApplication([])
        win = pg.GraphicsLayoutWidget(show=True, title="EMG Signal Processing")
        win.resize(800, 600)
        plot = win.addPlot(title="EMG Envelope")
        plot.setLabels(left="Amplitude [mV]", bottom="Time [s]")
        plot.showGrid(x=True, y=True)
        curve = plot.plot(pen=pg.mkPen('r', width=2))

        try:
            print(f"Connecting to server {SERVER_IP}:{SERVER_PORT}...")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_IP, SERVER_PORT))
            print("Connection established.")

            sensor_thread = threading.Thread(target=receive_data, args=(client_socket, sensor_writer))
            sensor_thread.daemon = True
            sensor_thread.start()

            ##. Filter warm-up
            for _ in range(Fs_EMG):
                batch = EMG_signal[_:_ + 1]
                _ = process_batch(batch, state, filters)

            for i in range(len(EMG_signal)):
                batch = EMG_signal[i:i + 1]
                if len(batch) == 0:
                    break

                envelope_batch = process_batch(batch, state, filters)
                envelope_full.extend(envelope_batch)

                envelope_data = np.roll(envelope_data, -1)
                envelope_data[-1] = envelope_batch

                if i - last_update >= update_interval:
                    current_time = i / Fs_EMG
                    if current_time >= vis_time:
                        x_data = np.linspace(current_time - vis_time, current_time, buffer_size)
                    curve.setData(x_data, envelope_data)
                    app.processEvents()
                    last_update = i

                ##. Trigger detection code
                if envelope_batch > th_value and trigger == 0:
                    time_saved.append(i)
                    if len(time_saved) >= th_time:
                        trigger = 1
                        print(f"Threshold reached at sample {i}.")
                        indices.append(i)
                        time_saved = []
                        movement_count += 1  # Increment the movement number
                        write_trigger_to_csv(trigger, movement_count)  # Write the trigger and movement number to the CSV
                        send_trigger(client_socket, "1")  # Communication with Arduino for starting the movement


                elif envelope_batch < th_value and trigger == 1:
                    time_saved.append(i)
                    if len(time_saved) >= 5*th_time: 
                        trigger = 0
                        print("End of movement.")
                        indices.append(i)
                        time_saved = []
                        write_trigger_to_csv(trigger, movement_count)  # Write the trigger and movement number to the CSV
                        send_trigger(client_socket, "0")  # Communication with Arduino for ending the movement

                if i % (Fs_EMG/2) == 0:  
                    print(f"Processing sample {i/Fs_EMG}/{(len(EMG_signal))/Fs_EMG}")

        finally:
            # Calculation of repetitions
            num_repetitions = len([idx for idx in range(len(indices)) if idx % 2 == 0])
            print(f"Total number of repetitions detected: {num_repetitions}")
        
            # Final report through speech synthesis
            summary_message = f"Session complete. You performed {num_repetitions} repetitions of the gesture. Well done!"
            play_audio_feedback(summary_message)

            # Closing comunication with Arduino
            client_socket.close()  # Closing the socket at the end
            print("Connection with Arduino closed.")

        # Header of the CSV file you want to add
        header_sensor_data = ['Timestamp', 'PosIsDeg', 'ForceIs', 'accX', 'accY', 'accZ', 'gyroX', 'gyroY', 'gyroZ']

        ##. Final plot
        win_final = pg.GraphicsLayoutWidget(show=True, title="EMG Signal Final Plot")
        win_final.resize(800, 600)
        plot_final = win_final.addPlot(title="Final EMG Envelope with trigger")
        time_axis = np.linspace(0, len(envelope_full) / Fs_EMG, len(envelope_full))
        plot_final.plot(time_axis, envelope_full, pen=pg.mkPen('b', width=2))
        plot_final.setLabels(left = "Amplitude [mV]", bottom = "Time [s]")

        for idx, marker in enumerate(indices):
            if idx % 2 == 0:
                plot_final.addLine(x=marker / Fs_EMG, pen=pg.mkPen('g', style=pg.QtCore.Qt.SolidLine))
            else:
                plot_final.addLine(x=marker / Fs_EMG, pen=pg.mkPen('r', style=pg.QtCore.Qt.DashLine))
        
        QtGui.QApplication.exec_()
        print("Stop, processing is completed")