'''
(c) 2025 Politecnico di Milano

   ###       #####     #####      #######    #     # 
  #   #     #     #    #    #     #          ##    # 
 #     #    #          #    #     #          # #   # 
 #######     #####     #####      #####      #  #  # 
 #     #          #    #          #          #   # # 
 #     #    #     #    #          #          #    ## 
 #     #     #####     #          #######    #     #
 
 #######    #     #    #####       #####     #     #    #######    #####   
 #          ##   ##    #    #     #     #    #     #    #          #    #
 #          # # # #    #    #     #     #    #     #    #          #    #
 #####      #  #  #    #####      #     #    #  #  #    #####      #####
 #          #     #    #          #     #    #  #  #    #          #   #
 #          #     #    #          #     #    #  #  #    #          #    #
 #######    #     #    #           #####      ## ##     #######    #     #

 '''

#  System libraries
import sys
from os.path import join, dirname, realpath
MyTMSi_dir = dirname(realpath(__file__)) # directory of this file
modules_dir = join(MyTMSi_dir, '..') # directory with all modules
measurements_dir = join(MyTMSi_dir,"_myTMSi", '../ASPEN_EMG_MEASUREMENTS') # directory with all measurements
sensor_dir = join(MyTMSi_dir,"_myTMSi", '../ASPEN_SENSORS_DATA') # directory with all sensors' data
sys.path.append(modules_dir)
# Plot libraries
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# TMSi libraries
from TMSiSDK.device import ChannelType
from TMSiSDK.tmsi_sdk import TMSiSDK, DeviceType, DeviceInterfaceType
from TMSiSDK.tmsi_errors.error import TMSiError
from TMSiSDK.device.devices.saga.saga_API_enums import SagaBaseSampleRate
from TMSiSDK.device.devices.saga.saga_API import TMSiGetDeviceData
from TMSiSDK.device.tmsi_device_enums import MeasurementType
from TMSiFileFormats.file_writer import FileWriter, FileFormat # Saving filtered datas
# Real time filter libraries
from scipy.signal import butter, sosfilt, sosfilt_zi
from TMSiProcessing.filters.real_time_filter import RealTimeFilter
# Time saving libraries for validation
import pyttsx3
import playsound
import csv
import time
import threading
import os

movement_count = 0 # Movement counter

# Creation pf a CSV file with starting timestamp 
timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
csv_filename = f"trigger_timestamps_{timestamp}.csv"
sensor_data_csv_filename = f"sensor_data_{timestamp}.csv"
#csv_filename = os.path.join(sensor_dir, f"trigger_timestamps_{timestamp}.csv")
#sensor_data_csv_filename = os.path.join(sensor_dir, f"sensor_data_{timestamp}.csv")

# Writing header for CSV file for trigger counting
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Trigger Type', 'Timestamp'])

# Writing header for CSV file for sensor's data
with open(sensor_data_csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Timestamp', 'PosIsDeg', 'ForceIs', 'accX', 'accY', 'accZ', 'gyroX', 'gyroY', 'gyroZ'])

def write_trigger_to_csv(trigger_count, movement_count):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S") # Getting current timestamp in [ms]
    timestamp_with_ms = f"{timestamp}.{int((time.time() % 1) * 1000)}"

    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([movement_count, trigger_count, timestamp_with_ms])

def add_header_as_first_row(filename, header):
    if os.path.exists(filename):
        temp_filename = f"temp_{filename}" # Creating a temporary file
        with open(filename, mode='r', newline='') as file:
            reader = csv.reader(file)
            data = list(reader)
        # Writing header and existing data
        with open(temp_filename, mode='w', newline='') as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow(header)
            writer.writerows(data)
        os.replace(temp_filename, filename) # Changing original file with temporary one

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
tts_engine.setProperty('voice', "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_EN-US_ZIRA_11.0") # List of available voices
tts_engine.say("Hi there! Let's get started and make this session amazing!")
tts_engine.runAndWait()

def play_audio_feedback(message, sound_file=None):
    if sound_file:
        try:
            playsound.playsound(sound_file, block=False)
        except Exception as e:
            print(f"ERROR during sound playblack: {e}")
    tts_engine.say(message)
    tts_engine.runAndWait()

##. Function to create filters
def create_filters(Fs_EMG):
    fcutlow = 10  # Low cutoff frequency in Hz
    fcuthigh = 100  # High cutoff frequency in Hz
    sos_bandpass = butter(5, [fcutlow, fcuthigh], btype='bandpass', fs=Fs_EMG, output='sos')
    sos_lowpass = butter(5, 5, btype='low', fs=Fs_EMG, output='sos')
    bandpass_state = sosfilt_zi(sos_bandpass) * 0  # Initial state of filter
    lowpass_state = sosfilt_zi(sos_lowpass) * 0
    return sos_bandpass, sos_lowpass, bandpass_state, lowpass_state

def process_batch(batch, state, filters):
    sos_bandpass, sos_lowpass = filters
    filtered_batch, state['bandpass'] = sosfilt(sos_bandpass, batch, zi=state['bandpass'])
    rectified_batch = np.abs(filtered_batch)
    envelope_batch, state['lowpass'] = sosfilt(sos_lowpass, rectified_batch, zi=state['lowpass'])
    return envelope_batch

##. Wifi parameters
import socket

SERVER_IP = "192.168.4.1"  # IP address of the Access Point created by Arduino
SERVER_PORT = 80           # Server port
BUFFER_SIZE = 1024         # Maximum buffer size for receiving messages

##. Trigger to Arduino
def send_trigger(client_socket, bit):
        try:    
                message = f"bit={bit}" # Sending the bit to Arduino's server
                client_socket.sendall(message.encode())
                print(f"Sent to Arduino: {message}")
                response = client_socket.recv(BUFFER_SIZE).decode()
                print(f"Response from the server: {response}")
        except Exception as e:
            print(f"ERROR while sending the trigger: {e}")

##. Connection to TMSi
try:
    # Initialize TMSiSDK and discover devices
    sdk = TMSiSDK()
    print('Looking for TMSi devices...')
    sdk.discover(dev_type=DeviceType.saga, 
                 dr_interface=DeviceInterfaceType.docked,ds_interface=DeviceInterfaceType.usb)
    discoveryList = sdk.get_device_list(DeviceType.saga)

    if len(discoveryList) > 0:
        print('Opening SAGA device...')
        # Open the first SAGA device found
        for i, _ in enumerate(discoveryList):
            dev = discoveryList[i]
            if dev.get_dr_interface() == DeviceInterfaceType.docked:
                dev.open()
                break
        
        print('Configuring channels...')

        dev.set_device_sampling_config(base_sample_rate = SagaBaseSampleRate.Decimal, channel_type = ChannelType.BIP,channel_divider = 8 )
        dev.set_device_sampling_config(channel_type = ChannelType.AUX, channel_divider = 8)

        # Set the channels to acquire
        AUX_list = []   # [0, 1, 2]
        BIP_list = [0, 1]  # [0, 1, 2]

        ch_list = dev.get_device_channels()
        AUX_count, BIP_count = 0, 0
        enable_channels = []

        for idx, ch in enumerate(ch_list):
            if ch.get_channel_type() == ChannelType.AUX and AUX_count in AUX_list:
                enable_channels.append(idx)
                AUX_count += 1
            elif ch.get_channel_type() == ChannelType.BIP and BIP_count in BIP_list:
                enable_channels.append(idx)
                BIP_count += 1

        dev.set_device_active_channels(enable_channels, True)

        ##. Start sampling
        dev.start_measurement(MeasurementType.SAGA_SIGNAL)
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Movement Number', 'Trigger Type', 'Timestamp'])
    with open(sensor_data_csv_filename, mode='w', newline='') as sensor_file:
        sensor_writer = csv.writer(sensor_file)

        ##. EMG vector for processing initialization
        emg_filtered_1 = []  
        emg_filtered_2 = []
        emg_raw_1 = []
        emg_raw_2 = []
        ##. Processing data
        while True:
            try:
                th_value_1 = float(input("Enter the value of threshold for muscle contraction (th_value_1): ")) # Threshold from ASPEN_CALIBRATION
                th_value_2 = float(input("Enter the value of threshold for muscle extension (th_value_2): ")) # Threshold from ASPEN_CALIBRATION
                break
            except ValueError:
                print("ERROR: invalid input, insert a number.")

        Fs_EMG = 500 # Sampling frequency [Hz]
        index_start = [] # idx tracking samples that start the muscle contraction
        index_end = [] # idx tracking samples that start the muscle extension
        count = 0 
        trigger = 0 # initializing trigger
        buffer_size = 100 # numbers of samples analyzed each time
        last_trigger_time = 0 # saves the time of the last trigger
        min_interval = 5 # [s] time interval accounting for exoskeleton's rise
        max_interval = 30 # [s] max contraction time for safety reason
 
        ##. Connection to Arduino
        print(f"Connecting to server {SERVER_IP}:{SERVER_PORT}...")
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_IP, SERVER_PORT))
        print("Connection is achieved!")

        sensor_thread = threading.Thread(target=receive_data, args=(client_socket, sensor_writer))
        sensor_thread.daemon = True
        sensor_thread.start()

        print("Reading data in real-time. Press Ctrl+C to stop.")
        
        ##. Create the real time filter
        filter = RealTimeFilter(dev)
        filter.start()

        ##. Filters creation
        sos_bandpass, sos_lowpass, bandpass_state, lowpass_state = create_filters(Fs_EMG)
        state_1 = {'bandpass': bandpass_state, 'lowpass': lowpass_state}
        filters_1 = (sos_bandpass, sos_lowpass)
        state_2 = {'bandpass': bandpass_state, 'lowpass': lowpass_state}
        filters_2 = (sos_bandpass, sos_lowpass)

        # Initialise a file-writer class (XDF-format) and state its file path
        file_writer = FileWriter(FileFormat.poly5, join(measurements_dir,"REAL_TIME_EMG.poly5"))
        
        file_writer.open(dev) # Define the handle to the device

        while filter.filter_thread.sampling:
            if not filter.filter_thread.q_filtered_sample_sets.empty():

                data_1 = filter.filter_thread.q_filtered_sample_sets.get()[0] # WARNING: select channel for muscle contraction
                data_2 = filter.filter_thread.q_filtered_sample_sets.get()[1] # WARNING: select channel for muscle extension
                emg_raw_1.extend(data_1)
                emg_raw_2.extend(data_2)

                ##. Filter warm-up
                if len(emg_raw_1) < Fs_EMG:
                    batch_1 = data_1
                    _ = process_batch(batch_1, state_1, filters_1)
                    batch_2 = data_2
                    _ = process_batch(batch_2, state_2, filters_2)

                else:
                    batch_1 = data_1
                    envelope_batch_1 = process_batch(batch_1, state_1, filters_1)
                    emg_filtered_1.extend(envelope_batch_1)

                    batch_2 = data_2
                    envelope_batch_2 = process_batch(batch_2, state_2, filters_2)
                    emg_filtered_2.extend(envelope_batch_2)

                    # Compare last buffer of acquired samples for both EMG signals
                    last_values_1 = emg_filtered_1[-buffer_size:] 
                    last_values_2 = emg_filtered_2[-buffer_size:]

                    ##. Trigger detection code
                    current_time = time.time()
                    if all(value_1 > th_value_1 for value_1 in last_values_1) and trigger == 0:
                        
                        if current_time - last_trigger_time >= min_interval: # compare time of trigger to avoid multiple trigger during exo's movement
                            count = count + 1
                            if count == 1: # Taking only the 1st iteration in which the double treshold condition is overcome
                                trigger = 1
                                last_trigger_time = current_time
                                movement_count += 1  # Increment the movement number
                                write_trigger_to_csv(trigger, movement_count)  # Write the trigger and movement number to the CSV
                                index_start.append((len(emg_filtered_1)-buffer_size))
                                print(f" Threshold is overcome at sample: {(len(emg_filtered_1)-buffer_size)}.")
                                send_trigger(client_socket, "1") # Communication with Arduino for starting the movement
                                
                    elif all(value_2 > th_value_2 for value_2 in last_values_2) and trigger == 1:
                        
                        if current_time - last_trigger_time >= min_interval:
                            trigger = 0
                            last_trigger_time = current_time
                            write_trigger_to_csv(trigger, movement_count) # Write the trigger and movement number to the CSV
                            index_end.append((len(emg_filtered_2)-buffer_size))
                            print("Starting muscle extention.")
                            send_trigger(client_socket, "0") # Communication with Arduino for ending the movement
                            count = 0
                        
                    elif trigger == 1 and current_time - last_trigger_time >= max_interval:
                        trigger = 0
                        last_trigger_time = current_time
                        write_trigger_to_csv(trigger, movement_count) # Write the trigger and movement number to the CSV
                        index_end.append((len(emg_filtered_2)-buffer_size))
                        print("Starting muscle extention due to inactivity.")
                        send_trigger(client_socket, "0") # Communication with Arduino for ending the movement
                        count = 0
except KeyboardInterrupt:
    print(" Stopping..")

finally:
    filter.stop()
    # Closing comunication with Arduino
    file_writer.close()
    client_socket.close()
    print("Connection with Arduino closed")

    # Calculation of repetitions performed
    num_repetitions = len([idx for idx in range(len(index_start + index_end)) if idx % 2 == 0])

    # Final report through speech synthesis
    summary_message = f"Session complete. You performed {num_repetitions} repetitions of the gesture. Well done!"
    play_audio_feedback(summary_message)
    print(f"Total number of repetitions detected: {num_repetitions}")

    # Header of the CSV file you want to add
    header_sensor_data = ['Timestamp', 'PosIsDeg', 'ForceIs', 'accX', 'accY', 'accZ', 'gyroX', 'gyroY', 'gyroZ']

    # At the end of the main, add the header to the files just created
    add_header_as_first_row(sensor_data_csv_filename, header_sensor_data)  

##.Final plot
# File selection and data loading
import tkinter as tk
from tkinter import filedialog
from TMSiFileFormats.file_readers import Poly5Reader

# Supported formats dictionary
format_dict = {
    'poly5': {'reader': Poly5Reader, 'samples': lambda data: data.samples.T, 'sample_rate': lambda data: data.sample_rate},
}
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

##. Filters creation for full envelope
sos_bandpass, sos_lowpass, bandpass_state, lowpass_state = create_filters(Fs_EMG)
state_full_1 = {'bandpass': bandpass_state, 'lowpass': lowpass_state}
filters_full_1 = (sos_bandpass, sos_lowpass)
state_full_2 = {'bandpass': bandpass_state, 'lowpass': lowpass_state}
filters_full_2 = (sos_bandpass, sos_lowpass)

##. Final plot with filtered EMG
for _ in range(Fs_EMG):
    data1 = EMG_signal[_:_ + 1,0]
    data2 = EMG_signal[_:_ + 1,1]
    _ = process_batch(data1, state_full_1, filters_full_1)
    _ = process_batch(data2, state_full_2, filters_full_2)

emg_filt_1 = process_batch(EMG_signal[:,0], state_full_1, filters_full_1)
emg_filt_2 = process_batch(EMG_signal[:,1], state_full_2, filters_full_2)

time_1 = np.arange(len(emg_filt_1)) / Fs_EMG
time_2 = np.arange(len(emg_filt_2)) / Fs_EMG

# Subplot creation
fig, axs = plt.subplots(2, 1, figsize=(10, 8))

axs[0].plot(time_1, emg_filt_1, label = "Filtered EMG 1")
axs[0].set_title("Filtered EMG - Muscle contraction")
axs[0].set_xlabel("Time [s]")
axs[0].set_ylabel("Amplitude [mV]")
axs[0].grid()
axs[0].legend()

axs[1].plot(time_2, emg_filt_2, label = " Filtered EMG 2", color = "orange")
axs[1].set_title("Filtered EMG - Muscle extension")
axs[1].set_xlabel("Time [s]")
axs[1].set_ylabel("Amplitude [mV]")
axs[1].grid()
axs[1].legend()
plt.tight_layout()

plt.show()
exit()