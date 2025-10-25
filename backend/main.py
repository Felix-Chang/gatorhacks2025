"""
NYC COâ‚‚ Sustainability Simulation - FastAPI Backend
Handles data fetching, processing, and AI-powered prompt interpretation
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import numpy as np
import json
from dotenv import load_dotenv
import os

from data_processor import NYCEmissionsData
from ai_processor import AIPromptProcessor

# Load environment variables
load_dotenv()

app = FastAPI(title="NYC COâ‚‚ Simulation API")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Set to False when allowing all origins
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize data processor
emissions_data = NYCEmissionsData()
ai_processor = AIPromptProcessor(api_key=os.getenv("OPENAI_API_KEY"))


class SimulationRequest(BaseModel):
    prompt: str


class GridPoint(BaseModel):
    lat: float
    lon: float
    value: float


class BaselineResponse(BaseModel):
    grid: List[GridPoint]
    metadata: Dict


class SimulationResponse(BaseModel):
    grid: List[GridPoint]
    intervention: Dict
    metadata: Dict


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "NYC COâ‚‚ Simulation API",
        "version": "1.0.0"
    }


@app.get("/api/baseline", response_model=BaselineResponse)
async def get_baseline():
    """
    Returns baseline NYC COâ‚‚ emissions grid
    
    Combines real OpenAQ station data with synthetic gridded emissions
    based on NYC geography and known emission patterns
    """
    try:
        # Fetch and process baseline data
        baseline_grid = emissions_data.get_baseline_grid()
        
        # Convert to response format
        grid_points = []
        for lat, lon, value in baseline_grid:
            grid_points.append({
                "lat": float(lat),
                "lon": float(lon),
                "value": float(value)
            })
        
        metadata = {
            "city": "New York City",
            "unit": "kg COâ‚‚/kmÂ²/day",
            "source": "OpenAQ + Synthetic Grid",
            "bounds": {
                "south": 40.49,
                "north": 40.92,
                "west": -74.26,
                "east": -73.70
            },
            "timestamp": emissions_data.get_last_update_time()
        }
        
        return {
            "grid": grid_points,
            "metadata": metadata
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching baseline data: {str(e)}")


@app.post("/api/simulate", response_model=SimulationResponse)
async def simulate_intervention(request: SimulationRequest):
    """
    Processes natural language prompt and returns simulated emissions grid
    
    Uses AI to parse the prompt and apply emissions reductions to relevant areas
    """
    try:
        # Parse the prompt using AI
        intervention = ai_processor.parse_prompt(request.prompt)
        
        # Apply the intervention to the emissions grid
        simulated_grid = emissions_data.apply_intervention(intervention)
        
        # Convert to response format
        grid_points = []
        for lat, lon, value in simulated_grid:
            grid_points.append({
                "lat": float(lat),
                "lon": float(lon),
                "value": float(value)
            })
        
        metadata = {
            "city": "New York City",
            "unit": "kg COâ‚‚/kmÂ²/day",
            "source": "Simulated",
            "bounds": {
                "south": 40.49,
                "north": 40.92,
                "west": -74.26,
                "east": -73.70
            },
            "timestamp": emissions_data.get_last_update_time()
        }
        
        return {
            "grid": grid_points,
            "intervention": intervention,
            "metadata": metadata
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulating intervention: {str(e)}")


@app.get("/api/openaq")
async def get_openaq_stations():
    """
    Returns raw OpenAQ station data for NYC
    Useful for debugging and transparency
    """
    try:
        stations = emissions_data.fetch_openaq_data()
        return {
            "stations": stations,
            "count": len(stations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching OpenAQ data: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"[START] Starting NYC COâ‚‚ Simulation API on port {port}")
    print(f"[URL] API Documentation: http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)


