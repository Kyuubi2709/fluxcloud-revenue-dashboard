async function loadStats() {
    try {
        const resp = await fetch("/stats");
        const data = await resp.json();

        document.getElementById("loading").classList.add("hidden");
        document.getElementById("content").classList.remove("hidden");

        // Existing metrics
        document.getElementById("total-apps").textContent = data.total_apps;
        document.getElementById("marketplace-apps").textContent = data.marketplace_apps;
        document.getElementById("custom-apps").textContent = data.custom_apps;

        // NEW metrics
        document.getElementById("marketplace-pct").textContent = data.marketplace_pct + "%";
        document.getElementById("custom-pct").textContent = data.custom_pct + "%";
        document.getElementById("total-instances").textContent = data.total_instances;
        document.getElementById("company-deployments").textContent = data.company_deployments;
        document.getElementById("company-instances").textContent = data.company_instances;

        // Top 5 marketplace apps
        const tbody = document.querySelector("#top5-table tbody");
        tbody.innerHTML = "";

        data.top_marketplace_apps.forEach(app => {
            const row = document.createElement("tr");

            const nameCell = document.createElement("td");
            nameCell.textContent = app.name;

            const countCell = document.createElement("td");
            countCell.textContent = app.deployments;

            row.appendChild(nameCell);
            row.appendChild(countCell);
            tbody.appendChild(row);
        });

    } catch (err) {
        document.getElementById("loading").textContent = "Error loading data.";
        console.error(err);
    }
}

loadStats();
