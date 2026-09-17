#include <HublinkNodeRaven.h>

raven::HublinkNode node;

// Softpot / colorimeter wiper on Raven A0 (GPIO 18).
const int WIPER = raven::PIN_A0;

// Three-sector drive lines on Raven A1–A3 (GPIO 17, 16, 15).
const int DRIVE1 = raven::PIN_A1;
const int DRIVE2 = raven::PIN_A2;
const int DRIVE3 = raven::PIN_A3;

const int drives[3] = {DRIVE1, DRIVE2, DRIVE3};

// ADC above this is treated as unloaded (no meaningful softpot contact).
const int ADC_ACTIVE_MAX = 3900;

// Quadratic fit: Load [grams] = a*ADC^2 + b*ADC + c  (ADC in active region only).
const float LOAD_A = 0.0015649f;
const float LOAD_B = -11.5986f;
const float LOAD_C = 21590.5f;

// Analog settle after drive switch.
// Front-end: 330 Ω series into 0.1 µF on PIN_A0 → τ ≈ 33 µs; 200 µs ≈ 6τ.
const uint32_t SETTLE_US = 200;

// Serial report period. Acquisition fills this window (no idle delay).
const uint32_t REPORT_MS = 50;

int adcToLoad(int adc)
{
  // Returns sector load in grams (0 when below activation / invalid).
  if (adc >= ADC_ACTIVE_MAX)
  {
    return 0;
  }

  const float x = static_cast<float>(adc);
  const float load_g = LOAD_A * x * x + LOAD_B * x + LOAD_C;
  if (load_g <= 0.0f)
  {
    return 0;
  }
  return static_cast<int>(load_g + 0.5f); // round to nearest gram
}

int readSectorAdc(int activeDrive)
{
  for (int i = 0; i < 3; i++)
  {
    digitalWrite(drives[i], HIGH);
  }

  digitalWrite(drives[activeDrive], LOW);
  delayMicroseconds(SETTLE_US);
  return analogRead(WIPER);
}

void setup()
{
  Serial.begin(115200);
  while (!Serial)
  {
    ; // wait for USB CDC on boards that need it
  }

  // Bring up Raven pin defaults (CPU clock, rails, LEDs, etc.).
  // beginHardware() leaves A0–A3 as INPUT; we override A1–A3 as drive outputs below.
  node.beginHardware();

  pinMode(WIPER, INPUT);

  for (int i = 0; i < 3; i++)
  {
    pinMode(drives[i], OUTPUT);
    digitalWrite(drives[i], HIGH);
  }

  // Header: d1/d2/d3/force are load in grams (not raw ADC).
  Serial.println(F("millis,d1,d2,d3,force"));
}

void loop()
{
  // Spend the full report interval sampling; average raw ADC, then convert once.
  // One round-robin of 3 sectors is ~0.7–1 ms, so expect ~50+ averages per line.
  const uint32_t t0 = millis();
  uint32_t sum1 = 0;
  uint32_t sum2 = 0;
  uint32_t sum3 = 0;
  uint32_t n = 0;

  do
  {
    sum1 += static_cast<uint32_t>(readSectorAdc(0));
    sum2 += static_cast<uint32_t>(readSectorAdc(1));
    sum3 += static_cast<uint32_t>(readSectorAdc(2));
    n++;
  } while ((millis() - t0) < REPORT_MS);

  const int avg1 = static_cast<int>(sum1 / n);
  const int avg2 = static_cast<int>(sum2 / n);
  const int avg3 = static_cast<int>(sum3 / n);

  const int v1 = adcToLoad(avg1);
  const int v2 = adcToLoad(avg2);
  const int v3 = adcToLoad(avg3);
  const int force = (v1 + v2 + v3) / 3;

  Serial.print(t0);
  Serial.print(',');
  Serial.print(v1);
  Serial.print(',');
  Serial.print(v2);
  Serial.print(',');
  Serial.print(v3);
  Serial.print(',');
  Serial.println(force);
}
