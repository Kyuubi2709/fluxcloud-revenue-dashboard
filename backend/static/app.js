async function loadStats() {
    try {
        const resp = await fetch("/stats"); 
        const data = await resp.json();

        document.getElementById("loading").classList.add("hidden");
        document.getElementById("content").classList.remove("hidden");

        document.getElementById("total-apps").textContent = data.total_apps;
        document.getElementById("marketplace-apps").textContent = data.marketplace_apps;
        document.getElementById("custom-apps").textContent = data.custom_apps;

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
