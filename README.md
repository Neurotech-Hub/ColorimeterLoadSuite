# ColorimeterGUI

Desktop control panel for a three-sector donut load cell. Connects over USB serial to an ESP32 (or similar) streaming:

```
millis,d1,d2,d3,force
1234,512,480,501,820
```

at **115200 baud**. Values are raw ADC counts (typically 0–4095).

## Setup

```bash
cd ColorimeterGUI
python3 -m venv .venv
source .venv/bin/activate
pip install --no-compile -r requirements.txt
pip install --no-compile -e .
```

> On macOS system Python 3.9, use `--no-compile` so pip does not choke on a PySide6 Android recipe template.
## Run

```bash
source .venv/bin/activate
python -m colorimeter_gui
```

Or after the editable install:

```bash
colorimeter-gui
```

## Usage

1. Click **Scan** to list serial ports.
2. Select your device (e.g. `/dev/cu.usbmodem…`).
3. Click **Connect**. The app waits for the `millis,d1,d2,d3,force` header, then updates the donut, force readout, and time-series plot.
4. Click **Disconnect** to close the port.
