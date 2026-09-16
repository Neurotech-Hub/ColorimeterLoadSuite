#include <HublinkNodeRaven.h>

raven::HublinkNode node;

// Softpot / colorimeter wiper on Raven A0 (GPIO 18).
const int WIPER = raven::PIN_A0;

// Three-sector drive lines on Raven A1–A3 (GPIO 17, 16, 15).
const int DRIVE1 = raven::PIN_A1;
const int DRIVE2 = raven::PIN_A2;
const int DRIVE3 = raven::PIN_A3;

const int drives[3] = {DRIVE1, DRIVE2, DRIVE3};

int readSector(int activeDrive)
{
  for (int i = 0; i < 3; i++) {
    digitalWrite(drives[i], HIGH);
  }

  digitalWrite(drives[activeDrive], LOW);

  delayMicroseconds(200);

  return analogRead(WIPER);
}

int readForce()
{
  for (int i = 0; i < 3; i++) {
    digitalWrite(drives[i], HIGH);
  }

  delayMicroseconds(200);

  return analogRead(WIPER);
}

void setup()
{
  Serial.begin(115200);
  while (!Serial) {
    ; // wait for USB CDC on boards that need it
  }

  // Bring up Raven pin defaults (CPU clock, rails, LEDs, etc.).
  // beginHardware() leaves A0–A3 as INPUT; we override A1–A3 as drive outputs below.
  node.beginHardware();

  pinMode(WIPER, INPUT);

  for (int i = 0; i < 3; i++) {
    pinMode(drives[i], OUTPUT);
    digitalWrite(drives[i], HIGH);
  }

  // One header line so Python can skip non-data until this appears, then use csv.DictReader.
  Serial.println(F("millis,d1,d2,d3,force"));
}

void loop()
{
  const uint32_t t = millis();
  const int v1 = readSector(0);
  const int v2 = readSector(1);
  const int v3 = readSector(2);
  const int force = readForce();

  Serial.print(t);
  Serial.print(',');
  Serial.print(v1);
  Serial.print(',');
  Serial.print(v2);
  Serial.print(',');
  Serial.print(v3);
  Serial.print(',');
  Serial.println(force);

  delay(37);
}
