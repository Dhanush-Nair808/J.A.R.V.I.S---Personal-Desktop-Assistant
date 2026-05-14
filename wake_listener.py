"""Wake word listener for J.A.R.V.I.S"""

import openwakeword
from openwakeword.model import Model
import pyaudio
import numpy as np
import subprocess
from pathlib import Path

# ================== WAKE WORD CONFIGURATION ==================
WAKE_WORD = "hey_jarvis"
TERMINATE_WORD = "alexa"

WAKE_SENSITIVITY = 0.5
TERMINATE_SENSITIVITY = 0.5

# ================== YOUR PROJECT PATH ==================
# Change this only if you move the project folder
PROJECT_ROOT = Path(r"C:\Users\Dhanush Nair\OneDrive\Desktop\voice-assistant\voice-assistant")
RUN_APP_PATH = PROJECT_ROOT / "run_app.ps1"
# =======================================================

openwakeword.utils.download_models()

model = Model(
    wakeword_models=[WAKE_WORD, TERMINATE_WORD],
    inference_framework="onnx",
    ncpu=2
)

print("🎤 Wake Word Listener Started")
print(f"   → Say 'Hey Jarvis' to launch")
print(f"   → Say 'Alexa' to stop")

# Audio setup
CHUNK = 1280
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

assistant_active = False
assistant_proc = None


def kill_browsers():
    for browser in ['msedge.exe']:
        subprocess.call(['taskkill', '/F', '/IM', browser], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


try:
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        prediction = model.predict(audio_data)

        # === Launch J.A.R.V.I.S ===
        if prediction.get(WAKE_WORD, 0) > WAKE_SENSITIVITY:
            print(f"\n✅ 'Hey Jarvis' detected! Launching J.A.R.V.I.S...")

            if not assistant_active:
                try:
                    if RUN_APP_PATH.exists():
                        assistant_proc = subprocess.Popen(
                            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(RUN_APP_PATH)],
                            cwd=PROJECT_ROOT
                        )
                        assistant_active = True
                        print(f"   ✅ Launched successfully from: {RUN_APP_PATH}")
                    else:
                        print(f"❌ run_app.ps1 not found at: {RUN_APP_PATH}")
                except Exception as e:
                    print(f"❌ Launch error: {e}")

        # === Terminate J.A.R.V.I.S ===
        if prediction.get(TERMINATE_WORD, 0) > TERMINATE_SENSITIVITY:
            print(f"\n🛑 'Alexa' detected! Shutting down J.A.R.V.I.S...")
            
            if assistant_proc:
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(assistant_proc.pid)])
                assistant_active = False
                assistant_proc = None
            
            kill_browsers()

except KeyboardInterrupt:
    print("\n⛔ Stopping wake word listener...")

finally:
    if assistant_proc:
        subprocess.call(['taskkill', '/F', '/T', '/PID', str(assistant_proc.pid)])
    kill_browsers()
    stream.stop_stream()
    stream.close()
    p.terminate()