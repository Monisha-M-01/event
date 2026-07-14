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

## Dashboard CSS Code

```css
/* Dashboard Specific Styles extending style.css */

.dashboard-body {
  align-items: flex-start;
  padding: 0;
  height: auto;
  min-height: 100vh;
}

.dashboard-container {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
}

.dashboard-main {
  display: flex;
  flex-direction: row;
  gap: 32px;
  padding: 32px;
}

@media (max-width: 900px) {
  .dashboard-main {
    flex-direction: column;
  }
}

.dashboard-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.left-col {
  flex: 1.5;
}

.section-title {
  font-family: var(--font-display);
  font-size: 1.5rem;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.nav-link {
  color: var(--primary-color);
  text-decoration: none;
  font-family: var(--font-display);
  font-weight: 700;
  text-transform: uppercase;
  padding: 8px 16px;
  border: 1px solid var(--primary-color);
  border-radius: 4px;
  transition: var(--transition);
}

.nav-link:hover {
  background-color: var(--primary-color);
  color: #fff;
}

/* Guidance Box */
.guidance-box {
  background: linear-gradient(135deg, #1A1A24 0%, #0E1117 100%);
  border: 1px solid #00A3E0;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,163,224,0.15);
}

.guidance-title {
  color: #00A3E0;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

#guidance-text {
  white-space: pre-line;
  font-size: 1.05rem;
  line-height: 1.5;
}

/* Occupancy Table/Bars */
.occupancy-item {
  background-color: var(--surface-color);
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  border-left: 4px solid var(--primary-color);
}

.occupancy-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-weight: 600;
}

.occupancy-bar-bg {
  background-color: var(--bg-color);
  height: 12px;
  border-radius: 6px;
  overflow: hidden;
}

.occupancy-bar-fill {
  background-color: var(--primary-color);
  height: 100%;
  transition: width 0.5s ease-in-out;
}

.occupancy-status {
  font-size: 0.85rem;
  color: var(--text-secondary);
  text-transform: uppercase;
}

/* Alerts */
.metrics-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.metric-card {
  flex: 1;
  background-color: var(--surface-color);
  padding: 20px;
  border-radius: 12px;
  border-left: 4px solid var(--primary-color);
}

.metric-card.critical {
  border-left-color: #FF4B4B;
}

.metric-label {
  font-size: 14px;
  color: #888;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 32px;
  font-weight: bold;
}

.metric-card.critical .metric-value {
  color: #FF4B4B;
}

.alert-card {
  background-color: var(--surface-color);
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  border: 1px solid var(--chalk-line);
}

.alert-critical { border-left: 4px solid #FF4B4B; }
.alert-high { border-left: 4px solid #FFA421; }
.alert-medium { border-left: 4px solid #FCE83A; }

.alert-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.alert-title {
  font-size: 1.1rem;
  font-weight: bold;
}

.alert-zone {
  color: #AAA;
  font-size: 0.85rem;
  background: #333;
  padding: 2px 8px;
  border-radius: 12px;
}

.alert-desc {
  font-size: 0.95rem;
  margin-bottom: 10px;
  color: #DDD;
}

.alert-action {
  font-size: 0.9rem;
  color: #00A3E0;
  background: var(--bg-color);
  padding: 8px;
  border-radius: 6px;
  border-left: 2px solid #00A3E0;
}
```
