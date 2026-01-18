'''
(c) 2025 Politecnico di Milano

   ###       #####     #####      #######    #     # 
  #   #     #     #    #    #     #          ##    # 
 #     #    #          #    #     #          # #   # 
 #######     #####     #####      #####      #  #  # 
 #     #          #    #          #          #   # # 
 #     #    #     #    #          #          #    ## 
 #     #     #####     #          #######    #     # 

'''

import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import pyttsx3
import threading
import time

# Get the directory of the current script
base_dir = os.path.dirname(__file__)
print(base_dir)
# Define the command to run the script !!! CHANGE to the location of python.exe in your tmsi_venv !!!
python_exe = r"C:\Users\robdi\OneDrive\Desktop\Collaborative_Robotics\Project\EMG\tmsi_venv\Scripts\python.exe"
# "C:\Users\simonesgorbati\tmsi_venv\Scripts\python.exe"

# Define relative paths
# !!! Modes with (tbd) are considered as a further improvement to the project (to be implemented in the future) !!!
scripts = {
    "RECORD": os.path.join(base_dir, "ASPEN_RECORD.py"), # RECORD EMG
    "CALIBRATE": os.path.join(base_dir, "ASPEN_CALIBRATE.py"), # CALIBRATE EMG
    "THERAPIST": os.path.join(base_dir, "ASPEN_THERAPIST.py"), # PASSIVE MODE (WITH THERAPIST)
    "STREAM": os.path.join(base_dir, "ASPEN_STREAM.py"), # PASSIVE MODE (WITHOUT THERAPIST)
    "EMPOWER": os.path.join(base_dir, "ASPEN_EMPOWER.py"), # PASSIVE MODE (EMG-TRIGGERED) MODE 
    "PROGRESS": os.path.join(base_dir, "ASPEN_PROGRESS.py"), # ACTIVE MODE !!! BETA VERSION (tbd)
    "CHALLENGE": os.path.join(base_dir, "ASPEN_CHALLENGE.py") # RESISTIVE MODE !!! BETA VERSION (tbd)
}

# Store the process object
current_process = None

# Function to execute a selected script
def run_script(script_name):
    global current_process
    try:
        # If another process is running, stop it first
        if current_process and current_process.poll() is None:
            stop_script()

        # Start the new process
        current_process = subprocess.Popen([python_exe, scripts[script_name]])
        messagebox.showinfo("Success", f"{script_name} mode is now running!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to run {script_name}:\n{e}")

# Function to stop the currently running script
def stop_script():
    global current_process
    if current_process and current_process.poll() is None:  # Check if a process is running
        current_process.terminate()  # Terminate the process
        current_process.wait()  # Wait for it to stop
    else:
        messagebox.showwarning("No Process", "No process is currently running.")

    # Immediately run ASPEN_STOP.py
    try:
        wifi_bit_script = os.path.join(base_dir, "ASPEN_STOP.py")
        subprocess.Popen([python_exe, wifi_bit_script])  # Run the script
    except Exception as e:
        messagebox.showerror("Error", f"Error returning to safety position:\n{e}")

# Timer thread to remind recalibration
def calibration_timer(interval_minutes):
    while True:
        # Show recalibration prompt
        response = messagebox.askokcancel(
            "Calibration Needed",
            "It is time to calibrate the device. Please perform the calibration and press OK to continue."
        )
        if not response:  # If the user cancels, stop further reminders
            break
        time.sleep(interval_minutes * 60)  # Wait for the specified time before showing the next reminder

# Function to show the initial recalibration message
def initial_recalibration_message(interval_minutes):
    # Show the initial message immediately
    calibration_timer(interval_minutes)

tts_engine = pyttsx3.init()

# Create the main application window
root = tk.Tk()
root.title("Welcome to ASPEN! What would you like to do?")
root.geometry("500x550")  # Set window size

# Setup section
setup_label = tk.Label(root, text="Set up the system:", font=("Arial", 16, "bold"), fg="black")
setup_label.pack(pady=10)

# Add RECORD and CALIBRATE buttons
setup_buttons = {
    "RECORD": {"bg": "#28a745", "fg": "black"},
    "CALIBRATE": {"bg": "#ffc107", "fg": "black"},
}

for script_name, style in setup_buttons.items():
    button = tk.Button(
        root,
        text=script_name,
        font=("Arial", 12),
        bg=style["bg"],
        fg=style["fg"],
        command=lambda name=script_name: run_script(name)
    )
    button.pack(pady=5)

# Choose a mode section
mode_label = tk.Label(root, text="Choose a mode:", font=("Arial", 16, "bold"), fg="black")
mode_label.pack(pady=20)

# Add remaining buttons
mode_buttons = {
    "THERAPIST": {"bg": "#007bff", "fg": "black"},
    "STREAM": {"bg": "#17a2b8", "fg": "black"},
    "EMPOWER": {"bg": "#fd7e14", "fg": "black"},
    "PROGRESS": {"bg": "#dc3545", "fg": "black"},
    "CHALLENGE": {"bg": "#992331", "fg": "black"}
}

for script_name, style in mode_buttons.items():
    button = tk.Button(
        root,
        text=script_name,
        font=("Arial", 12),
        bg=style["bg"],
        fg=style["fg"],
        command=lambda name=script_name: run_script(name)
    )
    button.pack(pady=5)

# Add a button to stop the current script
stop_button = tk.Button(
    root,
    text="STOP",
    font=("Arial", 12, "bold"),
    bg="#fa021f",  # Style for STOP button
    fg="black",
    command=stop_script
)
stop_button.pack(pady=10)

# Add an "Exit" button to close the application
exit_button = tk.Button(
    root,
    text="Exit",
    font=("Arial", 12, "bold"),
    command=root.destroy,
    bg="#343a40",
    fg="white"
)
exit_button.pack(pady=10)

# Welcome message
tts_engine.setProperty('voice', "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_EN-US_ZIRA_11.0")
tts_engine.say("Hello there! What would you like to do today? Select a mode!")
tts_engine.runAndWait()

# Start the recalibration timer in a separate thread
calibration_interval = 30  # Recalibration interval in minutes
timer_thread = threading.Thread(target=initial_recalibration_message, args=(calibration_interval,), daemon=True)
timer_thread.start()

# Run the GUI event loop
root.mainloop()
