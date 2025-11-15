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

// -------------------------------------------------------------------------
// NEW RESOURCES FILLER
// -------------------------------------------------------------------------
function fillResources(data) {

    // TOTAL USAGE (real usage from /apps/locations)
    document.getElementById("total-cpu").textContent =
        (data.resources_total_cpu_used ?? 0).toFixed(2) + " vCPU";

    document.getElementById("total-ram").textContent =
        formatStorage(data.resources_total_ram_gb_used ?? 0);

    document.getElementById("total-hdd").textContent =
        formatStorage(data.resources_total_hdd_gb_used ?? 0);

    // PER-TIER USAGE (real usage)
    const rtu = data.resources_tier_usage || {};

    function loadTier(prefix, d) {
        d = d || {};
        document.getElementById(prefix + "-instances").textContent = d.instances ?? 0;
        document.getElementById(prefix + "-cpu").textContent = (d.cpu ?? 0).toFixed(2) + " vCPU";
        document.getElementById(prefix + "-ram").textContent = formatStorage(d.ram_gb ?? 0);
        document.getElementById(prefix + "-hdd").textContent = formatStorage(d.hdd_gb ?? 0);
    }

    loadTier("rtu-cumulus", rtu.CUMULUS);
    loadTier("rtu-nimbus", rtu.NIMBUS);
    loadTier("rtu-stratus", rtu.STRATUS);

    // GLOBAL UTILIZATION (real, resources-based)
    document.getElementById("cpu-util-pct").textContent =
        (data.resources_cpu_util_pct ?? 0) + "%";

    document.getElementById("ram-util-pct").textContent =
        (data.resources_ram_util_pct ?? 0) + "%";

    document.getElementById("hdd-util-pct").textContent =
        (data.resources_hdd_util_pct ?? 0) + "%";

    // ---------------------------------------------------------------------
    // NEW: PER-TIER UTILIZATION (%)
    // ---------------------------------------------------------------------
    const tu = data.tier_utilization || {};

    function setTierUtil(idPrefix, obj) {
        obj = obj || {};
        document.getElementById(idPrefix + "-cpu").textContent =
            (obj.cpu_util_pct ?? 0) + "%";
        document.getElementById(idPrefix + "-ram").textContent =
            (obj.ram_util_pct ?? 0) + "%";
        document.getElementById(idPrefix + "-hdd").textContent =
            (obj.hdd_util_pct ?? 0) + "%";
    }

    setTierUtil("tier-util-cumulus", tu.CUMULUS);
    setTierUtil("tier-util-nimbus", tu.NIMBUS);
    setTierUtil("tier-util-stratus", tu.STRATUS);
}

// --- load stats -----------------------------------------------------------

async function loadStats() {
    try {
        const resp = await fetch("/stats", { credentials: "include" });
        const data = await resp.json();

        document.getElementById("loading").classList.add("hidden");

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

        // RESOURCES (new real usage + per-tier + per-tier utilization)
        fillResources(data);

        // NETWORK CAPACITY
        document.getElementById("network-total-cpu").textContent =
            (data.network_total_cpu ?? 0) + " vCPU";
        document.getElementById("network-total-ram").textContent =
            formatTB(data.network_total_ram_tb);
        document.getElementById("network-total-hdd").textContent =
            formatTB(data.network_total_hdd_tb);

        const tierCap = data.tier_capacity || {};
        ["CUMULUS", "NIMBUS", "STRATUS"].forEach(t => {
            const l = t.toLowerCase();
            const c = tierCap[t] || {};
            document.getElementById(`network-${l}-nodes`).textContent = c.nodes ?? 0;
            document.getElementById(`network-${l}-cpu`).textContent = (c.cpu ?? 0) + " vCPU";
            document.getElementById(`network-${l}-ram`).textContent = formatTB(c.ram_tb);
            document.getElementById(`network-${l}-hdd`).textContent = formatTB(c.hdd_tb);
        });

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
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        const tab = btn.dataset.tab;

        document.querySelectorAll(".tab-content").forEach(c => c.classList.add("hidden"));
        document.getElementById("tab-" + tab).classList.remove("hidden");
    });
});
