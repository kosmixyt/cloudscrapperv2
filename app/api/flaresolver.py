from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
import mycdp.network
import os
import base64
import datetime
from app.models import AllowedOrigin, Request, ChromeSession
from app.schemas import BrowserAction
from app.util import verifyStringIsProxy
from app.browser_manager.manager import newSession, deleteSession, getSession, NewDriver
import mycdp
from uuid import uuid4

import asyncio
from seleniumbase import SB
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
        actions = data.get("actions", [])
        parsed_actions = []
        response_values = []
        if actions:
            if not isinstance(actions, list):
                return {"error": "Actions must be an array"}
            try:
                for action_data in actions:
                    action = BrowserAction(**action_data)
                    parsed_actions.append(action)
            except Exception as e:
                return {"error": f"Invalid action format: {str(e)}"}
        if not isinstance(cookies, list) or not all(isinstance(cookie, dict) and "name" in cookie and "value" in cookie for cookie in cookies):
            return {"error": "Invalid cookies format"}
        cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        return_only_cookies = data.get("returnOnlyCookies", "false").lower() == "true"
        proxy = data.get("proxy")
        if proxy and not verifyStringIsProxy(proxy):
            return {"error": "Invalid proxy format"}
        browser = None
        sess = None
        if session_id is not None:
            print(f"Using session {session_id} for user {result.owner.id}")
            sess = await getSession(session_id)
            
            if sess is None:
                return {"error": "Session not found"}
            browser = sess["browser"]
        else:
            browser = await NewDriver()
            if proxy:
                browser.proxy = proxy
        last_document = None
        def receive_handler(event: mycdp.network.ResponseReceived):
            nonlocal last_document
            print(f"Document URL: {event.response.url}, {event.response.status} {event.type_}")
            if event.type_ == mycdp.network.ResourceType.DOCUMENT:
                last_document = event
                print("Document loaded")
        browser.uc_activate_cdp_mode("about:blank")
        browser.cdp.add_handler(mycdp.network.ResponseReceived, receive_handler)
        print("Waiting for page to load")
        browser.cdp.open(url)
        browser.sleep(6)
        # parsed_actions
        if len(parsed_actions) > 10:
            return {"error": "Too many actions"}
        for action in parsed_actions:
            match action.action:
                case "reload":
                    print("Reloading page")
                    browser.cdp.reload()
                case "wait":
                    print(f"Waiting for {action.value} seconds")
                    waitTime = int(action.value)
                    
                    if waitTime > 60:
                        return {"error": "Wait time too long"}
                    if waitTime < 0:
                        return {"error": "Wait time cannot be negative"}
                    browser.sleep(waitTime)
                case "script":
                    print("Executing script")
                    if not action.value:
                        return {"error": "Script is required"}
                    if len(action.value) > 10000:
                        return {"error": "Script too long"}
                    try:
                        f =  browser.cdp.evaluate(action.value)
                        response_values.append(f)
                    except Exception as e:
                        return {"error": f"Script execution failed: {str(e)}"}
                case "type":
                    print("Typing")
                    if not action.value:
                        return {"error": "Value is required"}
                    if len(action.value) > 10000:
                        return {"error": "Value too long"}
                    if not action.selector:
                        return {"error": "Selector is required"}
                    if len(action.selector) > 100:
                        return {"error": "Selector too long (100 max)"}
                    try:
                        browser.cdp.type(action.value, action.selector)
                    except Exception as e:
                        return {"error": f"Typing failed: {str(e)}"} 
                case "waitForSelector":
                    print("Waiting for selector")
                    if not action.selector:
                        return {"error": "Selector is required"}
                    if len(action.selector) > 100:
                        return {"error": "Selector too long (100 max)"}
                    try:
                        browser.cdp.wait_for_selector(action.selector, timeout=max_timeout * 1000)
                    except Exception as e:
                        return {"error": f"Waiting for selector failed: {str(e)}"}
                case _:
                    return {"error": f"Unknown action {action.action}"}
        cookies = browser.cdp.get_all_cookies()
        headers = last_document.response.headers if last_document else {}
        response = browser.cdp.get_page_source()
        status = last_document.response.status if last_document else 0
        ua = browser.get_user_agent()
        screen_path = f'{uuid4().hex}.png'
        screenshot = browser.cdp.save_screenshot(screen_path, os.getenv('SCREENSHOT_DIR'))
        print(f"Screenshot saved to {screenshot}")
        if session_id is None:
            browser.quit()
        
        # After successful request, log it to the database
        try:
            # Create a new Request object
            request_record = Request(
                method="GET",
                url=url,
                string_response=base64.b64encode(response.encode()).decode(),
                user_id=result.owner.id,
                request_origin_id=result.id,
                screenShotName=screen_path,
                status_code=status,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            )
            print("request origin id", result.id)
            
            # Associate with chrome session if one was used
            if chrome_session:
                request_record.chrome_session_id = chrome_session.id
            
            # Add to database and commit
            db.add(request_record)
            await db.commit()
            
            # Rename the screenshot file to use the request ID - with error handling
            try:
                new_screenshot_name = f"{request_record.id}.png"
                old_screenshot_path = os.path.join(os.getenv('SCREENSHOT_DIR'), screen_path)
                new_screenshot_path = os.path.join(os.getenv('SCREENSHOT_DIR'), new_screenshot_name)
                
                print(f"Renaming screenshot from: {old_screenshot_path}")
                print(f"Renaming screenshot to: {new_screenshot_path}")
                print(f"File exists (old path): {os.path.exists(old_screenshot_path)}")
                
                os.rename(old_screenshot_path, new_screenshot_path)
                
                # Update the request record with the new screenshot name
                request_record.screenShotName = new_screenshot_name
                await db.commit()
                print(f"Screenshot successfully renamed to {new_screenshot_name}")
            except Exception as rename_error:
                print(f"Error renaming screenshot: {rename_error}")
                # Keep the original name if rename fails
                print(f"Keeping original screenshot name: {screen_path}")

            print(f"Request logged to database: {url}")
        except Exception as e:
            print(f"Failed to log request to database: {e}")
            # Continue execution even if logging fails
        
        if return_only_cookies:
            return {
                "solution": {
                    "cookies": cookies,
                },
                "status": "ok",
                "message": "",
                "startTimestamp": start,
                "endTimestamp": time.time(),
                "version": "1.0.0",
            }
        
        return {
            "solution": {
                "url" : url,
                "status": status,
                "headers": headers,
                "response": response,
                "cookies": cookies,
                "userAgent": ua,
                "response_values": response_values,
            },
            "status": "ok",
            "message": "",
            "startTimestamp": start,
            "endTimestamp": time.time(),
            "version": "1.0.0",
        }


