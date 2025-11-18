# Water Utilities Financial Analysis - Frontend Dashboard

React-based dashboard for visualizing water utility financial data.

## Features

- 📊 Interactive dashboard with key metrics
- 📈 Revenue and expense trend visualizations
- 💰 Financial forecasting with scenario modeling
- 🔍 Search and filter utilities
- 📱 Responsive design (works on mobile)
- ⚡ Fast and lightweight

## Tech Stack

- React 18
- Vite (build tool)
- Recharts (charts)
- Tailwind CSS (styling)
- React Router (navigation)
- TanStack Query (data fetching)

## Setup

### Prerequisites

- Node.js 18+ and npm
- Backend API running (see `../api/`)

### Installation

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.jsx          # Main dashboard
│   │   ├── UtilityList.jsx        # List all utilities
│   │   ├── UtilityDetail.jsx      # Single utility view
│   │   └── ForecastView.jsx       # Forecast visualization
│   ├── App.jsx                    # Main app component
│   ├── App.css                    # Global styles
│   └── main.jsx                   # Entry point
├── public/                        # Static assets
├── package.json
└── vite.config.js
```

## Usage

### Starting the Full Stack

Terminal 1 - Backend:
```bash
cd api
python main.py
# API available at http://localhost:8000
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
# Dashboard at http://localhost:5173
```

### Features

1. **Dashboard** (`/`)
   - Overview of all utilities
   - Top 10 utilities by revenue
   - Aggregate revenue trends
   - State distribution

2. **Utilities List** (`/utilities`)
   - Browse all utilities
   - Filter by state
   - Search by name
   - View years of available data

3. **Utility Detail** (`/utility/:id`)
   - Financial summary
   - Multi-year trends
   - Growth rate calculations
   - Operating metrics

4. **Forecasts** (`/forecast/:id`)
   - View scenario projections
   - Compare base/optimistic/pessimistic
   - Export forecasts

## Development

### Running with Sample Data

If you haven't collected real data yet, generate sample data:

```bash
# From project root
python run_pipeline.py --setup --generate-data --utilities 20 --years 10
```

Then start the backend and frontend as shown above.

### Customization

#### Adding New Charts

1. Install chart library (if not using Recharts):
```bash
npm install chart.js react-chartjs-2
```

2. Create component in `src/components/`

3. Import in parent component

#### Changing Colors/Styling

Edit `tailwind.config.js` for Tailwind customization:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        // Add custom colors
      }
    }
  }
}
```

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`.

To change the API URL, update fetch calls in components:

```javascript
// Current
const response = await fetch('http://localhost:8000/api/utilities');

// Change to production
const API_URL = process.env.VITE_API_URL || 'https://api.waterutilities.com';
const response = await fetch(`${API_URL}/api/utilities`);
```

## Deployment

### Option 1: Static Hosting (Free)

Build and deploy to Vercel, Netlify, or GitHub Pages:

```bash
npm run build
# Upload dist/ folder to hosting service
```

### Option 2: Docker

```bash
# Build production image
docker build -t water-utilities-frontend .

# Run
docker run -p 3000:3000 water-utilities-frontend
```

### Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000
VITE_APP_TITLE=Water Utilities Analysis
```

## Performance

- Lazy loading for routes (code splitting)
- React Query for caching API responses
- Vite for fast builds and HMR
- Production builds are optimized (<200KB)

## Troubleshooting

**API Connection Failed**
- Ensure backend is running on port 8000
- Check CORS settings in `api/main.py`

**Charts Not Rendering**
- Check that data is in correct format
- Verify Recharts is installed: `npm install recharts`

**Slow Performance**
- Check browser console for errors
- Verify API responses are fast (<1s)
- Consider pagination for large datasets

## Cost

**Development:** $0 (runs locally)
**Production (optional):**
- Vercel/Netlify: $0 (free tier)
- Custom domain: ~$12/year (optional)

**Total: $0 for full functionality**
