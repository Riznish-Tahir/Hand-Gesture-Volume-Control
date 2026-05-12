# 🖐️ STARK AUDIO — Hand Gesture Volume Control

> Control your system volume with just your hand. No buttons. No keyboard. Pure Tony Stark energy.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.9-orange?style=flat-square)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## ✨ Demo

Pinch your **thumb and index finger** together — move them apart to raise the volume, bring them close to lower it. A glowing HUD overlay tracks your hand in real time.

---

## 🚀 Features

- 🤏 **Pinch gesture** controls system volume (thumb ↔ index distance)
- 🎨 **Iron Man HUD** overlay with volume bar, FPS counter, and status
- 📱 **DroidCam support** — use your phone as the webcam
- 🔇 **Mute toggle** with `M` key
- 📊 **5-frame smoothing** for jitter-free control
- 🪟 **Windows audio integration** via `pycaw`

---

## 🛠️ Installation

> ⚠️ **Python 3.11 or 3.12 required.** MediaPipe does NOT support Python 3.13+.

### 1. Install Python 3.11
Download from [python.org](https://www.python.org/downloads/release/python-3119/) and install.

### 2. Clone this repo
```bash
git clone https://github.com/Riznish-Tahir/Hand-Gesture-Volume-Control.git
cd stark-audio-gesture-volume
```

### 3. Install dependencies
```bash
py -3.11 -m pip install opencv-python mediapipe==0.10.9 pycaw==20240330 comtypes numpy
```

---

## 📷 Camera Setup

**Built-in / USB webcam:**
```python
cap = cv2.VideoCapture(0)  # change to 1 or 2 if needed
```

**DroidCam (phone as webcam):**
1. Install [DroidCam](https://www.dev47apps.com/) on your phone and PC
2. Connect phone and PC to the same Wi-Fi
3. Note the IP shown in the DroidCam app
4. Update the script:
```python
cap = cv2.VideoCapture("http://YOUR_PHONE_IP:4747/video")
```

---

## ▶️ Usage

```bash
py -3.11 volumecontrol.py
```

| Key | Action |
|-----|--------|
| **Pinch** thumb + index | Control volume |
| **M** | Toggle mute |
| **Q** | Quit |

> ⚠️ Always press **Q in the camera window** to quit — never Ctrl+C in the terminal.

---

## ⚙️ Configuration

At the top of `volumecontrol.py`:

```python
SMOOTH_FACTOR  = 5    # higher = smoother but slower response
HAND_DIST_MIN  = 30   # px distance = 0% volume
HAND_DIST_MAX  = 220  # px distance = 100% volume
```

Adjust `HAND_DIST_MIN` / `HAND_DIST_MAX` to match your hand size and camera distance.

---

## 🧠 How It Works

```
Webcam frame
    ↓
MediaPipe Hands  →  21 hand landmarks detected
    ↓
Landmark 4 (thumb tip) + Landmark 8 (index tip)
    ↓
Euclidean distance in pixels
    ↓
np.interp  →  maps 30–220px to 0–100%
    ↓
5-frame rolling average (smoothing)
    ↓
pycaw SetMasterVolumeLevel  →  Windows system volume
```

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `opencv-python` | 4.x | Webcam capture + drawing |
| `mediapipe` | 0.10.9 | Hand landmark detection |
| `pycaw` | 20240330 | Windows audio control |
| `comtypes` | latest | COM interface for pycaw |
| `numpy` | latest | Interpolation + smoothing |

---

## 🐛 Troubleshooting

**`module 'mediapipe' has no attribute 'solutions'`**
→ You're on Python 3.13+. Use Python 3.11: `py -3.11 volumecontrol.py`

**`'AudioDevice' object has no attribute 'Activate'`**
→ Reinstall pycaw: `py -3.11 -m pip install pycaw==20240330`

**Camera not opening**
→ Try `VideoCapture(0)`, `(1)`, `(2)` until one works. For DroidCam, confirm your phone IP and that both devices are on the same Wi-Fi.

**KeyboardInterrupt / script closes suddenly**
→ Don't click the terminal while running. Press **Q** in the video window to quit.

---

## 📄 License

MIT — do whatever you want with it. A star ⭐ is appreciated!

---

*Built with Python, MediaPipe, and a Tony Stark obsession.*
