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

### Exact Deployment Steps (Render)
1. **Push to GitHub**: Make sure this repository is pushed to your GitHub account.
2. Go to [Render.com](https://render.com) and log in.
3. Click **New** -> **Web Service**.
4. Connect the GitHub repository you just pushed.
5. Provide a name for your service.
6. Make sure the Environment is set to **Python 3**.
7. Set the **Build Command** to: `pip install -r requirements.txt`
8. Set the **Start Command** to: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
9. Under **Advanced**, click **Add Environment Variable** and add the following two secrets:
    * Key: `GEMINI_API_KEY`, Value: *<your_actual_gemini_api_key>*
    * Key: `STAFF_ACCESS_CODE`, Value: *<your_custom_admin_password>*
10. Click **Create Web Service** at the bottom.
11. Wait for the build and deployment to finish (this may take a few minutes).
12. Once deployed, click the provided Render URL at the top left. This single public URL will serve both the Fan Gate at `/` and the Staff Dashboard at `/staff`!
