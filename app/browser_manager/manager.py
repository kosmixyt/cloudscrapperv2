from app.models import ChromeSession
import asyncio
import platform
import sys
from seleniumwire import webdriver
from seleniumbase import Driver
import nodriver as uc
import cdp
import traceback
import json
import os
import datetime
from typing import Union

# Store browser sessions
browserSessions: list[dict] = []

# Create directory for JSON files
os.makedirs("c:\\Users\\kosmix\\cloudscrapperv2\\http_logs", exist_ok=True)

# Function to write responses to JSON file
def write_to_json(data):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"c:\\Users\\kosmix\\cloudscrapperv2\\http_logs\\http_responses.json"
    
    # If file exists, read existing data
    existing_data = []
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            existing_data = []
    
    # Append new data and write back
    existing_data.append(data)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, default=str)

async def newSession(session: ChromeSession) -> dict:
    browser = await NewDriver()
    browserSession = {
        "session": session,
        "browser": browser
    }
    browserSessions.append(browserSession)
    return browserSession

async def getSession(session: str, orDefault: bool = False) -> Driver:
    if session is None:
        return await NewDriver()
    
    for browserSession in browserSessions:
        if browserSession["session"].id == session:
            return browserSession["browser"]
    
    if orDefault:
        return await NewDriver()
    return None

async def deleteSession(session: ChromeSession) -> bool:
    for i, browserSession in enumerate(browserSessions):
        if browserSession["session"].id == session.id:
            # Properly close the browser
            try:
                await browserSession["browser"].close()
            except Exception as e:
                print(f"Error closing browser: {e}")
            
            # Remove from sessions list
            browserSessions.pop(i)
            return True
    return False
            
async def NewDriver():
    try:
        # Use SeleniumBase Driver instead of nodriver
        browser = Driver(
            headless=False,
            undetected=True,  # Similar to uc mode
            uc_cdp=True,  # Enable CDP
            
        )
        
        # Set up CDP handler for response events
        def response_handler(response):
            print(response)

        # Add the handler for network responses
        try:
            # Configure network monitoring with more parameters
            browser.execute_cdp_cmd('Network.enable', {
                'maxTotalBufferSize': 10000000,  # Increase buffer size
                'maxResourceBufferSize': 5000000,  # Increase resource buffer
                'maxPostDataSize': 500000  # Capture large post data
            })
            
            # Don't disable cache, but ensure we report cached responses
            browser.execute_cdp_cmd('Network.setCacheDisabled', {'cacheDisabled':True })
            
            # Add specific listeners for different response types
            browser.add_cdp_listener('Network.responseReceived', response_handler)
            # Add listener for cached requests
            # browser.add_cdp_listener('Network.requestServedFromCache', response_handler)
            
            # Set request/response interception patterns (including cached ones)
            browser.execute_cdp_cmd('Network.setRequestInterception', {
                'patterns': [{'urlPattern': '*'}]
            })
            
            
            print("CDP listeners and network monitoring configured successfully")
        except Exception as e:
            print(f"Warning: Could not add CDP listener: {e}")
            traceback.print_exc()
            
        return browser
    except Exception as e:
        print(e)
        print(f"Error starting browser: {e}")
        traceback.print_exc()
        return None

