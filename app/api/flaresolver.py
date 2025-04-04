from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
import nodriver as uc
from app.models import AllowedOrigin, Request, ChromeSession
from app.util import verifyStringIsProxy
from app.browser_manager.manager import newSession
from uuid import uuid4
import asyncio
async def flaresolverRoute(data : Dict[str, Any], ip: str, db: AsyncSession) -> Dict[str, Any]:
    is_allowed_host = await db.execute(
        select(AllowedOrigin)
        .options(joinedload(AllowedOrigin.owner))
        .where(AllowedOrigin.origin == ip)
    )
    result = is_allowed_host.scalar_one_or_none()
    if not result:
        return {"error": f"Not allowed ip {ip}"}
    
    cmd = data.get("cmd")
    if cmd == "sessions.create":
        session = data.get("session")
        proxy = data.get("proxy")
        if not session:
            session = uuid4().hex
        chromeSession = ChromeSession(session_id=session, user_id=result.owner.id)
        if proxy:
            if not verifyStringIsProxy(proxy):
                return {"error": "Invalid proxy format"}
            chromeSession.proxy = proxy
        db.add(chromeSession)
        await db.commit()
        await db.refresh(chromeSession)

        print(f"Creating session {session} for user {result.owner.id}")
        await newSession(chromeSession)
        print(f"Session {session} created")
        return {"session": chromeSession}
    if cmd == "sessions.destroy":
        session = data.get("session")
        if not session:
            return {"error": "session_id is required"}
        chromeSession = await db.execute(
            select(ChromeSession).where(ChromeSession.session_id == session)
        )
        chromeSession = chromeSession.scalar_one_or_none()
        if not chromeSession:
            return {"error": "session not found"}
        await db.delete(chromeSession)
        await db.commit()
        return {"message": "session deleted"}
    if cmd == "sessions.list":
        sessions = await db.execute(
            select(ChromeSession).where(ChromeSession.user_id == result.owner.id)
        )
        # il faut que l'output soit sessions : [session_id, session_id, ...]
        sessions = sessions.scalars().all()
        sessions = [session.session_id for session in sessions]
        return {"sessions": sessions}
    
