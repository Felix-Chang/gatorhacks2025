"""
AI Prompt Processing Module
Uses OpenAI API (or can be adapted for local LLM) to parse natural language
sustainability prompts into structured interventions
"""

from typing import Dict, Optional
import json
import re


class AIPromptProcessor:
    """
    Processes natural language sustainability prompts
    Can use OpenAI API or fallback to rule-based parsing
    """
    
    BOROUGHS = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']
    SECTORS = ['transport', 'buildings', 'industry', 'energy', 'all']
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with optional OpenAI API key
        If no key provided, will use rule-based parsing
        """
        self.api_key = api_key
        self.use_openai = bool(api_key)
        
        if self.use_openai:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
                print("[OK] OpenAI client initialized")
            except Exception as e:
                print(f"[WARN]  OpenAI initialization failed: {e}")
                print("[INFO] Falling back to rule-based parsing")
                self.use_openai = False
    
    def parse_prompt(self, prompt: str) -> Dict:
        """
        Parse natural language prompt into structured intervention
        
        Args:
            prompt: Natural language description (e.g., "Convert 30% of taxis to EVs in Manhattan")
        
        Returns:
            Dict with keys:
                - borough: str (Manhattan, Brooklyn, etc., or "citywide")
                - sector: str (transport, buildings, industry)
                - reduction_percent: float
                - description: str
        """
        print(f"[AI] Parsing prompt: '{prompt}'")
        
        if self.use_openai:
            try:
                return self._parse_with_openai(prompt)
            except Exception as e:
                print(f"[WARN]  OpenAI parsing failed: {e}")
                print("[INFO] Falling back to rule-based parsing")
                return self._parse_with_rules(prompt)
        else:
            return self._parse_with_rules(prompt)
    
    def _parse_with_openai(self, prompt: str) -> Dict:
        """
        Use OpenAI API to parse prompt
        """
        system_message = """You are an AI assistant that parses sustainability intervention prompts for NYC.

Given a natural language prompt, extract:
1. Borough (Manhattan, Brooklyn, Queens, Bronx, Staten Island, or "citywide")
2. Sector (transport, buildings, industry, or "all")
3. Reduction percentage (estimate if not explicit)
4. Brief description

Respond ONLY with valid JSON in this exact format:
{
    "borough": "Manhattan",
    "sector": "transport",
    "reduction_percent": 25,
    "description": "EV taxi conversion"
}

Examples:
- "Convert 30% of taxis to EVs in Manhattan" â†’ {"borough": "Manhattan", "sector": "transport", "reduction_percent": 25, "description": "EV taxi conversion"}
- "Add solar panels to all Brooklyn buildings" â†’ {"borough": "Brooklyn", "sector": "buildings", "reduction_percent": 20, "description": "Solar panel installation"}
- "Reduce citywide industrial emissions by 15%" â†’ {"borough": "citywide", "sector": "industry", "reduction_percent": 15, "description": "Industrial emission reduction"}
"""
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        content = response.choices[0].message.content.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            intervention = json.loads(json_match.group())
        else:
            intervention = json.loads(content)
        
        print(f"[OK] Parsed intervention: {intervention}")
        return intervention
    
    def _parse_with_rules(self, prompt: str) -> Dict:
        """
        Rule-based parsing as fallback or when no API key
        """
        prompt_lower = prompt.lower()
        
        # Extract borough
        borough = "citywide"
        for b in self.BOROUGHS:
            if b.lower() in prompt_lower:
                borough = b
                break
        
        # Extract sector
        sector = "transport"  # Default
        sector_keywords = {
            'transport': ['taxi', 'cab', 'bus', 'car', 'vehicle', 'ev', 'traffic', 'transport'],
            'buildings': ['building', 'solar', 'panel', 'heating', 'cooling', 'hvac', 'insulation'],
            'industry': ['industry', 'industrial', 'factory', 'manufacturing'],
            'energy': ['energy', 'power', 'electricity', 'grid']
        }
        
        for sector_name, keywords in sector_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                sector = sector_name
                break
        
        # Extract percentage
        reduction_percent = 20.0  # Default
        
        # Look for explicit percentages
        percent_match = re.search(r'(\d+)\s*%', prompt)
        if percent_match:
            reduction_percent = float(percent_match.group(1))
            # Adjust if it's a conversion rather than direct reduction
            if 'convert' in prompt_lower or 'replace' in prompt_lower:
                reduction_percent *= 0.8  # Converting X% of fleet reduces emissions by ~0.8X%
        else:
            # Look for implicit amounts
            if 'all' in prompt_lower:
                reduction_percent = 50
            elif 'half' in prompt_lower:
                reduction_percent = 25
            elif 'double' in prompt_lower or 'increase' in prompt_lower:
                reduction_percent = 30
        
        # Cap at reasonable values
        reduction_percent = min(reduction_percent, 60)
        
        # Generate description
        description = self._generate_description(sector, borough, reduction_percent)
        
        intervention = {
            "borough": borough,
            "sector": sector,
            "reduction_percent": reduction_percent,
            "description": description
        }
        
        print(f"[OK] Rule-based parsing: {intervention}")
        return intervention
    
    def _generate_description(self, sector: str, borough: str, percent: float) -> str:
        """Generate human-readable description"""
        location = borough if borough != "citywide" else "NYC"
        return f"{percent:.0f}% {sector} emission reduction in {location}"


