document.addEventListener("DOMContentLoaded", () => {
  const fanForm = document.getElementById("fan-login-form");
  const staffForm = document.getElementById("staff-login-form");
  const staffError = document.getElementById("staff-error");

  fanForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("fan-name").value.trim() || "Anonymous Fan";
    
    // Store simple token in sessionStorage for quick client-side checks
    const sessionData = { role: "fan", name: name };
    sessionStorage.setItem("fanflow_auth", JSON.stringify(sessionData));
    
    // Also hit the backend to potentially set a cookie for server-side auth
    await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "fan", name: name })
    });
    
    window.location.href = "/fan";
  });

  staffForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("staff-name").value.trim();
    const code = document.getElementById("staff-code").value.trim();
    
    staffError.classList.add("hidden");
    
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: "staff", name: name, access_code: code })
      });
      
      if (res.ok) {
        const sessionData = { role: "staff", name: name };
        sessionStorage.setItem("fanflow_auth", JSON.stringify(sessionData));
        window.location.href = "/staff";
      } else {
        const data = await res.json();
        staffError.textContent = data.detail || "Invalid access code.";
        staffError.classList.remove("hidden");
      }
    } catch (err) {
      staffError.textContent = "Network error. Try again.";
      staffError.classList.remove("hidden");
    }
  });
});
