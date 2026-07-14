# FanFlow AI

FanFlow AI is a hybrid prototype built for the FIFA World Cup 2026 at MetLife Stadium. It features a scalable FastAPI backend that powers two distinct interfaces: a mobile-first, vanilla web chat UI for stadium attendees to receive real-time, translated navigational assistance, and a premium Command Center dashboard for stadium organizers to monitor live crowd density and prioritize AI-generated incident alerts.

## Running Locally

1. Install dependencies: `pip install -r requirements.txt`
2. Set up your `.env` file with any required keys (e.g., `GOOGLE_API_KEY`).
3. Run the single FastAPI app:
   ```bash
   uvicorn backend.main:app --reload
   ```

## Deployment

- **Live Application**: [https://fanflow.onrender.com](https://fanflow.onrender.com)
