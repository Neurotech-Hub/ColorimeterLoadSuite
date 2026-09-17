# ColorimeterGUI

Desktop control panel for a three-sector donut load cell. Connects over USB serial to an ESP32 (or similar) streaming:

```
millis,d1,d2,d3,force
1234,512,480,501,820
```

at **115200 baud**. `d1`/`d2`/`d3`/`force` are **load in grams** (not raw ADC). Firmware converts each sector ADC with:

`Load [g] = 0.0015649·ADC² − 11.5986·ADC + 21590.5`

only when `ADC < 3900` (active contact); otherwise that sector reports `0`. `force` is the mean of the three sector loads (g).

Each serial line is emitted every **50 ms**. During that window the firmware round-robins the three sectors continuously (~50+ ADC samples each), averages the raw ADC, then applies the load fit once. Drive-switch settle is **200 µs** (≈6τ for the 330 Ω × 0.1 µF ADC node).

Firmware lives in [`arduino/ColorimeterLoadSensor`](arduino/ColorimeterLoadSensor).

## Hardware

Raven (ESP32-S3) senses a three-sector softpot / load cell: common **wiper** plus three **drive** lines. One sector is measured at a time by driving that line **LOW** and holding the others **HIGH**.

| Signal | Raven pin |
|--------|-----------|
| Wiper (ADC) | `PIN_A0` |
| Sector 1 drive | `PIN_A1` |
| Sector 2 drive | `PIN_A2` |
| Sector 3 drive | `PIN_A3` |

### Analog front-end

```text
                         3.3V (VDD)
                            |
                         3.3 kΩ          pull-up
                            |
         softpot wiper -----+---- 330 Ω ---- PIN_A0 (ADC)
                            |
                         0.1 µF          to GND
                            |
                           GND

         sector 1 ----------- PIN_A1
         sector 2 ----------- PIN_A2
         sector 3 ----------- PIN_A3
```

- **3.3 kΩ** to VDD — forms a divider with the active sector resistance (~open unloaded → ~300 Ω heavy press).
- **330 Ω** series — isolation into the ADC.
- **0.1 µF** from `PIN_A0` to GND — supply bypass / noise filter on the sample node.

Unloaded, the pull-up drives the ADC toward full scale (~4095). Pressing a sector lowers resistance to the active (LOW) drive and pulls the reading down. The map is nonlinear in force.

## Setup

```bash
cd ColorimeterGUI
python3 -m venv .venv
source .venv/bin/activate
pip install --no-compile -r requirements.txt
pip install --no-compile -e .
python scripts/install_fonts.py
```

> On macOS system Python 3.9, use `--no-compile` so pip does not choke on a PySide6 Android recipe template.

`install_fonts.py` downloads **DSEG7 Classic** (OFL) into `src/colorimeter_gui/assets/fonts/` so the force readout uses a 7-segment face without a system font install. Safe to re-run; it skips if the files are already present.

## Run

```bash
source .venv/bin/activate
python run.py
```

Or:

```bash
python -m colorimeter_gui
```

## Usage

1. Click **Scan** to list serial ports.
2. Select your device (e.g. `/dev/cu.usbmodem…`).
3. Click **Connect** — the app parses CSV sample lines (`millis,d1,d2,d3,force`) and updates the donut, force readout, and time-series plot.
4. Optional: in the footer, choose a save folder, then **Start Session** / **Stop Session** to record force to `load_YYYYMMDD-HHMMSS.csv` (`Datetime` with ms, `Force` in grams).
5. Click **Disconnect** to close the port.
