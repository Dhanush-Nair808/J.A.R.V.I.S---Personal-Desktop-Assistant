import openwakeword
from openwakeword.model import Model
import pyaudio
import numpy as np
import subprocess
import sys

# Suppress warnings
openwakeword.utils.download_models()

# Use ONNX model
model = Model(
    wakeword_models=["hey_jarvis", "alexa"],
    inference_framework="onnx",
    ncpu=2
)

print("🎤 Listening for 'Hey Jarvis' or 'alexa'... (Press Ctrl+C to stop)")

# Audio setup
CHUNK = 1280
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

assistant_active = False
assistant_proc = None

# List of common browser processes to kill


def kill_browsers():
    
    subprocess.call(['taskkill', '/F', '/IM', 'msedge.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        prediction = model.predict(audio_data)

        # Hey Jarvis: Launch assistant
        if prediction.get("hey_jarvis", 0) > 0.5:
            print("\n✅ Hey Jarvis detected! Launching assistant...")
            if not assistant_active:
                try:
                    assistant_proc = subprocess.Popen(
                        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", "run_app.ps1"],
                        cwd=r"C:\Users\Dhanush Nair\OneDrive\Desktop\voice-assistant\voice-assistant"
                    )
                    assistant_active = True
                except Exception as e:
                    print(f"Launch error: {e}")

        # # Alexa: Terminate assistant and close browser
        # if prediction.get("jarvis_terminate", 0) > 0.4:
        #     prediction["alexa"] = 1.0
            
        if prediction.get("alexa", 0) > 0.5:
            print("\n🛑 Terminating assistant and closing browser...")
            if assistant_proc:
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(assistant_proc.pid)])
                assistant_active = False
                assistant_proc = None
            kill_browsers()  # Close all browser processes

except KeyboardInterrupt:
    print("\nStopping wake word listener...")
finally:
    if assistant_proc:
        subprocess.call(['taskkill', '/F', '/T', '/PID', str(assistant_proc.pid)])
    kill_browsers()  # Ensure browsers are closed on exit
    stream.stop_stream()
    stream.close()
    p.terminate()