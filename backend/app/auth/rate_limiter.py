import time
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import threading


class RateLimiter:
    """Thread-safe rate limiter with lockout functionality."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._attempts: Dict[str, list] = defaultdict(list)
        self._lockouts: Dict[str, datetime] = {}
        
        # Rate limiting configuration
        self.login_attempts_limit = 5
        self.login_lockout_duration = timedelta(minutes=5)
        self.api_rate_limit = 60  # requests per minute
        self.agent_rate_limit = 5  # agent requests per minute
    
    def _clean_old_attempts(self, key: str, window_seconds: int):
        """Remove attempts older than the window."""
        now = time.time()
        cutoff = now - window_seconds
        self._attempts[key] = [attempt for attempt in self._attempts[key] if attempt > cutoff]
    
    def _get_key(self, identifier: str, action: str) -> str:
        """Generate a key for rate limiting."""
        return f"{action}:{hashlib.sha256(identifier.encode()).hexdigest()[:16]}"
    
    def check_login_attempts(self, email: str) -> Tuple[bool, Optional[datetime]]:
        """Check if login attempts are within limits."""
        with self._lock:
            key = self._get_key(email, "login")
            
            # Check if currently locked out
            if key in self._lockouts:
                lockout_until = self._lockouts[key]
                if datetime.now() < lockout_until:
                    return False, lockout_until
                else:
                    # Lockout expired, remove it
                    del self._lockouts[key]
                    self._attempts[key] = []
            
            # Clean old attempts (last 5 minutes)
            self._clean_old_attempts(key, 300)
            
            # Check if under limit
            if len(self._attempts[key]) < self.login_attempts_limit:
                return True, None
            else:
                # Too many attempts, initiate lockout
                lockout_until = datetime.now() + self.login_lockout_duration
                self._lockouts[key] = lockout_until
                return False, lockout_until
    
    def record_login_attempt(self, email: str, success: bool):
        """Record a login attempt."""
        with self._lock:
            key = self._get_key(email, "login")
            
            if success:
                # Clear attempts on successful login
                if key in self._attempts:
                    del self._attempts[key]
                if key in self._lockouts:
                    del self._lockouts[key]
            else:
                # Record failed attempt
                self._attempts[key].append(time.time())
    
    def check_api_rate_limit(self, user_id: int) -> bool:
        """Check API rate limit for a user (60 requests per minute)."""
        with self._lock:
            key = self._get_key(str(user_id), "api")
            
            # Clean old attempts (last minute)
            self._clean_old_attempts(key, 60)
            
            # Check if under limit
            if len(self._attempts[key]) < self.api_rate_limit:
                self._attempts[key].append(time.time())
                return True
            else:
                return False
    
    def check_agent_rate_limit(self, user_id: int) -> bool:
        """Check agent request rate limit for a user (5 requests per minute)."""
        with self._lock:
            key = self._get_key(str(user_id), "agent")
            
            # Clean old attempts (last minute)
            self._clean_old_attempts(key, 60)
            
            # Check if under limit
            if len(self._attempts[key]) < self.agent_rate_limit:
                self._attempts[key].append(time.time())
                return True
            else:
                return False
    
    def reset_user_limits(self, user_id: int):
        """Reset all rate limits for a user (admin function)."""
        with self._lock:
            user_str = str(user_id)
            keys_to_remove = []
            
            for key in self._attempts:
                if key.endswith(hashlib.sha256(user_str.encode()).hexdigest()[:16]):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                if key in self._attempts:
                    del self._attempts[key]
                if key in self._lockouts:
                    del self._lockouts[key]
    
    def get_stats(self) -> Dict[str, int]:
        """Get rate limiter statistics."""
        with self._lock:
            return {
                "active_rate_limits": len(self._attempts),
                "active_lockouts": len(self._lockouts),
                "total_attempts_tracked": sum(len(attempts) for attempts in self._attempts.values())
            }


# Global rate limiter instance
rate_limiter = RateLimiter()

