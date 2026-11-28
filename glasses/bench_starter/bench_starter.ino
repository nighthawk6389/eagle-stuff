/*
  Bench starter for the Waveshare ESP32-S3-CAM-OV5640 + 1.83inch Touch LCD Module.

  What it does
    1. Powers the board's peripherals and lights the screen.
    2. Identifies the camera and tests three photo sizes (small, 2 MP, full 5 MP).
    3. Optionally tries autofocus (see USE_AUTOFOCUS).
    4. On a button press, takes a photo and shows its size and timing on the screen.
    5. Optionally serves the last photo over Wi-Fi so you can look at it
       (see WIFI_SSID).

  Arduino IDE setup
    Boards Manager:  "esp32 by Espressif Systems", version 3.2.x
    Library Manager: "Adafruit ST7735 and ST7789 Library" (it pulls in Adafruit GFX)
    Tools menu:
      Board            ESP32S3 Dev Module
      Flash Size       16MB (128Mb)
      PSRAM            OPI PSRAM
      Partition Scheme Huge APP (3MB No OTA/1MB SPIFFS)
      USB CDC On Boot  Enabled   (needed to see the Serial output over USB-C)
    Serial Monitor at 115200 baud.

  Pin numbers come from Waveshare's examples for this board
  (github.com/waveshareteam/ESP32-S3-CAM-OVxxxx). Not yet run on real hardware.
*/

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include "esp_camera.h"

// ---------------- settings you may change ----------------
#define USE_AUTOFOCUS 0        // 1 = try autofocus. Needs the library
                               // "OV5640 Auto Focus for ESP32 Camera" installed.
const char *WIFI_SSID = "";    // fill in both to view photos at http://<address>/
const char *WIFI_PASS = "";
// ----------------------------------------------------------

#if USE_AUTOFOCUS
#include "ESP32_OV5640_AF.h"
OV5640 af;
bool afReady = false;
#endif

// I2C bus shared by the IO expander, the camera's control lines and the touch chip
#define PIN_I2C_SDA 8
#define PIN_I2C_SCL 7

// IO expander: a small helper chip that switches power, resets and backlight
#define EXP_ADDR       0x24
#define EXP_REG_MODE   0x02
#define EXP_REG_OUTPUT 0x03
#define EXP_REG_PWM    0x05
#define EXP_BIT_LCD_RESET 1
// Waveshare's board support drives expander pins 0, 1, 2, 5 and 6 high at start-up.
#define EXP_DEFAULT_HIGH 0x67

// Screen (ST7789 controller over SPI). Reset and backlight go through the expander.
#define PIN_LCD_MOSI 1
#define PIN_LCD_MISO 2
#define PIN_LCD_SCLK 5
#define PIN_LCD_CS   6
#define PIN_LCD_DC   3
#define LCD_VISIBLE_W 240
#define LCD_VISIBLE_H 284

// Camera (24-pin parallel connector)
#define PIN_CAM_XCLK  38
#define PIN_CAM_PCLK  41
#define PIN_CAM_VSYNC 17
#define PIN_CAM_HREF  18
#define PIN_CAM_D0    45
#define PIN_CAM_D1    47
#define PIN_CAM_D2    48
#define PIN_CAM_D3    46
#define PIN_CAM_D4    42
#define PIN_CAM_D5    40
#define PIN_CAM_D6    39
#define PIN_CAM_D7    21

// Buttons: the board's user key and the BOOT key both work as a shutter
#define PIN_KEY  15
#define PIN_BOOT 0

// The controller has 240x320 of memory; the 1.83" glass shows 240x284 of it.
// Initialising at the full 320 keeps the offsets at zero, as Waveshare's code does.
Adafruit_ST7789 tft(&SPI, PIN_LCD_CS, PIN_LCD_DC, -1);
WebServer server(80);

uint8_t expOutputs = 0;
bool cameraOk = false;
framesize_t shutterSize = FRAMESIZE_UXGA;
uint8_t *lastJpeg = nullptr;
size_t lastJpegLen = 0;
int line = 0;

// ---------------- IO expander ----------------
void expWrite(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(EXP_ADDR);
  Wire.write(reg);
  Wire.write(value);
  if (Wire.endTransmission(true) != 0) Serial.println("IO expander: I2C write failed");
}

void expSet(uint8_t bit, bool high) {
  if (high) expOutputs |= (1 << bit); else expOutputs &= ~(1 << bit);
  expWrite(EXP_REG_OUTPUT, expOutputs);
}

void expBegin() {
  expWrite(EXP_REG_MODE, 0xFF);            // all pins are outputs
  expOutputs = EXP_DEFAULT_HIGH;
  expWrite(EXP_REG_OUTPUT, expOutputs);
  expWrite(EXP_REG_PWM, 247);              // backlight, about 97% (Waveshare's cap)
}

// ---------------- screen ----------------
void say(const String &text, uint16_t colour = ST77XX_WHITE) {
  Serial.println(text);
  if (line >= 15) {                        // screen full: start again from the top
    tft.fillRect(1, 1, LCD_VISIBLE_W - 2, LCD_VISIBLE_H - 2, ST77XX_BLACK);
    line = 0;
  }
  tft.setTextColor(colour);
  tft.setCursor(6, 6 + line * 18);
  tft.print(text);
  line++;
}

void lcdBegin() {
  expSet(EXP_BIT_LCD_RESET, false);
  delay(10);
  expSet(EXP_BIT_LCD_RESET, true);
  delay(50);
  SPI.begin(PIN_LCD_SCLK, PIN_LCD_MISO, PIN_LCD_MOSI, PIN_LCD_CS);
  tft.init(240, 320);
  tft.setSPISpeed(40000000);
  tft.invertDisplay(true);                 // Waveshare inverts colours for this panel
  tft.fillScreen(ST77XX_BLACK);
  // The border should hug the edges of the glass. If it is cut off or shifted,
  // the visible window is offset and LCD_VISIBLE_* need adjusting.
  tft.drawRect(0, 0, LCD_VISIBLE_W, LCD_VISIBLE_H, ST77XX_GREEN);
  tft.setTextSize(2);
  tft.setTextWrap(false);
}

// ---------------- camera ----------------
bool cameraBegin(framesize_t maxSize) {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = PIN_CAM_D0;  c.pin_d1 = PIN_CAM_D1;  c.pin_d2 = PIN_CAM_D2;  c.pin_d3 = PIN_CAM_D3;
  c.pin_d4 = PIN_CAM_D4;  c.pin_d5 = PIN_CAM_D5;  c.pin_d6 = PIN_CAM_D6;  c.pin_d7 = PIN_CAM_D7;
  c.pin_xclk = PIN_CAM_XCLK;
  c.pin_pclk = PIN_CAM_PCLK;
  c.pin_vsync = PIN_CAM_VSYNC;
  c.pin_href = PIN_CAM_HREF;
  c.pin_sccb_sda = PIN_I2C_SDA;
  c.pin_sccb_scl = PIN_I2C_SCL;
  c.pin_pwdn = -1;
  c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = maxSize;                  // buffers are sized for the largest photo
  c.jpeg_quality = 10;                     // lower number = better quality, bigger file
  c.fb_count = 1;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    esp_camera_deinit();
    return false;
  }
  return true;
}

// Takes one photo at the given size. Returns the JPEG size in bytes, 0 on failure.
size_t capture(framesize_t size, uint32_t *ms, bool keep) {
  sensor_t *s = esp_camera_sensor_get();
  if (!s) return 0;
  s->set_framesize(s, size);
  delay(300);                              // let exposure settle after a size change
  camera_fb_t *fb = esp_camera_fb_get();   // throw away one stale frame
  if (fb) esp_camera_fb_return(fb);
  uint32_t t0 = millis();
  fb = esp_camera_fb_get();
  *ms = millis() - t0;
  if (!fb) return 0;
  size_t len = fb->len;
  // A real JPEG starts with the bytes FF D8. Anything else is a failed capture.
  bool valid = len > 1000 && fb->buf[0] == 0xFF && fb->buf[1] == 0xD8;
  if (valid && keep) {
    free(lastJpeg);
    lastJpeg = (uint8_t *)ps_malloc(len);
    if (lastJpeg) { memcpy(lastJpeg, fb->buf, len); lastJpegLen = len; } else lastJpegLen = 0;
  }
  esp_camera_fb_return(fb);
  return valid ? len : 0;
}

void testSize(const char *name, framesize_t size, bool *worked) {
  uint32_t ms = 0;
  size_t len = capture(size, &ms, false);
  *worked = len > 0;
  if (len) say(String(name) + " " + String(len / 1024) + "KB " + String(ms) + "ms", ST77XX_GREEN);
  else     say(String(name) + " FAILED", ST77XX_RED);
}

#if USE_AUTOFOCUS
void autofocusBegin() {
  af.start(esp_camera_sensor_get());
  if (af.focusInit() != 0) { say("AF: no response", ST77XX_RED); return; }
  if (af.autoFocusMode() != 0) { say("AF: mode failed", ST77XX_RED); return; }
  afReady = true;
  say("AF: started", ST77XX_GREEN);
}
#endif

// ---------------- Wi-Fi photo viewer ----------------
void wifiBegin() {
  if (strlen(WIFI_SSID) == 0) { say("WiFi: off"); return; }
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  if (WiFi.status() != WL_CONNECTED) { say("WiFi: failed", ST77XX_RED); return; }
  server.on("/", []() {
    server.send(200, "text/html",
      "<body style='margin:0;background:#111;color:#eee;font-family:sans-serif'>"
      "<p style='padding:8px'>Press the button on the board, then reload.</p>"
      "<img src='/photo.jpg' style='max-width:100%'></body>");
  });
  server.on("/photo.jpg", []() {
    if (!lastJpegLen) { server.send(404, "text/plain", "No photo yet"); return; }
    server.setContentLength(lastJpegLen);
    server.send(200, "image/jpeg", "");
    server.sendContent((const char *)lastJpeg, lastJpegLen);
  });
  server.begin();
  say(WiFi.localIP().toString(), ST77XX_CYAN);
}

// ---------------- main ----------------
void setup() {
  Serial.begin(115200);
  delay(1500);                             // give the USB serial port time to appear
  pinMode(PIN_KEY, INPUT_PULLUP);
  pinMode(PIN_BOOT, INPUT_PULLUP);

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);
  expBegin();
  lcdBegin();
  say("Bench starter");
  say(psramFound() ? "PSRAM " + String(ESP.getPsramSize() / 1048576) + "MB" : "PSRAM MISSING",
      psramFound() ? ST77XX_WHITE : ST77XX_RED);

  // Try to set up for full 5 MP photos; fall back to 2 MP if that fails.
  cameraOk = cameraBegin(FRAMESIZE_QSXGA) || cameraBegin(FRAMESIZE_UXGA);
  if (!cameraOk) {
    say("Camera: NOT FOUND", ST77XX_RED);
  } else {
    sensor_t *s = esp_camera_sensor_get();
    char id[24];
    snprintf(id, sizeof(id), "Camera ID %04X", s->id.PID);   // 5640 is the 5 MP sensor
    say(id);
    bool vga, uxga, full;
    testSize("VGA ", FRAMESIZE_VGA, &vga);
    testSize("2MP ", FRAMESIZE_UXGA, &uxga);
    testSize("5MP ", FRAMESIZE_QSXGA, &full);
    shutterSize = full ? FRAMESIZE_QSXGA : (uxga ? FRAMESIZE_UXGA : FRAMESIZE_VGA);
#if USE_AUTOFOCUS
    autofocusBegin();
#else
    say("AF: not tried");
#endif
  }
  wifiBegin();
  say("Press key for photo", ST77XX_YELLOW);
}

void loop() {
  server.handleClient();
  static bool wasDown = false;
  bool down = digitalRead(PIN_KEY) == LOW || digitalRead(PIN_BOOT) == LOW;
  if (down && !wasDown && cameraOk) {
#if USE_AUTOFOCUS
    if (afReady) {                          // wait up to 2 s for focus to lock
      uint32_t t0 = millis();
      while (af.getFWStatus() != FW_STATUS_S_FOCUSED && millis() - t0 < 2000) delay(20);
      say(af.getFWStatus() == FW_STATUS_S_FOCUSED ? "AF: locked" : "AF: no lock");
    }
#endif
    uint32_t ms = 0;
    size_t len = capture(shutterSize, &ms, true);
    if (len) say("Photo " + String(len / 1024) + "KB " + String(ms) + "ms", ST77XX_GREEN);
    else     say("Photo FAILED", ST77XX_RED);
  }
  wasDown = down;
  delay(20);
}
