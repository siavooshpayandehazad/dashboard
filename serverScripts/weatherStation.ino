/*
This project uses a esp32 nodemcu along with a BMP280 module. Nothing else is used.
Configure the following constants:
* ssid
* password
* serverName
* roomNumber: provide numbers for each room
* TIME_TO_SLEEP: time span between samples
make sure I2C_SDA and I2C_SCL are pointing to the correct pins...
the rest should work out of the box.
*/



#include <HTTPClient.h>

/* get it from: https://github.com/amcewen/HttpClient
 */

#include "WiFi.h"

/*
 * To setup NTPClient Download this: https://github.com/taranais/NTPClient/archive/master.zip
 * Unzip the .zip folder and you should get NTPClient-master folder
 * Rename your folder from NTPClient-master to NTPClient
 * Move the NTPClient folder to your Arduino IDE installation libraries folder
 * Finally, re-open your Arduino IDE
*/

#include <NTPClient.h>
#include <WiFiUdp.h>

#include <esp_task_wdt.h>

const char* ssid = "<wifi name>";
const char* password =  "<wifi password>";

/*---------------------------------------------------------------------------------*/
String serverName = "http://<server ip>:5000/homeAutomation";
/*---------------------------------------------------------------------------------*/

const int LED_PIN = 2;
const String roomNumber = "1";
/*---------------------------------------------------------------------------------*/
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP);

// Variables to save date and time
String formattedDate;
String dayStamp;
String timeStamp;

#define WDT_TIMEOUT 10  /* watchdog time out 10 second*/

#define uS_TO_S_FACTOR 1000000   /* Conversion factor for micro seconds to seconds */
#define TIME_TO_SLEEP  600        /* Time ESP32 will go to sleep (in seconds) */
/*---------------------------------------------------------------------------------*/

RTC_DATA_ATTR int bootCount = 0;


#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>


#define I2C_SDA 21
#define I2C_SCL 22

#define SEALEVELPRESSURE_HPA (1013.25)

TwoWire I2CBME = TwoWire(0);
Adafruit_BME280 bme;

unsigned long delayTime;

void setup() {

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  esp_task_wdt_init(WDT_TIMEOUT, true); //enable panic so ESP32 restarts
  esp_task_wdt_add(NULL); //add current thread to WDT watch

  ++bootCount;
  Serial.begin(115200);
  Serial.println("----------------------------");
  Serial.println("waking up...");
  Serial.println("Boot number: " + String(bootCount));

  Serial.println(F("BME280 test"));
  I2CBME.begin(I2C_SDA, I2C_SCL, 100000);

  bool status;

  status = bme.begin(0x76, &I2CBME);
  if (!status) {
    Serial.println("Could not find a valid BME280 sensor, check wiring!");
    while (1);
  }

  Serial.println("-- Default Test --");
  delayTime = 10000;

  Serial.println();

  Serial.println("setting up the wifi begin..");
  WiFi.begin(ssid, password);

  Serial.println("Resetting WDT...");
  esp_task_wdt_reset();

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Connecting to WiFi..");
  }
  Serial.println("Connected to the WiFi network!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  Serial.println("----------------------------");

  Serial.println("Resetting WDT...");
  esp_task_wdt_reset();

  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  Serial.println("Setup ESP32 to sleep for every " + String(TIME_TO_SLEEP) + " Seconds");



  /* Initialize a NTPClient to get time */
  timeClient.begin();
  // Set offset time in seconds to adjust for your timezone: GMT +2 = 7200
  timeClient.setTimeOffset(7200);

  while(!timeClient.update()) {
    timeClient.forceUpdate();
  }
  /* The formattedDate comes with the following format: 2018-05-28T16:00:13Z */
  formattedDate = timeClient.getFormattedDate();

  // Extract date
  int splitT = formattedDate.indexOf("T");
  dayStamp = formattedDate.substring(0, splitT);
  Serial.print("DATE: ");
  Serial.print(dayStamp);
  // Extract time
  timeStamp = formattedDate.substring(splitT+1, formattedDate.length()-1);
  Serial.print("   HOUR: ");
  Serial.println(timeStamp);

  printValues();
  HTTPClient http;

  // Your Domain name with URL path or IP address with path
  http.begin(serverName);

  // Specify content-type header
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");

  // Data to send with HTTP POST
  String httpRequestData;

  httpRequestData = "value={\"room\": \"" + roomNumber                      + "\", " +
                           "\"temp\": \"" + bme.readTemperature()           + "\", " +
                           "\"humidity\": \"" + bme.readHumidity()              + "\", " +
                           "\"pressure\": \"" + (bme.readPressure() / 100.0F )  + "\", " +
                           "\"date\": \"" + dayStamp                        + "\", " +
                           "\"hour\": \"" + timeStamp                       + "\" "  +
                            "}";
  // Send HTTP POST request
  int httpResponseCode = -2;


  Serial.print("trying to post: ");
  Serial.println(httpRequestData);

  Serial.print("to server: ");
  Serial.println(serverName);

  httpResponseCode = http.POST(httpRequestData);

  Serial.println("Resetting WDT...");
  esp_task_wdt_reset();

  if (httpResponseCode>0) {
          Serial.print("HTTP Response code: ");
          Serial.println(httpResponseCode);
          String payload = http.getString();
          Serial.println(payload);
          for (int i = 1; i < 10; ++i)
          {
            digitalWrite(LED_PIN, LOW);
            delay(100);
            digitalWrite(LED_PIN, HIGH);
            delay(100);
          }
          digitalWrite(LED_PIN, LOW);
    }else {
          Serial.print("Error code: ");
          Serial.println(httpResponseCode);
    }

  // Free resources
  http.end();
  Serial.println("Going to sleep now");
  Serial.flush();  //Waits for the transmission of outgoing serial data to complete.
  esp_deep_sleep_start();
}

void loop() {

}

void printValues() {
  Serial.print("Temperature = ");
  Serial.print(bme.readTemperature());
  Serial.println(" *C");

  Serial.print("Pressure = ");
  Serial.print(bme.readPressure() / 100.0F);
  Serial.println(" hPa");

  Serial.print("Approx. Altitude = ");
  Serial.print(bme.readAltitude(SEALEVELPRESSURE_HPA));
  Serial.println(" m");

  Serial.print("Humidity = ");
  Serial.print(bme.readHumidity());
  Serial.println(" %");

  Serial.println();
}
