#include <b64.h>
#include <ESP8266HTTPClient.h>



/* get it from: https://github.com/amcewen/HttpClient
 */
 #include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <WiFiClient.h>


ESP8266WiFiMulti WiFiMulti;

#include <AHT10.h>

/*
 * To setup NTPClient Download this: https://github.com/taranais/NTPClient/archive/master.zip
 * Unzip the .zip folder and you should get NTPClient-master folder
 * Rename your folder from NTPClient-master to NTPClient
 * Move the NTPClient folder to your Arduino IDE installation libraries folder
 * Finally, re-open your Arduino IDE
*/

#include <NTPClient.h>
#include <WiFiUdp.h>
#include <time.h>
#include <TimeLib.h>
#include <Timezone.h>

const char* ssid = "<wifi name>";
const char* password =  "<wifi password>";

/*---------------------------------------------------------------------------------*/
String serverName = "http://<server ip>:5000/homeAutomation";
/*---------------------------------------------------------------------------------*/

const int LED_PIN = 2;
const String roomNumber = "3";
/*---------------------------------------------------------------------------------*/
WiFiUDP ntpUDP;


int GTMOffset = 1; // SET TO UTC TIME
NTPClient timeClient(ntpUDP, "europe.pool.ntp.org", GTMOffset*60*60, 60*60*1000);


// Variables to save date and time
String formattedDate;
String dayStamp;
String timeStamp;

// Central European Time (Frankfurt, Paris)
TimeChangeRule CEST = {"CEST", Last, Sun, Mar, 2, 120};     // Central European Summer Time
TimeChangeRule CET = {"CET ", Last, Sun, Oct, 3, 60};       // Central European Standard Time
Timezone CE(CEST, CET);

#define WDT_TIMEOUT 10  /* watchdog time out 10 second*/

#define mS_TO_S_FACTOR 1000   /* Conversion factor for mili seconds to seconds */
#define TIME_TO_SLEEP  600        /* Time ESP32 will go to sleep (in seconds) */
/*---------------------------------------------------------------------------------*/

int bootCount = 0;


#include <Wire.h>
#include <Adafruit_Sensor.h>
// #include <Adafruit_BMP280.h>
#include <AHT10.h>

uint8_t readStatus = 0;


#define I2C_SDA 21
#define I2C_SCL 22

#define SEALEVELPRESSURE_HPA (1013.25)

// Adafruit_BMP280 bmp; // I2C

AHT10 myAHT10(AHT10_ADDRESS_0X38);

unsigned long delayTime;

/*
void BMP280Test () {
  Serial.println(F("BMP280 test"));
  unsigned status;

  status = bmp.begin(0x76);
  if (!status) {
    Serial.println(F("Could not find a valid BMP280 sensor, check wiring or "
                      "try a different address!"));
    Serial.print("SensorID was: 0x"); Serial.println(bmp.sensorID(),16);
    Serial.print("        ID of 0xFF probably means a bad address, a BMP 180 or BMP 085\n");
    Serial.print("   ID of 0x56-0x58 represents a BMP 280,\n");
    Serial.print("        ID of 0x60 represents a BME 280.\n");
    Serial.print("        ID of 0x61 represents a BME 680.\n");
    while (1) delay(10);
  }

  // Default settings from datasheet.
  bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,     // Operating Mode. //
                  Adafruit_BMP280::SAMPLING_X2,     // Temp. oversampling //
                  Adafruit_BMP280::SAMPLING_X16,    // Pressure oversampling //
                  Adafruit_BMP280::FILTER_X16,      // Filtering. //
                  Adafruit_BMP280::STANDBY_MS_500); // Standby time. //
}
*/

void AH10Test (){
  Serial.println(F("AHT10 test"));

  while (myAHT10.begin() != true)
  {
    Serial.println(F("AHT10 not connected or fail to load calibration coefficient")); //(F()) save string to flash & keeps dynamic memory free
    delay(5000);
  }
  Serial.println(F("AHT10 OK"));
  readStatus = myAHT10.readRawData(); //read 6 bytes from AHT10 over I2C

  if (readStatus != AHT10_ERROR)
  {
    Serial.print(F("Temperature: ")); Serial.print(myAHT10.readTemperature(AHT10_USE_READ_DATA)); Serial.println(F(" +-0.3C"));
    Serial.print(F("Humidity...: ")); Serial.print(myAHT10.readHumidity(AHT10_USE_READ_DATA));    Serial.println(F(" +-2%"));
  }
}


void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  ESP.wdtEnable(WDT_TIMEOUT);

  ++bootCount;
  Serial.begin(115200);
  Serial.println("----------------------------");
  Serial.println("waking up...");
  Serial.println("Boot number: " + String(bootCount));


  AH10Test();

  //BMP280Test();

  Serial.println();

  Serial.println("setting up the wifi begin..");
  WiFi.mode(WIFI_STA);
  WiFiMulti.addAP(ssid, password);

  Serial.println("Resetting WDT...");
  ESP.wdtFeed();


  while (WiFiMulti.run() != WL_CONNECTED) {
    delay(500);
    Serial.println("Connecting to WiFi..");
  }

  WiFiClient client;

  Serial.println("Connected to the WiFi network!");
  Serial.println("----------------------------");

  Serial.println("Resetting WDT...");
  ESP.wdtFeed();



  /* Initialize a NTPClient to get time */
  timeClient.begin();
  // Set offset time in seconds to adjust for your timezone: GMT +2 = 7200
  //timeClient.setTimeOffset(7200);

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

  //printValues();
  HTTPClient http;

  // Your Domain name with URL path or IP address with path
  http.begin(client, serverName);

  // Specify content-type header
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");

  // Data to send with HTTP POST
  String httpRequestData;

  httpRequestData = "value={\"room\": \"" + roomNumber                      + "\", " +
                           "\"temp\": \"" + myAHT10.readTemperature(AHT10_USE_READ_DATA)           + "\", " +
                           "\"humidity\": \"" +  myAHT10.readHumidity(AHT10_USE_READ_DATA)    + "\", " +
                           "\"pressure\": \"" + 0  + "\", " +
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
  ESP.wdtFeed();

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
    }else {
          Serial.print("Error code: ");
          Serial.println(httpResponseCode);
    }

  // Free resources
  http.end();
  Serial.flush();  //Waits for the transmission of outgoing serial data to complete.

  Serial.println(" going into deep sleep...");
  ESP.deepSleep(60e7);
}

void loop() {
  //delay(TIME_TO_SLEEP*mS_TO_S_FACTOR);
  //setup();
}

/*
void printValues() {
  Serial.print("Temperature = ");
  Serial.print(bmp.readTemperature());
  Serial.println(" *C");

  Serial.print("Pressure = ");
  Serial.print(bmp.readPressure() / 100.0F);
  Serial.println(" hPa");

  Serial.print("Approx. Altitude = ");
  Serial.print(bmp.readAltitude(SEALEVELPRESSURE_HPA));
  Serial.println(" m");

  Serial.print("Humidity = ");
  //Serial.print(bmp.readHumidity());
  Serial.println(" %");

  Serial.println();
}
*/
