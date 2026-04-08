# 🌍 Wandr AI — Intelligent Travel Planning System

An AI-powered travel planning web application using Flask, Random Forest ML, and NLP chatbot.

## 📁 Project Structure

```
travel_planner/
├── run.py                  # App entry point
├── requirements.txt
├── travel.db               # Auto-created SQLite database
├── app/
│   ├── __init__.py         # App factory, DB init
│   ├── ai_engine.py        # ML predictions, itinerary, chatbot, sentiment
│   └── models.py           # (Reference only — using raw SQLite)
├── routes/
│   ├── auth.py             # Login, register, logout
│   ├── main.py             # Page routes (dashboard, planner, itinerary)
│   └── api.py              # JSON API endpoints
├── templates/
│   ├── index.html          # Landing page
│   ├── auth.html           # Login/Register
│   ├── dashboard.html      # User dashboard
│   ├── planner.html        # Trip planner + AI recommendations
│   └── itinerary.html      # Day-wise itinerary view
├── data/
│   ├── generate_dataset.py # Dataset generator
│   └── travel_data.csv     # 5000-record training dataset
└── models/
    ├── train_model.py      # ML training script
    ├── rf_model.pkl        # Trained Random Forest model
    ├── encoders.pkl        # Label encoders
    └── feature_names.pkl   # Feature list
```

## ⚙️ Setup & Installation

### 1. Install Dependencies
```bash
pip install Flask scikit-learn pandas numpy Werkzeug
```

### 2. Generate Dataset & Train Model
```bash
cd data
python generate_dataset.py    # Creates travel_data.csv
cd ../models
python train_model.py         # Trains and saves rf_model.pkl
```

### 3. Run the App
```bash
python run.py
```

Visit: http://localhost:5000

## 🤖 AI/ML Components

| Component | Details |
|-----------|---------|
| Algorithm | Random Forest Classifier |
| Training Data | 5000 Indian travel records |
| Features | Budget, accommodation, food, travel time, season, trip type, traffic |
| Accuracy | ~87% (on synthetic data; improves with real data) |
| Sentiment | Keyword-based NLP (positive/negative word matching) |
| Chatbot | Pattern-matching NLP with destination-aware responses |
| Itinerary | Rule-based day-wise schedule generation |

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/recommend` | POST | Get ML-ranked destination recommendations |
| `/api/itinerary` | POST | Generate day-wise itinerary |
| `/api/chat` | POST | AI chatbot response |
| `/api/sentiment` | POST | Analyse review sentiment |
| `/api/trips` | GET | Get user's trip history |

## 🔐 Authentication
- Session-based authentication using Flask sessions
- Passwords hashed with Werkzeug's `generate_password_hash`
- SQLite database stores users, trips, and reviews

## 📊 Features
- ✅ User Registration & Login
- ✅ Random Forest destination feasibility analysis
- ✅ Budget-aware recommendations (8 destinations ranked by AI score)
- ✅ Day-wise itinerary generation (collapsible timeline UI)
- ✅ NLP chatbot with destination-specific knowledge
- ✅ Sentiment analysis on reviews
- ✅ Trip history dashboard
- ✅ Responsive, travel-themed UI

## 🚀 Extending the Project
- **Real APIs**: Add OpenWeatherMap, Google Places, Skyscanner APIs
- **Better NLP**: Integrate transformers (BERT) for sentiment analysis
- **More ML**: Add collaborative filtering for personalized recommendations  
- **Maps**: Embed Google Maps/Leaflet.js in itinerary view
- **Reviews**: Allow users to write and view real community reviews

## 📝 Tech Stack
- **Backend**: Flask (Python), SQLite
- **ML**: scikit-learn (Random Forest), pandas, numpy
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Auth**: Flask Sessions + Werkzeug password hashing
- **NLP**: Custom keyword-based sentiment + pattern chatbot
