import flet as ft
from flet_mqtt_client import FletMQTTClient, MQTTConfig
import json
import time
import asyncio
from datetime import datetime

# --- Constants for the Example ---
# You can use a public broker like 'broker.hivemq.com' for testing
BROKER_HOST = "broker.hivemq.com" 
# Using a unique topic to avoid conflicts with other users
BASE_TOPIC = f"flet-mqtt-demo/user/{time.time_ns()}"
STATE_TOPIC = f"{BASE_TOPIC}/light/state"
COMMAND_TOPIC = f"{BASE_TOPIC}/light/set"


class LightControlApp(FletMQTTClient):
    """
    An example Flet application that controls a virtual light switch via MQTT.
    It inherits from FletMQTTClient to integrate MQTT functionality directly.
    """
    def __init__(self, page: ft.Page, config: MQTTConfig):
        """
        Initializes the application.
        
        Args:
            page: The Flet Page object.
            config: The MQTT configuration.
        """
        super().__init__(page, config)
        self._setup_ui()

    def _setup_ui(self):
        """Sets up the Flet user interface components."""
        self.page.title = "Flet MQTT Light Control (Async)"
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        
        self.light_icon = ft.Icon(name=ft.Icons.LIGHTBULB_OUTLINE, size=100, color=ft.Colors.GREY)
        self.status_text = ft.Text("Waiting for status...", size=24, weight=ft.FontWeight.BOLD)
        self.last_updated_text = ft.Text("Never", italic=True, color=ft.Colors.GREY_600)
        self.broker_info_text = ft.Text(f"Topic: {STATE_TOPIC}", size=12, selectable=True, text_align=ft.TextAlign.CENTER)

        self.toggle_button = ft.ElevatedButton(
            text="Toggle Light",
            on_click=self.toggle_light_state_async, # Event handlers can be async
            width=200,
            height=50,
            disabled=True 
        )

        self.page.add(
            ft.Column(
                [
                    self.light_icon,
                    self.status_text,
                    self.toggle_button,
                    ft.Divider(),
                    self.last_updated_text,
                    self.broker_info_text
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20
            )
        )
        self.page.update()

    def on_message(self, msg: 'paho.mqtt.client.MQTTMessage'):
        """
        Overrides the parent method to handle incoming MQTT messages.
        This method is called from the background MQTT loop.
        """
        try:
            payload = json.loads(msg.payload.decode())
            if 'state' in payload:
                self.update_ui(payload['state'])
        except json.JSONDecodeError:
            self.logger.error(f"Could not decode JSON payload: {msg.payload.decode()}")
        except Exception as e:
            self.logger.error(f"Error updating UI from message: {e}")

    def update_ui(self, state: str):
        """Safely updates the Flet UI based on the received state."""
        if state.upper() == "ON":
            self.light_icon.name = ft.Icons.LIGHTBULB
            self.light_icon.color = ft.Colors.YELLOW_600
            self.status_text.value = "ON"
        else: # OFF
            self.light_icon.name = ft.Icons.LIGHTBULB_OUTLINE
            self.light_icon.color = ft.Colors.GREY
            self.status_text.value = "OFF"
            
        self.last_updated_text.value = f"Last update: {datetime.now().strftime('%H:%M:%S')}"
        self.toggle_button.disabled = False
        
        # self.page.update() must be called to render the changes
        self.page.update()

    async def toggle_light_state_async(self, e: ft.ControlEvent):
        """Publishes a command to toggle the light's state."""
        current_state = self.status_text.value
        new_state = "OFF" if current_state == "ON" else "ON"
        
        self.logger.info(f"Publishing new state: {new_state}")
        # The publish method is a coroutine and should be awaited.
        await self.publish(
            topic=COMMAND_TOPIC,
            payload={"state": new_state}
        )

async def main(page: ft.Page):
    """The main async entry point for the Flet application."""
    page.title = "Flet MQTT Demo"
    
    mqtt_config = MQTTConfig(
        broker_host=BROKER_HOST,
        subscribe_topics=[STATE_TOPIC, COMMAND_TOPIC]
    )

    app = LightControlApp(page, mqtt_config)
    
    # Define the async cleanup function
    async def on_window_destroy(e):
        """Gracefully stops the MQTT client when the window is closed."""
        app.logger.info("Window closed. Stopping MQTT client...")
        await app.stop()
    
    page.window_destroy = on_window_destroy
    
    # Start the MQTT client in the background
    await app.start()
    
    # Initially publish an OFF state to get things started.
    await app.publish(STATE_TOPIC, {"state": "OFF"}, retain=True)

if __name__ == "__main__":
    ft.app(target=main)
