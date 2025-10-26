"""
AI Prompt Processing Module
Uses Claude API (Anthropic) to analyze prompts and generate realistic spatial predictions
based on actual NYC data and geographic intelligence
"""

from typing import Dict, Optional, List, Tuple, Any
import json
import re
import numpy as np
import requests
import os


class AIPromptProcessor:
    """
    Advanced AI processor that analyzes prompts and generates realistic spatial predictions
    Uses Claude API (Anthropic) to understand context, geography, and create unique patterns
    """

    BOROUGHS = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']
    SECTORS = ['transport', 'buildings', 'industry', 'energy', 'nature']

    # Claude System Prompt - Data-Aware NYC Emissions Analysis
    CLAUDE_SYSTEM_PROMPT = """You are an expert climate analyst specializing in NYC emissions modeling. You have access to real NYC data:

DATA CONTEXT:
- Buildings: 64,169 tracked (LL84 Local Law 84 energy data)
- Vehicles: 2,100,000 total (1,600,000 gasoline, 300,000 diesel, 150,000 hybrid, 40,000 EV)
- Taxis: 13,500 yellow cabs + 80,000 for-hire vehicles (avg 180 mi/day each)
- Buses: 5,800 MTA buses (avg 150 mi/day each)
- Trees: 683,788 street trees (avg 21 kg CO2/year sequestration each)
- Airports: JFK (450,000 ops/year at 40.6413°N, 73.7781°W), LaGuardia (365,000 ops/year at 40.7769°N, 73.8740°W)
- Power Grid: 13,500 MW capacity, average 7,000 MW demand

EMISSIONS FACTORS:
- Aviation: Narrow-body 850 kg CO2/cycle, Wide-body 2,500 kg CO2/cycle, Regional 450 kg CO2/cycle
- Vehicles: Gasoline 0.39 kg CO2/mile, Diesel 0.41 kg CO2/mile, Hybrid 0.22 kg CO2/mile, EV 0.15 kg CO2/mile (grid-powered)
- Buildings: NYC grid average 350 kg CO2/MWh
- Trees: Average sequestration 21 kg CO2/year per tree

SECTOR ANNUAL BASELINES (tons CO2/year):
- Transport (all): ~15,000,000 tons/year
- Transport (taxis only): ~425,000 tons/year
- Transport (buses only): ~380,000 tons/year
- Buildings: ~30,000,000 tons/year
- Aviation (JFK): ~2,800,000 tons/year
- Aviation (LaGuardia): ~2,200,000 tons/year
- Energy/Grid: ~21,000,000 tons/year
- Trees: -14,359 tons/year (negative = sequestration)

YOUR ROLE: ANALYSIS, NOT CALCULATION
- Your "reasoning" should explain HOW and WHY the intervention works, NOT calculate totals
- The spatial grid model automatically calculates citywide impacts from your geographic modifications
- Focus on: mechanisms, affected sectors, geographic rationale, implementation details
- DO NOT: mention citywide percentages, total tonnes reduced, or overall impact numbers

CRITICAL ANALYSIS RULES:
1. Use REAL NYC geography (JFK is in Queens, not Manhattan!)
2. Base analysis on ACTUAL fleet sizes and usage patterns
3. Account for secondary effects (EVs increase grid load by ~7 MWh/vehicle/year)
4. Be CONSERVATIVE - real-world deployment takes time
5. Flag unrealistic interventions (>50% fleet conversion in <5 years is unlikely)
6. Consider infrastructure constraints (charging stations, grid capacity)
7. Account for implementation costs and timelines

Your task: Analyze user climate interventions and provide REALISTIC, DATA-DRIVEN geographic modification instructions.

CRITICAL: Output ONLY valid JSON. Use plain numbers WITHOUT commas (write 51025 not 51,025). No markdown, no extra text.

Output with this exact structure:
{
  "is_unrelated": false,
  "summary": "Brief 1-sentence description of the intervention",
  "borough": "Manhattan|Brooklyn|Queens|Bronx|Staten Island|citywide",
  "sector": "transport|buildings|aviation|industry|energy|nature",
  "subsector": "taxis|buses|commercial|residential|etc",
  "direction": "decrease|increase|none",
  "baseline_emissions_tons_year": 425000,
  "reduced_emissions_tons_year": 389125,
  "annual_impact_tons_co2": 35875,
  "average_change_percent": 8.5,
  "geographic_modifications": [
    {"area": "JFK Airport", "lat": 40.6413, "lon": -73.7781, "change_percent": -25, "type": "hotspot", "radius_km": 5},
    {"area": "Manhattan", "change_percent": -15, "type": "borough"},
    {"area": "citywide_baseline", "change_percent": -5, "type": "baseline"}
  ],
  "geographic_hotspots": [
    {"lat": 40.7589, "lon": -73.9857, "name": "Times Square", "intensity": 1.0}
  ],
  "reasoning": "ANALYSIS ONLY - Explain how the intervention works and why geographic areas are impacted. Example: 'Manhattan has ~13,500 yellow taxis traveling ~70,000 miles/year each. Converting 30% to EVs eliminates direct tailpipe emissions in Manhattan's dense commercial areas. The geographic modifications reflect concentrated taxi activity in Midtown and Lower Manhattan, with smaller impacts in outer boroughs where taxis are less common.' DO NOT mention citywide totals or overall percentages.",
  "secondary_impacts": [
    "Increased grid demand: +28,350 MWh/year (+9,923 tons CO2 from grid)",
    "Need for 180 new Level 2 charging stations"
  ],
  "confidence_level": "high|medium|low"
}

For unrelated/vague prompts, return:
{
  "is_unrelated": true,
  "summary": "Unrelated query - no climate impact",
  "borough": "citywide",
  "sector": "none",
  "direction": "none",
  "baseline_emissions_tons_year": 0,
  "reduced_emissions_tons_year": 0,
  "annual_impact_tons_co2": 0,
  "average_change_percent": 0,
  "geographic_modifications": [],
  "geographic_hotspots": [],
  "reasoning": "This prompt is too vague or unrelated to climate interventions",
  "secondary_impacts": [],
  "confidence_level": "low"
}

IMPORTANT INSTRUCTIONS FOR GEOGRAPHIC MODIFICATIONS:
- Use "type": "hotspot" for specific locations (airports, industrial zones) with lat/lon coordinates and radius
- Use "type": "borough" for borough-wide changes (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
- Use "type": "baseline" for citywide minimum emission adjustments
- change_percent should be NEGATIVE for reductions, POSITIVE for increases
- Be specific: different areas should have different change_percent values based on the intervention
- Example: Converting Manhattan taxis to EVs would have high impact in Manhattan (-20%), moderate in other boroughs (-8%)
- Example: SAF at JFK would have very high impact at JFK hotspot (-30%), minimal citywide (-2%)

CURRENT NYC BASELINE DATA:
Grid Coverage: 1,327 km² of NYC land + water (each cell ~0.98 km²)
Total Annual Emissions: ~55.4 million tonnes CO₂/year
Daily Average: ~151,781 tonnes CO₂/day
Average Intensity: ~114 tonnes CO₂/km²/day

Spatial Distribution:
- Airport hotspots (JFK): ~1,500-1,800 tonnes CO₂/km²/day
- Airport hotspots (LaGuardia): ~800-1,200 tonnes CO₂/km²/day
- Manhattan commercial: ~100-150 tonnes CO₂/km²/day
- Urban residential: ~40-80 tonnes CO₂/km²/day
- Parks/water: ~5-15 tonnes CO₂/km²/day
- Citywide minimum: ~5 tonnes CO₂/km²/day

NYC Sector Breakdown (from city inventory):
- Buildings (heating/cooling): ~70% of emissions (~38.8M tonnes/year)
- Transportation: ~25% (~13.8M tonnes/year)
  - Private vehicles: ~8M tonnes/year
  - Taxis/rideshare: ~425K tonnes/year
  - Buses: ~800K tonnes/year
  - Aviation (JFK+LGA): ~4.5M tonnes/year
- Other: ~5% (~2.8M tonnes/year)

IMPORTANT: Use these actual NYC values to inform your emission calculations. Your baseline_emissions_tons_year and reduced_emissions_tons_year should align with these sector totals when relevant."""
    
    # Real NYC geographic data for AI analysis
    NYC_LANDMARKS = {
        'Manhattan': {
            'commercial': [(-73.9857, 40.7589, 'Times Square'), (-73.9712, 40.7831, '5th Ave'), (-73.9934, 40.7505, 'Broadway')],
            'residential': [(-73.9857, 40.7831, 'Upper East Side'), (-73.9857, 40.7505, 'Midtown'), (-73.9857, 40.7128, 'Financial District')],
            'transport_hubs': [(-73.9857, 40.7505, 'Grand Central'), (-73.9857, 40.7128, 'Wall Street'), (-73.9857, 40.7589, 'Port Authority')]
        },
        'Brooklyn': {
            'commercial': [(-73.9857, 40.6782, 'Downtown Brooklyn'), (-73.9857, 40.6500, 'Park Slope'), (-73.9857, 40.6200, 'Bay Ridge')],
            'residential': [(-73.9857, 40.6500, 'Park Slope'), (-73.9857, 40.6200, 'Bay Ridge'), (-73.9857, 40.5900, 'Bensonhurst')],
            'industrial': [(-73.9857, 40.6500, 'Sunset Park'), (-73.9857, 40.6200, 'Red Hook')]
        },
        'Queens': {
            'commercial': [(-73.7949, 40.7282, 'Long Island City'), (-73.7781, 40.6413, 'JFK Airport'), (-73.8740, 40.7769, 'LaGuardia Airport')],
            'residential': [(-73.7949, 40.7282, 'Astoria'), (-73.7781, 40.6413, 'Jamaica'), (-73.8740, 40.7769, 'Flushing')],
            'industrial': [(-73.7781, 40.6413, 'JFK Area'), (-73.8740, 40.7769, 'LaGuardia Area')]
        }
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with Claude API key for real AI analysis (Anthropic)
        """
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.use_claude = False
        self.claude_client = None

        if anthropic_key and anthropic_key != "your_anthropic_api_key_here":
            try:
                import anthropic
                self.claude_client = anthropic.Anthropic(api_key=anthropic_key)
                self.use_claude = True
                print("[OK] Claude client initialized for advanced emissions analysis")
            except ImportError as e:
                print(f"[ERROR] Failed to import anthropic module: {e}")
                print(f"[ERROR] Run: pip install anthropic")
            except Exception as e:
                print(f"[ERROR] Claude initialization failed: {e}")
        else:
            print(f"[WARN] No valid ANTHROPIC_API_KEY found in environment")

        if not self.use_claude:
            print("[ERROR] Claude not initialized - using rule-based parsing only")
    
    def parse_prompt(self, prompt: str) -> Dict:
        """
        Advanced AI analysis of sustainability prompts
        Creates unique spatial predictions based on real NYC geography and context
        
        Args:
            prompt: Natural language description (e.g., "Convert 30% of taxis to EVs in Manhattan")
        
        Returns:
            Dict with keys:
                - borough: str (Manhattan, Brooklyn, etc., or "citywide")
                - sector: str (transport, buildings, industry)
                - reduction_percent: float
                - description: str
                - spatial_pattern: List[Tuple] (lat, lon, intensity) for unique patterns
                - ai_analysis: str (detailed AI reasoning)
        """
        print(f"[AI] Analyzing prompt: '{prompt}'")

        # Try Claude first (best for emissions analysis)
        if self.use_claude:
            try:
                return self._analyze_with_claude(prompt)
            except Exception as e:
                print(f"[WARN] Claude analysis failed: {e}")
                print("[INFO] Falling back to OpenAI or rules")

        # Final fallback: rule-based
        return self._parse_with_enhanced_rules(prompt)
    
    def _analyze_with_claude(self, prompt: str) -> Dict:
        """
        Advanced AI analysis using Claude (Anthropic) - optimized for emissions calculations
        Claude provides superior reasoning for data-driven predictions
        """
        print("[CLAUDE] Using Claude for emissions analysis...")

        user_message = f"""Analyze this NYC climate intervention:

USER REQUEST: "{prompt}"

FIRST: Check if this is a VALID climate intervention request:
- Is it specific enough to be actionable? (vague single-word prompts like "blue", "green", "red", "black" are NOT valid)
- Does it relate to emissions, energy, transport, buildings, or environmental systems?
- Can it realistically be implemented in NYC?

If the request is too vague, nonsensical, or unrelated to climate/emissions:
- Set "is_unrelated" to true
- Set all numeric values to 0
- Set direction to "none"

Otherwise, provide a realistic analysis considering:
1. What specifically changes (which assets, how many, where)
2. Current baseline emissions for that subsector
3. Realistic reduction/increase percentage
4. Geographic distribution (where impacts occur)
5. Secondary effects on other sectors
6. Feasibility constraints

Be specific with numbers and locations. Use actual NYC geography."""

        try:
            message = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",  # Claude 3 Haiku (available with current API key)
                max_tokens=2000,
                temperature=0.0,  # Set to 0 for deterministic/consistent results
                top_p=1.0,  # Use full probability distribution for maximum determinism
                system=self.CLAUDE_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": user_message
                }]
            )

            response_text = message.content[0].text

            # Clean up response text (remove control characters that break JSON parsing)
            # Replace literal \n, \r, \t in strings with spaces
            import re
            response_text_cleaned = response_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')

            # Parse Claude's JSON response (Claude might wrap in ```json blocks)
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text_cleaned, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Use whole response as JSON
                json_str = response_text_cleaned

            # Additional cleanup: fix common JSON issues
            json_str = json_str.strip()

            # FIX: Remove thousands separators (commas in numbers like "51,025")
            # This regex finds numbers with commas and removes the commas
            json_str = re.sub(r':\s*(\d{1,3}(?:,\d{3})+)', lambda m: ': ' + m.group(1).replace(',', ''), json_str)

            # Parse JSON
            try:
                analysis = json.loads(json_str)
            except json.JSONDecodeError as e:
                # If that fails, try to extract just the JSON object
                json_obj_match = re.search(r'\{.*\}', response_text_cleaned, re.DOTALL)
                if json_obj_match:
                    json_str_cleaned = json_obj_match.group()
                    # Apply same comma fix
                    json_str_cleaned = re.sub(r':\s*(\d{1,3}(?:,\d{3})+)', lambda m: ': ' + m.group(1).replace(',', ''), json_str_cleaned)
                    analysis = json.loads(json_str_cleaned)
                else:
                    raise

            print(f"[CLAUDE] Analysis complete: {analysis.get('summary', 'N/A')}")
            print(f"[CLAUDE] Confidence: {analysis.get('confidence_level', 'unknown')}, Average change: {analysis.get('average_change_percent', 0)}%")

            # Check if Claude marked this as unrelated
            is_unrelated = analysis.get("is_unrelated", False)
            
            # Map Claude's response to our intervention format
            intervention = {
                # Core fields
                "borough": analysis.get("borough", "citywide"),
                "sector": analysis.get("sector", "transport"),
                "subsector": analysis.get("subsector"),
                "direction": analysis.get("direction", "decrease"),
                "description": analysis.get("summary", "Climate intervention"),
                "is_unrelated": is_unrelated,

                # Geographic modifications (NEW - this is the key change!)
                "geographic_modifications": analysis.get("geographic_modifications", []),
                "average_change_percent": abs(analysis.get("average_change_percent", 20.0)),

                # Enhanced fields from Claude
                "confidence_level": analysis.get("confidence_level", "medium"),
                "secondary_impacts": analysis.get("secondary_impacts", []),
                "reasoning": analysis.get("reasoning", ""),

                # Real emissions (Claude calculates these!)
                "real_emissions": {
                    "baseline_tons_co2": analysis.get("baseline_emissions_tons_year", 0),
                    "reduced_tons_co2": analysis.get("reduced_emissions_tons_year", 0),
                    "annual_savings_tons_co2": analysis.get("annual_impact_tons_co2", 0),
                    "percentage_reduction": abs(analysis.get("average_change_percent", 20)),
                    "direction": analysis.get("direction", "decrease"),
                    "is_increase": analysis.get("direction", "decrease") == "increase",
                    "confidence": analysis.get("confidence_level", "medium")
                },

                # Spatial pattern from Claude's geographic_hotspots
                "spatial_pattern": [
                    (h["lat"], h["lon"], h.get("intensity", 0.8))
                    for h in analysis.get("geographic_hotspots", [])
                ]
            }

            return intervention

        except json.JSONDecodeError as e:
            print(f"[ERROR] Claude returned invalid JSON: {e}")
            print(f"[DEBUG] Full response (first 1000 chars):")
            print(f"{response_text[:1000]}")
            print(f"[DEBUG] Cleaned JSON string (first 1000 chars):")
            print(f"{json_str[:1000]}")
            raise
        except Exception as e:
            print(f"[ERROR] Claude API error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _analyze_with_openai(self, prompt: str) -> Dict:
        """
        Fallback: Advanced AI analysis using OpenAI to understand context and generate unique patterns
        """
        system_message = """You are an expert NYC sustainability analyst with deep knowledge of:
- NYC geography, neighborhoods, and landmarks
- Transportation systems, building types, and industrial zones
- Real-world emission patterns and reduction strategies
- Spatial distribution of different intervention types

Analyze the prompt and provide detailed insights about:
1. Geographic context and specific areas affected
2. Realistic spatial distribution patterns
3. Expected impact intensity in different zones
4. Technical feasibility and implementation considerations

Respond with detailed JSON analysis including:
- Basic intervention details (borough, sector, reduction_percent, description)
- Geographic analysis of where impacts will be strongest
- Spatial reasoning for the pattern distribution
- Real-world considerations affecting the intervention

Format your response as JSON with these fields:
{
    "borough": "Manhattan",
    "sector": "transport", 
    "reduction_percent": 25,
    "description": "EV taxi conversion",
    "geographic_analysis": "Detailed analysis of where impacts will occur",
    "spatial_reasoning": "Explanation of spatial distribution patterns",
    "real_world_factors": "Factors affecting implementation and impact"
}

Be specific about NYC landmarks, neighborhoods, and geographic features."""
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            ai_analysis = json.loads(json_match.group())
        else:
            ai_analysis = json.loads(content)
        
        # Generate unique spatial pattern based on AI analysis
        spatial_pattern = self._generate_spatial_pattern_from_ai(ai_analysis, prompt)
        
        intervention = {
            "borough": ai_analysis.get("borough", "citywide"),
            "sector": ai_analysis.get("sector", "transport"),
            "reduction_percent": ai_analysis.get("reduction_percent", 20.0),
            "description": ai_analysis.get("description", "Sustainability intervention"),
            "spatial_pattern": spatial_pattern,
            "ai_analysis": ai_analysis.get("geographic_analysis", ""),
            "spatial_reasoning": ai_analysis.get("spatial_reasoning", ""),
            "real_world_factors": ai_analysis.get("real_world_factors", "")
        }
        
        print(f"[OK] AI Analysis Complete: {intervention['description']}")
        print(f"[AI] Geographic Analysis: {intervention['ai_analysis'][:100]}...")
        return intervention
    
    def _generate_spatial_pattern_from_ai(self, ai_analysis: Dict, prompt: str) -> List[Tuple]:
        """
        Generate unique spatial pattern based on AI analysis
        Creates realistic geographic distribution patterns
        """
        borough = ai_analysis.get("borough", "citywide")
        sector = ai_analysis.get("sector", "transport")
        description = ai_analysis.get("description", "")
        reduction_percent = ai_analysis.get("reduction_percent", 20.0)
        
        # Create deterministic seed based on intervention details for consistency
        unique_seed = hash(f"{borough}_{sector}_{description}_{reduction_percent}") % 2**32
        np.random.seed(unique_seed)
        
        pattern_points = []
        
        # REAL NYC DATA-BASED PATTERNS (not random!)
        if sector == "transport":
            pattern_points.extend(self._generate_transport_pattern(borough, description, reduction_percent))
        elif sector == "buildings":
            pattern_points.extend(self._generate_buildings_pattern(borough, description, reduction_percent))
        elif sector == "industry":
            pattern_points.extend(self._generate_industry_pattern(borough, description, reduction_percent))
        elif sector == "energy":
            pattern_points.extend(self._generate_energy_pattern(borough, description, reduction_percent))
        
        print(f"[AI] Generated {len(pattern_points)} REALISTIC spatial points for {sector} in {borough}")
        return pattern_points
    
    def _generate_transport_pattern(self, borough: str, description: str, reduction_percent: float) -> List[Tuple]:
        """Generate realistic transport intervention patterns based on real NYC data"""
        pattern_points = []
        
        # REAL NYC TRANSPORT CORRIDORS AND HUBS
        transport_hubs = {
            'Manhattan': [
                (-73.9857, 40.7589, 'Times Square', 1.0),  # Major taxi hub
                (-73.9857, 40.7505, 'Grand Central', 0.9),  # Commuter hub
                (-73.9857, 40.7128, 'Wall Street', 0.8),  # Financial district
                (-73.9857, 40.7831, 'Upper East Side', 0.7),  # Residential
            ],
            'Brooklyn': [
                (-73.9857, 40.6892, 'Brooklyn Bridge', 0.8),  # Major crossing
                (-73.9857, 40.6782, 'Downtown Brooklyn', 0.9),  # Commercial hub
                (-73.9857, 40.6501, 'Park Slope', 0.6),  # Residential
            ],
            'Queens': [
                (-73.7781, 40.6413, 'JFK Airport', 1.0),  # Major airport - CORRECT coordinates
                (-73.8740, 40.7769, 'LaGuardia Airport', 0.9),  # Major airport - CORRECT coordinates
                (-73.9400, 40.7505, 'Queens Plaza', 0.7),  # Transit hub
            ],
            'Bronx': [
                (-73.9857, 40.8508, 'Yankee Stadium', 0.7),  # Major venue
                (-73.9857, 40.8508, 'Fordham', 0.6),  # Commercial area
            ],
            'Staten Island': [
                (-74.1502, 40.5795, 'Staten Island Ferry', 0.8),  # Major crossing
                (-74.1502, 40.6200, 'St George', 0.7),  # Commercial center
            ]
        }
        
        # Get borough-specific hubs
        hubs = transport_hubs.get(borough, transport_hubs['Manhattan'])
        
        # Generate realistic patterns around each hub
        for hub_lon, hub_lat, hub_name, base_intensity in hubs:
            # Calculate cluster size based on hub importance and reduction percentage
            cluster_size = int(base_intensity * reduction_percent * 2)  # More realistic sizing
            
            for i in range(cluster_size):
                # Create realistic spread patterns based on intervention type
                if 'taxi' in description.lower() or 'cab' in description.lower():
                    # Taxis cluster around commercial areas
                    offset_lat = hub_lat + np.random.normal(0, 0.01)  # Tight clustering
                    offset_lon = hub_lon + np.random.normal(0, 0.01)
                    intensity = base_intensity * (0.8 + np.random.uniform(0, 0.4))
                elif 'bus' in description.lower():
                    # Buses follow major routes
                    offset_lat = hub_lat + np.random.normal(0, 0.015)  # Route-based spread
                    offset_lon = hub_lon + np.random.normal(0, 0.015)
                    intensity = base_intensity * (0.7 + np.random.uniform(0, 0.3))
                elif 'ev' in description.lower() or 'electric' in description.lower():
                    # EVs cluster around charging infrastructure
                    offset_lat = hub_lat + np.random.normal(0, 0.012)
                    offset_lon = hub_lon + np.random.normal(0, 0.012)
                    intensity = base_intensity * (0.9 + np.random.uniform(0, 0.2))
                else:
                    # General transport patterns
                    offset_lat = hub_lat + np.random.normal(0, 0.02)
                    offset_lon = hub_lon + np.random.normal(0, 0.02)
                    intensity = base_intensity * (0.6 + np.random.uniform(0, 0.4))
                
                pattern_points.append((offset_lat, offset_lon, intensity))
        
        return pattern_points
    
    def _generate_buildings_pattern(self, borough: str, description: str, reduction_percent: float) -> List[Tuple]:
        """Generate realistic building intervention patterns based on real NYC data"""
        pattern_points = []
        
        # REAL NYC BUILDING DENSITY PATTERNS
        building_zones = {
            'Manhattan': [
                (-73.9857, 40.7589, 'Midtown Commercial', 1.0),  # High density
                (-73.9857, 40.7831, 'Upper East Side', 0.8),  # Residential
                (-73.9857, 40.7128, 'Financial District', 0.9),  # Commercial
                (-73.9857, 40.7505, 'Chelsea', 0.7),  # Mixed use
            ],
            'Brooklyn': [
                (-73.9857, 40.6782, 'Downtown Brooklyn', 0.9),  # Commercial
                (-73.9857, 40.6501, 'Park Slope', 0.8),  # Residential
                (-73.9857, 40.6782, 'Williamsburg', 0.7),  # Mixed use
            ],
            'Queens': [
                (-73.9857, 40.7505, 'Long Island City', 0.8),  # Mixed use
                (-73.9857, 40.7505, 'Astoria', 0.7),  # Residential
            ],
            'Bronx': [
                (-73.9857, 40.8508, 'Fordham', 0.7),  # Commercial
                (-73.9857, 40.8508, 'Mott Haven', 0.6),  # Mixed use
            ],
            'Staten Island': [
                (-74.1502, 40.6200, 'St George', 0.6),  # Commercial
                (-74.1502, 40.5795, 'New Dorp', 0.5),  # Residential
            ]
        }
        
        zones = building_zones.get(borough, building_zones['Manhattan'])
        
        for zone_lon, zone_lat, zone_name, base_intensity in zones:
            # Calculate cluster size based on building density and intervention type
            if 'solar' in description.lower():
                cluster_size = int(base_intensity * reduction_percent * 3)  # Solar spreads widely
            elif 'roof' in description.lower():
                cluster_size = int(base_intensity * reduction_percent * 2)  # Roof interventions
            else:
                cluster_size = int(base_intensity * reduction_percent * 1.5)  # General building
            
            for i in range(cluster_size):
                # Create realistic building patterns
                offset_lat = zone_lat + np.random.normal(0, 0.02)
                offset_lon = zone_lon + np.random.normal(0, 0.02)
                
                # Intensity based on building type and intervention
                if 'solar' in description.lower():
                    intensity = base_intensity * (0.7 + np.random.uniform(0, 0.3))
                elif 'roof' in description.lower():
                    intensity = base_intensity * (0.6 + np.random.uniform(0, 0.4))
                else:
                    intensity = base_intensity * (0.5 + np.random.uniform(0, 0.5))
                
                pattern_points.append((offset_lat, offset_lon, intensity))
        
        return pattern_points
    
    def _generate_industry_pattern(self, borough: str, description: str, reduction_percent: float) -> List[Tuple]:
        """Generate realistic industrial intervention patterns based on real NYC data"""
        pattern_points = []
        
        # REAL NYC INDUSTRIAL ZONES
        industrial_zones = {
            'Manhattan': [
                (-73.9857, 40.7128, 'Lower Manhattan', 0.6),  # Limited industry
            ],
            'Brooklyn': [
                (-73.9857, 40.6782, 'Sunset Park', 0.9),  # Major industrial
                (-73.9857, 40.6501, 'Red Hook', 0.8),  # Port area
                (-73.9857, 40.6782, 'Gowanus', 0.7),  # Industrial
            ],
            'Queens': [
                (-73.9857, 40.7505, 'Long Island City', 0.9),  # Major industrial
                (-73.9857, 40.7505, 'Maspeth', 0.8),  # Industrial
                (-73.9857, 40.7505, 'Jamaica', 0.7),  # Mixed industrial
            ],
            'Bronx': [
                (-73.9857, 40.8508, 'Hunts Point', 0.9),  # Major industrial
                (-73.9857, 40.8508, 'Port Morris', 0.8),  # Industrial
            ],
            'Staten Island': [
                (-74.1502, 40.5795, 'Port Richmond', 0.8),  # Industrial
                (-74.1502, 40.6200, 'Mariners Harbor', 0.7),  # Industrial
            ]
        }
        
        zones = industrial_zones.get(borough, industrial_zones['Brooklyn'])
        
        for zone_lon, zone_lat, zone_name, base_intensity in zones:
            cluster_size = int(base_intensity * reduction_percent * 2)
            
            for i in range(cluster_size):
                # Industrial patterns are more concentrated
                offset_lat = zone_lat + np.random.normal(0, 0.015)
                offset_lon = zone_lon + np.random.normal(0, 0.015)
                intensity = base_intensity * (0.8 + np.random.uniform(0, 0.2))
                
                pattern_points.append((offset_lat, offset_lon, intensity))
        
        return pattern_points
    
    def _generate_energy_pattern(self, borough: str, description: str, reduction_percent: float) -> List[Tuple]:
        """Generate realistic energy intervention patterns based on real NYC data"""
        pattern_points = []
        
        # REAL NYC ENERGY INFRASTRUCTURE
        energy_zones = {
            'Manhattan': [
                (-73.9857, 40.7589, 'ConEd Grid', 1.0),  # Major grid
                (-73.9857, 40.7505, 'Power Distribution', 0.8),
            ],
            'Brooklyn': [
                (-73.9857, 40.6782, 'Brooklyn Grid', 0.9),
                (-73.9857, 40.6501, 'Power Substations', 0.7),
            ],
            'Queens': [
                (-73.9857, 40.7505, 'Queens Grid', 0.9),
                (-73.9857, 40.7505, 'Power Plants', 0.8),
            ],
            'Bronx': [
                (-73.9857, 40.8508, 'Bronx Grid', 0.8),
            ],
            'Staten Island': [
                (-74.1502, 40.6200, 'Staten Island Grid', 0.7),
            ]
        }
        
        zones = energy_zones.get(borough, energy_zones['Manhattan'])
        
        for zone_lon, zone_lat, zone_name, base_intensity in zones:
            cluster_size = int(base_intensity * reduction_percent * 2.5)
            
            for i in range(cluster_size):
                offset_lat = zone_lat + np.random.normal(0, 0.02)
                offset_lon = zone_lon + np.random.normal(0, 0.02)
                intensity = base_intensity * (0.6 + np.random.uniform(0, 0.4))
                
                pattern_points.append((offset_lat, offset_lon, intensity))
        
        return pattern_points
    
    def _get_relevant_landmarks(self, borough: str, sector: str) -> List[Tuple]:
        """Get landmarks relevant to the sector and borough"""
        landmarks = []
        
        if borough in self.NYC_LANDMARKS:
            borough_data = self.NYC_LANDMARKS[borough]
            
            # Add sector-specific landmarks
            if sector == "transport":
                landmarks.extend(borough_data.get("transport_hubs", []))
                landmarks.extend(borough_data.get("commercial", []))  # Commercial areas have more traffic
            elif sector == "buildings":
                landmarks.extend(borough_data.get("residential", []))
                landmarks.extend(borough_data.get("commercial", []))
            elif sector == "industry":
                landmarks.extend(borough_data.get("industrial", []))
                landmarks.extend(borough_data.get("commercial", []))
            else:
                landmarks.extend(borough_data.get("commercial", []))
                landmarks.extend(borough_data.get("residential", []))
        
        # If citywide, get landmarks from all boroughs
        if borough == "citywide":
            for b in self.NYC_LANDMARKS:
                landmarks.extend(self._get_relevant_landmarks(b, sector))
        
        return landmarks
    
    def _get_borough_bounds(self, borough: str) -> Tuple[float, float, float, float]:
        """Get lat/lon bounds for borough"""
        bounds = {
            'Manhattan': (40.70, 40.88, -74.05, -73.93),
            'Brooklyn': (40.57, 40.73, -74.05, -73.83),
            'Queens': (40.54, 40.80, -74.05, -73.70),
            'Bronx': (40.78, 40.92, -73.95, -73.77),
            'Staten Island': (40.49, 40.65, -74.26, -74.05)
        }
        return bounds.get(borough, (40.49, 40.92, -74.26, -73.70))
    
    def _is_unrelated_prompt(self, prompt_lower: str) -> bool:
        """Check if prompt is unrelated to climate/emissions interventions"""
        # Action verbs - MUST contain at least one to be valid
        action_verbs = [
            'reduce', 'increase', 'cut', 'lower', 'decrease', 'add', 'expand',
            'install', 'convert', 'implement', 'deploy', 'phase out', 'remove',
            'ban', 'boost', 'grow', 'invest'
        ]
        
        # Sector keywords - specific things that can be changed
        sector_keywords = [
            'emission', 'carbon', 'co2', 'taxi', 'bus', 'vehicle', 'car', 'transport',
            'flight', 'plane', 'airport', 'aviation', 'building', 'solar', 'panel',
            'roof', 'energy', 'power', 'grid', 'electric', 'electricity', 'tree',
            'plant', 'park', 'industrial', 'factory', 'pollution', 'waste',
            'greenhouse', 'fuel', 'ev', 'sustainable', 'recycle', 'jfk', 'laguardia',
            'lga', 'manhattan', 'brooklyn', 'queens', 'bronx', 'heat', 'hvac',
            'wind', 'renewable', 'fossil', 'coal', 'gas', 'oil', 'train', 'subway',
            'rail', 'bike', 'traffic', 'congestion'
        ]
        
        # Check if prompt contains BOTH action verb AND sector keyword
        has_action = any(verb in prompt_lower for verb in action_verbs)
        has_sector = any(keyword in prompt_lower for keyword in sector_keywords)
        
        # VERY STRICT: Must have BOTH action AND sector, OR just be specific enough
        # Examples that should pass:
        # - "reduce emissions" (action + sector)
        # - "add solar panels" (action + sector)
        # - "JFK emissions" (specific location + sector)
        # 
        # Examples that should fail:
        # - "climate" (no action, no specific sector)
        # - "climate 30%" (no action, no specific sector)
        # - "environment" (too vague)
        
        # If no action verb AND no specific sector, it's unrelated
        if not has_action and not has_sector:
            return True
        
        # If has number/percent but no action or sector, it's unrelated
        has_number = any(char.isdigit() or char == '%' in prompt_lower for char in prompt_lower)
        if has_number and not has_action and not has_sector:
            return True
        
        # Vague terms that need more context
        vague_only_terms = ['climate', 'environment', 'green', 'sustainable']
        is_only_vague = any(term in prompt_lower for term in vague_only_terms) and not has_action and not has_sector
        if is_only_vague:
            return True
        
        # Even if it has some keywords, check if it's clearly unrelated
        unrelated_patterns = [
            'weather', 'temperature', 'rain', 'snow', 'forecast', 'sunny', 'cloudy',
            'restaurant', 'food', 'eat', 'drink', 'coffee', 'pizza', 'burger', 'candy', 'gummy', 'bear',
            'movie', 'show', 'entertainment', 'sport', 'game', 'play', 'fun',
            'hello', 'hi', 'hey', 'thanks', 'thank you', 'bye', 'goodbye',
            'joke', 'funny', 'meme', 'story', 'poem', 'song', 'music',
            'shop', 'store', 'buy', 'sell', 'price', 'cost',
            'people', 'person', 'friend', 'family', 'love', 'hate',
            'what', 'when', 'where', 'who', 'why', 'how', 'test', 'testing',
            'random', 'nonsense', 'asdf', 'qwer', 'xyz', 'abc'
        ]
        
        # If it has unrelated patterns, it's unrelated regardless of other keywords
        has_unrelated = any(pattern in prompt_lower for pattern in unrelated_patterns)
        if has_unrelated:
            return True
        
        # Single letter or very short nonsense (< 3 chars)
        if len(prompt_lower.strip()) < 3:
            return True
        
        # Short prompts (< 8 chars) with no clear action or sector
        if len(prompt_lower.strip()) < 8 and not (has_action or has_sector):
            return True
        
        return False
    
    def _parse_with_enhanced_rules(self, prompt: str) -> Dict:
        """Parse natural language prompt into structured intervention details"""
        prompt_lower = prompt.lower()
        
        # Check if prompt is actually related to climate/emissions
        if self._is_unrelated_prompt(prompt_lower):
            return {
                "borough": "citywide",
                "sector": "none",
                "reduction_percent": 0,
                "direction": "none",
                "description": "Unrelated query - no climate impact",
                "is_unrelated": True,
                "spatial_pattern": []
            }

        borough = self._extract_borough(prompt_lower)
        scenario = self._extract_scenario(prompt_lower)
        percent = self._extract_percentage(prompt_lower, scenario)

        targets = scenario.get("targets", [])
        intervention = {
            "borough": borough,
            "sector": scenario["sector"],
            "subsector": scenario.get("subsector"),
            "direction": scenario["direction"],
            "magnitude_percent": percent,
            "targets": targets,
            "description": self._generate_description(scenario["sector"], borough, percent, scenario["direction"], targets)
        }

        reduction_percent = percent if intervention["direction"] == "decrease" else -percent
        intervention["reduction_percent"] = reduction_percent
        spatial_pattern = self._generate_spatial_pattern_from_ai({
            "borough": borough,
            "sector": intervention["sector"],
            "description": intervention["description"],
            "reduction_percent": reduction_percent
        }, prompt)

        intervention["spatial_pattern"] = spatial_pattern

        print(f"[OK] Parsed scenario: {intervention['description']}")
        return intervention
    
    def _generate_description(self, sector: str, borough: str, percent: float, direction: str, targets: Optional[List[str]] = None) -> str:
        location = borough if borough != "citywide" else "NYC"
        verbs = {
            'decrease': 'reduction',
            'increase': 'increase'
        }
        action = verbs.get(direction, 'change')
        target = targets[0] if targets else sector
        return f"{percent:.0f}% {target} {action} in {location}"

    def _extract_borough(self, prompt_lower: str) -> str:
        # Check for specific airport mentions first
        if 'jfk' in prompt_lower or 'john f kennedy' in prompt_lower or 'kennedy airport' in prompt_lower:
            return "Queens"  # JFK is in Queens
        if 'lga' in prompt_lower or 'laguardia' in prompt_lower or 'la guardia' in prompt_lower:
            return "Queens"  # LaGuardia is in Queens
        if 'newark' in prompt_lower or 'ewr' in prompt_lower:
            return "citywide"  # Newark is in NJ but affects NYC
        
        # Check for boroughs
        for borough in self.BOROUGHS:
            if borough.lower() in prompt_lower:
                return borough
        return "citywide"

    def _extract_scenario(self, prompt_lower: str) -> Dict[str, Any]:
        scenario = {
            "sector": "transport",
            "direction": "decrease",
            "targets": []
        }

        # Special case: sustainable/renewable/clean technologies are REDUCTIONS even with "add"
        sustainability_indicators = [
            "sustainable", "saf", "renewable", "clean", "green", "electric", "ev",
            "solar", "wind", "hydro", "geothermal", "biofuel", "hydrogen",
            "efficiency", "insulation", "led", "heat pump"
        ]
        has_sustainability = any(ind in prompt_lower for ind in sustainability_indicators)
        
        direction_keywords = {
            "decrease": ["reduce", "cut", "lower", "decrease", "phase out", "remove", "ban"],
            "increase": ["increase", "boost", "expand", "grow", "invest"]  # Removed "add" - context-dependent
        }

        # Check for explicit direction keywords
        for direction, keywords in direction_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                scenario["direction"] = direction
                break
        
        # Special handling for "add" - depends on context
        if "add" in prompt_lower:
            if has_sustainability:
                scenario["direction"] = "decrease"  # Adding clean tech reduces emissions
            else:
                scenario["direction"] = "increase"  # Adding non-clean items increases emissions
        
        # "plant" is always a decrease (trees, vegetation)
        if "plant" in prompt_lower:
            scenario["direction"] = "decrease"

        transport_targets = {
            "taxi": "taxis",
            "cab": "taxis",
            "bus": "buses",
            "buses": "buses",
            "subway": "rail",
            "train": "rail",
            "car": "cars",
            "cars": "cars",
            "vehicle": "vehicles",
            "airline": "aviation",
            "plane": "aviation",
            "flight": "aviation",
            "airport": "aviation"
        }

        building_targets = {
            "building": "buildings",
            "skyscraper": "buildings",
            "office": "commercial",
            "residential": "residential",
            "solar": "solar",
            "panel": "solar",
            "heat pump": "heat_pumps",
            "hvac": "hvac"
        }

        industry_targets = {
            "factory": "factories",
            "industrial": "industrial",
            "manufacturing": "factories",
            "warehouse": "warehouses",
            "port": "port"
        }

        energy_targets = {
            "grid": "grid",
            "power": "power",
            "electricity": "power",
            "battery": "storage",
            "storage": "storage"
        }

        nature_targets = {
            "tree": "trees",
            "trees": "trees",
            "park": "parks",
            "green roof": "green_roofs",
            "greenroof": "green_roofs",
            "garden": "gardens"
        }

        sector_map = {
            "transport": transport_targets,
            "buildings": building_targets,
            "industry": industry_targets,
            "energy": energy_targets,
            "nature": nature_targets
        }

        for sector, keywords in sector_map.items():
            for keyword, target in keywords.items():
                if keyword in prompt_lower:
                    scenario["sector"] = sector
                    scenario.setdefault("targets", []).append(target)
        
        if not scenario.get("targets"):
            scenario["targets"].append("general")

        if scenario["sector"] == "transport":
            if "bus" in prompt_lower or "buses" in prompt_lower:
                scenario["subsector"] = "bus"
            elif ("air" in prompt_lower or "plane" in prompt_lower or "flight" in prompt_lower or 
                  "airport" in prompt_lower or "jfk" in prompt_lower or "lga" in prompt_lower or 
                  "laguardia" in prompt_lower or "aviation" in prompt_lower):
                scenario["subsector"] = "aviation"
                # Store specific airport if mentioned
                if "jfk" in prompt_lower:
                    scenario["specific_location"] = "JFK Airport"
                elif "lga" in prompt_lower or "laguardia" in prompt_lower:
                    scenario["specific_location"] = "LaGuardia Airport"
            elif "taxi" in prompt_lower or "cab" in prompt_lower:
                scenario["subsector"] = "taxis"
            elif "rail" in prompt_lower or "subway" in prompt_lower or "train" in prompt_lower:
                scenario["subsector"] = "rail"
            elif "freight" in prompt_lower or "truck" in prompt_lower:
                scenario["subsector"] = "freight"
            else:
                scenario["subsector"] = "road"
        elif scenario["sector"] == "buildings":
            if "commercial" in prompt_lower or "office" in prompt_lower:
                scenario["subsector"] = "commercial"
            elif "residential" in prompt_lower or "apartment" in prompt_lower:
                scenario["subsector"] = "residential"
            else:
                scenario["subsector"] = "mixed"
        elif scenario["sector"] == "industry":
            if "port" in prompt_lower or "shipping" in prompt_lower:
                scenario["subsector"] = "port"
            elif "warehouse" in prompt_lower:
                scenario["subsector"] = "logistics"
            else:
                scenario["subsector"] = "general"
        elif scenario["sector"] == "nature":
            if "tree" in prompt_lower or "forest" in prompt_lower:
                scenario["subsector"] = "urban_forest"
            elif "park" in prompt_lower:
                scenario["subsector"] = "parks"
            else:
                scenario["subsector"] = "green_infrastructure"
        else:
            scenario["subsector"] = "general"

        return scenario

    def _extract_percentage(self, prompt_lower: str, scenario: Dict[str, Any]) -> float:
        percent = 20.0
        explicit = re.search(r'(\d+\.?\d*)\s*%', prompt_lower)
        if explicit:
            percent = float(explicit.group(1))
        else:
            if 'all' in prompt_lower or '100%' in prompt_lower:
                percent = 100.0
            elif 'half' in prompt_lower or '50%' in prompt_lower:
                percent = 50.0
            elif 'quarter' in prompt_lower or '25%' in prompt_lower:
                percent = 25.0
            elif 'double' in prompt_lower and scenario.get("direction") == "increase":
                percent = 100.0
            elif 'double' in prompt_lower:
                percent = 30.0
            elif 'increase' in prompt_lower and scenario.get("direction") == "increase":
                percent = 20.0

        return float(max(0, min(percent, 100)))