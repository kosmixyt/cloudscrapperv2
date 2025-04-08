import mycdp.network
from app.models import ChromeSession
import asyncio
import platform
import sys
import mycdp
from seleniumbase import Driver
import nodriver as uc
import cdp
from app.models import User
import traceback
import json
import os
import datetime
from typing import Union

from seleniumbase import SB
# Store browser sessions
browserSessions = []





async def newSession(session: ChromeSession):
    browser = await NewDriver()
    browserSession = {
        "session": session,
        "browser": browser
    }
    browserSessions.append(browserSession)
    return browser

async def getSession(session: str) -> Driver:
    for browserSession in browserSessions:
        print(browserSession["session"].session_id, session)
        if browserSession["session"].session_id == session:
            return browserSession
    return None

async def deleteSession(session: ChromeSession) -> bool:
    for i, browserSession in enumerate(browserSessions):
        if browserSession["session"].session_id == session.session_id:
            browserSession["browser"].quit()
            del browserSessions[i]
            return True
    return False




async def NewDriver():
    d = Driver(uc=True, locale_code="en", headless=False)

    return d




