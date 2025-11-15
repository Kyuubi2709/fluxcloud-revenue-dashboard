// --- formatting helpers --------------------------------------------------

function formatStorage(gb) {
    if (gb === null || gb === undefined || isNaN(gb)) return "–";
    const v = Number(gb);
    return v >= 1000 ? (v / 1000).toFixed(2) + " TB" : v.toFixed(2) + " GB";
}

function formatTB(val) {
    if (val === null || val === undefined || isNaN(val)) return "0.00 TB";
    return Number(val).toFixed(2) + " TB";
}

// --- load stats -----------------------------------------------------------

async function loadStats() {
    try {
        const resp = await fetch("/stats", { credentials: "include" });
        const data = await resp.json();

        document.getElementById("loading").classList.add("hidden");

        // timestamp
        if (data.last_updated) {
            document.getElementById("last-updated").textContent =
                "Last updated: " + new Date(data.last_updated).toLocaleString();
        }

        document.getElementById("content").classList.remove("hidden");

        // BASIC COUNTS
        document.getElementById("total-apps").textContent = data.total_apps;
        document.getElementById("marketplace-apps").textContent = data.marketplace_apps;
        document.getElementById("custom-apps").textContent = data.custom_apps;
        document.getElementById("unique-owners").textContent = data.unique_owners;

        // PERCENTAGES
        document.getElementById("marketplace-pct").textContent = data.marketplace_pct + "%";
        document.getElementById("custom-pct").textContent = data.custom_pct + "%";

        // INSTANCES
        document.getElementById("total-instances").textContent = data.total_instances;
        document.getElementById("company-deployments").textContent = data.company_deployments;
        document.getElementById("company-instances").textContent = data.company_instances;

        // CONTACTS
        document.getElementById("marketplace-with-contacts").textContent = data.marketplace_with_contacts;
        document.getElementById("marketplace-contact-pct").textContent = data.marketplace_contact_pct + "%";
        document.getElementById("total-with-contacts").textContent = data.total_with_contacts;
        document.getElementById("total-contact-pct").textContent = data.total_contact_pct + "%";
        document.getElementById("custom-with-contacts").textContent = data.custom_with_contacts;
        document.getElementById("custom-contact-pct").textContent = data.custom_contact_pct + "%";

        // secrets & static ip
        document.getElementById("total-with-secrets").textContent = data.total_with_secrets;
        document.getElementById("total-with-staticip").textContent = data.total_with_staticip;
        document.getElementById("marketplace-with-secrets").textContent = data.marketplace_with_secrets;
        document.getElementById("marketplace-with-staticip").textContent = data.marketplace_with_staticip;

        // RESOURCES
        document.getElementById("total-cpu").textContent = data.total_cpu + " vCPU";
        document.getElementById("total-ram").textContent = formatStorage(data.total_ram_gb);
        document.getElementById("total-hdd").textContent = formatStorage(data.total_hdd_gb);

        // TIER USAGE
        const tierUsage = data.tier_usage || {};
        ["CUMULUS", "NIMBUS", "STRATUS"].forEach(t => {
            const l = t.toLowerCase();
            const u = tierUsage[t] || {};
            document.getElementById(`tier-${l}-instances`).textContent = u.instances ?? 0;
            document.getElementById(`tier-${l}-cpu`).textContent = (u.cpu ?? 0) + " vCPU";
            document.getElementById(`tier-${l}-ram`).textContent = formatStorage(u.ram_gb);
            document.getElementById(`tier-${l}-hdd`).textContent = formatStorage(u.hdd_gb);
        });

        // NETWORK CAPACITY
        document.getElementById("network-total-cpu").textContent = data.network_total_cpu + " vCPU";
        document.getElementById("network-total-ram").textContent = formatTB(data.network_total_ram_tb);
        document.getElementById("network-total-hdd").textContent = formatTB(data.network_total_hdd_tb);

        const tierCap = data.tier_capacity || {};
        ["CUMULUS", "NIMBUS", "STRATUS"].forEach(t => {
            const l = t.toLowerCase();
            const c = tierCap[t] || {};
            document.getElementById(`network-${l}-nodes`).textContent = c.nodes ?? 0;
            document.getElementById(`network-${l}-cpu`).textContent = (c.cpu ?? 0) + " vCPU";
            document.getElementById(`network-${l}-ram`).textContent = formatTB(c.ram_tb);
            document.getElementById(`network-${l}-hdd`).textContent = formatTB(c.hdd_tb);
        });

        // UTILIZATION
        document.getElementById("cpu-util-pct").textContent = data.cpu_util_pct + "%";
        document.getElementById("ram-util-pct").textContent = data.ram_util_pct + "%";
        document.getElementById("hdd-util-pct").textContent = data.hdd_util_pct + "%";

        // TOP 5
        const tbody = document.querySelector("#top5-table tbody");
        tbody.innerHTML = "";
        data.top_marketplace_apps.forEach(app => {
            const row = document.createElement("tr");
            row.innerHTML = `<td>${app.name}</td><td>${app.deployments}</td>`;
            tbody.appendChild(row);
        });

    } catch (err) {
        console.error(err);
        document.getElementById("loading").textContent = "Error loading data.";
    }
}

loadStats();

// --- refresh logic -------------------------------------------------------

document.getElementById("refresh-btn").addEventListener("click", async () => {
    const status = document.getElementById("refresh-status");
    const spinner = document.getElementById("spinner");

    const oldTime = document.getElementById("last-updated").textContent;
    spinner.classList.remove("hidden");
    status.textContent = "Refreshing...";

    const resp = await fetch("/refresh", {
        method: "POST",
        credentials: "include"
    });

    const data = await resp.json();

    if (data.status !== "ok") {
        status.textContent = data.message;
        spinner.classList.add("hidden");
        return;
    }

    status.textContent = "Refresh started — updating shortly...";

    // Poll until cache updates
    const poll = setInterval(async () => {
        const r = await fetch("/stats", { credentials: "include" });
        const stats = await r.json();
        const newTime = "Last updated: " + new Date(stats.last_updated).toLocaleString();

        if (newTime !== oldTime) {
            clearInterval(poll);
            spinner.classList.add("hidden");
            status.textContent = "";
            loadStats();
        }
    }, 2000);
});

// --- tab handling ---------------------------------------------------------

document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        // Switch active button
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        const tab = btn.dataset.tab;

        // Hide all tabs
        document.querySelectorAll(".tab-content").forEach(c => c.classList.add("hidden"));

        // Show selected tab
        document.getElementById("tab-" + tab).classList.remove("hidden");
    });
});
