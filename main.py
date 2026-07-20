import asyncio
import json
import os
from typing import Dict, Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

# Mount static directory for frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/init-swarm")
async def init_swarm(request: Request):
    async def event_generator() -> AsyncGenerator[dict, None]:
        # Yield initial connected state
        yield {
            "event": "connected",
            "data": json.dumps({"message": "Swarm initialized. Starting Harvester..."})
        }
        
        try:
            # 1. Simulate Harvester
            await asyncio.sleep(2.5) # Simulate thinking time
            harvester_data = "Mumbai AQI: 142 (Moderate), PM2.5: 55 µg/m³. Delhi AQI: 310 (Hazardous), PM2.5: 210 µg/m³. Pune AQI: 85 (Satisfactory). Traffic density high in Delhi NCR."
            yield {
                "event": "harvester_done",
                "data": json.dumps({
                    "message": "Data harvested successfully for Mumbai, Delhi, and Pune.",
                    "details": harvester_data
                })
            }
            
            if await request.is_disconnected(): return

            # 2. Simulate Analyst
            await asyncio.sleep(3.0)
            analyst_data = "CRITICAL ANOMALY: Delhi PM2.5 levels are 4x above safe limits, strongly correlated with morning traffic peaks and winter inversion. Mumbai shows localized spikes in industrial sectors."
            yield {
                "event": "analyst_done",
                "data": json.dumps({
                    "message": "Analysis complete. Anomalies detected.",
                    "details": analyst_data
                })
            }
            
            if await request.is_disconnected(): return

            # 3. Simulate Strategist
            await asyncio.sleep(3.5)
            strategist_data = "Action Plan 1: Reroute heavy transit away from Delhi NCR during 7AM-10AM. Action Plan 2: Deploy automated air scrubbers in Mumbai industrial zones. Action Plan 3: Issue public health advisories via SMS."
            yield {
                "event": "strategist_done",
                "data": json.dumps({
                    "message": "Mitigation strategy formulated and deployed.",
                    "details": strategist_data
                })
            }
            
            if await request.is_disconnected(): return
            
            yield {
                "event": "complete",
                "data": json.dumps({"message": "Swarm execution completed successfully."})
            }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)})
            }
            
    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
