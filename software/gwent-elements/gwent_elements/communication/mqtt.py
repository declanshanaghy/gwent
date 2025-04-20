#!/usr/bin/env python3

"""
MQTT client using asyncio-mqtt
"""

import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from asyncio_mqtt import Client, MqttError


class MQTTClient:
    """
    MQTT client using asyncio-mqtt
    """
    
    def __init__(self, host="localhost", port=1883, username=None, password=None):
        """
        Initialize the MQTT client
        
        Args:
            host (str): MQTT broker host (default: localhost)
            port (int): MQTT broker port (default: 1883)
            username (str): MQTT broker username (default: None)
            password (str): MQTT broker password (default: None)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        
        self.client = None
        self.stack = None
        self.tasks = set()
        
    async def connect(self):
        """
        Connect to the MQTT broker
        """
        # Create a new exit stack
        self.stack = AsyncExitStack()
        
        # Push a callback to cancel all tasks on exit
        self.stack.push_async_callback(self._cancel_tasks)
        
        # Connect to the MQTT broker
        self.client = Client(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password
        )
        await self.stack.enter_async_context(self.client)
        
    async def disconnect(self):
        """
        Disconnect from the MQTT broker
        """
        if self.stack:
            await self.stack.aclose()
            self.stack = None
            self.client = None
            
    async def _cancel_tasks(self, tasks):
        """
        Cancel all tasks
        
        Args:
            tasks (set): Set of tasks to cancel
        """
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
    async def subscribe(self, topic_filter, callback=None):
        """
        Subscribe to a topic filter
        
        Args:
            topic_filter (str): Topic filter to subscribe to
            callback (function): Callback function that takes message as argument
        """
        if not self.client:
            raise RuntimeError("Not connected to MQTT broker")
            
        # Subscribe to the topic filter
        await self.client.subscribe(topic_filter)
        
        # If a callback is provided, create a task to handle messages
        if callback:
            # Create a filtered message manager
            manager = self.client.filtered_messages(topic_filter)
            messages = await self.stack.enter_async_context(manager)
            
            # Create a task to handle messages
            task = asyncio.create_task(self._handle_messages(messages, callback))
            self.tasks.add(task)
            
    async def _handle_messages(self, messages, callback):
        """
        Handle messages from a topic filter
        
        Args:
            messages (asyncio_mqtt.MessageIterator): Message iterator
            callback (function): Callback function that takes message as argument
        """
        async for message in messages:
            try:
                await callback(message)
            except Exception as e:
                print(f"Error handling message: {e}")
                
    async def publish(self, topic, payload, qos=0, retain=False):
        """
        Publish a message to a topic
        
        Args:
            topic (str): Topic to publish to
            payload: Message payload
            qos (int): Quality of service (default: 0)
            retain (bool): Retain flag (default: False)
        """
        if not self.client:
            raise RuntimeError("Not connected to MQTT broker")
            
        await self.client.publish(topic, payload, qos=qos, retain=retain)
        
    @staticmethod
    async def run_with_reconnect(coro, reconnect_interval=3):
        """
        Run a coroutine with automatic reconnection
        
        Args:
            coro (coroutine): Coroutine to run
            reconnect_interval (int): Reconnect interval in seconds (default: 3)
        """
        while True:
            try:
                await coro()
            except MqttError as error:
                print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
            finally:
                await asyncio.sleep(reconnect_interval)