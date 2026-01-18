'''
(c) 2025 Politecnico di Milano

   ###       #####     #####      #######    #     # 
  #   #     #     #    #    #     #          ##    # 
 #     #    #          #    #     #          # #   # 
 #######     #####     #####      #####      #  #  # 
 #     #          #    #          #          #   # # 
 #     #    #     #    #          #          #    ## 
 #     #     #####     #          #######    #     #
 
  #####       ###      #            ###      #####      #####        ###      #######    ####### 
 #     #     #   #     #             #       #    #     #    #      #   #        #       #       
 #          #     #    #             #       #    #     #    #     #     #       #       #       
 #          #######    #             #       #####      #####      #######       #       #####   
 #          #     #    #             #       #    #     #   #      #     #       #       #       
 #     #    #     #    #             #       #    #     #    #     #     #       #       #       
  #####     #     #    #######      ###      #####      #     #    #     #       #       ####### 

'''

# Libraries
import os
import sys
import csv
import time
import statistics
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
from scipy.signal import butter, filtfilt, lfilter
import matplotlib
matplotlib.use('TkAgg')

## 1.OPEN THE WINDOW THAT PROMPTS FOR THE FILE AND PLOT THE FILTERED DATA
# Directory settings
MyTMSi_dir = os.path.dirname(os.path.realpath(__file__))
modules_dir = os.path.join(MyTMSi_dir, '..')
measurements_dir = os.path.join(MyTMSi_dir,"_myTMSi", '../ASPEN_EMG_MEASUREMENTS')
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

print(f"Reading file {file_path}")
print(f"Number of samples: {len(EMG_signal)}")
print(f"Sample rate: {Fs_EMG} Hz")

while True:
    try:
        # Asks for two values separated by space
        inputs = input("Which channels do you want to analyze? (Enter 0 and/or 1, separated by space): ").split()
        
        # Converts the inputs to integers
        numbers = list(map(int, inputs))
        
        # Checks that the entered numbers are only 0 or 1
        if all(num in [0, 1] for num in numbers) and len(numbers) <= 2:
            break  # Valid input, exit the loop
        else:
            print("Error: Please enter 0 and/or 1, separated by space. Maximum 2 inputs.")
    except ValueError:
        print("Error: Invalid input. Please enter integers only (0 or 1).")

numbers = sorted(numbers)
print(f"You selected channels: {numbers}")

# %%%%%%%%%%%%%%%%%%%%%%________SELECTION OF CHANNELS_______ %%%%%%%%%%%%%%%%%%%%%%%
EMG_signal_selected = EMG_signal[:, numbers]

# Function to create filters
def create_filters(Fs_EMG):
    fcutlow = 10  # Low cutoff frequency in Hz
    fcuthigh = 100  # High cutoff frequency in Hz
    B_bandpass, A_bandpass = butter(5, [fcutlow, fcuthigh], btype='bandpass', fs=Fs_EMG)
    B_lowpass, A_lowpass = butter(5, 5, btype='low', fs=Fs_EMG)
    bandpass_state = np.zeros(max(len(A_bandpass), len(B_bandpass)) - 1)
    lowpass_state = np.zeros(max(len(A_lowpass), len(B_lowpass)) - 1)
    return (B_bandpass, A_bandpass), (B_lowpass, A_lowpass), bandpass_state, lowpass_state

# Function to process data
def process_sample(sample, state, filters):
    (B_bandpass, A_bandpass), (B_lowpass, A_lowpass) = filters
    filtered_sample, state['bandpass'] = lfilter(
        B_bandpass, A_bandpass, [sample], zi=state['bandpass']
    )
    filtered_sample = filtered_sample[0]
    rectified_sample = np.abs(filtered_sample)
    envelope_sample, state['lowpass'] = lfilter(
        B_lowpass, A_lowpass, [rectified_sample], zi=state['lowpass']
    )
    envelope_sample = envelope_sample[0]
    return filtered_sample, rectified_sample, envelope_sample

# Main processing
if __name__ == "__main__":
    # Configure filters
    (B_bandpass, A_bandpass), (B_lowpass, A_lowpass), bandpass_state, lowpass_state = create_filters(Fs_EMG)
    state = {'bandpass': bandpass_state, 'lowpass': lowpass_state}
    filters = ((B_bandpass, A_bandpass), (B_lowpass, A_lowpass))
    print("Processing EMG signal. Please wait...")

    # Number of channels (columns) in EMG_signal_selected
    num_channels = EMG_signal_selected.shape[1]

    # Preallocate buffer for envelopes
    buffer_size = len(EMG_signal_selected)
    envelope_data = np.zeros((buffer_size, num_channels))

    # Process each sample for each channel
    for ch in range(num_channels):
        # Apply warm-up for the filter to avoid initial peak
        for warmup_idx in range(Fs_EMG):
            _, _, _ = process_sample(EMG_signal_selected[warmup_idx, ch], state, filters)
        for i in range(buffer_size):
            sample = EMG_signal_selected[i, ch]
            _, _, envelope_sample = process_sample(sample, state, filters)
            envelope_data[i, ch] = envelope_sample

    print(f'{buffer_size} samples processed for {num_channels} channels.')

    # Plot results
    time_axis = np.arange(buffer_size) / Fs_EMG  # Convert sample indices to time in seconds
    fig, axs = plt.subplots(num_channels, 1, figsize=(10, 6), sharex=True)

    if num_channels == 1:
        axs = [axs]  # Ensure axs is a list for consistency

    # Colors for the channels (Matplotlib default colors)
    colors = ['C0', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9']  # Standard Matplotlib colors

    for i, ch in enumerate(numbers):  # Uses `enumerate` to associate the correct channel with the subplot
        axs[i].plot(
            time_axis,
            envelope_data[:, i],
            label=f'EMG Envelope - Channel {ch}',  
            color=colors[i % len(colors)]  # Cycles colors if channels > 10
        )
        axs[i].set_xlabel('Time [s]')
        axs[i].set_ylabel('Amplitude [mV]')
        axs[i].grid(True)
        axs[i].legend()
    plt.tight_layout()
    plt.show()

EMG_time = time_axis # Store the indices of time

# Ask if you want to perform the calibration for that channel
for j, ch in enumerate(numbers):
    print(f"Processing channel {ch}")
    no_calib = False
    while True:
        try:
            # Asks if the user wants to proceed with calibration
            proceed = input("Do you want to proceed with calibration? (Y/N): ").strip().upper()
            # Checks if the response is valid
            if proceed == 'Y':
                print("Proceeding with calibration...")
                break # Proceed with calibration, exit the loop
            elif proceed == 'N':
                if ch == numbers[-1]:
                    print("Exiting program...")
                    exit()  # Closes the program
                else:
                    print(f"Skipping calibration for channel {ch}...")
                    no_calib = True
                    break  # Move to the next loop (channel)
            else:
                print("Error: Please enter 'Y' for Yes or 'N' for No.")
        except ValueError:
            print("Error: Invalid input. Please enter 'Y' or 'N'.")
    
    if no_calib:
        continue  # Exits the main for loop if the flag is True

    EMG_en1 = envelope_data[:, j]

    ## 2. CALCULATION OF THRESHOLD TH1 FROM THE BASELINE (DOUBLE THRESHOLD METHOD)
    th = []  # Vector where all thresholds are saved
    th2 = 0.2  # s 
    nr_sample = th2 * Fs_EMG # Number of samples above the threshold
    nr_sample_end = 5*nr_sample # Single Muscle: Number of samples that should be below threshold
    EMG_time_trunc = np.trunc(EMG_time * 100) / 100  # Truncate to two decimal places (necessary for comparison later)

    # Calculation of th1, with baseline selection from the graph
    prompt = "How many baseline samples? "
    n = int(input(prompt))  # Converts input to an integer
    for i in range(n):
        # Display the graph to select the baseline
        plt.figure(i+1, figsize=(10, 6))
        plt.plot(EMG_time, EMG_en1)
        plt.title('Select the baseline points')
        plt.xlabel('Time [s]')
        plt.ylabel('Amplitude [mV]')
        plt.grid(True)
        # Select the points for the baseline
        baseline_pts = plt.ginput(2)
        plt.show()

        # Initialize a vector of the same length as EMG_time to compare with the function on line 153
        baseline_pts_copy = np.full(2, 0, dtype=np.float64)
        # Replace the first two values with the time values selected from the graph
        baseline_pts_copy[0] = baseline_pts[0][0]
        baseline_pts_copy[1] = baseline_pts[1][0]
        #print("Baseline indices from input:", baseline_pts_copy)
        baseline_pts_copy = np.trunc(baseline_pts_copy * 100) / 100
        # np.where is used to find the positions (indices) of the two points selected from the graph
        baseline_indices_copy = np.where((EMG_time_trunc == baseline_pts_copy[0]) | (EMG_time_trunc == baseline_pts_copy[1]))[0]
        # Print results for verification in each iteration
        print(f"Iteration {i+1}:")
        # DEBUG: Baseline sample interval
        #print("Baseline sample interval:", baseline_indices_copy[0], baseline_indices_copy[len(baseline_indices_copy)-1])

        # Threshold settings
        baseline_env = EMG_en1[range(baseline_indices_copy[0], baseline_indices_copy[len(baseline_indices_copy)-1])]
        # DEBUG: Baseline, mean and standard deviation
        #print("Selected baseline:", baseline_env)  # Select the baseline envelope
        #print("Mean:", baseline_env.mean())
        #print("Standard Deviation:", baseline_env.std(ddof=1))
        thi = baseline_env.mean() + 3 * baseline_env.std(ddof=1)  # Calculate the threshold of this segment, ddof=1 for MATLAB compatibility
        print("Threshold:", thi)
        th.append(thi)  # Add this threshold to the vector with all thresholds

    # Final threshold calculation using three methods
    thmin = min(th)
    thmed = statistics.median(th)
    thmax = max(th)
    print("Maximum threshold", thmax)
    print("Minimum threshold", thmin)
    print("Median threshold", thmed)

    ## Final threshold selection
    # Prompt the user to select the method
    print("Choose the method to calculate the final threshold:")
    print("1. Maximum")
    print("2. Minimum")
    print("3. Median")

    # Get the user's choice
    method_choice = input("Enter your choice (1/2/3): ")

    # Determine the threshold based on the chosen method
    if method_choice == "1":
        th1 = thmax  # Maximum method
        print("Selected method: Maximum")
    elif method_choice == "2":
        th1 = thmin  # Minimum method
        print("Selected method: Minimum")
    elif method_choice == "3":
        th1 = thmed  # Median method
        print("Selected method: Median")
    else:
        print("Invalid choice. Defaulting to Maximum method.")
        th1 = thmax  # Default to Maximum method

    # Print the selected threshold
    print(f"Final threshold (th1): {th1}")

    while True:
        try:
            # Asks if the user wants to verify the threshold for the current channel
            verify_threshold = input(f"Do you want to verify the threshold for channel {ch}? (Y/N): ").strip().upper()

            if verify_threshold == 'Y':
                print(f"Proceeding with threshold verification for channel {ch}...")
                break  # Proceed with threshold verification

            elif verify_threshold == 'N':
                print(f"Skipping threshold verification for channel {ch}...")
                if ch == numbers[-1]:
                    print("Exiting program...")
                    exit()  # Exit the program if it is the last channel
                else:
                    no_calib = True
                    break  # Move to the next iteration of the for loop for the next channel
            else:
                print("Error: Please enter 'Y' for Yes or 'N' for No.")
        except ValueError:
            print("Error: Invalid input. Please enter 'Y' or 'N'.")

    if no_calib:
        continue  # Exit the main for loop if the flag is True


    ## 4. MOVEMENT ANALYSIS, THRESHOLD VERIFICATION, AND PLOTTING
    # Creation of vectors used to save data for each movement
    all_movement_indices = []  # Movement indices
    all_time_cut = []  # Corresponding movement times
    all_EMG_en_cut = []  # EMG_en values for each movement
    all_act_init = []  # Movement start value for each movement
    all_act_fin = []  # Movement final value for each movement
    # Vectors used to save every time it rises and falls below th1
    ind_start = np.array([])
    ind_stop = np.array([])

    # Number of movements chosen from the keyboard
    prompt = "How many movements? "
    n = int(input(prompt))  # Converts input to an integer

    # Execute the loop n times
    for k in range(n):
        # Create the figure for each loop
        plt.figure(k+1,figsize=(10, 6))
        plt.plot(EMG_time, EMG_en1)
        plt.title('Select the movement points')
        plt.xlabel('Time [s]')
        plt.ylabel('Amplitude [mV]')
        plt.grid(True)
        # Select the movement points
        movement_pts = plt.ginput(2)
        plt.show()

        # Create an array to store truncated values
        movement_pts_copy = np.full(2, 0, dtype=np.float64)
        # Assign the selected values
        movement_pts_copy[0] = movement_pts[0][0]
        movement_pts_copy[1] = movement_pts[1][0]
        # Truncate EMG_time and movement_pts_copy to the second decimal place
        movement_pts_copy = np.trunc(movement_pts_copy * 100) / 100
        # Find the indices corresponding to the selected values
        movement_indices_copy = np.where((EMG_time_trunc == movement_pts_copy[0]) | (EMG_time_trunc == movement_pts_copy[1]))[0]
        # Add the found indices to the list
        all_movement_indices.append([movement_indices_copy[0], movement_indices_copy[len(movement_indices_copy)-1]])

        # Create a vector containing all values between the two previously found indices (both for time and signal)
        EMG_time_cut = EMG_time[range(movement_indices_copy[0], movement_indices_copy[len(movement_indices_copy)-1])]
        EMG_en_cut = EMG_en1[range(movement_indices_copy[0], movement_indices_copy[len(movement_indices_copy)-1])]
        all_time_cut.extend(EMG_time_cut)
        all_EMG_en_cut.extend(EMG_en_cut)

        # DEBUG: Print results for verification in each iteration
        #print(f"Iteration {i+1}:")
        #print("Movement points:", movement_pts_copy)
        #print("Movement interval:", movement_indices_copy[0], movement_indices_copy[len(movement_indices_copy)-1])

        # Search for the movement start point
        # Create a boolean mask to find where the signal is above the threshold
        mask_above_threshold = EMG_en_cut > th1
        # Find state changes (start and end of segments)
        change_points = np.diff(mask_above_threshold.astype(int))
        # Find start and end indices
        ind_start = np.where(change_points == 1)[0] + 1  # +1 to get the correct index
        ind_stop = np.where(change_points == -1)[0] + 1  # +1 for the next point

        # DEBUG: Start and stop indices
        #print ("Start indices", ind_start)
        #print ("Stop indices", ind_stop)
        if ind_start.size == 0 and ind_stop.size == 0:
            # Code to execute if both arrays are empty
            print("No activation indices found")
            continue
        
        # Handle edge cases
        if len(ind_stop) > len(ind_start):  # First change is a stop index
            ind_start = np.append(0, ind_start)  # Add index 0 as the first start point
        # Case 2: If there is no stop index for the last segment, set the last stop index to len(EMG_en_cut)-1
        if len(ind_stop) < len(ind_start):
            ind_stop = np.append(ind_stop, len(EMG_en_cut)-1)
        # Ensure every start has a corresponding stop
        if len(ind_start) > len(ind_stop):
            # If there is one extra start, remove it
            ind_start = ind_start[:len(ind_stop)]

        # Calculate the length of each segment
        block_length = ind_stop[:len(ind_start)] - ind_start[:len(ind_stop)]
        # Find blocks exceeding a minimum length
        blocks_ind = np.where(block_length > nr_sample)[0]
        # DEBUG: Block indices
        #print("Block indices", blocks_ind)
        # Find the first activation point and add nr_sample
        act_init = movement_indices_copy[0] + ind_start[blocks_ind[0]] + nr_sample
        all_act_init.extend([int(act_init)])

        ## Deactivation points
        # Filter segments to include only those after `act_init`
        mask_below_threshold = (EMG_en_cut < th1) & (np.arange(len(EMG_en_cut)) > (act_init - movement_indices_copy[0]))
        # Find state changes (start and end of below-threshold segments)
        change_points_below = np.diff(mask_below_threshold.astype(int))
        ind_stop_start = np.where(change_points_below == 1)[0] + 1  # Start of below-threshold region
        ind_stop_end = np.where(change_points_below == -1)[0] + 1  # End of below-threshold region

        if ind_stop_start.size == 0 and ind_stop_end.size == 0:
            # Code to execute if both arrays are empty
            print("No deactivation indices found")
            continue

        # Handle edge cases for stop points
        if len(ind_stop_end) > len(ind_stop_start):  # First change is an end index
            ind_stop_start = np.append(0, ind_stop_start)  # Add index 0 as the first start point
        if len(ind_stop_end) < len(ind_stop_start):  # No end index for the last segment
            ind_stop_end = np.append(ind_stop_end, len(EMG_en_cut) - 1)
        if len(ind_stop_start) > len(ind_stop_end):  # Ensure every start has a corresponding end
            ind_stop_start = ind_stop_start[:len(ind_stop_end)]

        # Calculate the length of each below-threshold segment
        stop_block_length = ind_stop_end[:len(ind_stop_start)] - ind_stop_start[:len(ind_stop_end)]
        # Find blocks exceeding a minimum length
        stop_blocks_ind = np.where(stop_block_length > nr_sample_end)[0]

        # Find the final deactivation point and add nr_sample
        if len(stop_blocks_ind) > 0:
            act_fin = movement_indices_copy[0] + ind_stop_start[stop_blocks_ind[0]] + nr_sample_end
            all_act_fin.extend([int(act_fin)])
            #print(f"Deactivation point found: {act_fin}")
        else:
            print("No valid deactivation block found.")
        
    # DEBUG: Print all activation/disactivation points
    #print("All activation points", all_act_init)
    #print("All disactivation points", all_act_fin)

    # Plot cut values
    plt.figure(j,figsize=(10, 6))
    plt.plot(all_time_cut, all_EMG_en_cut, label=f'EMG Envelope - Channel {ch}')
    plt.plot(EMG_time, th1 * np.ones(len(EMG_time)), 'k', linewidth=1.5, label='Threshold th1')
    
    # Add a single label for trigger 1 (green line)
    for z, init in enumerate(all_act_init):
        if z == 0 and (j == 0 or num_channels==1):  # Only the first time, add the label
            plt.axvline(x=EMG_time[init], color='g', linewidth=1.5, label='Trigger 1')
        elif z == 0 and j == 1:
            plt.axvline(x=EMG_time[init], color='r', linewidth=1.5, label='Trigger 0')
        else:  # Other green lines will not have the label
            if num_channels==2 and j==0:
                plt.axvline(x=EMG_time[init], color='g', linewidth=1.5)
            elif num_channels==2 and j==1:
                plt.axvline(x=EMG_time[init], color='r', linewidth=1.5)
            else:
                plt.axvline(x=EMG_time[init], color='g', linewidth=1.5)

    # Add a single label for trigger 0 (red line) for single muscle
    if num_channels == 1:  
        for z, final in enumerate(all_act_fin):
            if z == 0:  # Only the first time, add the label
                plt.axvline(x=EMG_time[final], color='r', linewidth=1.5, linestyle='--', label='Trigger 0')
            else:  # Other red lines will not have the label
                plt.axvline(x=EMG_time[final], color='r', linewidth=1.5, linestyle='--')

    plt.title('Selected movements with activation', fontsize=14)
    plt.xlabel('Time [s]')
    plt.ylabel('Amplitude [mV]')
    plt.legend()
    plt.grid(True)
    plt.show()

    if ch == numbers[-1]:
        print("Exiting program...")
        exit()  # Closes the program if it is the last channel