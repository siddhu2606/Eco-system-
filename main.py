import asyncio
import json
import os
from typing import Dict, Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

# Load environment variables (e.g. GEMINI_API_KEY)
load_dotenv()

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

# Mount static directory for frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Define the State for LangGraph
class AgentState(TypedDict):
    city_data: str
    anomalies: str
    mitigation_plan: str

def extract_text(content) -> str:
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    return str(content)

# Define the nodes (agents)
async def data_harvester_node(state: AgentState):
    print("Agent 1: Data Harvester executing...")
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")
    
    prompt = """
    You are the Data Harvester AI Agent. 
    Your task is to fetch (simulate) real-time environmental data, sensor readings, 
    and satellite imagery stats for the following urban areas: Mumbai, Delhi, and Pune.
    Provide realistic, currently relevant data regarding AQI, PM2.5, traffic density, and temperature.
    Keep your response concise but detailed enough for analysis.
    """
    
    response = await llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content="Fetch the latest data.")])
    return {"city_data": extract_text(response.content)}

async def analyst_node(state: AgentState):
    print("Agent 2: Analyst executing...")
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")
    
    prompt = f"""
    You are the Analyst AI Agent.
    Process the following raw environmental data collected by the Data Harvester.
    Identify any ecological anomalies, threats, or severe pollution patterns in Mumbai, Delhi, and Pune.
    
    Raw Data:
    {state['city_data']}
    
    Keep your response analytical and concise.
    """
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"anomalies": extract_text(response.content)}

async def strategist_node(state: AgentState):
    print("Agent 3: Strategist executing...")
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")
    
    prompt = f"""
    You are the Strategist AI Agent.
    Based on the anomalies identified by the Analyst, formulate a concrete, actionable 
    mitigation plan for the affected cities (Mumbai, Delhi, Pune).
    
    Anomalies identified:
    {state['anomalies']}
    
    Keep your mitigation strategy clear, actionable, and concise.
    """
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"mitigation_plan": extract_text(response.content)}

# Build the graph
workflow = StateGraph(AgentState)
workflow.add_node("harvester", data_harvester_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("strategist", strategist_node)

workflow.set_entry_point("harvester")
workflow.add_edge("harvester", "analyst")
workflow.add_edge("analyst", "strategist")
workflow.add_edge("strategist", END)

app_graph = workflow.compile()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/chat")
async def chat_with_eco_buddy(payload: ChatRequest):
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")
        system_instruction = """
        You are Eco Buddy, the helpful and premium AI companion for the Eco Mitra ecological swarm management system.
        Answer user questions about the ecological swarm, environment, or system diagnostics. Keep your answers concise, engaging, and in a friendly, high-tech robot helper persona.
        """
        response = await llm.ainvoke([
            SystemMessage(content=system_instruction),
            HumanMessage(content=payload.message)
        ])
        return {"response": extract_text(response.content)}
    except Exception as e:
        return {"response": f"Error communicating with Eco Buddy: {str(e)}"}


@app.get("/api/init-swarm")
async def init_swarm(request: Request):
    async def event_generator() -> AsyncGenerator[dict, None]:
        # Yield initial connected state
        yield {
            "event": "connected",
            "data": json.dumps({"message": "Swarm initialized. Starting Harvester..."})
        }
        
        # Start streaming LangGraph events
        initial_state = {"city_data": "", "anomalies": "", "mitigation_plan": ""}
        
        try:
            # We will use stream() yielding after each node executes
            async for output in app_graph.astream(initial_state):
                if await request.is_disconnected():
                    break
                    
                if "harvester" in output:
                    yield {
                        "event": "harvester_done",
                        "data": json.dumps({
                            "message": "Data harvested successfully for Mumbai, Delhi, and Pune.",
                            "details": output["harvester"]["city_data"][:200] + "..." # Snippet
                        })
                    }
                elif "analyst" in output:
                    yield {
                        "event": "analyst_done",
                        "data": json.dumps({
                            "message": "Analysis complete. Anomalies detected.",
                            "details": output["analyst"]["anomalies"][:200] + "..."
                        })
                    }
                elif "strategist" in output:
                    yield {
                        "event": "strategist_done",
                        "data": json.dumps({
                            "message": "Mitigation strategy formulated and deployed.",
                            "details": output["strategist"]["mitigation_plan"][:200] + "..."
                        })
                    }
            
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
