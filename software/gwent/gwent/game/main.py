import signal
import sys
import threading
import time
import queue
import traceback
from typing import List

import paho.mqtt.client as mqtt

from gwent.utils.logging import configure_logging, get_logger, DEBUG
import gwent.game.cards
import gwent.game.controller
import gwent.game.mfd
import gwent.game.player
import gwent.game.sfx
import gwent.hal
import gwent.hal.matrix


class MQTTClient:
    """Thread-safe MQTT client wrapper"""
    
    def __init__(self, host='localhost', username=None, password=None):
        self._log = get_logger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        self._client = mqtt.Client()
        self._host = host
        self._username = username
        self._password = password
        self._connected = threading.Event()
        self._lock = threading.RLock()
        self._subscriptions = {}
        
        # Set up callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        
        if username and password:
            self._client.username_pw_set(username, password)
    
    def _on_connect(self, client, userdata, flags, rc):
        self._log.info(f"Connected to MQTT broker with result code {rc}")
        self._connected.set()
        
        # Resubscribe to topics on reconnect
        with self._lock:
            for topic, callbacks in self._subscriptions.items():
                self._client.subscribe(topic)
    
    def _on_disconnect(self, client, userdata, rc):
        self._log.info(f"Disconnected from MQTT broker with result code {rc}")
        self._connected.clear()
    
    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        
        self._log.debug({
            'action': 'received raw message',
            'topic': topic,
            'message': payload,
        })
        
        # Find matching subscriptions and call callbacks
        with self._lock:
            for sub_topic, callbacks in self._subscriptions.items():
                match = mqtt.topic_matches_sub(sub_topic, topic)
                self._log.info(f"Checking topic: {topic}, {sub_topic}, {match}")
                if match:
                    for callback in callbacks:
                        try:
                            callback(topic, payload)
                        except Exception as e:
                            self._log.error(f"Error in callback: {e}", exc_info=True)
    
    def connect(self):
        """Connect to the MQTT broker"""
        self._log.info(f"Connecting to MQTT broker at {self._host}")
        self._client.connect_async(self._host)
        self._client.loop_start()
        return self._connected.wait(timeout=5)
    
    def disconnect(self):
        """Disconnect from the MQTT broker"""
        self._log.info("Disconnecting from MQTT broker")
        self._client.loop_stop()
        self._client.disconnect()
        
        # Wait for the connected event to be cleared (with timeout)
        start_time = time.time()
        timeout = 5  # 5 seconds timeout
        while self._connected.is_set() and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        return not self._connected.is_set()
    
    def subscribe(self, topic, callback):
        """Subscribe to a topic with a callback"""
        with self._lock:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = []
                self._client.subscribe(topic)
            
            self._subscriptions[topic].append(callback)
            
        self._log.info({
            'action': 'subscribe',
            'topic': topic,
        })
    
    def unsubscribe(self, topic, callback=None):
        """Unsubscribe from a topic"""
        with self._lock:
            if topic in self._subscriptions:
                if callback:
                    self._subscriptions[topic].remove(callback)
                    if not self._subscriptions[topic]:
                        del self._subscriptions[topic]
                        self._client.unsubscribe(topic)
                else:
                    del self._subscriptions[topic]
                    self._client.unsubscribe(topic)
        
        self._log.info({
            'action': 'unsubscribe',
            'topic': topic,
        })
    
    def publish(self, topic, payload, qos=1):
        """Publish a message to a topic"""
        self._log.info({
            'action': 'publish',
            'topic': topic,
            'payload': payload,
        })
        self._client.publish(topic, payload, qos=qos)


class ThreadComponent:
    """Base class for threaded components"""
    
    def __init__(self, pubsub: MQTTClient):
        self._log = get_logger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        self._pubsub = pubsub
        self._thread = None
        self._stop_event = threading.Event()
        self._initialized = threading.Event()
    
    def init(self):
        """Initialize the component"""
        self._log.debug("Initializing component")
        self._initialized.set()
    
    def start(self):
        """Start the component in a new thread"""
        if self._thread is not None and self._thread.is_alive():
            self._log.warning("Component already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()
    
    def _run(self):
        """Main thread function"""
        self._log.info("Component started")
        try:
            self.run()
        except Exception as e:
            self._log.error(f"Error in component thread: {e}", exc_info=True)
        finally:
            self._log.info("Component stopped")
    
    def run(self):
        """Override this method in subclasses"""
        while not self._stop_event.is_set():
            time.sleep(0.1)
    
    def shutdown(self):
        """Shutdown the component"""
        self._log.info("Shutting down component")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
            if self._thread.is_alive():
                self._log.warning("Component thread did not terminate gracefully")


class Gwent:
    """Main Gwent application class"""
    
    def __init__(self):
        self._log = get_logger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        self.pubsub = None
        self.components = None
        self._stop_event = threading.Event()
    
    def close_pubsub(self):
        """Close the MQTT connection"""
        if self.pubsub:
            self._log.info('Closing pubsub')
            self.pubsub.disconnect()
    
    def shutdown_components(self):
        """Shutdown all components"""
        if self.components:
            self._log.info('Shutting down components')
            for component in self.components:
                component.shutdown()
    
    def shutdown(self):
        """Shutdown the application"""
        self._log.info('Shutting down application')
        self.shutdown_components()
        self.close_pubsub()
        self._stop_event.set()
    
    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        sig_name = signal.Signals(signum).name
        self._log.info(f'Received exit signal {sig_name}...')
        self.shutdown()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful exit"""
        for sig in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                   signal.SIGQUIT, signal.SIGTERM):
            signal.signal(sig, self.signal_handler)
    
    def create_components(self):
        """Create all application components"""
        self._log.info('Creating components')
        
        # Create component adapters
        self.components = []
        self.components.append(gwent.game.controller.Controller(self.pubsub))
        self.components.append(gwent.game.player.Player(gwent.game.controller.PLAYER_ONE, self.pubsub, mux_channel=gwent.hal.matrix.MATRIX_CHANNEL_DEFAULT))
        self.components.append(gwent.game.player.Player(gwent.game.controller.PLAYER_TWO, self.pubsub, mux_channel=gwent.hal.matrix.MATRIX_CHANNEL_SEVEN))
        self.components.append(gwent.game.cards.Reader(self.pubsub))
        self.components.append(gwent.game.mfd.MFD(self.pubsub))
        self.components.append(gwent.game.sfx.SFX(self.pubsub))
        
    def initialize_components(self):
        """Initialize all components"""
        for component in self.components:
            component.init()
    
    def start_components(self):
        """Start all components"""
        self._log.info('Starting components')
        for component in self.components:
            component.start()
    
    def run(self):
        """Run the application"""
        self._log.info('Starting Gwent application')
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Connect to MQTT broker
        self.pubsub = MQTTClient('localhost', username='geralt', password='gwent')
        if not self.pubsub.connect():
            self._log.error('Failed to connect to MQTT broker')
            return
        
        # Create and start components
        self.create_components()
        self.initialize_components()
        self.start_components()
        
        # Wait for shutdown signal
        try:
            while not self._stop_event.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            self._log.info('Keyboard interrupt received')
        finally:
            self.shutdown()


def run():
    """Run the Gwent application"""
    configure_logging(level=DEBUG, log_stdout=True)
    try:
        Gwent().run()
    except Exception as ex:
        logger = get_logger(__name__)
        exception_type, exception_value, trace = sys.exc_info()
        trace_string = "\n\t".join(traceback.format_tb(trace))
        logger.error(f"Exception type: {exception_type}") # <class 'RuntimeError'>
        logger.error(f"Exception value: {exception_value}") # This is an error
        print(trace_string)


if __name__ == '__main__':
    run()
