import pyaudio
import numpy as np
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains

# Configure Selenium for Firefox
firefox_options = Options()
firefox_options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"  # Adjust as needed
service = Service(executable_path="path/to/geckodriver")  # Update this path for your system
driver = webdriver.Firefox(service=service, options=firefox_options)

# Audio monitoring settings
silence_threshold = 0.01  # Silence threshold for audio level
silence_duration = 5      # Duration (seconds) of silence before refreshing
monitoring = False        # Flag to control audio monitoring

# Initialize PyAudio
p = pyaudio.PyAudio()

# Find the output device that supports WASAPI loopback
wasapi_loopback_device = None
for i in range(p.get_device_count()):
    dev = p.get_device_info_by_index(i)
    if (dev['hostApi'] == p.get_host_api_info_by_type(pyaudio.paWASAPI)['index'] and
            dev['maxInputChannels'] > 0 and "output" in dev['name'].lower()):
        wasapi_loopback_device = i
        print(f"Using device: {dev['name']}")
        break

if wasapi_loopback_device is None:
    print("No WASAPI loopback device found.")
    driver.quit()
    exit()

def monitor_audio():
    """Function to check audio activity."""
    sample_rate = 48000  # Try this rate; adjust if needed
    try:
        stream = p.open(format=pyaudio.paFloat32,
                        channels=1,
                        rate=sample_rate,
                        input=True,
                        frames_per_buffer=1024,
                        input_device_index=wasapi_loopback_device)
    except OSError:
        print(f"Sample rate {sample_rate} Hz not supported.")
        return False

    silent_frames = 0
    for _ in range(int(sample_rate / 1024 * silence_duration)):  # Check for the duration
        data = np.frombuffer(stream.read(1024, exception_on_overflow=False), dtype=np.float32)
        if np.abs(data).mean() < silence_threshold:
            silent_frames += 1
        else:
            silent_frames = 0

        if silent_frames >= int(sample_rate / 1024 * silence_duration):
            stream.close()
            return True  # Silence detected

    stream.close()
    return False  # Audio detected

try:
    # Step 1: Wait for the user to enter a URL and navigate to it
    url = input("Enter the URL to monitor: ")
    driver.get(url)
    print("Page loaded. Type 'start' to begin monitoring for audio.")

    # Step 2: Wait for the user to start monitoring
    while not monitoring:
        command = input("Enter command: ")
        if command.lower() == "start":
            monitoring = True
            print("Started monitoring audio...")
        else:
            print("Unknown command. Type 'start' to begin monitoring.")

    # Step 3: Monitor audio and refresh if silent for too long
    while monitoring:
        if monitor_audio():
            print("No audio detected, refreshing the page...")
            driver.refresh()
            time.sleep(2)  # Give the page a moment to reload

            # Click the button specified by the XPath
            try:
                load_button = driver.find_element(By.XPATH, '//*[@id="loadVideoBtn"]')
                load_button.click()
                print("Clicked on the load video button.")
            except Exception as e:
                print("Failed to click the load video button:", e)

            # Wait for audio to be detected
            print("Waiting for audio to start...")
            audio_detected = False
            for _ in range(int(silence_duration)):
                if not monitor_audio():  # Check for audio activity
                    audio_detected = True
                    print("Audio detected.")
                    break
                time.sleep(1)  # Check every second

            # If audio isn't detected, refresh again
            if not audio_detected:
                print("Audio not detected within time window, refreshing again...")
                continue  # Go back to the start of the loop to refresh the page

            # Double-click the video frame to enter fullscreen after audio is detected
            try:
                video_frame = driver.find_element(By.XPATH, '//*[@id="my-jwplayer"]')
                actions = ActionChains(driver)
                actions.double_click(video_frame).perform()
                print("Double-clicked on the video frame to enter fullscreen.")
            except Exception as e:
                print("Failed to double-click the video frame:", e)
        
        time.sleep(silence_duration)

except KeyboardInterrupt:
    print("Stopped by user")

finally:
    driver.quit()
    p.terminate()
