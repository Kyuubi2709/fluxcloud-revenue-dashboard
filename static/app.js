async function loadStats() {
    try {
        const resp = await fetch("/stats");
        const data = await resp.json();

        document.getElementById("loading").classList.add("hidden");
        document.getElementById("content").classList.remove("hidden");

        // BASIC METRICS
        document.getElementById("total-apps").textContent = data.total_apps;
        document.getElementById("marketplace-apps").textContent = data.marketplace_apps;
        document.getElementById("custom-apps").textContent = data.custom_apps;

        // PERCENTAGES
        document.getElementById("marketplace-pct").textContent = data.marketplace_pct + "%";
        document.getElementById("custom-pct").textContent = data.custom_pct + "%";

        // INSTANCES + COMPANY
        document.getElementById("total-instances").textContent = data.total_instances;
        document.getElementById("company-deployments").textContent = data.company_deployments;
        document.getElementById("company-instances").textContent = data.company_instances;

        // CONTACT METRICS
        document.getElementById("marketplace-with-contacts").textContent = data.marketplace_with_contacts;
        document.getElementById("marketplace-contact-pct").textContent = data.marketplace_contact_pct + "%";

        // NEW FLAGS (ALL APPS)
        document.getElementById("total-with-secrets").textContent = data.total_with_secrets;
        document.getElementById("total-with-staticip").textContent = data.total_with_staticip;

        // NEW FLAGS (MARKETPLACE)
        document.getElementById("marketplace-with-secrets").textContent = data.marketplace_with_secrets;
        document.getElementById("marketplace-with-staticip").textContent = data.marketplace_with_staticip;

        // TOP 5
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
