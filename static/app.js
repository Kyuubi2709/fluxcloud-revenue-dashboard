function formatStorage(gb) {
    if (gb === null || gb === undefined || isNaN(gb)) {
        return "–";
    }

    const value = Number(gb);
    if (value >= 1000) {
        const tb = value / 1000;
        return tb.toFixed(2) + " TB";
    }
    return value.toFixed(2) + " GB";
}

function formatTB(val) {
    if (val === null || val === undefined || isNaN(val)) {
        return "0.00 TB";
    }
    return Number(val).toFixed(2) + " TB";
}

async function loadStats() {
    try {
        // IMPORTANT: include session cookies
        const resp = await fetch("/stats", {
            credentials: "include"
        });

        const data = await resp.json();

        document.getElementById("loading").classList.add("hidden");
        document.getElementById("content").classList.remove("hidden");

        // LAST UPDATED TIMESTAMP
        if (data.last_updated) {
            document.getElementById("last-updated").textContent =
                "Last updated: " + new Date(data.last_updated).toLocaleString();
        }

        // BASIC COUNTS
        document.getElementById("total-apps").textContent = data.total_apps;
        document.getElementById("marketplace-apps").textContent = data.marketplace_apps;
        document.getElementById("custom-apps").textContent = data.custom_apps;
        document.getElementById("unique-owners").textContent = data.unique_owners;

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

        document.getElementById("total-with-contacts").textContent = data.total_with_contacts;
        document.getElementById("total-contact-pct").textContent = data.total_contact_pct + "%";

        document.getElementById("custom-with-contacts").textContent = data.custom_with_contacts;
        document.getElementById("custom-contact-pct").textContent = data.custom_contact_pct + "%";

        // SECRETS & STATIC IP
        document.getElementById("total-with-secrets").textContent = data.total_with_secrets;
        document.getElementById("total-with-staticip").textContent = data.total_with_staticip;

        document.getElementById("marketplace-with-secrets").textContent = data.marketplace_with_secrets;
        document.getElementById("marketplace-with-staticip").textContent = data.marketplace_with_staticip;

        // ----------------------
        // RESOURCES (APPS)
        // ----------------------
        document.getElementById("total-cpu").textContent = `${data.total_cpu} vCPU`;
        document.getElementById("total-ram").textContent = formatStorage(data.total_ram_gb);
        document.getElementById("total-hdd").textContent = formatStorage(data.total_hdd_gb);

        // ----------------------
        // RESOURCE USAGE BY TIER
        // ----------------------
        const tierUsage = data.tier_usage || {};

        function fillTierUsage(tierKey) {
            const lower = tierKey.toLowerCase();
            const u = tierUsage[tierKey] || {};

            const instEl = document.getElementById(`tier-${lower}-instances`);
            const cpuEl = document.getElementById(`tier-${lower}-cpu`);
            const ramEl = document.getElementById(`tier-${lower}-ram`);
            const hddEl = document.getElementById(`tier-${lower}-hdd`);

            if (instEl) instEl.textContent = u.instances ?? 0;
            if (cpuEl) cpuEl.textContent = (u.cpu ?? 0) + " vCPU";
            if (ramEl) ramEl.textContent = formatStorage(u.ram_gb);
            if (hddEl) hddEl.textContent = formatStorage(u.hdd_gb);
        }

        ["CUMULUS", "NIMBUS", "STRATUS"].forEach(fillTierUsage);

        // ----------------------
        // NETWORK CAPACITY (ALL TIERS)
        // ----------------------
        document.getElementById("network-total-cpu").textContent =
            (data.network_total_cpu ?? 0) + " vCPU";

        document.getElementById("network-total-ram").textContent =
            formatTB(data.network_total_ram_tb);

        document.getElementById("network-total-hdd").textContent =
            formatTB(data.network_total_hdd_tb);

        // ----------------------
        // NETWORK CAPACITY BY TIER
        // ----------------------
        const tierCap = data.tier_capacity || {};

        function fillTierCap(tierKey) {
            const lower = tierKey.toLowerCase();
            const c = tierCap[tierKey] || {};

            const nodesEl = document.getElementById(`network-${lower}-nodes`);
            const cpuEl = document.getElementById(`network-${lower}-cpu`);
            const ramEl = document.getElementById(`network-${lower}-ram`);
            const hddEl = document.getElementById(`network-${lower}-hdd`);

            if (nodesEl) nodesEl.textContent = c.nodes ?? 0;
            if (cpuEl) cpuEl.textContent = (c.cpu ?? 0) + " vCPU";
            if (ramEl) ramEl.textContent = formatTB(c.ram_tb);
            if (hddEl) hddEl.textContent = formatTB(c.hdd_tb);
        }

        ["CUMULUS", "NIMBUS", "STRATUS"].forEach(fillTierCap);

        // ----------------------
        // NETWORK UTILIZATION
        // ----------------------
        document.getElementById("cpu-util-pct").textContent =
            (data.cpu_util_pct ?? 0) + "%";

        document.getElementById("ram-util-pct").textContent =
            (data.ram_util_pct ?? 0) + "%";

        document.getElementById("hdd-util-pct").textContent =
            (data.hdd_util_pct ?? 0) + "%";

        // TOP 5
        const tbody = document.querySelector("#top5-table tbody");
        tbody.innerHTML = "";

        data.top_marketplace_apps.forEach(app => {
            const row = document.createElement("tr");
            row.innerHTML = `<td>${app.name}</td><td>${app.deployments}</td>`;
            tbody.appendChild(row);
        });

    } catch (err) {
        document.getElementById("loading").textContent = "Error loading data.";
        console.error(err);
    }
}

loadStats();


// --------------------------------------------------------
// MANUAL REFRESH BUTTON
// --------------------------------------------------------
document.getElementById("refresh-btn").addEventListener("click", async () => {
    const statusEl = document.getElementById("refresh-status");
    statusEl.textContent = "Refreshing...";

    const resp = await fetch("/refresh", {
        method: "POST",
        credentials: "include"   // IMPORTANT
    });

    const data = await resp.json();

    if (data.status === "ok") {
        statusEl.textContent = "Refresh started — updating shortly...";
        setTimeout(loadStats, 5000);
    }
    else if (data.status === "cooldown") {
        statusEl.textContent = data.message;
    }
    else {
        statusEl.textContent = "Failed to refresh.";
    }
});
