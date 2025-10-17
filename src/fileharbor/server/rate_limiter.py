"""
FileHarbor Rate Limiter

Token bucket rate limiter for bandwidth throttling.
"""

import time
import threading
from typing import Dict

from fileharbor.common.constants import RATE_LIMITER_INTERVAL


class RateLimiter:
    """
    Token bucket rate limiter for bandwidth control.
    
    Implements per-client rate limiting using the token bucket algorithm.
    """
    
    def __init__(self, rate_limit_bps: int):
        """
        Initialize rate limiter.
        
        Args:
            rate_limit_bps: Maximum bytes per second (0 = unlimited)
        """
        self.rate_limit_bps = rate_limit_bps
        self.unlimited = (rate_limit_bps == 0)
        
        if not self.unlimited:
            self.tokens = float(rate_limit_bps)
            self.max_tokens = float(rate_limit_bps)
            self.last_update = time.time()
            self.lock = threading.Lock()
    
    def acquire(self, byte_count: int) -> float:
        """
        Acquire tokens for sending/receiving bytes.
        
        This method blocks if necessary to enforce the rate limit.
        
        Args:
            byte_count: Number of bytes to send/receive
            
        Returns:
            Time waited in seconds (0 if no wait)
        """
        if self.unlimited:
            return 0.0
        
        with self.lock:
            # Refill tokens based on time elapsed
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.max_tokens,
                self.tokens + (elapsed * self.rate_limit_bps)
            )
            self.last_update = now
            
            # If we don't have enough tokens, calculate wait time
            if byte_count > self.tokens:
                tokens_needed = byte_count - self.tokens
                wait_time = tokens_needed / self.rate_limit_bps
                
                # Wait for tokens to refill
                time.sleep(wait_time)
                
                # Refill tokens again after waiting
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(
                    self.max_tokens,
                    self.tokens + (elapsed * self.rate_limit_bps)
                )
                self.last_update = now
            else:
                wait_time = 0.0
            
            # Consume tokens
            self.tokens -= byte_count
            
            return wait_time
    
    def get_current_rate(self) -> int:
        """
        Get current rate limit.
        
        Returns:
            Rate limit in bytes per second
        """
        return self.rate_limit_bps
    
    def is_unlimited(self) -> bool:
        """
        Check if rate limiting is disabled.
        
        Returns:
            True if unlimited
        """
        return self.unlimited


class RateLimiterManager:
    """
    Manages rate limiters for multiple clients.
    """
    
    def __init__(self):
        """Initialize rate limiter manager."""
        self.limiters: Dict[str, RateLimiter] = {}
        self.lock = threading.Lock()
    
    def get_limiter(self, client_id: str, rate_limit_bps: int = 0) -> RateLimiter:
        """
        Get or create rate limiter for a client.
        
        Args:
            client_id: Client identifier
            rate_limit_bps: Rate limit in bytes per second
            
        Returns:
            RateLimiter instance
        """
        with self.lock:
            if client_id not in self.limiters:
                self.limiters[client_id] = RateLimiter(rate_limit_bps)
            return self.limiters[client_id]
    
    def remove_limiter(self, client_id: str) -> None:
        """
        Remove rate limiter for a client.
        
        Args:
            client_id: Client identifier
        """
        with self.lock:
            if client_id in self.limiters:
                del self.limiters[client_id]
    
    def update_rate_limit(self, client_id: str, rate_limit_bps: int) -> None:
        """
        Update rate limit for a client.
        
        Args:
            client_id: Client identifier
            rate_limit_bps: New rate limit in bytes per second
        """
        with self.lock:
            if client_id in self.limiters:
                self.limiters[client_id] = RateLimiter(rate_limit_bps)


def throttle_transfer(rate_limiter: RateLimiter, data: bytes) -> float:
    """
    Throttle a data transfer according to rate limit.
    
    Args:
        rate_limiter: Rate limiter to use
        data: Data being transferred
        
    Returns:
        Time waited in seconds
    """
    return rate_limiter.acquire(len(data))
