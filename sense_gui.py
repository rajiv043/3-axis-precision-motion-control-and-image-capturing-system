from tkinter.filedialog import askopenfilename
from tkinter import simpledialog
from tkinter import Canvas
from tkinter import Scrollbar
from tkinter import filedialog
from tkinter import ttk
import pandas as pd
from tkinter import messagebox, Tk, Button, Entry, Label, LabelFrame, ttk, Frame, IntVar, Checkbutton, StringVar, Radiobutton, Toplevel
import serial
import os
import threading
from PIL import Image, ImageTk
from tkinter import Toplevel, Label, Canvas, Scrollbar, HORIZONTAL, VERTICAL, BOTH, X, Y, RIGHT, LEFT, BOTTOM
from PIL import Image, ImageTk
import cv2
import time

# Serial communication parameters
serial_port = 'COM17'  # Change as needed
baud_rate = 115200
ser = None
connected = False
current_x = 0
current_y = 0
current_z = 0

# Global variables for video streaming
video_stream = None
video_label = None
is_streaming = False
video_window = None
stored_x_plus = 0
stored_x_minus = 0
stored_y_plus = 0
stored_y_minus = 0
stored_z_plus = 0
stored_z_minus = 0

def connect_to_serial(status_label):
    global ser, connected
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        if ser.is_open:  # Check if the serial port is actually open
            connected = True
            status_label.config(text="Status: Connected", fg="green")
            print("Connected to serial port.")
            # start_position_polling()  # Start polling positions from ESP32
        else:
            connected = False
            status_label.config(text="Status: Disconnected", fg="red")
            print("Failed to open serial port.")
    except Exception as e:
        connected = False
        status_label.config(text="Status: Disconnected", fg="red")
        print(f"Error connecting to serial port: {e}")

def disconnect_serial():
    global ser, connected
    try:
        if ser and ser.is_open:
            ser.close()
        connected = False
        status_label.config(text="Status: Disconnected", fg="red")
        print("Disconnected from serial port.")
    except Exception as e:
        print(f"Error disconnecting from serial port: {e}")

def reconnect_serial(status_label):
    global connected
    while True:
        if not connected:  # Only attempt to reconnect if not connected
            print("Attempting to reconnect...")
            connect_to_serial(status_label)
        time.sleep(5)  # Wait 5 seconds before checking again

def start_reconnection_thread(status_label):
    """
    Starts a thread that continuously attempts to reconnect to the serial port
    if the connection is lost.
    """
    def reconnection_loop():
        while True:
            if not connected:  # Only attempt to reconnect if not connected
                print("Attempting to reconnect...")
                connect_to_serial(status_label)
            time.sleep(5)  # Wait 5 seconds before checking again

    # Start the reconnection thread
    threading.Thread(target=reconnection_loop, daemon=True).start()

def on_right_click(event, axis, button_type):
    global stored_x_plus, stored_x_minus, stored_y_plus, stored_y_minus, stored_z_plus, stored_z_minus
    try:
        # Ask for integer input
        value = simpledialog.askinteger("Input", f"Enter absolute value for {axis}:", parent=root)
        if value is not None:  # If the user provides a value
            # Store the value based on the axis and button type
            if axis == 'X':
                if button_type == 'plus':
                    stored_x_plus = value
                elif button_type == 'minus':
                    stored_x_minus = -value
            elif axis == 'Y':
                if button_type == 'plus':
                    stored_y_plus = value
                elif button_type == 'minus':
                    stored_y_minus = -value
            elif axis == 'Z':
                if button_type == 'plus':
                    stored_z_plus = value
                elif button_type == 'minus':
                    stored_z_minus = -value
            print(f"Stored {axis} {button_type} value: {value}")  # Debugging
    except Exception as e:
        print(f"Error handling right-click input: {e}")

def send_command(axis, value):
    global ser, connected, current_x, current_y, current_z

    if ser and ser.is_open:
        try:
            # Multiply the value by 20 before sending (if needed)
            value = int(value * 1 / 4.6012)
            
            # Send the command with the correct sign
            command = f"{axis}{value}\n"
            ser.write(command.encode('utf-8'))
            print(f"Command sent: {command.strip()}")
            
            # Update the respective axis variable based on the command
            if axis == 'X':
                current_x += value
            elif axis == 'Y':
                current_y += value
            elif axis == 'Z':
                current_z += value

            # Update real-time position display
            update_realtime_position(axis)

            # Add delay based on the value
            # delay = (abs(value) * 2.5) / 1957
            # time.sleep(4)
                
        except Exception as e:
            print(f"Error sending command: {e}")
            disconnect_serial()  # Disconnect if there's an error
    else:
        print("Serial connection is not open.")
        disconnect_serial()  # Ensure status is updated if connection is lost



# Add this line to the increment_position function
def increment_position(axis, value=1):
    global stored_x_plus, stored_y_plus, stored_z_plus
    if axis == 'X':
        send_command('X', stored_x_plus)
        stored_x_plus += value  # Update stored value for X+
    elif axis == 'Y':
        send_command('Y', stored_y_plus)
        stored_y_plus += value  # Update stored value for Y+
    elif axis == 'Z':
        send_command('Z', stored_z_plus)
        stored_z_plus += value  # Update stored value for Z+
    update_realtime_position()  # Update real-time position display

# Add this line to the decrement_position function
def decrement_position(axis, value=1):
    global stored_x_minus, stored_y_minus, stored_z_minus
    if axis == 'X':
        send_command('X', stored_x_minus)
        stored_x_minus -= value  # Update stored value for X-
    elif axis == 'Y':
        send_command('Y', stored_y_minus)
        stored_y_minus -= value  # Update stored value for Y-
    elif axis == 'Z':
        send_command('Z', stored_z_minus)
        stored_z_minus -= value  # Update stored value for Z-
    update_realtime_position()  # Update real-time position display

# Add this line to the home_axis function
def home_axis(axis):
    global current_x, current_y, current_z
    try:
        if axis == 'X':
            # Send the home position directly (absolute value)
            send_command('X', -70000)
            current_x = 0  # Reset the current position to zero
            print("X-axis calibrated to home position")
        elif axis == 'Y':
            # Send the home position directly (absolute value)
            send_command('Y', -70000)
            current_y = 0  # Reset the current position to zero
            print("Y-axis calibrated to home position")
        elif axis == 'Z':
            # Send the home position directly (absolute value)
            send_command('Z', -70000)
            current_z = 0  # Reset the current position to zero
            print("Z-axis calibrated to home position")
        
        # Update only the relevant axis in the GUI
        update_realtime_position(axis)
    except Exception as e:
        print(f"Error during {axis}-axis calibration: {e}")

def move_z_axis_with_capture(x_pos, y_pos, Zi, Zf, StepSize):
    print(f"Moving to position X:{x_pos}, Y:{y_pos}")
    send_command('X', x_pos)
    send_command('Y', y_pos)
    time.sleep(5)  # Wait for XY movement to complete
    
    # Update global positions and GUI
    global current_x, current_y, current_z
    current_x = x_pos
    current_y = y_pos
    update_realtime_position()  # Update the real-time position display
    
    print(f"Moving Z axis from {Zi} to {Zf} with step size {StepSize}")
    for position in range(Zi, Zf + StepSize, StepSize):
        send_command('Z', position)
        current_z = position  # Update current Z position
        capture_image(f"X{x_pos}_Y{y_pos}_Z{position}")
        update_realtime_position()  # Update the real-time position display
        time.sleep(1)

def move_from_excel():
    try:
        if not use_excel_var.get():
            messagebox.showinfo("Information", "Excel file option is not selected.")
            return
            
        excel_file_path = excel_file_entry.get()
        if not excel_file_path:
            messagebox.showinfo("No File Selected", "Please select an Excel file.")
            return

        # Get Z parameters from entries
        try:
            Zi = int(entry_Zi.get())
            Zf = int(entry_Zf.get())
            StepSize = int(entry_StepSize.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for Z-axis parameters")
            return

        df = pd.read_excel(excel_file_path)

        if df.empty:
            messagebox.showerror("Error", "No data found in the selected Excel file.")
            return

        for i in range(len(df)):
            x_value = int(df.iloc[i]['X'])
            y_value = int(df.iloc[i]['Y'])
            
            # Update current position values
            global current_x, current_y
            current_x = x_value
            current_y = y_value
            
            move_z_axis_with_capture(x_value, y_value, Zi, Zf, StepSize)
            time.sleep(2)  # Wait before next position

        messagebox.showinfo("Move Complete", "All movements completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

def capture_image(filename="captured_image"):
    try:
        if video_stream and video_stream.isOpened():
            ret, frame = video_stream.read()
            if ret:
                # Get the initial folder name and selected folder path from the GUI
                initial_folder_name = initial_folder_entry.get()
                selected_folder = folder_combobox.get()

                # Create the folder if it doesn't exist
                if selected_folder:
                    save_folder = os.path.join(selected_folder, initial_folder_name)
                else:
                    save_folder = os.path.join("captured_images", initial_folder_name)

                if not os.path.exists(save_folder):
                    os.makedirs(save_folder)

                # Generate the filename with timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filepath = os.path.join(save_folder, f"{filename}_{timestamp}.jpg")
                
                # Save the image
                cv2.imwrite(filepath, frame)
                print(f"Image saved at {filepath}")
            else:
                print("Error: Failed to capture image.")
        else:
            print("Error: Video stream not available.")
    except Exception as e:
        print(f"Error capturing image: {e}")


def update_realtime_position(axis=None):
    global current_x, current_y, current_z, target_x, target_y, target_z

    # Calculate the scaled values (multiplied by 4.6)
    target_x = int(current_x * 4.60135)
    target_y = int(current_y * 4.60135)
    target_z = int(current_z * 4.60135)

    # Update only the specified axis
    if axis is None or axis == 'X':
        # Get the current displayed value for X
        current_display_x = int(realtime_x_value.cget("text"))
        if current_display_x != target_x:
            step_x = 10 if target_x > current_display_x else -10
            if (step_x > 0 and current_display_x + step_x > target_x) or (step_x < 0 and current_display_x + step_x < target_x):
                current_display_x = target_x
            else:
                current_display_x += step_x
            realtime_x_value.config(text=f"{current_display_x}")

    if axis is None or axis == 'Y':
        # Get the current displayed value for Y
        current_display_y = int(realtime_y_value.cget("text"))
        if current_display_y != target_y:
            step_y = 10 if target_y > current_display_y else -10
            if (step_y > 0 and current_display_y + step_y > target_y) or (step_y < 0 and current_display_y + step_y < target_y):
                current_display_y = target_y
            else:
                current_display_y += step_y
            realtime_y_value.config(text=f"{current_display_y}")

    if axis is None or axis == 'Z':
        # Get the current displayed value for Z
        current_display_z = int(realtime_z_value.cget("text"))
        if current_display_z != target_z:
            step_z = 10 if target_z > current_display_z else -10
            if (step_z > 0 and current_display_z + step_z > target_z) or (step_z < 0 and current_display_z + step_z < target_z):
                current_display_z = target_z
            else:
                current_display_z += step_z
            realtime_z_value.config(text=f"{current_display_z}")

    # Schedule the function to run again after a short delay (e.g., 10ms for smoother animation)
    root.after(10, update_realtime_position)
def open_video_window():
    global video_window, video_label, zoom_level, canvas, h_scroll, v_scroll

    if video_window is not None:
        return  # Prevent opening multiple windows

    # Create the video window
    video_window = Toplevel(root)
    video_window.title("Microscope Camera Feed")
    video_window.configure(bg="#2c3e50")
    video_window.geometry("800x600")  

    # Create a canvas to hold the video label and add scrollbars
    canvas = Canvas(video_window, bg="black")
    canvas.pack(side=LEFT, fill=BOTH, expand=True)

    # Add horizontal and vertical scrollbars
    h_scroll = Scrollbar(video_window, orient=HORIZONTAL, command=canvas.xview)
    h_scroll.pack(side=BOTTOM, fill=X)
    v_scroll = Scrollbar(video_window, orient=VERTICAL, command=canvas.yview)
    v_scroll.pack(side=RIGHT, fill=Y)

    # Configure the canvas to work with the scrollbars
    canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
    canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # Video label for displaying frames
    video_label = Label(canvas, bg="black")
    canvas.create_window((0, 0), window=video_label, anchor="nw")

    # Handle window close event
    video_window.protocol("WM_DELETE_WINDOW", handle_video_window_close)

    # Initialize zoom level
    zoom_level = 1.0

def handle_video_window_close():
    global video_window, is_streaming
    if is_streaming:
        stop_video_stream()
    if video_window:
        video_window.destroy()
        video_window = None

def start_video_stream():
    global video_stream, is_streaming, video_window

    if video_window is None:
        open_video_window()  # Open the video window first

    if not is_streaming:
        video_stream = cv2.VideoCapture(0)
        is_streaming = True
        update_video_feed()

def stop_video_stream():
    global video_stream, is_streaming
    is_streaming = False
    if video_stream and video_stream.isOpened():
        video_stream.release()
        video_stream = None  

def update_video_feed():
    if is_streaming and video_stream and video_stream.isOpened() and video_label:
        ret, frame = video_stream.read()
        if ret:
            global zoom_level
            if zoom_level != 1.0:
                h, w = frame.shape[:2]
                new_h, new_w = int(h * zoom_level), int(w * zoom_level)
                frame = cv2.resize(frame, (new_w, new_h))

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
            video_label.config(image=photo)
            video_label.image = photo

            # Update the canvas scroll region to match the new frame size
            canvas.configure(scrollregion=canvas.bbox("all"))

        if video_window and is_streaming:
            video_window.after(10, update_video_feed)

def set_exposure(value):
    if video_stream and video_stream.isOpened():
        exposure_value = int(float(value))
        video_stream.set(cv2.CAP_PROP_EXPOSURE, exposure_value)
        print(f"Exposure set to: {exposure_value}")

def change_exposure(delta):
    current_exposure = exposure_slider.get()
    new_exposure = current_exposure + delta
    exposure_slider.set(new_exposure)
    set_exposure(new_exposure)

def change_zoom(delta):
    global zoom_level
    zoom_level += delta
    zoom_level = max(0.1, zoom_level)  # Prevent zooming out too much
    print(f"Zoom level: {zoom_level}")

def select_excel_file():
    excel_file_path = askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel Files", ".xlsx .xls"), ("All Files", ".")]
    )
    if excel_file_path:
        excel_file_entry.delete(0, 'end')
        excel_file_entry.insert(0, excel_file_path)

def increment_count():
    current = int(image_count_entry.get())
    image_count_entry.delete(0, 'end')
    image_count_entry.insert(0, str(current + 1))

def decrement_count():
    current = int(image_count_entry.get())
    if current > 1:
        image_count_entry.delete(0, 'end')
        image_count_entry.insert(0, str(current - 1))

def send_individual_axis(axis, entry):
    try:
        value = int(entry.get())
        
        if position_mode.get() == "relative":
            # In relative mode, send the value directly
            send_command(axis, value)
        else:
            if axis == 'X':
                current_x_scaled = current_x * 4.6  # Scale current_x by 4.6
                delta = value - current_x_scaled  # Calculate the difference
                send_command(axis, delta)  # Send the delta
                print(f"Sent X: {delta} (Current X: {current_x}, Target X: {value})")
            elif axis == 'Y':
                delta = value - current_y  # Calculate the difference
                send_command(axis, delta)  # Send the delta
                print(f"Sent Y: {delta} (Current Y: {current_y}, Target Y: {value})")
            elif axis == 'Z':
                delta = value - current_z  # Calculate the difference
                send_command(axis, delta)  # Send the delta
                print(f"Sent Z: {delta} (Current Z: {current_z}, Target Z: {value})")
        
        # Update real-time position display
        update_realtime_position()
        
    except ValueError:
        messagebox.showerror("Error", f"Please enter a valid number for {axis}")

# Add bit depth option to the camera controls
def set_bit_depth(bit_depth):
    if video_stream and video_stream.isOpened():
        if bit_depth == 8:
            video_stream.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 8-bit
        elif bit_depth == 10:
            video_stream.set(cv2.CAP_PROP_CONVERT_RGB, 0)  # 10-bit
        elif bit_depth == 12:
            video_stream.set(cv2.CAP_PROP_CONVERT_RGB, 0)  # 12-bit
        print(f"Bit depth set to: {bit_depth}-bit")


def send_manual_position(x_entry, y_entry, z_entry):
    try:
        x_val = int(x_entry.get())
        y_val = int(y_entry.get())
        z_val = int(z_entry.get())
        
        if position_mode.get() == "relative":
            # In relative mode, send the values directly
            send_command('X', x_val)
            send_command('Y', y_val)
            send_command('Z', z_val)
        else:
           # In absolute mode, calculate the difference and send
            current_x_scaled = current_x * 4.6  # Scale current_x by 4.61
            current_y_scaled = current_y * 4.6  # Scale current_y by 4.61
            current_z_scaled = current_z * 4.6  # Scale current_z by 4.61
            
            delta_x = x_val - current_x_scaled  # Calculate the difference for X
            delta_y = y_val - current_y_scaled  # Calculate the difference for Y
            delta_z = z_val - current_z_scaled  # Calculate the difference for Z
            
            send_command('X', delta_x)  # Send the delta for X
            send_command('Y', delta_y)  # Send the delta for Y
            send_command('Z', delta_z)  # Send the delta for Z
            
            print(f"Sent X: {delta_x} (Current X: {current_x}, Target X: {x_val})")
            print(f"Sent Y: {delta_y} (Current Y: {current_y}, Target Y: {y_val})")
            print(f"Sent Z: {delta_z} (Current Z: {current_z}, Target Z: {z_val})")
        
        # Update real-time position display
        update_realtime_position()
        
    except ValueError:
        messagebox.showerror("Error", "Please enter valid numbers for position")

def start():
    # Dictionary to store axis parameters
    axes_params = {
        'X': {'i': entry_Xi, 'f': entry_Xf, 'step': entry_XStepSize},
        'Y': {'i': entry_Yi, 'f': entry_Yf, 'step': entry_YStepSize},
        'Z': {'i': entry_Zi, 'f': entry_Zf, 'step': entry_StepSize}
    }

    # Dictionary to store validated axis ranges
    validated_axes = {}

    # Validate and store axis parameters if provided
    for axis, params in axes_params.items():
        try:
            i = int(params['i'].get())
            f = int(params['f'].get())
            step = int(params['step'].get())

            # Check if step size is greater than 0
            if step <= 0:
                messagebox.showerror("Error", f"Step size for {axis} axis must be greater than 0")
                return

            # Check if start (i) and end (f) values are valid
            if i is not None and f is not None and step is not None:
                validated_axes[axis] = {'i': i, 'f': f, 'step': step}
        except ValueError:
            # If any value is invalid, skip this axis
            continue

    # Check if at least one axis is provided
    if not validated_axes:
        messagebox.showerror("Error", "Please provide valid parameters for at least one axis (X, Y, or Z)")
        return

    # Get the number of sets (default to 1 if less than 1)
    try:
        num_sets = int(image_count_entry.get())
        if num_sets < 1:
            num_sets = 1
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid number for the number of sets")
        return

    # Get the interval duration in milliseconds
    try:
        interval_ms = int(interval_entry.get())
        if interval_ms < 0:
            interval_ms = 0
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid number for the interval duration")
        return

    # Move axes in steps and capture images for the specified number of sets
    try:
        for set_num in range(num_sets):  # Loop for the number of sets
            # Generate all combinations of positions for the provided axes
            from itertools import product

            # Create a list of ranges for each axis
            axis_ranges = []
            for axis, params in validated_axes.items():
                axis_ranges.append(range(params['i'], params['f'] + params['step'], params['step']))

            # Iterate through all combinations of positions
            for positions in product(*axis_ranges):
                # Move to the current position for the provided axes
                for idx, axis in enumerate(validated_axes.keys()):
                    target_position = positions[idx]

                    if position_mode.get() == "absolute":
                        # Calculate delta for absolute mode
                        if axis == 'X':
                            delta = target_position - (current_x * 4.6)  # Scale current_x by 4.6
                            print(target_position)
                            print(current_x)
                        elif axis == 'Y':
                            delta = target_position - (current_y * 4.6)  # Scale current_y by 4.6
                        elif axis == 'Z':
                            delta = target_position - (current_z * 4.6)  # Scale current_z by 4.6
                    else:
                        # Relative mode: send the value directly
                        delta = target_position

                    # Send the command
                    send_command(axis, delta)
                    time.sleep(1)  # Wait for movement to complete

                # Capture image at the current position
                position_str = "_".join([f"{axis}{pos}" for axis, pos in zip(validated_axes.keys(), positions)])
                initial_folder_name = initial_folder_entry.get()  # Get the initial folder name
                capture_image(f"{initial_folder_name}Set{set_num + 1}{position_str}")  # Use the initial folder name in the filename

            # Wait for the specified interval duration between sets
            if set_num < num_sets - 1:  # No need to wait after the last set
                time.sleep(interval_ms / 1000.0)

        messagebox.showinfo("Complete", f"All movements and captures completed successfully for {num_sets} set(s)!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def start_all():
    # Check if "Use Excel File" is selected
    if not use_excel_var.get():
        messagebox.showerror("Error", "Excel file option is not selected.")
        return

    # Validate Zi, Zf, and Step Size
    try:
        Zi = int(entry_Zi.get())
        Zf = int(entry_Zf.get())
        StepSize = int(entry_StepSize.get())
    except ValueError:
        messagebox.showerror("Error", "Please enter valid numbers for Zi, Zf, and Step Size")
        return

    # Ensure Zi, Zf, and Step Size are provided
    if not entry_Zi.get() or not entry_Zf.get() or not entry_StepSize.get():
        messagebox.showerror("Error", "Zi, Zf, and Step Size are mandatory")
        return

    # Get the Excel file path
    excel_file_path = excel_file_entry.get()
    if not excel_file_path:
        messagebox.showerror("Error", "Please select an Excel file.")
        return

    # Read the Excel file
    try:
        df = pd.read_excel(excel_file_path)
        if df.empty:
            messagebox.showerror("Error", "No data found in the selected Excel file.")
            return
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read Excel file: {e}")
        return

    # Process each row in the Excel file
    for i in range(len(df)):
        try:
            x_value = int(df.iloc[i]['X'])
            y_value = int(df.iloc[i]['Y'])
        except KeyError:
            messagebox.showerror("Error", "Excel file must contain 'X' and 'Y' columns.")
            return
        except ValueError:
            messagebox.showerror("Error", "Invalid data in Excel file. Ensure 'X' and 'Y' are numbers.")
            return

        # Move to X, Y position
        if position_mode.get() == "absolute":
            # Calculate delta for absolute mode
            delta_x = x_value - (current_x * 4.6)  # Scale current_x by 4.6
            delta_y = y_value - (current_y * 4.6)  # Scale current_y by 4.6
        else:
            # Relative mode: send the value directly
            delta_x = x_value
            delta_y = y_value

        send_command('X', delta_x)
        send_command('Y', delta_y)
        time.sleep(2)  # Wait for movement to complete

        # Move Z-axis from Zi to Zf in steps of StepSize
        for position in range(Zi, Zf + StepSize, StepSize):
            if position_mode.get() == "absolute":
                # Calculate delta for absolute mode
                delta_z = position - (current_z * 4.6)  # Scale current_z by 4.6
            else:
                # Relative mode: send the value directly
                delta_z = position

            send_command('Z', delta_z)  # Send Z position to the controller
            initial_folder_name = initial_folder_entry.get()  # Get the initial folder name
            capture_image(f"{initial_folder_name}_X{x_value}_Y{y_value}_Z{position}")
            time.sleep(1)  # Wait for movement and capture

    messagebox.showinfo("Complete", "All movements and captures completed successfully!")
    
# GUI Setup
root = Tk()
root.title("Microscope Stage Control")
root.configure(bg="#2c3e50")

# Set a smaller window size
root.geometry("1600x1200")  # Adjust size as needed

# Configure grid for responsiveness
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=3)

# Color variables
PRIMARY_COLOR = "#3498db"
SECONDARY_COLOR = "#000000"
DANGER_COLOR = "#e74c3c"
WHITE_COLOR = "#ffffff"
BG_COLOR = "#2c3e50"
TEXT_COLOR = "#ecf0f1"

# Left side frame
left_frame = Frame(root, bg=BG_COLOR)
left_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

# Z-axis parameters frame
xyz_axis_frame = LabelFrame(
    left_frame,
    text="Axis Parameters",
    padx=15,
    pady=15,
    bg=BG_COLOR,
    fg=PRIMARY_COLOR,
    font=("Arial", 14, "bold")
)
xyz_axis_frame.pack(pady=0)


# X-Axis Parameters
label_Xi = Label(xyz_axis_frame, text="Enter Xi (Start Position):", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
label_Xi.grid(row=0, column=0, padx=10, pady=5, sticky="w")
entry_Xi = Entry(xyz_axis_frame, font=("Arial", 12), width=20)
entry_Xi.grid(row=0, column=1, padx=10, pady=5)
entry_Xi.insert(0, "")

label_Xf = Label(xyz_axis_frame, text="Enter Xf (End Position):", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
label_Xf.grid(row=1, column=0, padx=10, pady=5, sticky="w")
entry_Xf = Entry(xyz_axis_frame, font=("Arial", 12), width=20)
entry_Xf.grid(row=1, column=1, padx=10, pady=5)
entry_Xf.insert(0, "")

label_XStepSize = Label(xyz_axis_frame, text="Enter X Step Size:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
label_XStepSize.grid(row=2, column=0, padx=10, pady=5, sticky="w")
entry_XStepSize = Entry(xyz_axis_frame, font=("Arial", 12), width=20)
entry_XStepSize.grid(row=2, column=1, padx=10, pady=5)
entry_XStepSize.insert(0, "")

# Y-Axis Parameters
label_Yi = Label(xyz_axis_frame, text="Enter Yi (Start Position):", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
label_Yi.grid(row=3, column=0, padx=10, pady=5, sticky="w")
entry_Yi = Entry(xyz_axis_frame, font=("Arial", 12), width=20)
entry_Yi.grid(row=3, column=1, padx=10, pady=5)
entry_Yi.insert(0, "")

label_Yf = Label(xyz_axis_frame, text="Enter Yf (End Position):", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
label_Yf.grid(row=4, column=0, padx=10, pady=5, sticky="w")
entry_Yf = Entry(xyz_axis_frame, font=("Arial", 12), width=20)
entry_Yf.grid(row=4, column=1, padx=10, pady=5)
entry_Yf.insert(0, "")

label_YStepSize = Label(xyz_axis_frame, text="Enter Y Step Size:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
label_YStepSize.grid(row=5, column=0, padx=10, pady=5, sticky="w")
entry_YStepSize = Entry(xyz_axis_frame, font=("Arial", 12), width=20)
entry_YStepSize.grid(row=5, column=1, padx=10, pady=5)
entry_YStepSize.insert(0, "")

# Z-Axis Parameters
label_Zi = Label(xyz_axis_frame, text="Enter Zi (Start Position):", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
label_Zi.grid(row=6, column=0, padx=10, pady=5, sticky="w")
entry_Zi = Entry(xyz_axis_frame, font=("Arial", 12), width=20)
entry_Zi.grid(row=6, column=1, padx=10, pady=5)
entry_Zi.insert(0, "")

label_Zf = Label(xyz_axis_frame, text="Enter Zf (End Position):", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
label_Zf.grid(row=7, column=0, padx=10, pady=5, sticky="w")
entry_Zf = Entry(xyz_axis_frame, font=("Arial", 12), width=20)
entry_Zf.grid(row=7, column=1, padx=10, pady=5)
entry_Zf.insert(0, "")

label_StepSize = Label(xyz_axis_frame, text="Enter Z Step Size:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
label_StepSize.grid(row=8, column=0, padx=10, pady=5, sticky="w")
entry_StepSize = Entry(xyz_axis_frame, font=("Arial", 12), width=20)
entry_StepSize.grid(row=8, column=1, padx=10, pady=5)
entry_StepSize.insert(0, "")
# Folder Selection Frame
folder_frame = LabelFrame(
    left_frame,
    text="Folder Selection",
    padx=15,
    pady=15,
    bg=BG_COLOR,
    fg=PRIMARY_COLOR,
    font=("Arial", 14, "bold")
)
folder_frame.pack(pady=0)

# Initial Folder Name Entry
initial_folder_label = Label(folder_frame, text="Initial file Name:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
initial_folder_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
initial_folder_entry = Entry(folder_frame, font=("Arial", 12), width=20)
initial_folder_entry.grid(row=0, column=1, padx=10, pady=10)
initial_folder_entry.insert(0, "imgxyz")  # Default folder name

# Folder Selection Combobox
folder_label = Label(folder_frame, text="Selected Folder:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
folder_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
folder_combobox = ttk.Combobox(folder_frame, font=("Arial", 12), width=18,)
folder_combobox.grid(row=1, column=1, padx=10, pady=10)

# Browse Button
def browse_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        folder_combobox.set(folder_path)

browse_btn = Button(
    folder_frame,
    text="Browse",
    command=browse_folder,
    bg=PRIMARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 10)
)
browse_btn.grid(row=1, column=2, padx=10, pady=10)

# Time Points Frame (Combined with Main Controls)
time_points_frame = LabelFrame(
    left_frame,
    text="Time Points ",
    padx=10,
    pady=10,
    bg=BG_COLOR,
    fg=PRIMARY_COLOR,
    font=("Arial", 14, "bold")
)
time_points_frame.pack(side="left", anchor="sw", padx=10, pady=0, fill="x")  # Fill horizontally

# Enable Time Points Checkbox
use_timepoints_var = IntVar()
timepoints_check = Checkbutton(
    time_points_frame, 
    text="Enable Time Points", 
    variable=use_timepoints_var,
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    selectcolor=BG_COLOR,
    font=("Arial", 12)
)
timepoints_check.grid(row=0, column=0, columnspan=4, padx=10, pady=5, sticky="w")

# Number of Sets
image_count_label = Label(time_points_frame, text="Number of sets:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
image_count_label.grid(row=1, column=0, padx=5, pady=5)
image_count_entry = Entry(time_points_frame, font=("Arial", 12), width=5)
image_count_entry.grid(row=1, column=1, padx=5, pady=5)
image_count_entry.insert(0, "1")

# Increment/Decrement Buttons for Number of Sets
count_controls_frame = Frame(time_points_frame, bg=BG_COLOR)
count_controls_frame.grid(row=1, column=2, padx=5, pady=5)

increment_btn = Button(
    count_controls_frame,
    text="+",
    command=increment_count,
    bg=PRIMARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 10),
    width=2
)
increment_btn.pack(side="left", padx=2)

decrement_btn = Button(
    count_controls_frame,
    text="-",
    command=decrement_count,
    bg=DANGER_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 10),
    width=2
)
decrement_btn.pack(side="left", padx=2)

# Start Button in the same row as Number of Sets
start_button = Button(
    time_points_frame,
    text="Start",
    command=start,
    bg="#27ae60",  # Green
    fg=WHITE_COLOR,
    font=("Arial", 12, "bold"),
    relief="raised",
    bd=3,
    width=10
)
start_button.grid(row=1, column=3, padx=10, pady=5)

# Time Interval
interval_label = Label(time_points_frame, text="Interval (ms):", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
interval_label.grid(row=2, column=0, padx=5, pady=5)
interval_entry = Entry(time_points_frame, font=("Arial", 12), width=5)
interval_entry.grid(row=2, column=1, padx=5, pady=5)
interval_entry.insert(0, "0")


# Center frame
center_frame = Frame(root, bg=BG_COLOR)
center_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

# Stage Control
control_frame = LabelFrame(
    center_frame,
    text="Stage Control",
    padx=50,
    pady=15,
    bg=BG_COLOR,
    fg=PRIMARY_COLOR,
    font=("Arial", 14, "bold")
)
control_frame.pack(pady=0)

# X axis controls with current position
x_plus_btn = Button(control_frame, text="X+", command=lambda: increment_position('X'), bg=PRIMARY_COLOR, fg=WHITE_COLOR, font=("Arial", 12), relief="raised", bd=3)
x_plux_plus_btn = Button(control_frame, text="X+", command=lambda: increment_position('X'), bg=PRIMARY_COLOR, fg=WHITE_COLOR, font=("Arial", 12), relief="raised", bd=3)
x_plus_btn.grid(row=0, column=1, padx=8, pady=8)
x_plus_btn.bind("<Button-3>", lambda event: on_right_click(event, 'X', 'plus'))  # Right-click binding

x_minus_btn = Button(control_frame, text="X-", command=lambda: decrement_position('X'), bg=DANGER_COLOR, fg=WHITE_COLOR, font=("Arial", 12), relief="raised", bd=3)
x_minus_btn.grid(row=0, column=2, padx=8, pady=8)
x_minus_btn.bind("<Button-3>", lambda event: on_right_click(event, 'X', 'minus'))  # Right-click binding



home_x_btn = Button(control_frame, text="Home X", command=lambda: home_axis('X'), bg=SECONDARY_COLOR, fg=WHITE_COLOR, font=("Arial", 12, "bold"), relief="raised", bd=3)
home_x_btn.grid(row=0, column=5, padx=8, pady=8)

# Y axis controls with right-click bindings
y_plus_btn = Button(control_frame, text="Y+", command=lambda: increment_position('Y'), bg=PRIMARY_COLOR, fg=WHITE_COLOR, font=("Arial", 12), relief="raised", bd=3)
y_plus_btn.grid(row=1, column=1, padx=8, pady=8)
y_plus_btn.bind("<Button-3>", lambda event: on_right_click(event, 'Y','plus'))  # Right-click binding

y_minus_btn = Button(control_frame, text="Y-", command=lambda: decrement_position('Y'), bg=DANGER_COLOR, fg=WHITE_COLOR, font=("Arial", 12), relief="raised", bd=3)
y_minus_btn.grid(row=1, column=2, padx=8, pady=8)
y_minus_btn.bind("<Button-3>", lambda event: on_right_click(event, 'Y','minus'))  # Right-click binding



home_y_btn = Button(control_frame, text="Home Y", command=lambda: home_axis('Y'), bg=SECONDARY_COLOR, fg=WHITE_COLOR, font=("Arial", 12, "bold"), relief="raised", bd=3)
home_y_btn.grid(row=1, column=5, padx=8, pady=8)

# Z axis controls with right-click bindings
z_plus_btn = Button(control_frame, text="Z+", command=lambda: increment_position('Z'), bg=PRIMARY_COLOR, fg=WHITE_COLOR, font=("Arial", 12), relief="raised", bd=3)
z_plus_btn.grid(row=2, column=1, padx=8, pady=8)
z_plus_btn.bind("<Button-3>", lambda event: on_right_click(event, 'Z', 'plus'))  # Right-click binding

z_minus_btn = Button(control_frame, text="Z-", command=lambda: decrement_position('Z'), bg=DANGER_COLOR, fg=WHITE_COLOR, font=("Arial", 12), relief="raised", bd=3)
z_minus_btn.grid(row=2, column=2, padx=8, pady=8)
z_minus_btn.bind("<Button-3>", lambda event: on_right_click(event, 'Z', 'minus'))


home_z_btn = Button(control_frame, text="Home Z", command=lambda: home_axis('Z'), bg=SECONDARY_COLOR, fg=WHITE_COLOR, font=("Arial", 12, "bold"), relief="raised", bd=3)
home_z_btn.grid(row=2, column=5, padx=8, pady=8)

# Movement Options Frame
file_selection_frame = LabelFrame(
    center_frame,  # Moved from left_frame to center_frame
    text="Movement Options",
    padx=0,
    pady=0,
    bg=BG_COLOR,
    fg=PRIMARY_COLOR,
    font=("Arial", 14, "bold")
)
file_selection_frame.pack(side="bottom", fill="x", pady=0)

use_excel_var = IntVar()
excel_check = Checkbutton(
    file_selection_frame, 
    text="Use X,Y Positions from Excel File", 
    variable=use_excel_var,
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    selectcolor=BG_COLOR,
    font=("Arial", 12)
)
excel_check.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

excel_file_label = Label(file_selection_frame, text="Excel File:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
excel_file_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
excel_file_entry = Entry(file_selection_frame, font=("Arial", 12), width=20)
excel_file_entry.grid(row=1, column=1, padx=10, pady=10)

browse_btn = Button(
    file_selection_frame,
    text="Browse",
    command=select_excel_file,
    bg=PRIMARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 10)
)
browse_btn.grid(row=1, column=2, padx=10, pady=10)

# Add Start button to the same row as Browse button
start_button_movement = Button(
    file_selection_frame,
    text="Start",
    command=start_all,  # New function for movement options
    bg="#27ae60",  # Green
    fg=WHITE_COLOR,
    font=("Arial", 10),
    relief="raised",
    bd=3,
    width=5
)
start_button_movement.grid(row=1, column=3, padx=10, pady=10)  # Place in the same row as Browse button

# Manual Position Control Frame
manual_control_frame = LabelFrame(
    center_frame,
    text="Manual Position Control",
    padx=50,
    pady=10,
    bg=BG_COLOR,
    fg=PRIMARY_COLOR,
    font=("Arial", 14, "bold")
)
manual_control_frame.pack(side="bottom", pady=0, padx=80, anchor="e")

# Position mode selection
position_mode = StringVar()
position_mode.set("absolute")

position_mode_frame = Frame(manual_control_frame, bg=BG_COLOR)
position_mode_frame.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

absolute_radio = Radiobutton(
    position_mode_frame,
    text="Absolute",
    variable=position_mode,
    value="absolute",
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    selectcolor=SECONDARY_COLOR,
    font=("Arial", 12)
)
absolute_radio.pack(side="left", padx=10)

relative_radio = Radiobutton(
    position_mode_frame,
    text="Relative",
    variable=position_mode,
    value="relative",
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    selectcolor=SECONDARY_COLOR,
    font=("Arial", 12)
)
relative_radio.pack(side="left", padx=10)

# Individual Send X button
send_x_button = Button(
    manual_control_frame,
    text="Send X",
    command=lambda: send_individual_axis('X', manual_x_entry),
    bg=PRIMARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 10),
    relief="raised",
    bd=3
)
send_x_button.grid(row=1, column=1, padx=5, pady=10)

manual_x_entry = Entry(manual_control_frame, font=("Arial", 12), width=10)
manual_x_entry.grid(row=1, column=2, padx=10, pady=10)
manual_x_entry.insert(0, "0")


# Individual Send Y button
send_y_button = Button(
    manual_control_frame,
    text="Send Y",
    command=lambda: send_individual_axis('Y', manual_y_entry),
    bg=PRIMARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 10),
    relief="raised",
    bd=3
)
send_y_button.grid(row=2, column=1, padx=5, pady=10)

manual_y_entry = Entry(manual_control_frame, font=("Arial", 12), width=10)
manual_y_entry.grid(row=2, column=2, padx=10, pady=10)
manual_y_entry.insert(0, "0")


# Individual Send Z button
send_z_button = Button(
    manual_control_frame,
    text="Send Z",
    command=lambda: send_individual_axis('Z', manual_z_entry),
    bg=PRIMARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 10),
    relief="raised",
    bd=3
)
send_z_button.grid(row=3, column=1, padx=5, pady=10)

manual_z_entry = Entry(manual_control_frame, font=("Arial", 12), width=10)
manual_z_entry.grid(row=3, column=2, padx=10, pady=10)
manual_z_entry.insert(0, "0")

# Common Send Button
common_send_button = Button(
    manual_control_frame,
    text="Send All",
    command=lambda: send_manual_position(manual_x_entry, manual_y_entry, manual_z_entry),
    bg=SECONDARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 12, "bold"),
    relief="raised",
    bd=3
)
common_send_button.grid(row=4, column=0, columnspan=3, padx=10, pady=10)

# Right Panel for Camera Controls and Real-time Position
right_frame = Frame(root, bg=BG_COLOR)
right_frame.grid(row=0, column=2, sticky="nsew", padx=0, pady=0)

# Connection status
status_label = Label(
    right_frame,
    text="Status: Disconnected",
    fg="red",
    bg=BG_COLOR,
    font=("Arial", 12, "bold")
)
status_label.pack(side="bottom", pady=20)

# Real-time position tracking
realtime_position_frame = LabelFrame(
    right_frame,
    text="Real-time Position",
    padx=15,
    pady=15,
    bg=BG_COLOR,
    fg=PRIMARY_COLOR,
    font=("Arial", 14, "bold")
)
realtime_position_frame.pack(pady=20)

# X position (real-time)
realtime_x_label = Label(realtime_position_frame, text="X:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12, "bold"))
realtime_x_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
realtime_x_value = Label(realtime_position_frame, text="0", fg=PRIMARY_COLOR, bg=BG_COLOR, font=("Arial", 14))
realtime_x_value.grid(row=0, column=1, padx=10, pady=5, sticky="w")

# Y position (real-time)
realtime_y_label = Label(realtime_position_frame, text="Y:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12, "bold"))
realtime_y_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
realtime_y_value = Label(realtime_position_frame, text="0", fg=PRIMARY_COLOR, bg=BG_COLOR, font=("Arial", 14))
realtime_y_value.grid(row=1, column=1, padx=10, pady=5, sticky="w")

# Z position (real-time)
realtime_z_label = Label(realtime_position_frame, text="Z:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12, "bold"))
realtime_z_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
realtime_z_value = Label(realtime_position_frame, text="0", fg=PRIMARY_COLOR, bg=BG_COLOR, font=("Arial", 14))
realtime_z_value.grid(row=2, column=1, padx=10, pady=5, sticky="w")

# Camera Controls Frame
camera_frame = LabelFrame(
    right_frame,
    text="Camera Controls",
    padx=0,
    pady=0,
    bg=BG_COLOR,
    fg=PRIMARY_COLOR,
    font=("Arial", 14, "bold")
)
camera_frame.pack(pady=0, fill="y")

# Controls Frame (Stacked Buttons)
controls_frame = Frame(camera_frame, bg=BG_COLOR)
controls_frame.pack(pady=20)

start_video_btn = Button(
    controls_frame,
    text="Start Video",
    command=start_video_stream,  # Starts video directly
    bg=PRIMARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 12, "bold"),
    relief="raised",
    bd=3,
    width=20
)
start_video_btn.pack(pady=5)

stop_video_btn = Button(
    controls_frame,
    text="Stop Video",
    command=stop_video_stream,
    bg=DANGER_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 12, "bold"),
    relief="raised",
    bd=3,
    width=20
)
stop_video_btn.pack(pady=5)

capture_btn = Button(
    controls_frame,
    text="Capture Image",
    command=lambda: capture_image(),
    bg=SECONDARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 12, "bold"),
    relief="raised",
    bd=3,
    width=20
)
capture_btn.pack(pady=5)

# Exposure Controls
exposure_label = Label(camera_frame, text="Exposure:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
exposure_label.pack(pady=5)

exposure_slider = ttk.Scale(camera_frame, from_=-10, to=10, orient="horizontal", command=set_exposure)
exposure_slider.pack(pady=5)

exposure_controls_frame = Frame(camera_frame, bg=BG_COLOR)
exposure_controls_frame.pack(pady=5)

exposure_decrement_btn = Button(
    exposure_controls_frame,
    text="-",
    command=lambda: change_exposure(-1),
    bg=DANGER_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 12),
    width=5
)
exposure_decrement_btn.pack(side="left", padx=5)

exposure_increment_btn = Button(
    exposure_controls_frame,
    text="+",
    command=lambda: change_exposure(1),
    bg=PRIMARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 12),
    width=5
)
exposure_increment_btn.pack(side="left", padx=5)

# Zoom Controls
zoom_label = Label(camera_frame, text="Zoom:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
zoom_label.pack(pady=5)

zoom_controls_frame = Frame(camera_frame, bg=BG_COLOR)
zoom_controls_frame.pack(pady=5)

zoom_out_btn = Button(
    zoom_controls_frame,
    text="Zoom Out",
    command=lambda: change_zoom(-0.1),
    bg=SECONDARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 12),
    width=10
)
zoom_out_btn.pack(side="left", padx=0)

zoom_in_btn = Button(
    zoom_controls_frame,
    text="Zoom In",
    command=lambda: change_zoom(0.1),
    bg=SECONDARY_COLOR,
    fg=WHITE_COLOR,
    font=("Arial", 12),
    width=10
)
zoom_in_btn.pack(side="left", padx=0)
# Add bit depth controls to the camera frame
bit_depth_frame = Frame(camera_frame, bg=BG_COLOR)
bit_depth_frame.pack(pady=10)

bit_depth_label = Label(bit_depth_frame, text="Bit Depth:", fg=TEXT_COLOR, bg=BG_COLOR, font=("Arial", 12))
bit_depth_label.pack(side="left", padx=5)

bit_depth_var = StringVar()
bit_depth_var.set("8")  # Default to 8-bit

bit_depth_8 = Radiobutton(
    bit_depth_frame,
    text="8-bit",
    variable=bit_depth_var,
    value="8",
    command=lambda: set_bit_depth(8),
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    selectcolor=SECONDARY_COLOR,
    font=("Arial", 12)
)
bit_depth_8.pack(side="left", padx=5)

bit_depth_10 = Radiobutton(
    bit_depth_frame,
    text="10-bit",
    variable=bit_depth_var,
    value="10",
    command=lambda: set_bit_depth(10),
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    selectcolor=SECONDARY_COLOR,
    font=("Arial", 12)
)
bit_depth_10.pack(side="left", padx=5)

bit_depth_12 = Radiobutton(
    bit_depth_frame,
    text="12-bit",
    variable=bit_depth_var,
    value="12",
    command=lambda: set_bit_depth(12),
    bg=BG_COLOR,
    fg=TEXT_COLOR,
    selectcolor=SECONDARY_COLOR,
    font=("Arial", 12)
)
bit_depth_12.pack(side="left", padx=5)

# Initialize the app
if __name__ == "__main__":
    root.after(100, lambda: start_reconnection_thread(status_label))  
    root.mainloop()
