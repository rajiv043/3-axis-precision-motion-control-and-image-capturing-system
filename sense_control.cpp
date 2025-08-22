#include <SCServo.h>

SMS_STS st;

#define S_RXD 18
#define S_TXD 19
#define LIMIT_SWITCH_X_PIN 4   // GPIO pin for the limit switch for Motor X
#define LIMIT_SWITCH_Y_PIN 5   // GPIO pin for the limit switch for Motor Y
#define LIMIT_SWITCH_X_BLOCK_PIN 16  // GPIO pin to block clockwise motion for Motor X
#define LIMIT_SWITCH_Y_BLOCK_PIN 27  // GPIO pin to block clockwise motion for Motor Y
#define LIMIT_SWITCH_Z_NEGATIVE_PIN 33 // GPIO pin to stop negative motion for Motor Z
#define LIMIT_SWITCH_Z_BLOCK_PIN 32   // GPIO pin to stop clockwise motion for Motor Z

void setup() {
  Serial.begin(115200);  // Debugging Serial Monitor
  Serial1.begin(1000000, SERIAL_8N1, S_RXD, S_TXD);
  st.pSerial = &Serial1;
  delay(1000);  // Initialization delay

  // Set all servos to Wheel Mode (Continuous Rotation)
  st.WheelMode(1);  // X-axis servo (ID 1)
  st.WheelMode(2);  // Y-axis servo (ID 2)
  st.WheelMode(3);  // Z-axis servo (ID 3)

  // Set up the limit switch pins as pull-up inputs
  pinMode(LIMIT_SWITCH_X_PIN, INPUT_PULLUP);
  pinMode(LIMIT_SWITCH_Y_PIN, INPUT_PULLUP);
  pinMode(LIMIT_SWITCH_X_BLOCK_PIN, INPUT_PULLUP);
  pinMode(LIMIT_SWITCH_Y_BLOCK_PIN, INPUT_PULLUP);
  pinMode(LIMIT_SWITCH_Z_NEGATIVE_PIN, INPUT_PULLUP);
  pinMode(LIMIT_SWITCH_Z_BLOCK_PIN, INPUT_PULLUP);

  Serial.println("Servos set to Wheel Mode.");
  Serial.println("Enter commands in the format: <Axis><Direction><Time>");
  Serial.println("Example: X+1000 (Run X-axis clockwise for 1000 ms)");
  Serial.println("Example: X1200 (Run X-axis clockwise for 1200 ms)");
  Serial.println("Example: X-500 (Run X-axis anticlockwise for 500 ms)");
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');  // Read the entire command
    command.trim();  // Remove any leading/trailing whitespace

    if (command.length() >= 2) {  // Ensure the command has at least 2 characters (axis + time)
      char axis = command.charAt(0);  // Extract the axis (X, Y, or Z)
      char direction = '+';  // Default direction is clockwise
      int timeIndex = 1;  // Start index for time value

      // Check if the second character is a direction (+ or -)
      if (command.charAt(1) == '+' || command.charAt(1) == '-') {
        direction = command.charAt(1);  // Extract the direction
        timeIndex = 2;  // Time value starts from the third character
      }

      int time = command.substring(timeIndex).toInt();  // Extract the time value

      if (time > 0) {  // Check if a valid time was received
        int servoID = 0;
        switch (axis) {
          case 'X':
          case 'x':
            servoID = 1;
            break;
          case 'Y':
          case 'y':
            servoID = 2;
            break;
          case 'Z':
          case 'z':
            servoID = 3;
            break;
          default:
            Serial.println("Invalid axis. Use X, Y, or Z.");
            return;
        }

        int speed = 0;
        if (direction == '+') {
          // Check clockwise block limit switches
          if (servoID == 1 && digitalRead(LIMIT_SWITCH_X_BLOCK_PIN) == LOW) {
            Serial.println("Clockwise rotation is blocked for Motor X.");
            return;
          } else if (servoID == 2 && digitalRead(LIMIT_SWITCH_Y_BLOCK_PIN) == LOW) {
            Serial.println("Clockwise rotation is blocked for Motor Y.");
            return;
          } else if (servoID == 3 && digitalRead(LIMIT_SWITCH_Z_BLOCK_PIN) == HIGH) {
            Serial.println("Clockwise rotation is blocked for Motor Z.");
            return;
          }
          speed = 1000;  // Clockwise rotation
        } else if (direction == '-') {
          // Check negative rotation limit switches
          if (servoID == 1 && digitalRead(LIMIT_SWITCH_X_PIN) == LOW) {
            Serial.println("Limit switch for Motor X triggered! Cannot run in negative direction.");
            return;
          } else if (servoID == 2 && digitalRead(LIMIT_SWITCH_Y_PIN) == LOW) {
            Serial.println("Limit switch for Motor Y triggered! Cannot run in negative direction.");
            return;
          } else if (servoID == 3 && digitalRead(LIMIT_SWITCH_Z_NEGATIVE_PIN) == HIGH) {
            Serial.println("Limit switch for Motor Z triggered! Cannot run in negative direction.");
            return;
          }
          speed = -1000;  // Anticlockwise rotation
        } else {
          Serial.println("Invalid direction. Use + or -.");
          return;
        }

        Serial.print("Running ");
        Serial.print(axis);
        Serial.print("-axis motor (ID ");
        Serial.print(servoID);
        Serial.print(") ");
        Serial.print(direction == '+' ? "clockwise" : "anticlockwise");
        Serial.print(" for ");
        Serial.print(time);
        Serial.println(" milliseconds...");

        st.WriteSpe(servoID, speed);  // Rotate motor in the specified direction
        unsigned long startTime = millis();  // Record the start time

        // Run the motor for the specified time, but continuously check the appropriate limit switch
        while (millis() - startTime < time) {
          if (servoID == 1 && direction == '-' && digitalRead(LIMIT_SWITCH_X_PIN) == LOW) {
            Serial.println("Limit switch for Motor X triggered! Stopping Motor X...");
            st.WriteSpe(servoID, 0);  // Stop the motor immediately
            return;
          } else if (servoID == 2 && direction == '-' && digitalRead(LIMIT_SWITCH_Y_PIN) == LOW) {
            Serial.println("Limit switch for Motor Y triggered! Stopping Motor Y...");
            st.WriteSpe(servoID, 0);  // Stop the motor immediately
            return;
          } else if (servoID == 3) {
            if (direction == '-' && digitalRead(LIMIT_SWITCH_Z_NEGATIVE_PIN) == HIGH) {
              Serial.println("Limit switch for Motor Z triggered! Stopping Motor Z...");
              st.WriteSpe(servoID, 0);  // Stop the motor immediately
              return;
            } else if (direction == '+' && digitalRead(LIMIT_SWITCH_Z_BLOCK_PIN) == HIGH) {
              Serial.println("Clockwise rotation blocked for Motor Z! Stopping Motor Z...");
              st.WriteSpe(servoID, 0);  // Stop the motor immediately
              return;
            }
          }
          delay(10);  // Small delay to avoid busy-waiting
        }

        Serial.println("Stopping motor...");
        st.WriteSpe(servoID, 0);  // Stop motor

        Serial.println("Enter new command:");
      } else {
        Serial.println("Invalid time. Please enter a positive number.");
      }
    } else {
      Serial.println("Invalid command format. Use <Axis><Direction><Time> or <Axis><Time>.");
    }
  }
}
