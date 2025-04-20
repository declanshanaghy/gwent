#!/usr/bin/env python3

"""
Redis client using aioredis
"""

import asyncio
import aioredis


class RedisClient:
    """
    Redis client using aioredis
    """
    
    def __init__(self, url="redis://localhost", password=None, db=0):
        """
        Initialize the Redis client
        
        Args:
            url (str): Redis URL (default: redis://localhost)
            password (str): Redis password (default: None)
            db (int): Redis database (default: 0)
        """
        self.url = url
        self.password = password
        self.db = db
        
        self.redis = None
        self.pubsub_tasks = {}
        
    async def connect(self):
        """
        Connect to Redis
        
        Returns:
            aioredis.Redis: Redis connection
        """
        if self.redis is None:
            self.redis = await aioredis.create_redis_pool(
                self.url,
                password=self.password,
                db=self.db
            )
        return self.redis
        
    async def disconnect(self):
        """
        Disconnect from Redis
        """
        if self.redis:
            # Cancel all pubsub tasks
            for task in self.pubsub_tasks.values():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
            self.pubsub_tasks = {}
            
            # Close the Redis connection
            self.redis.close()
            await self.redis.wait_closed()
            self.redis = None
            
    async def get(self, key):
        """
        Get a value from Redis
        
        Args:
            key (str): Key to get
            
        Returns:
            bytes: Value
        """
        if not self.redis:
            await self.connect()
            
        return await self.redis.get(key)
        
    async def set(self, key, value, expire=None):
        """
        Set a value in Redis
        
        Args:
            key (str): Key to set
            value: Value to set
            expire (int): Expiration time in seconds (default: None)
        """
        if not self.redis:
            await self.connect()
            
        await self.redis.set(key, value, expire=expire)
        
    async def delete(self, key):
        """
        Delete a key from Redis
        
        Args:
            key (str): Key to delete
        """
        if not self.redis:
            await self.connect()
            
        await self.redis.delete(key)
        
    async def publish(self, channel, message):
        """
        Publish a message to a channel
        
        Args:
            channel (str): Channel to publish to
            message: Message to publish
        """
        if not self.redis:
            await self.connect()
            
        await self.redis.publish(channel, message)
        
    async def subscribe(self, *channels, callback=None):
        """
        Subscribe to channels
        
        Args:
            *channels: Channels to subscribe to
            callback (function): Callback function that takes channel and message as arguments
        """
        if not self.redis:
            await self.connect()
            
        # Subscribe to channels
        channels_obj = await self.redis.subscribe(*channels)
        
        # If a callback is provided, create a task to handle messages
        if callback:
            for channel in channels_obj:
                # Create a task to handle messages
                task = asyncio.create_task(self._handle_channel(channel, callback))
                self.pubsub_tasks[channel.name] = task
                
        return channels_obj
        
    async def _handle_channel(self, channel, callback):
        """
        Handle messages from a channel
        
        Args:
            channel (aioredis.Channel): Channel to handle
            callback (function): Callback function that takes channel and message as arguments
        """
        try:
            async for message in channel.iter():
                try:
                    await callback(channel.name, message)
                except Exception as e:
                    print(f"Error handling message: {e}")
        except asyncio.CancelledError:
            pass
            
    async def unsubscribe(self, *channels):
        """
        Unsubscribe from channels
        
        Args:
            *channels: Channels to unsubscribe from
        """
        if not self.redis:
            return
            
        # Unsubscribe from channels
        await self.redis.unsubscribe(*channels)
        
        # Cancel tasks
        for channel in channels:
            if channel in self.pubsub_tasks:
                self.pubsub_tasks[channel].cancel()
                try:
                    await self.pubsub_tasks[channel]
                except asyncio.CancelledError:
                    pass
                del self.pubsub_tasks[channel]