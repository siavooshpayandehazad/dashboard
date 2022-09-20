#include <WiFi.h>

const char* ssid = "<SSID>";
const char* password ="<PASSWORD>";

WiFiServer server(80);

// Variable to store the HTTP request
String header;

int PWM_FREQUENCY = 1000;
int PWM_RESOUTION = 8;
//-------------------------------
int PWM_CHANNEL1 = 0;
int GPIOPIN = 32 ;
//-------------------------------
int PWM_CHANNEL2 = 1;
int GPIOPIN2 = 33 ;
//-------------------------------
int PWM_CHANNEL3 = 2;
int GPIOPIN3 = 25 ;
//-------------------------------

// Current time
unsigned long currentTime = millis();
// Previous time
unsigned long previousTime = 0;
// Define timeout time in milliseconds (example: 2000ms = 2s)
const long timeoutTime = 2000;

String getValue(String data, char separator, int index)
{
    int found = 0;
    int strIndex[] = { 0, -1 };
    int maxIndex = data.length() - 1;

    for (int i = 0; i <= maxIndex && found <= index; i++) {
        if (data.charAt(i) == separator || i == maxIndex) {
            found++;
            strIndex[0] = strIndex[1] + 1;
            strIndex[1] = (i == maxIndex) ? i+1 : i;
        }
    }
    return found > index ? data.substring(strIndex[0], strIndex[1]) : "";
}

void setup() {
  Serial.begin(115200);
  //-------------------------------
  ledcSetup(PWM_CHANNEL1, PWM_FREQUENCY, PWM_RESOUTION);
  ledcAttachPin(GPIOPIN, PWM_CHANNEL1);
  //-------------------------------
  ledcSetup(PWM_CHANNEL2, PWM_FREQUENCY, PWM_RESOUTION);
  ledcAttachPin(GPIOPIN2, PWM_CHANNEL2);
  //-------------------------------
  ledcSetup(PWM_CHANNEL3, PWM_FREQUENCY, PWM_RESOUTION);
  ledcAttachPin(GPIOPIN3, PWM_CHANNEL3);
  //-------------------------------

  // Connect to Wi-Fi network with SSID and password
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  // Print local IP address and start web server
  Serial.println("");
  Serial.println("WiFi connected.");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  server.begin();
  // set all three channels to low light.
  ledcWrite(PWM_CHANNEL1, 10);
  ledcWrite(PWM_CHANNEL2, 10);
  ledcWrite(PWM_CHANNEL3, 10);
}

void loop(){
  WiFiClient client = server.available();   // Listen for incoming clients

  if (client) {                             // If a new client connects,
    currentTime = millis();
    previousTime = currentTime;
    Serial.println("New Client.");          // print a message out in the serial port
    String currentLine = "";                // make a String to hold incoming data from the client
    while (client.connected() && currentTime - previousTime <= timeoutTime) {  // loop while the client's connected
      currentTime = millis();
      if (client.available()) {             // if there's bytes to read from the client,
        char c = client.read();             // read a byte, then
        Serial.write(c);                    // print it out the serial monitor
        header += c;
        if (c == '\n') {                    // if the byte is a newline character
          // if the current line is blank, you got two newline characters in a row.
          // that's the end of the client HTTP request, so send a response:
          if (currentLine.length() == 0) {
            // HTTP headers always start with a response code (e.g. HTTP/1.1 200 OK)
            // and a content-type so the client knows what's coming, then a blank line:
            client.println("HTTP/1.1 200 OK");
            client.println("Content-type:text/html");
            client.println("Connection: close");
            client.println();

            // turns the GPIOs on and off
           if (header.indexOf("GET /33/val") >= 0) {
              String value;
              value = getValue(header, '=', 1);
              value = getValue(value, ' ', 0);
              int intVal = value.toInt();
              ledcWrite(PWM_CHANNEL2, intVal);
            }
            else if (header.indexOf("GET /25/val") >= 0) {
              String value;
              value = getValue(header, '=', 1);
              value = getValue(value, ' ', 0);
              int intVal = value.toInt();
              ledcWrite(PWM_CHANNEL3, intVal);
            }
            else if (header.indexOf("GET /32/val") >= 0) {
              String value;
              value = getValue(header, '=', 1);
              value = getValue(value, ' ', 0);
              int intVal = value.toInt();
              ledcWrite(PWM_CHANNEL1, intVal);
            }

            // Display the HTML web page
            client.println("<!DOCTYPE html><html>");
            client.println("<head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">");
            client.println("<link rel=\"icon\" href=\"data:,\">");
            // CSS to style the on/off buttons
            // Feel free to change the background-color and font-size attributes to fit your preferences
            client.println("<style>html { font-family: Helvetica; display: inline-block; margin: 0px auto; text-align: center;}");
            client.println(".button { background-color: #4CAF50; border: none; color: white; padding: 16px 40px;");
            client.println("text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}");
            client.println(".button2 {background-color: #555555;}</style></head>");

            // Web Page Heading
            client.println("<body><h1>ESP32 Web Server</h1>");

            client.println("<script>function relased25(item){console.log(item.value); fetch(\"/25/val=\"+item.value)}</script>");
            client.println("<p>green:</p>");
            client.println("<input type=\"range\" min=\"0\" max=\"255\" value=\"0\" style=\"width:80%\" onchange=\"relased25(this)\">");

            client.println("<script>function relased32(item){console.log(item.value); fetch(\"/32/val=\"+item.value)}</script>");
            client.println("<p>blue:</p>");
            client.println("<input type=\"range\" min=\"0\" max=\"255\" value=\"0\" style=\"width:80%\" onchange=\"relased32(this)\">");

            client.println("<script>function relased33(item){console.log(item.value); fetch(\"/33/val=\"+item.value)}</script>");
            client.println("<p>red:</p>");
            client.println("<input type=\"range\" min=\"0\" max=\"255\" value=\"0\" style=\"width:80%\" onchange=\"relased33(this)\">");

            client.println("</body></html>");

            // The HTTP response ends with another blank line
            client.println();
            // Break out of the while loop
            break;
          } else { // if you got a newline, then clear currentLine
            currentLine = "";
          }
        } else if (c != '\r') {  // if you got anything else but a carriage return character,
          currentLine += c;      // add it to the end of the currentLine
        }
      }
    }
    // Clear the header variable
    header = "";
    // Close the connection
    client.stop();
    Serial.println("Client disconnected.");
    Serial.println("");
  }
}
