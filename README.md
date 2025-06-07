# **Flet MQTT Client Demo**

This project demonstrates how to robustly integrate an MQTT client into a [Flet](https://flet.dev/) application for real-time, bi-directional communication. It provides a reusable, asynchronous MQTT client class that handles publishing and subscribing without blocking the Flet UI.

The example application is a simple "light switch" that you can control from the Flet UI. The state is synchronized via an MQTT broker, meaning you could have multiple instances of the app open, and they would all stay in sync.

## **Features**

* **Asynchronous:** Built with asyncio to work seamlessly with Flet's modern concurrency model (page.run\_task).  
* **Non-Blocking:** All MQTT communication runs in a background task, ensuring the user interface remains fast and responsive.  
* **Publish & Subscribe:** A single client class handles both publishing commands and subscribing to state updates.  
* **Reusable Class:** The FletMQTTClient is designed to be easily subclassed or used directly in any Flet project.  
* **Graceful Shutdown:** The client correctly disconnects from the MQTT broker when the Flet application window is closed.

## **Project Structure**

.  
├── flet_mqtt_client.py   \# The reusable, async FletMQTTClient class.  
└── main.py               \# The example light switch application.

* **flet_mqtt_client.py**: This is the core of the project. It contains the FletMQTTClient class that you can import into your own Flet apps to add MQTT capabilities.  
* **main.py**: This file provides a working example of how to use the FletMQTTClient class by building a simple UI.

## **Requirements**

* Python 3.8+  
* flet  
* paho-mqtt

## **Setup and Installation**

1. **Clone the repository (or download the files):**  
   git clone https://github.com/IoT-gamer/flet-mqtt-client-demo.git 
   cd flet-mqtt-client-demo

2. **Create and activate a virtual environment (recommended):**  
   \# For Linux/macOS  
   python3 \-m venv venv  
   source venv/bin/activate

   \# For Windows  
   python \-m venv venv  
   .\\venv\\Scripts\\activate

3. **Install the required packages:**  
   pip install -r requirements.txt

## **Running the Demo**

To run the example application, simply execute the main.py script:

python main.py

A Flet window should open displaying the light control UI. You can click the "Toggle Light" button to send an MQTT message. The UI updates when it receives a confirmation message back from the broker.

The application uses a public MQTT broker (broker.hivemq.com) by default, so you don't need to run your own for testing.

## **How to Use FletMQTTClient in Your Own Project**

1. **Copy flet_mqtt_client.py** to your project directory.  
2. **Import the client and config classes:**  
   from flet_mqtt_client import FletMQTTClient, MQTTConfig
3. **Create your main Flet app as an async function:**  
   import flet as ft  
   import asyncio

   async def main(page: ft.Page):  
       \# Your app logic here

   ft.app(target=main)

4. **Configure and initialize the client** inside your main function or a class that has access to the page object.  
   \# Define the configuration for your MQTT broker and topics  
   mqtt_config = MQTTConfig(  
       broker_host="your.broker.com",  
       broker_port=1883,  
       subscribe_topics=["my/device/state", "another/topic"]  
   )

   \# Initialize the client  
   \# You can either subclass it (like the example) or pass a handler  
   mqtt_client = FletMQTTClient(page, mqtt_config, on_message_handler=my_message_handler)

5. **Start the client** and set up the shutdown handler.  
   \# Start the background task  
   await mqtt_client.start()

   \# Ensure it stops cleanly  
   async def on_window_destroy(e):  
       await mqtt_client.stop()

   page.window_destroy = on_window_destroy

6. **Publish and handle messages:**  
   \# Publish a message from an event handler  
   async def on_button_click(e):  
       await mqtt_client.publish("my/device/set", {"command": "on"})

   \# Define a function to process incoming messages  
   def my_message_handler(msg):  
       print(f"New message on {msg.topic}: {msg.payload.decode()}")  
       \# Update your Flet controls here  
       \# Remember to call page.update()  
