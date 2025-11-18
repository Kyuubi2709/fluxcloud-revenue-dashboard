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

// --- Chart.js center-text plugin & chart handle -------------------------

let tierNodesChart = null;

// Simple plugin to draw center text inside doughnut charts
const centerTextPlugin = {
    id: "centerText",
    afterDraw(chart, args, options) {
        if (!options || !options.title) return;

        const { ctx, chartArea } = chart;
        if (!chartArea) return;

        const { left, right, top, bottom } = chartArea;
        const x = (left + right) / 2;
        const y = (top + bottom) / 2;

        ctx.save();
        ctx.textAlign = "center";
        ctx.fillStyle = options.color || "#333";

        ctx.font = "bold 14px Arial";
        ctx.fillText(options.title, x, y - 4);

        if (options.subTitle) {
            ctx.font = "12px Arial";
            ctx.fillText(options.subTitle, x, y + 14);
        }

        ctx.restore();
    }
};

// Register plugin if Chart.js is loaded
if (window.Chart) {
    Chart.register(centerTextPlugin);
}

// -------------------------------------------------------------------------
// NEW: Update Nodes Running Apps (By Tier) doughnut
// -------------------------------------------------------------------------
function updateTierNodesChart(data) {
    if (!window.Chart) return;

    const ctx = document.getElementById("tierNodesChart");
    if (!ctx) return;

    const nodeUsage = data.tier_node_usage || {};

    const tierKeys = ["CUMULUS", "NIMBUS", "STRATUS"];
    const labels = ["Cumulus", "Nimbus", "Stratus"];
    const values = tierKeys.map(tier =>
        (nodeUsage[tier] && nodeUsage[tier].used_nodes) ? nodeUsage[tier].used_nodes : 0
    );

    const totalNodes = values.reduce((sum, v) => sum + v, 0);

    if (tierNodesChart) {
        tierNodesChart.destroy();
    }

    tierNodesChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    "#2b6cb0", // Cumulus - blue
                    "#38a169", // Nimbus - green
                    "#805ad5"  // Stratus - purple
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "60%",
            plugins: {
                legend: {
                    position: "bottom"
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const label = context.label || "";
                            const value = context.parsed || 0;
                            const pct = totalNodes ? ((value / totalNodes) * 100).toFixed(1) : 0;
                            return `${label}: ${value} nodes (${pct}%)`;
                        }
                    }
                },
                centerText: {
                    title: `${totalNodes} nodes`,
                    subTitle: "with \u22651 app",
                    color: "#333"
                }
            }
        }
    });
}

// -------------------------------------------------------------------------
// RESOURCES FILLER
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
        const instEl = document.getElementById(prefix + "-instances");
        const cpuEl = document.getElementById(prefix + "-cpu");
        const ramEl = document.getElementById(prefix + "-ram");
        const hddEl = document.getElementById(prefix + "-hdd");

        if (instEl) instEl.textContent = d.instances ?? 0;
        if (cpuEl) cpuEl.textContent = (d.cpu ?? 0).toFixed(2) + " vCPU";
        if (ramEl) ramEl.textContent = formatStorage(d.ram_gb ?? 0);
        if (hddEl) hddEl.textContent = formatStorage(d.hdd_gb ?? 0);
    }

    loadTier("rtu-cumulus", rtu.CUMULUS);
    loadTier("rtu-nimbus", rtu.NIMBUS);
    loadTier("rtu-stratus", rtu.STRATUS);

    // GLOBAL UTILIZATION (real, resources-based)
    const cpuUtilEl = document.getElementById("cpu-util-pct");
    const ramUtilEl = document.getElementById("ram-util-pct");
    const hddUtilEl = document.getElementById("hdd-util-pct");

    if (cpuUtilEl) cpuUtilEl.textContent = (data.resources_cpu_util_pct ?? 0) + "%";
    if (ramUtilEl) ramUtilEl.textContent = (data.resources_ram_util_pct ?? 0) + "%";
    if (hddUtilEl) hddUtilEl.textContent = (data.resources_hdd_util_pct ?? 0) + "%";

    // PER-TIER UTILIZATION (%)
    const tu = data.tier_utilization || {};

    function setTierUtil(idPrefix, obj) {
        obj = obj || {};
        const cpuEl = document.getElementById(idPrefix + "-cpu");
        const ramEl = document.getElementById(idPrefix + "-ram");
        const hddEl = document.getElementById(idPrefix + "-hdd");

        if (cpuEl) cpuEl.textContent = (obj.cpu_util_pct ?? 0) + "%";
        if (ramEl) ramEl.textContent = (obj.ram_util_pct ?? 0) + "%";
        if (hddEl) hddEl.textContent = (obj.hdd_util_pct ?? 0) + "%";
    }

    setTierUtil("tier-util-cumulus", tu.CUMULUS);
    setTierUtil("tier-util-nimbus", tu.NIMBUS);
    setTierUtil("tier-util-stratus", tu.STRATUS);

    // Update the doughnut chart for nodes running apps
    updateTierNodesChart(data);
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

        // RESOURCES (new real usage + per-tier + per-tier utilization + chart)
        fillResources(data);

        // NETWORK CAPACITY (totals)
        document.getElementById("network-total-cpu").textContent =
            (data.network_total_cpu ?? 0) + " vCPU";
        document.getElementById("network-total-ram").textContent =
            formatTB(data.network_total_ram_tb);
        document.getElementById("network-total-hdd").textContent =
            formatTB(data.network_total_hdd_tb);

        // NETWORK CAPACITY BY TIER
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
