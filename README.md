# FanFlow AI

FanFlow AI is a hybrid hackathon prototype built for the FIFA World Cup 2026 at MetLife Stadium. It features a scalable FastAPI backend that powers two distinct interfaces: a mobile-first, vanilla web chat UI for stadium attendees to receive real-time, translated navigational assistance, and a premium Command Center dashboard for stadium organizers to monitor live crowd density and prioritize AI-generated incident alerts.

## Running Locally

1. Install dependencies: `pip install -r requirements.txt`
2. Set up your `.env` file with any required keys (e.g., `GOOGLE_API_KEY`).
3. Run the single FastAPI app:
   ```bash
   uvicorn backend.main:app --reload
   ```
4. Access the apps:
   - **Fan Chat UI**: [http://localhost:8000/](http://localhost:8000/)
   - **Organizer Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)

## Deployment

This project is structured as a **single deployable service**. 
You only need ONE deployment/service on platforms like Render, Railway, or Fly.io.

1. Connect your repository to your hosting provider.
2. Set the build command to `pip install -r requirements.txt`.
3. Set the start command to `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
4. The same URL will serve both the fan app at the root (`/`) and the organizer dashboard at (`/dashboard`).
