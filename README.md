# NYC CO₂ Sustainability Simulation

An AI-powered climate action visualization tool for New York City that simulates the environmental impact of sustainability interventions.

## 🌍 Overview

This application uses artificial intelligence to parse natural language prompts about sustainability actions and generates realistic spatial predictions of their environmental impact across NYC's five boroughs.

## ✨ Features

- **AI-Driven Spatial Modeling**: Each prompt creates unique, realistic spatial patterns based on NYC geography
- **Interactive Map Visualization**: Leaflet.js-powered map showing emission data and intervention impacts
- **Real NYC Geography Integration**: Uses actual landmarks, transportation corridors, and building zones
- **Sector-Specific Analysis**: Different modeling for transport, buildings, industry, and energy sectors
- **Borough-Specific Targeting**: Manhattan commercial areas, Brooklyn residential zones, Queens industrial areas, etc.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Modern web browser

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Alternative: HTML Version
Simply open `test-app.html` in your browser (backend must be running).

## 🎯 How It Works

1. **AI Prompt Processing**: Parses natural language descriptions of sustainability actions
2. **Spatial Pattern Generation**: Creates realistic geographic patterns based on:
   - Borough-specific zones (Manhattan commercial, Brooklyn residential, etc.)
   - Sector-specific modeling (transport corridors, building density, industrial zones)
   - Description analysis (taxi vs bus patterns, solar vs green roof effects)
3. **Map Visualization**: Displays baseline emissions and intervention impacts

## 📊 Example Prompts

Try these prompts to see different spatial patterns:

- **"Convert 30% of taxis to EVs in Manhattan"** → Linear patterns along Broadway/5th Ave
- **"Add solar panels to 50% of Brooklyn buildings"** → Dense clusters in Park Slope/Downtown Brooklyn  
- **"Reduce citywide industrial emissions by 20%"** → Concentrated zones near JFK/LaGuardia/ports
- **"Convert Staten Island buses to electric"** → Route-based patterns on Staten Island
- **"Install green roofs on 25% of Queens buildings"** → Building density patterns in Long Island City

## 🗺️ Map Features

- **Baseline Emissions**: Red dots showing current NYC emission data
- **Simulation Results**: Green dots showing intervention impact
- **Impact Difference**: Color-coded visualization of reduction percentages
- **Interactive Popups**: Detailed emission data for each location

## 🧠 AI Technology

### Spatial Modeling
- **Transport**: Broadway, 5th Ave, Brooklyn Bridge, JFK/LaGuardia airports
- **Buildings**: Times Square, Financial District, Downtown Brooklyn, Park Slope
- **Industry**: JFK area, Sunset Park industrial, Hunts Point, Staten Island ports
- **Energy**: Commercial districts, power grid areas

### Description Intelligence
- **"taxi"** → Concentrates in commercial areas
- **"bus"** → Follows major routes  
- **"EV"** → Charging station patterns
- **"solar"** → South-facing roof optimization
- **"green roof"** → Flat roof (commercial) focus
- **"industrial"** → Airport and port concentration

## 📁 Project Structure

```
nyc-co2-app/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── ai_processor.py      # AI prompt parsing
│   ├── data_processor.py    # Spatial modeling & data processing
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # React frontend
│   │   └── main.jsx       # React entry point
│   ├── package.json       # Node.js dependencies
│   └── vite.config.js     # Vite configuration
├── test-app.html          # Standalone HTML version
├── start-backend.bat      # Backend startup script
└── start-frontend.bat     # Frontend startup script
```

## 🔧 API Endpoints

- `GET /` - Health check
- `GET /api/baseline` - Baseline NYC emissions data
- `POST /api/simulate` - Run sustainability simulation
- `GET /api/openaq` - Raw OpenAQ station data
- `GET /docs` - Interactive API documentation

## 🌟 Key Innovations

1. **Deterministic Spatial Patterns**: Each prompt creates unique, reproducible patterns
2. **Real Geography Integration**: Uses actual NYC landmarks and zones
3. **Sector-Specific Intelligence**: Different modeling for different intervention types
4. **Dynamic Visualization**: Map adapts to show relative differences between interventions

## 🎨 Visualization Features

- **Dynamic Range Calculation**: Each dataset is normalized for optimal visualization
- **Color-Coded Impact**: Red (baseline) → Green (simulation) → Color-coded (difference)
- **Interactive Elements**: Click any dot for detailed emission data
- **Console Logging**: Debug information showing data ranges and patterns

## 🚀 Future Enhancements

- Real-time data integration
- Machine learning model training
- Additional cities and regions
- Advanced visualization options
- Mobile app development

## 📄 License

This project is part of GatorHacks 2025.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

---

**Built with ❤️ for NYC's sustainable future**
