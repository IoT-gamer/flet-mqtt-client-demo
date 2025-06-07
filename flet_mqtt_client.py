"""
Flet-MQTT Client (Async Version)

This module provides a reusable, non-blocking MQTT client class designed to integrate 
seamlessly with modern async Flet applications. It uses asyncio and Flet's
background task manager to ensure the UI remains responsive.
"""

import flet as ft
import paho.mqtt.client as paho
from datetime import datetime
import logging
import json
import sys
import socket
import asyncio
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

# --- Configuration ---
@dataclass
class MQTTConfig:
    """General configuration settings for the MQTT client."""
    broker_host: str = '127.0.0.1'
    broker_port: int = 1883
    broker_user: Optional[str] = None
    broker_password: Optional[str] = None
    client_id: str = f'flet_mqtt_async_{socket.gethostname()}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    keepalive: int = 60
    qos: int = 0
    subscribe_topics: list[str] = field(default_factory=list)

# --- Flet MQTT Client Class (Async) ---
class FletMQTTClient:
    """
    An async, non-blocking MQTT client for Flet applications.
    
    This class establishes a persistent connection to an MQTT broker and handles
    all communication in a background asyncio task managed by Flet, preventing 
    UI freezes. It supports both subscribing to topics and publishing messages.
    
    The on_message_handler can be overridden in a subclass or passed as a
    callable to process incoming messages and update the Flet UI.
    """
    def __init__(self, page: ft.Page, config: MQTTConfig, on_message_handler: Optional[Callable[[paho.MQTTMessage], None]] = None):
        """
        Initializes the FletMQTTClient.
        
        Args:
            page: The Flet Page object, used to run background tasks.
            config: An MQTTConfig object with connection details.
            on_message_handler: An optional callback to handle incoming messages.
        """
        self.page = page
        self.config = config
        self.client = paho.Client(client_id=self.config.client_id)
        self.logger = self._setup_logging()
        self.connected_event = asyncio.Event()
        self._is_running = False

        if on_message_handler:
            self.on_message_handler = on_message_handler
        else:
            self.on_message_handler = self.on_message

        self._setup_callbacks()

    def _setup_logging(self) -> logging.Logger:
        """Configures logging for the client."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _setup_callbacks(self) -> None:
        """Sets up the Paho MQTT client callbacks."""
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message_internal
        self.client.on_disconnect = self._on_disconnect
        if self.config.broker_user and self.config.broker_password:
            self.client.username_pw_set(self.config.broker_user, self.config.broker_password)

    def _on_connect(self, client: paho.Client, userdata: Any, flags: dict, rc: int) -> None:
        """Callback for when the client connects to the broker."""
        if rc == 0:
            self.logger.info(f"Successfully connected to MQTT broker at {self.config.broker_host}")
            self.connected_event.set()
            if self.config.subscribe_topics:
                for topic in self.config.subscribe_topics:
                    client.subscribe(topic, qos=self.config.qos)
                    self.logger.info(f"Subscribed to topic: {topic}")
        else:
            self.logger.error(f"Failed to connect to broker with result code {rc}")
            self.connected_event.clear()

    def _on_message_internal(self, client: paho.Client, userdata: Any, msg: paho.MQTTMessage) -> None:
        """Internal callback to pass messages to the handler."""
        self.logger.info(f"Message received on topic '{msg.topic}': {msg.payload.decode()}")
        try:
            self.on_message_handler(msg)
        except Exception as e:
            self.logger.error(f"Error processing message in handler: {e}")

    def _on_disconnect(self, client: paho.Client, userdata: Any, rc: int) -> None:
        """Callback for when the client disconnects."""
        self.connected_event.clear()
        if rc != 0:
            self.logger.warning("Unexpected disconnection from MQTT broker.")

    async def _background_loop(self):
        """The background task that runs the MQTT client loop."""
        self.logger.info("MQTT background loop started.")
        while self._is_running:
            # loop() is a non-blocking call that processes network events.
            self.client.loop()
            await asyncio.sleep(0.1) # Sleep briefly to yield control
        self.logger.info("MQTT background loop stopped.")

    async def start(self) -> None:
        """Connects to the broker and starts the non-blocking background task."""
        if self._is_running:
            self.logger.warning("Client is already running.")
            return
        try:
            self.logger.info("Starting MQTT client...")
            self.connected_event.clear()
            self.client.connect(self.config.broker_host, self.config.broker_port, self.config.keepalive)
            self._is_running = True
            await self.page.run_task(self._background_loop)
        except (socket.error, OSError) as e:
            self.logger.error(f"Could not connect to MQTT broker at {self.config.broker_host}: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while starting the client: {e}")

    async def stop(self) -> None:
        """Stops the background task and disconnects gracefully."""
        if not self._is_running:
            return
        self.logger.info("Stopping MQTT client...")
        self._is_running = False
        self.client.disconnect()
        self.connected_event.clear()

    async def publish(self, topic: str, payload: Any, qos: Optional[int] = None, retain: bool = False) -> None:
        """
        Publishes a message to a given topic, waiting for a connection first.
        """
        try:
            await asyncio.wait_for(self.connected_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self.logger.error("Publish failed: MQTT client is not connected.")
            return

        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
            
        qos_level = qos if qos is not None else self.config.qos
        
        result = self.client.publish(topic, payload, qos=qos_level, retain=retain)
        
        if result.rc == paho.MQTT_ERR_SUCCESS:
            self.logger.info(f"Queued publish to topic '{topic}': {payload}")
        else:
            self.logger.error(f"Failed to queue publish to topic '{topic}'")

    def on_message(self, msg: paho.MQTTMessage) -> None:
        """Placeholder message handler, intended to be overridden by a subclass."""
        self.logger.warning(
            "on_message not implemented. Subclass FletMQTTClient and override this method "
            "to process incoming messages."
        )
