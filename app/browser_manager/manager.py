from app.models import ChromeSession
import asyncio
from seleniumbase import Driver


browserSessions: list[dict] = []
async def newSession(session: ChromeSession) -> ChromeSession:
        browser = Driver(headless=False, uc=True)
        try:
            browser.open("https://www.ygg.re")
            print(browser.get_title())
            browser.wait_for_element('input[type="text"]', timeout=5)
            print(browser.get_cookies())
        except Exception as e:
            print(e)
        browserSession = {
            "session": session,
            "browser": browser
        }
        browserSessions.append(browserSession)
        return browserSessions[-1]
async def getSession(session: ChromeSession):
    for browserSession in browserSessions:
        if browserSession["session"].id == session.id:
            return browserSession["browser"]
        
    return None
async def deleteSession(session: ChromeSession) -> None:
    for browserSession in browserSessions:
        if browserSession["session"].id == session.id:
            await browserSession["browser"].close()
            browserSessions.remove(browserSession)
            return
        