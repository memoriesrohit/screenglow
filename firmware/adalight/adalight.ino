// ScreenGlow Adalight receiver for Arduino (Uno / Nano / Mega) + WS2812B strip.
// Needs the FastLED library (Arduino IDE: Tools > Manage Libraries > FastLED).
// Run on the PC with:  python -m screenglow --adalight COM5

#include <FastLED.h>

#define NUM_LEDS   100     // must be >= the total from --leds
#define DATA_PIN   6       // strip DIN, through a 330 ohm resistor
#define BAUD       115200  // must match --baud
#define MAX_MA     3500    // stay under your 5 V power supply's rating

CRGB leds[NUM_LEDS];

static uint8_t readByte() {
  while (!Serial.available()) {}
  return Serial.read();
}

void setup() {
  FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setMaxPowerInVoltsAndMilliamps(5, MAX_MA);
  Serial.begin(BAUD);

  // Brief dim blue flash so you know the wiring works.
  fill_solid(leds, NUM_LEDS, CRGB(0, 0, 40));
  FastLED.show();
  delay(400);
  FastLED.clear(true);
}

void loop() {
  // Wait for the "Ada" header.
  const char magic[] = "Ada";
  for (uint8_t i = 0; i < 3;) {
    uint8_t b = readByte();
    if (b == magic[i]) i++;
    else i = (b == 'A') ? 1 : 0;
  }

  uint8_t hi = readByte(), lo = readByte(), chk = readByte();
  if (chk != (hi ^ lo ^ 0x55)) return;  // corrupted header, resync

  uint16_t count = ((uint16_t)hi << 8 | lo) + 1;
  for (uint16_t i = 0; i < count; i++) {
    uint8_t r = readByte(), g = readByte(), b = readByte();
    if (i < NUM_LEDS) leds[i] = CRGB(r, g, b);
  }
  FastLED.show();
}
