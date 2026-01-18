#include <SPI.h>
#include <WiFiNINA.h>
#include <Arduino_LSM6DS3.h>
#include <Servo.h>
#include "arduino_secrets.h" // Contains WiFi credentials

// WiFi credentials
char ssid[] = SECRET_SSID;    // Network SSID
char pass[] = SECRET_PASS;    // Network Password

// Servo and motion control
Servo myservo;
int status = WL_IDLE_STATUS;
int vel = 20; // Speed control -> 10 fast, 20 slow (ms)
int posTargetDesired = 90; // Maximum Flexion Target (°)
//int posTargetDesired = 105; // Extended ROM (°)
//int posTargetDesired = 60; // Reduced ROM (°)
int posOffset = 15; //Servomotor offset in relation to the anatomical system (°)
int posDesired = posTargetDesired + posOffset; // Corrected Maximum Flexion Target (°)
int posTargetBase = 0; // Maximum Extension Target (°)
int posBase = posTargetBase + posOffset; // Corrected Maximum Extension Target (°)

// Result of the mV-° calibration through a straight line (see Handbook)
float posIs; // Current position sensed by encoder (mV)
float posIsDeg; // Current position (°)
float posServo1 = 0, posServo2 = 90; // Servo calibration points (°)
float posSensor1 = 870, posSensor2 = 470; // Analog input calibration points (mV)

// IMU and force sensor variables
float accX, accY, accZ; // Acceleration values from IMU (m/s^2)
float forceIs; // Force sensor reading (bit)

// Gyroscope variables
int startTime, calibrationCount = 0, calibrationMillis = 1000;
float gyroX, gyroY, gyroZ, gyroDriftX, gyroDriftY, gyroDriftZ, sumX, sumY, sumZ; // Angular velocity values from Gyroscope (°/s)

// Flags and control variables
int trigger = 0; // 0: Extension, 1: Flexion
bool moveToDesired = false; // Indicates whether the servo should move to the desired position
bool alreadyMoved = false; // Keeps track if a movement has been made
float tol = 10; // Error tolerance (°)
bool actionExecuted = false; // Ensures actions are executed only once per trigger and within the feedback tolerance

// Pin assignments
const int servoOnPin = 7, PWMPin = 5; 
const int servoAnalogPin = A1; 
const int forceAnalogInPin = A2; 
const int AmpliSwitchPin = 8, GainSelectPin = 4;
const int buttonPin = 2; // Pin for button B2 (black button)

// Emergency Button state
// If pressed, it remains connected but is prevented from receiving further commands. To restart, the Arduino code must be reloaded onto the exo.
bool emergency = false; 

// Angle variables for position control
float startAngle, endAngle;

// Server WiFi
WiFiServer server(80);

// Function to print the WiFi connection status
void printWiFiStatus() {
  IPAddress ip = WiFi.localIP();
}

// Smooth servo movement
void moveServoSmoothly(int startAngle, int endAngle) {
  if (startAngle < endAngle) {
    for (int angle = startAngle; angle <= endAngle; angle++) {
      myservo.write(angle);
      delay(vel); // Speed control -> 10 fast, 20 slow
    }
  } else {
    for (int angle = startAngle; angle >= endAngle; angle--) {
      myservo.write(angle);
      delay(vel); // Speed control -> 10 fast, 20 slow
    }
  }
}

// Initialization
void setup() {
  // Initialize the servo
  pinMode(servoOnPin, OUTPUT);
  digitalWrite(servoOnPin, HIGH);
  // Reads the initial position and calculates in degrees
  posIs = analogRead(servoAnalogPin);
  posIsDeg = ((posServo2 - posServo1) / (posSensor2 - posSensor1)) * (posIs - posSensor1) + posServo1;

  // Move the servo to the base position for initialization
  myservo.write(posIsDeg+posOffset);
  myservo.attach(PWMPin);
  moveServoSmoothly(posIsDeg+posOffset, posBase);  
  delay(1300);
  myservo.detach();

  // Button setup
  pinMode(buttonPin, INPUT_PULLUP); // Button as input with pull-up resistor

  // Start the serial communication
  Serial.begin(9600);
  while (!Serial);

  // Initialize IMU
  IMU.begin();

  // Initialize gyroscope
  startTime = millis();
  while (millis() < startTime + calibrationMillis) {
    IMU.readGyroscope(gyroX, gyroY, gyroZ);
    sumX += gyroX;
    sumY += gyroY;
    sumZ += gyroZ;
    calibrationCount++;
  }
  gyroDriftX = sumX / calibrationCount;
  gyroDriftY = sumY / calibrationCount;
  gyroDriftZ = sumZ / calibrationCount;

  // WiFi setup
  Serial.println("Access Point Web Server");
  if (WiFi.status() == WL_NO_MODULE) {
    //Serial.println("Communication failed with the WiFi module!"); // For Debug
    while (true);
  }

  String fv = WiFi.firmwareVersion();
  if (fv < WIFI_FIRMWARE_LATEST_VERSION) {
    //Serial.println("Update the firmware");  // For Debug
  }

  //Serial.print("Creating the access point with name: ");  // For Debug
  //Serial.println(ssid);  // For Debug
  status = WiFi.beginAP(ssid);
  if (status != WL_AP_LISTENING) {
    //Serial.println("Access point creation failed");  // For Debug
    while (true);
  }

  delay(10000); // Wait for the connection to stabilize
  server.begin();
  //printWiFiStatus();  // For Debug
  
  // Amplifier and gain configuration
  pinMode(AmpliSwitchPin, OUTPUT);
  digitalWrite(AmpliSwitchPin, HIGH);
  pinMode(GainSelectPin, OUTPUT);
  digitalWrite(GainSelectPin, LOW);
}

// Main loop
void loop() {

  // Check button state
  if (digitalRead(buttonPin) == LOW) { // Button is pressed
    myservo.detach();
    emergency = true; 
    }

  // Manages the WiFi connection
  if (status != WiFi.status()) {
    status = WiFi.status();
    if (status == WL_AP_CONNECTED) {
      //Serial.println("Device connected to the AP");  // For Debug
    } else {
      //Serial.println("Device disconnected from the AP");  // For Debug
    }
  }

  // Manages incoming connections
  WiFiClient client = server.available();
  if (client && !emergency) {

    while (client.connected() && !emergency) { 
      if (digitalRead(buttonPin) == LOW) {
          myservo.detach();
          emergency = true;
          return;
        }
      if (client.available()) {
        String request = client.readStringUntil('\r');
        //Serial.println(request); // For Debug

        // Manages incoming triggers
        if (request == "bit=1") {
          trigger = 1;
          moveToDesired = true;
          actionExecuted = false;
          //Serial.println("Moving servo to the desired position");  // For Debug
        } else if (request == "bit=0") {
          trigger = 0;
          moveToDesired = false;
          actionExecuted = false;
          //Serial.println("Moving servo to 0°");  // For Debug
        }

        client.flush();
      }

      // Reads data from IMU, gyroscope, force sensor, and motor encoder
      IMU.readAcceleration(accX, accY, accZ);
      posIs = analogRead(servoAnalogPin);
      posIsDeg = ((posServo2 - posServo1) / (posSensor2 - posSensor1)) * (posIs - posSensor1) + posServo1;
      forceIs = analogRead(forceAnalogInPin);
      IMU.readGyroscope(gyroX, gyroY, gyroZ);
      gyroX = gyroX - gyroDriftX;
      gyroY = gyroY - gyroDriftY;
      gyroZ = gyroZ - gyroDriftZ;

      // Continuously sends sensor data to the client
      String data = "PosIsDeg: " + String(posIsDeg) + ", ForceIs: " + String(forceIs) +
                    ", accX: " + String(accX) + ", accY: " + String(accY) + ", accZ: " + String(accZ) +
                    ", gyroX: " + String(gyroX) + ", gyroY: " + String(gyroY) + ", gyroZ: " + String(gyroZ);
      client.println(data); // Sends data to the client

      // Conditions for overwrite and servo movement
      /*if (forceIs < 490 && alreadyMoved) { // FORCE mode for extension: not used due to unreliable force sensor 
        //Serial.println("Servo movement to 0°");  // For Debug
        startAngle = posIsDeg + posOffset;
        endAngle = posBase;
        myservo.write(startAngle);
        myservo.attach(PWMPin);
        if (startAngle < endAngle) {
          for (int angle = startAngle; angle <= endAngle; angle++) {
            if (digitalRead(buttonPin) == LOW) {
            emergency = true; // If button is pressed, stop the movement
            return;}
            myservo.write(angle);
            delay(vel); // Speed control -> 10 fast, 20 slow
            IMU.readAcceleration(accX, accY, accZ);
            posIs = analogRead(servoAnalogPin);
            posIsDeg = ((posServo2 - posServo1) / (posSensor2 - posSensor1)) * (posIs - posSensor1) + posServo1;
            forceIs = analogRead(forceAnalogInPin);
            IMU.readGyroscope(gyroX, gyroY, gyroZ);
            gyroX = gyroX - gyroDriftX;
            gyroY = gyroY - gyroDriftY;
            gyroZ = gyroZ - gyroDriftZ;
            // Continuously sends sensor data to the client
            String data = "PosIsDeg: " + String(posIsDeg) + ", ForceIs: " + String(forceIs) +
                    ", accX: " + String(accX) + ", accY: " + String(accY) + ", accZ: " + String(accZ) +
                    ", gyroX: " + String(gyroX) + ", gyroY: " + String(gyroY) + ", gyroZ: " + String(gyroZ);
            client.println(data); // Sends data to the client
          }
        }
        else {
          for (int angle = startAngle; angle >= endAngle; angle--) {
            if (digitalRead(buttonPin) == LOW) {
            emergency = true; // If button is pressed, stop the movement
            return;}
            myservo.write(angle);
            delay(vel); // Speed control -> 10 fast, 20 slow
            IMU.readAcceleration(accX, accY, accZ);
            posIs = analogRead(servoAnalogPin);
            posIsDeg = ((posServo2 - posServo1) / (posSensor2 - posSensor1)) * (posIs - posSensor1) + posServo1;
            forceIs = analogRead(forceAnalogInPin);
            IMU.readGyroscope(gyroX, gyroY, gyroZ);
            gyroX = gyroX - gyroDriftX;
            gyroY = gyroY - gyroDriftY;
            gyroZ = gyroZ - gyroDriftZ;
            // Continuously sends sensor data to the client
            String data = "PosIsDeg: " + String(posIsDeg) + ", ForceIs: " + String(forceIs) +
                  ", accX: " + String(accX) + ", accY: " + String(accY) + ", accZ: " + String(accZ) +
                  ", gyroX: " + String(gyroX) + ", gyroY: " + String(gyroY) + ", gyroZ: " + String(gyroZ);
            client.println(data); // Sends data to the client
          }
        }
        delay(1300);
        // Position Control (feedback)
        if (abs((posIsDeg + posOffset) - posBase) < tol || emergency == true) {
        myservo.detach();
        actionExecuted = true;
        }
      }
      else*/ if (trigger == 1 && moveToDesired && !actionExecuted) {
        startAngle = posIsDeg + posOffset;
        endAngle = abs(posDesired);
        myservo.write(startAngle);
        myservo.attach(PWMPin);
        if (startAngle < endAngle) {
          for (int angle = startAngle; angle <= endAngle; angle++) {
            if (digitalRead(buttonPin) == LOW) {
            emergency = true; // If button is pressed, stop the movement
            return;}
            myservo.write(angle);
            delay(vel); // Speed control -> 10 fast, 20 slow
            IMU.readAcceleration(accX, accY, accZ);
            posIs = analogRead(servoAnalogPin);
            posIsDeg = ((posServo2 - posServo1) / (posSensor2 - posSensor1)) * (posIs - posSensor1) + posServo1;
            forceIs = analogRead(forceAnalogInPin);
            IMU.readGyroscope(gyroX, gyroY, gyroZ);
            gyroX = gyroX - gyroDriftX;
            gyroY = gyroY - gyroDriftY;
            gyroZ = gyroZ - gyroDriftZ;
            // Continuously sends sensor data to the client
            String data = "PosIsDeg: " + String(posIsDeg) + ", ForceIs: " + String(forceIs) +
                  ", accX: " + String(accX) + ", accY: " + String(accY) + ", accZ: " + String(accZ) +
                  ", gyroX: " + String(gyroX) + ", gyroY: " + String(gyroY) + ", gyroZ: " + String(gyroZ);
            client.println(data); // Sends data to the client
          }
        }
        else {
          for (int angle = startAngle; angle >= endAngle; angle--) {
            if (digitalRead(buttonPin) == LOW) {
            emergency = true; // If button is pressed, stop the movement
            return;}
            myservo.write(angle);
            delay(vel); // Speed control -> 10 fast, 20 slow
            IMU.readAcceleration(accX, accY, accZ);
            posIs = analogRead(servoAnalogPin);
            posIsDeg = ((posServo2 - posServo1) / (posSensor2 - posSensor1)) * (posIs - posSensor1) + posServo1;
            forceIs = analogRead(forceAnalogInPin);
            IMU.readGyroscope(gyroX, gyroY, gyroZ);
            gyroX = gyroX - gyroDriftX;
            gyroY = gyroY - gyroDriftY;
            gyroZ = gyroZ - gyroDriftZ;
            // Continuously sends sensor data to the client
            String data = "PosIsDeg: " + String(posIsDeg) + ", ForceIs: " + String(forceIs) +
                    ", accX: " + String(accX) + ", accY: " + String(accY) + ", accZ: " + String(accZ) +
                    ", gyroX: " + String(gyroX) + ", gyroY: " + String(gyroY) + ", gyroZ: " + String(gyroZ);
            client.println(data); // Sends data to the client
          }
        }
        delay(1300);
        // Position Control (feedback)
        if (abs((posIsDeg + posOffset) - posDesired) < tol || emergency == true) {
        myservo.detach();
        alreadyMoved = true;
        actionExecuted = true;
        }
      }
      else if (trigger == 0 && !moveToDesired && !actionExecuted) {
        //Serial.println("Servo movement to 0°");  // For Debug
        startAngle = posIsDeg + posOffset;
        endAngle = posBase;
        myservo.write(startAngle);
        myservo.attach(PWMPin);
        if (startAngle < endAngle) {
          for (int angle = startAngle; angle <= endAngle; angle++) {
            if (digitalRead(buttonPin) == LOW) {
            emergency = true; // If button is pressed, stop the movement
            return;}
            myservo.write(angle);
            delay(vel); // Speed control -> 10 fast, 20 slow
            IMU.readAcceleration(accX, accY, accZ);
            posIs = analogRead(servoAnalogPin);
            posIsDeg = ((posServo2 - posServo1) / (posSensor2 - posSensor1)) * (posIs - posSensor1) + posServo1;
            forceIs = analogRead(forceAnalogInPin);
            IMU.readGyroscope(gyroX, gyroY, gyroZ);
            gyroX = gyroX - gyroDriftX;
            gyroY = gyroY - gyroDriftY;
            gyroZ = gyroZ - gyroDriftZ;
            // Continuously sends sensor data to the client
            String data = "PosIsDeg: " + String(posIsDeg) + ", ForceIs: " + String(forceIs) +
                  ", accX: " + String(accX) + ", accY: " + String(accY) + ", accZ: " + String(accZ) +
                  ", gyroX: " + String(gyroX) + ", gyroY: " + String(gyroY) + ", gyroZ: " + String(gyroZ);
            client.println(data); // Sends data to the client
          }
        }
        else {
          for (int angle = startAngle; angle >= endAngle; angle--) {
            if (digitalRead(buttonPin) == LOW) {
            emergency = true; // If button is pressed, stop the movement
            return;}
            myservo.write(angle);
            delay(vel); // Speed control -> 10 fast, 20 slow
            IMU.readAcceleration(accX, accY, accZ);
            posIs = analogRead(servoAnalogPin);
            posIsDeg = ((posServo2 - posServo1) / (posSensor2 - posSensor1)) * (posIs - posSensor1) + posServo1;
            forceIs = analogRead(forceAnalogInPin);
            IMU.readGyroscope(gyroX, gyroY, gyroZ);
            gyroX = gyroX - gyroDriftX;
            gyroY = gyroY - gyroDriftY;
            gyroZ = gyroZ - gyroDriftZ;
            // Continuously sends sensor data to the client
            String data = "PosIsDeg: " + String(posIsDeg) + ", ForceIs: " + String(forceIs) +
                  ", accX: " + String(accX) + ", accY: " + String(accY) + ", accZ: " + String(accZ) +
                  ", gyroX: " + String(gyroX) + ", gyroY: " + String(gyroY) + ", gyroZ: " + String(gyroZ);
            client.println(data); // Sends data to the client
          }
        }
        delay(1300);
        // Position Control (feedback)
        if (abs((posIsDeg + posOffset) - posBase) < tol || emergency == true) {
        myservo.detach();
        actionExecuted = true;
        }
      }
    }
    client.stop();
    //Serial.println("Client disconnected");  // For Debug
  }
}
