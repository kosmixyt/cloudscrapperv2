from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
import nodriver as uc
from app.models import AllowedOrigin, Request, ChromeSession
from app.util import verifyStringIsProxy
from app.browser_manager.manager import newSession, deleteSession, getSession
from uuid import uuid4
import asyncio
import time
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
        return {"session": session}
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
        await deleteSession(chromeSession)
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
    if cmd == "request.get":
        start = time.time()
        url = data.get("url")
        if not url:
            return {"error": "URL is required"}
        
        session_id = data.get("session")
        chrome_session = None
        if session_id:
            chrome_session = await db.execute(
                select(ChromeSession).where(ChromeSession.session_id == session_id)
            )
            chrome_session = chrome_session.scalar_one_or_none()
            if not chrome_session:
                return {"error": "Session not found"}
        
        session_ttl_minutes = int(data.get("session_ttl_minutes", 5))
        max_timeout = int(data.get("maxTimeout", 60))
        cookies = data.get("cookies", [])
        if not isinstance(cookies, list) or not all(isinstance(cookie, dict) and "name" in cookie and "value" in cookie for cookie in cookies):
            return {"error": "Invalid cookies format"}
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        return_only_cookies = data.get("returnOnlyCookies", "false").lower() == "true"
        proxy = data.get("proxy")
        if proxy and not verifyStringIsProxy(proxy):
            return {"error": "Invalid proxy format"}
        browser = await getSession(session_id, True)
        if not browser:
            return {"error": "Browser session could not be created or found"}
        if proxy and chrome_session:
            if chrome_session.proxy is not None:
                return {"error": "Session already has a proxy"}
        # browser.uc_activate_cdp_mode(url)
        # cookies = browser.get_cookies()
        # headers = {}
        # response = browser.get_page_source()
        # status_code = 200
        # ua = browser.get_user_agent()
        browser.get(url)
        
        cookies = []
        headers = {}
        response = ""
        status_code = 200
        ua = ""
        if return_only_cookies:
            return {
                "cookies": cookies,
                "status": "ok",
                "message": "",
                "startTimestamp": start,
                "endTimestamp": time.time(),
                "version": "1.0.0",
            }
        if chrome_session is None:
            # browser.quit()
            pass
        return {
            "solution":
            {
                "url" : url,
                "status": status_code,
                "headers": headers,
                "response": response,
                "cookies": cookies,
                "userAgent": ua,
            },
            "status": "ok",
            "message": "",
            "startTimestamp": start,
            "endTimestamp": time.time(),
            "version": "1.0.0",
        }
        
        
