"""FastAPI dependencies shared by authentication and RBAC."""
from __future__ import annotations
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from backend.services import auth, rbac
bearer = HTTPBearer(auto_error=False)
def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
 if not credentials or credentials.scheme.lower() != "bearer":
  raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.", headers={"WWW-Authenticate":"Bearer"})
 try: return auth.decode_access_token(credentials.credentials)
 except Exception as exc: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired authentication token.", headers={"WWW-Authenticate":"Bearer"}) from exc
def require_permission(permission: str):
 def checker(user: dict = Depends(current_user)) -> dict:
  if not rbac.has_permission(user, permission):
   raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Your role does not have permission for: {permission.replace('_',' ')}.")
  return user
 return checker
