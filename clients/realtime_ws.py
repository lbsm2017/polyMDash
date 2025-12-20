"""
WebSocket Client for Polymarket Real-Time Data Socket (RTDS).
Handles live price updates, volume changes, and market activity.
"""

import asyncio
import json
import websockets
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealtimeWebSocket:
    """Client for Polymarket Real-Time Data Socket (RTDS)."""
    
    WS_URL = "wss://ws-live-data.polymarket.com"
    
    def __init__(self):
        """Initialize the WebSocket client."""
        self.websocket = None
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.running = False
        self._reconnect_delay = 5  # seconds
        
    async def connect(self):
        """Establish WebSocket connection."""
        try:
            self.websocket = await websockets.connect(self.WS_URL)
            self.running = True
            logger.info("WebSocket connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise
            
    async def disconnect(self):
        """Close WebSocket connection."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket disconnected")
            
    async def subscribe(
        self,
        channel: str,
        market_id: Optional[str] = None,
        callback: Optional[Callable] = None
    ):
        """
        Subscribe to a data channel.
        
        Args:
            channel: Channel type (e.g., 'price', 'volume', 'trades')
            market_id: Optional specific market to track
            callback: Function to call when data is received
        """
        subscription_key = f"{channel}:{market_id or 'all'}"
        
        # Store callback
        if subscription_key not in self.subscriptions:
            self.subscriptions[subscription_key] = []
        if callback:
            self.subscriptions[subscription_key].append(callback)
            
        # Send subscription message
        message = {
            "type": "subscribe",
            "channel": channel
        }
        if market_id:
            message["market_id"] = market_id
            
        await self._send(message)
        logger.info(f"Subscribed to {subscription_key}")
        
    async def unsubscribe(self, channel: str, market_id: Optional[str] = None):
        """
        Unsubscribe from a data channel.
        
        Args:
            channel: Channel type
            market_id: Optional specific market
        """
        subscription_key = f"{channel}:{market_id or 'all'}"
        
        if subscription_key in self.subscriptions:
            del self.subscriptions[subscription_key]
            
        message = {
            "type": "unsubscribe",
            "channel": channel
        }
        if market_id:
            message["market_id"] = market_id
            
        await self._send(message)
        logger.info(f"Unsubscribed from {subscription_key}")
        
    async def _send(self, message: Dict):
        """Send message to WebSocket."""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
            
    async def _receive_loop(self):
        """Main receive loop for WebSocket messages."""
        while self.running:
            try:
                if not self.websocket:
                    logger.warning("WebSocket not connected, attempting reconnect...")
                    await asyncio.sleep(self._reconnect_delay)
                    await self.connect()
                    continue
                    
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Route message to appropriate callbacks
                await self._handle_message(data)
                
            except websockets.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                await asyncio.sleep(self._reconnect_delay)
                try:
                    await self.connect()
                    # Resubscribe to all channels
                    await self._resubscribe()
                except Exception as e:
                    logger.error(f"Reconnection failed: {e}")
                    
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                await asyncio.sleep(1)
                
    async def _handle_message(self, data: Dict):
        """
        Handle incoming WebSocket message.
        
        Args:
            data: Parsed JSON message
        """
        channel = data.get("channel")
        market_id = data.get("market_id")
        
        # Create subscription keys to check
        keys_to_check = [
            f"{channel}:{market_id}",
            f"{channel}:all"
        ]
        
        # Call all matching callbacks
        for key in keys_to_check:
            if key in self.subscriptions:
                for callback in self.subscriptions[key]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        logger.error(f"Error in callback for {key}: {e}")
                        
    async def _resubscribe(self):
        """Resubscribe to all channels after reconnection."""
        for subscription_key in list(self.subscriptions.keys()):
            channel, market_id = subscription_key.split(":", 1)
            if market_id == "all":
                market_id = None
                
            message = {
                "type": "subscribe",
                "channel": channel
            }
            if market_id:
                message["market_id"] = market_id
                
            await self._send(message)
            logger.info(f"Resubscribed to {subscription_key}")
            
    async def start_listening(self):
        """Start the WebSocket receive loop."""
        if not self.websocket:
            await self.connect()
        await self._receive_loop()
        
    async def stop_listening(self):
        """Stop the WebSocket receive loop."""
        await self.disconnect()


class PriceTracker:
    """Helper class for tracking price updates via WebSocket."""
    
    def __init__(self):
        """Initialize price tracker."""
        self.ws_client = RealtimeWebSocket()
        self.current_prices: Dict[str, Dict] = {}
        self.price_history: Dict[str, List[Dict]] = {}
        
    async def start(self, market_ids: Optional[List[str]] = None):
        """
        Start tracking prices.
        
        Args:
            market_ids: Optional list of specific markets to track
        """
        await self.ws_client.connect()
        
        # Subscribe to price updates
        if market_ids:
            for market_id in market_ids:
                await self.ws_client.subscribe(
                    "price",
                    market_id=market_id,
                    callback=self._update_price
                )
        else:
            await self.ws_client.subscribe(
                "price",
                callback=self._update_price
            )
            
        # Start listening in background
        asyncio.create_task(self.ws_client.start_listening())
        
    async def stop(self):
        """Stop tracking prices."""
        await self.ws_client.stop_listening()
        
    async def _update_price(self, data: Dict):
        """
        Update price data from WebSocket message.
        
        Args:
            data: Price update message
        """
        market_id = data.get("market_id")
        if not market_id:
            return
            
        price_data = {
            "timestamp": datetime.now().isoformat(),
            "market_id": market_id,
            "outcome": data.get("outcome"),
            "price": data.get("price"),
            "volume": data.get("volume"),
            "liquidity": data.get("liquidity")
        }
        
        # Update current price
        self.current_prices[market_id] = price_data
        
        # Add to history
        if market_id not in self.price_history:
            self.price_history[market_id] = []
        self.price_history[market_id].append(price_data)
        
        # Keep only recent history (last 100 updates)
        if len(self.price_history[market_id]) > 100:
            self.price_history[market_id] = self.price_history[market_id][-100:]
            
        logger.debug(f"Updated price for {market_id}: {price_data['price']}")
        
    def get_current_price(self, market_id: str) -> Optional[Dict]:
        """
        Get current price for a market.
        
        Args:
            market_id: Market identifier
            
        Returns:
            Current price data or None
        """
        return self.current_prices.get(market_id)
        
    def get_price_history(
        self,
        market_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get price history for a market.
        
        Args:
            market_id: Market identifier
            limit: Optional limit on history length
            
        Returns:
            List of price data points
        """
        history = self.price_history.get(market_id, [])
        if limit:
            return history[-limit:]
        return history
        
    def get_price_change(self, market_id: str, periods: int = 10) -> Optional[float]:
        """
        Calculate price change over a number of periods.
        
        Args:
            market_id: Market identifier
            periods: Number of historical periods to compare
            
        Returns:
            Percentage price change or None
        """
        history = self.price_history.get(market_id, [])
        if len(history) < periods + 1:
            return None
            
        old_price = float(history[-periods]['price'])
        new_price = float(history[-1]['price'])
        
        if old_price == 0:
            return None
            
        return ((new_price - old_price) / old_price) * 100


if __name__ == "__main__":
    # Test the WebSocket client
    async def test():
        tracker = PriceTracker()
        
        print("Starting price tracker...")
        await tracker.start()
        
        # Let it run for 30 seconds
        print("Tracking prices for 30 seconds...")
        await asyncio.sleep(30)
        
        # Display tracked markets
        print(f"\nTracked {len(tracker.current_prices)} markets:")
        for market_id, price_data in list(tracker.current_prices.items())[:5]:
            print(f"  Market: {market_id}")
            print(f"  Price: {price_data.get('price')}")
            print(f"  Volume: {price_data.get('volume')}")
            
        await tracker.stop()
        
    asyncio.run(test())
