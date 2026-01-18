'''
(c) 2025 Politecnico di Milano

   ###       #####     #####      #######    #     # 
  #   #     #     #    #    #     #          ##    # 
 #     #    #          #    #     #          # #   # 
 #######     #####     #####      #####      #  #  # 
 #     #          #    #          #          #   # # 
 #     #    #     #    #          #          #    ## 
 #     #     #####     #          #######    #     # 

 #######    #     #    #######    #####        ###      #####        ###       #####     ####### 
    #       #     #    #          #    #      #   #     #    #        #       #     #       #
    #       #     #    #          #    #     #     #    #    #        #       #             #
    #       #######    #####      #####      #######    #####         #        #####        #
    #       #     #    #          #   #      #     #    #             #             #       #
    #       #     #    #          #    #     #     #    #             #       #     #       #
    #       #     #    #######    #     #    #     #    #            ###       #####        #

'''

import tkinter as tk
from tkinter import messagebox
import socket
import csv
import time
import threading
import sys
import os
from os.path import join, dirname, realpath
MyTMSi_dir = dirname(realpath(__file__)) # directory of this file
modules_dir = join(MyTMSi_dir, '..') # directory with all modules
sensor_dir = join(MyTMSi_dir,"_myTMSi", '../ASPEN_SENSORS_DATA') # directory with all sensors' data
sys.path.append(modules_dir)

# Server configuration
SERVER_IP = "192.168.4.1"  # IP address of the Access Point
SERVER_PORT = 80           # Server port
BUFFER_SIZE = 1024         # Maximum buffer size for receiving messages
TIMEOUT = 5                # Timeout for data reception

# Function to generate a timestamped filename
def get_timestamped_filename():
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    timestamp_with_ms = f"{timestamp}_{int(time.time() * 1000) % 1000}"
    filename = os.path.join(sensor_dir, f"data_exo_{timestamp_with_ms}.csv")

    return filename

# Function to receive data and save it in a CSV file
def receive_data(client_socket, writer):
    while True:
        try:
            data = client_socket.recv(BUFFER_SIZE).decode()
            if data:
                # Parsing and saving data
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

                # Save complete data
                if None not in [posIsDeg, forceIs, accX, accY, accZ, gyroX, gyroY, gyroZ]:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    timestamp_with_ms = f"{timestamp}.{int((time.time() % 1) * 1000)}"
                    writer.writerow([timestamp_with_ms, posIsDeg, forceIs, accX, accY, accZ, gyroX, gyroY, gyroZ])
            else:
                print("Error: No data received from the server.")
        except socket.timeout:
            continue

# Function to send commands (bits) to the server
def send_bit(bit, client_socket):
    try:
        message = f"bit={bit}"
        client_socket.sendall(message.encode())
        print(f"Sent: {message}")
        response = client_socket.recv(BUFFER_SIZE).decode()
        print(f"Server response: {response}")
        #messagebox.showinfo("Success", f"Command {bit} sent successfully!")
    except Exception as e:
        print(f"Error while sending bit: {e}")
        messagebox.showerror("Error", f"Error while sending bit: {e}")

# Main function with GUI
def main():
    # Create the CSV file
    CSV_FILENAME = get_timestamped_filename()

    with open(CSV_FILENAME, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "PosIsDeg", "ForceIs", "AccX", "AccY", "AccZ", "GyroX", "GyroY", "GyroZ"])

        # Create the socket to connect to the server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            try:
                print(f"Connecting to server {SERVER_IP}:{SERVER_PORT}...")
                client_socket.connect((SERVER_IP, SERVER_PORT))
                print("Connection established.")

                # Set the timeout
                client_socket.settimeout(TIMEOUT)

                # Thread to receive data
                thread_receive = threading.Thread(target=receive_data, args=(client_socket, writer))
                thread_receive.start()

                # Create the GUI
                root = tk.Tk()
                root.title("Therapist Mode")
                root.geometry("400x300")

                label = tk.Label(root, text="Choose the muscular command:", font=("Arial", 14, "bold"))
                label.pack(pady=10)

                # Button to send bit 0 (Extension)
                btn_extension = tk.Button(
                    root,
                    text="Extension (0)",
                    font=("Arial", 12),
                    bg="#39ff14",
                    fg="black",
                    command=lambda: send_bit("0", client_socket)
                )
                btn_extension.pack(pady=10)

                # Button to send bit 1 (Flexion)
                btn_flexion = tk.Button(
                    root,
                    text="Flexion (1)",
                    font=("Arial", 12),
                    bg="#ff7f50",
                    fg="black",
                    command=lambda: send_bit("1", client_socket)
                )
                btn_flexion.pack(pady=10)
                # Button to exit
                btn_exit = tk.Button(
                    root,
                    text="Exit",
                    font=("Arial", 12),
                    bg="black",
                    fg="white",
                    command=lambda: (client_socket.close(), root.destroy())
                )
                btn_exit.pack(pady=10)
                
                root.mainloop()

                # Wait for the receiving thread to finish
                thread_receive.join()



            except Exception as e:
                print(f"Error during communication: {e}")
                messagebox.showerror("Error", f"Error during communication: {e}")

if __name__ == "__main__":
    main()
