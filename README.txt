# ASPEN Demo Guide

---

## Folder Structure
```
ASPEN_CONTROL/
│── ASPEN_CALIBRATE.py
│── ASPEN_CONTROL.ino
│── ASPEN_EMPOWER.py
│── ASPEN_GUI.py
│── ASPEN_RECORD.py
│── ASPEN_STOP.py
│── ASPEN_STREAM.py
│── ASPEN_THERAPIST.py
│── arduino_secrets.h
│── STREAM_SAMPLE_EXERCISES/
│   │── Calibration_th1.txt
│   │── Exercise_1.poly5
│   │── Exercise_2.poly5
│── DATA_ANALYSIS/
```

---

## Prerequisites
1. Ensure that `tmsi_venv` is set up correctly. For setup instructions of the TMSi virtual environment, refer to the notes uploaded on the WeBeep course channel by Dr. Luca Pozzi.
2. Python environment with the required dependencies installed.

---

## Setup Instructions
1. Place `ASPEN_GUI.py` inside the `tmsi_venv` folder.
2. Place the other scripts inside the `tmsi-python-interface-V5.3.0.0` folder located in `tmsi_venv`.

---

## How to Run
1. Activate the virtual environment (`tmsi_venv`).
   ```
   source tmsi_venv/bin/activate  # For Linux/Mac
   tmsi_venv\Scripts\activate     # For Windows
   ```
2. Run `ASPEN_GUI.py`:
   ```
   python ASPEN_GUI.py
   ```
3. Use the graphical user interface (GUI) to advance through the demo.

---

## Description of Main Files
- **`ASPEN_CALIBRATE.py`**: Performs EMG signal calibration to identify activation thresholds.
- **`ASPEN_CONTROL.ino`**: Arduino code managing the exoskeleton’s control logic.
- **`ASPEN_EMPOWER.py`**: Implements real-time EMG-triggered movement of the exo.
- **`ASPEN_GUI.py`**: Provides a graphical interface to control the exoskeleton.
- **`ASPEN_RECORD.py`**: Records EMG signals.
- **`ASPEN_STOP.py`**: Stops exoskeleton operation and returns exo to base position.
- **`ASPEN_STREAM.py`**: Streams pre-recorded EMG data.
- **`ASPEN_THERAPIST.py`**: Special mode for therapist-assisted use.
- **`arduino_secrets.h`**: Stores configuration settings for the WiFi connection.

### **STREAM_SAMPLE_EXERCISES/**
- Contains example exercise files for the STREAM mode.
  - `Calibration_th1.txt`: Calibration data for EMG thresholds.
  - `Exercise_1.poly5`, `Exercise_2.poly5`: Sample recorded exercises.

### **DATA_ANALYSIS/**
- Contains MATLAB scripts and functions for data analysis and testing (see Report) of the system and example raw data.

---

## Authors
Developed at **Politecnico di Milano**, 2025.

---
