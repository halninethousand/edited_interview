from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List
import uuid
import os
from playwright.async_api import async_playwright
from .database import SessionLocal, engine, Base
from .models import ScreenshotRecord

Base.metadata.create_all(bind=engine)

app = FastAPI()

class ScreenshotRequest(BaseModel):
    start_url: str
    num_links: int

@app.get("/isalive")
async def is_alive():
    return {"status": "alive"}

@app.post("/screenshots")
async def create_screenshot_task(request: ScreenshotRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    background_tasks.add_task(crawl_and_capture, request.start_url, request.num_links, task_id)
    return {"task_id": task_id}

@app.get("/screenshots/{task_id}")
async def get_screenshots(task_id: str):
    session = SessionLocal()
    records = session.query(ScreenshotRecord).filter(ScreenshotRecord.task_id == task_id).all()
    if not records:
        raise HTTPException(status_code=404, detail="Task ID not found")
    screenshots = [record.file_path for record in records]
    return {"task_id": task_id, "screenshots": screenshots}

async def crawl_and_capture(start_url: str, num_links: int, task_id: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(start_url)
        screenshot_path = f"screenshots/{task_id}_start.png"
        await page.screenshot(path=screenshot_path)
        
        session = SessionLocal()
        session.add(ScreenshotRecord(task_id=task_id, file_path=screenshot_path))
        session.commit()
        
        links = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a')).map(a => a.href).slice(0, num_links);
        }""")
        
        for index, link in enumerate(links):
            await page.goto(link)
            screenshot_path = f"screenshots/{task_id}_{index}.png"
            await page.screenshot(path=screenshot_path)
            session.add(ScreenshotRecord(task_id=task_id, file_path=screenshot_path))
            session.commit()
        
        await browser.close()
        session.close()
