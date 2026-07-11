document.addEventListener("DOMContentLoaded", () => {
  const authData = JSON.parse(sessionStorage.getItem("fanflow_auth") || "null");
  if (!authData || authData.role !== "staff") {
    window.location.href = "/";
    return;
  }
  
  document.getElementById("auth-info").textContent = `Logged in as ${authData.name} · Staff`;
  document.getElementById("logout-btn").addEventListener("click", () => {
    sessionStorage.removeItem("fanflow_auth");
    window.location.href = "/";
  });

  const API_BASE = window.location.origin;

  const guidanceText = document.getElementById("guidance-text");
  const occupancyContainer = document.getElementById("occupancy-container");
  const totalAlertsVal = document.getElementById("total-alerts-val");
  const criticalAlertsVal = document.getElementById("critical-alerts-val");
  const alertsContainer = document.getElementById("alerts-container");

  async function fetchDashboardData() {
    try {
      const [crowdRes, alertsRes] = await Promise.all([
        fetch(`${API_BASE}/api/crowd-status`),
        fetch(`${API_BASE}/api/alerts`)
      ]);

      if (crowdRes.ok) {
        const crowdData = await crowdRes.json();
        updateCrowdData(crowdData);
      }

      if (alertsRes.ok) {
        const alertsData = await alertsRes.json();
        updateAlertsData(alertsData);
      }
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    }
  }

  function updateCrowdData(data) {
    if (data.guidance) {
      guidanceText.textContent = data.guidance;
    }

    if (data.zones && data.zones.length > 0) {
      occupancyContainer.innerHTML = data.zones.map(zone => {
        const percent = parseFloat(zone.occupancy_percent).toFixed(1);
        return `
          <div class="occupancy-item">
            <div class="occupancy-header">
              <span>${zone.zone_name} <span class="occupancy-status">(${zone.density_level})</span></span>
              <span>${percent}% (${zone.crowd_count} / ${zone.capacity})</span>
            </div>
            <div class="occupancy-bar-bg">
              <div class="occupancy-bar-fill" style="width: ${percent}%;"></div>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  function updateAlertsData(data) {
    totalAlertsVal.textContent = data.total_alerts || 0;
    criticalAlertsVal.textContent = data.critical_count || 0;

    if (data.cards && data.cards.length > 0) {
      alertsContainer.innerHTML = data.cards.map(card => {
        const a = card.alert;
        const sev = a.severity;
        const rank = card.priority_rank;
        
        let cls = "alert-medium";
        let icon = "🟡";
        if (sev >= 4) {
          cls = "alert-critical";
          icon = "🔴";
        } else if (sev === 3) {
          cls = "alert-high";
          icon = "🟠";
        }

        const typeFormatted = a.type.replace('_', ' ').toUpperCase();

        return `
          <div class="alert-card ${cls}">
            <div class="alert-header">
              <div class="alert-title">${icon} Rank ${rank}: ${typeFormatted}</div>
              <div class="alert-zone">${a.zone}</div>
            </div>
            <div class="alert-desc">${a.description}</div>
            <div class="alert-action">
              <strong>AI Action:</strong> ${card.llm_summary}
            </div>
          </div>
        `;
      }).join('');
    }
  }

  // Initial fetch
  fetchDashboardData();

  // Poll every 5 seconds
  setInterval(fetchDashboardData, 5000);
});
