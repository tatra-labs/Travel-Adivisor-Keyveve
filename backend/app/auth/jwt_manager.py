from jose import jwt
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import RefreshToken, User
from app.core.config import settings


class JWTManager:
    """Manages JWT token creation, validation, and refresh token rotation."""
    
    def __init__(self):
        # Generate RSA key pair for RS256 signing
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        
        # Serialize keys for JWT library
        self.private_key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        self.public_key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Token TTLs
        self.access_token_ttl = timedelta(minutes=15)
        self.refresh_token_ttl = timedelta(days=7)
    
    def create_access_token(self, user_id: int, org_id: int, role: str) -> str:
        """Create a new access token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "org_id": org_id,
            "role": role,
            "iat": now,
            "exp": now + self.access_token_ttl,
            "type": "access"
        }
        
        return jwt.encode(payload, self.private_key_pem, algorithm="RS256")
    
    def create_refresh_token(self, user_id: int) -> Tuple[str, str]:
        """Create a new refresh token and store it in the database."""
        # Generate a random JTI (JWT ID)
        jti = secrets.token_urlsafe(32)
        
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "jti": jti,
            "iat": now,
            "exp": now + self.refresh_token_ttl,
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self.private_key_pem, algorithm="RS256")
        
        # Hash the JTI for storage
        jti_hash = hashlib.sha256(jti.encode()).hexdigest()
        
        # Store in database
        db = SessionLocal()
        try:
            refresh_token = RefreshToken(
                user_id=user_id,
                jti=jti,
                hashed_token=jti_hash,
                expires_at=now + self.refresh_token_ttl
            )
            db.add(refresh_token)
            db.commit()
        finally:
            db.close()
        
        return token, jti
    
    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode an access token."""
        try:
            payload = jwt.decode(token, self.public_key_pem, algorithms=["RS256"])
            
            # Check token type
            if payload.get("type") != "access":
                return None
            
            return payload
        except jwt.InvalidTokenError:
            return None
    
    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a refresh token and check if it's still valid in the database."""
        try:
            payload = jwt.decode(token, self.public_key_pem, algorithms=["RS256"])
            
            # Check token type
            if payload.get("type") != "refresh":
                return None
            
            jti = payload.get("jti")
            if not jti:
                return None
            
            # Hash the JTI and check database
            jti_hash = hashlib.sha256(jti.encode()).hexdigest()
            
            db = SessionLocal()
            try:
                refresh_token = db.query(RefreshToken).filter(
                    RefreshToken.jti_hash == jti_hash,
                    RefreshToken.expires_at > datetime.now(timezone.utc),
                    RefreshToken.revoked == False
                ).first()
                
                if not refresh_token:
                    return None
                
                return payload
            finally:
                db.close()
                
        except jwt.InvalidTokenError:
            return None
    
    def revoke_refresh_token(self, jti: str) -> bool:
        """Revoke a refresh token by JTI."""
        jti_hash = hashlib.sha256(jti.encode()).hexdigest()
        
        db = SessionLocal()
        try:
            refresh_token = db.query(RefreshToken).filter(
                RefreshToken.jti_hash == jti_hash
            ).first()
            
            if refresh_token:
                refresh_token.revoked = True
                db.commit()
                return True
            
            return False
        finally:
            db.close()
    
    def revoke_all_user_tokens(self, user_id: int) -> int:
        """Revoke all refresh tokens for a user. Returns count of revoked tokens."""
        db = SessionLocal()
        try:
            count = db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False
            ).update({"revoked": True})
            
            db.commit()
            return count
        finally:
            db.close()
    
    def rotate_refresh_token(self, old_token: str) -> Optional[Tuple[str, str, str]]:
        """Rotate a refresh token, returning new access and refresh tokens."""
        # Verify the old token
        payload = self.verify_refresh_token(old_token)
        if not payload:
            return None
        
        user_id = int(payload["sub"])
        old_jti = payload["jti"]
        
        # Get user info for new access token
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Revoke the old token
            self.revoke_refresh_token(old_jti)
            
            # Create new tokens
            new_access_token = self.create_access_token(user.id, user.org_id, user.role)
            new_refresh_token, new_jti = self.create_refresh_token(user.id)
            
            return new_access_token, new_refresh_token, new_jti
            
        finally:
            db.close()
    
    def cleanup_expired_tokens(self) -> int:
        """Clean up expired refresh tokens from the database."""
        db = SessionLocal()
        try:
            count = db.query(RefreshToken).filter(
                RefreshToken.expires_at < datetime.now(timezone.utc)
            ).delete()
            
            db.commit()
            return count
        finally:
            db.close()


# Global JWT manager instance
jwt_manager = JWTManager()

