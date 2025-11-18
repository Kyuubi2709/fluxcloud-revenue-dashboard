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
// Chart.js center text plugin (for tier donut charts & nodes chart)
// -------------------------------------------------------------------------
let centerTextPluginRegistered = false;

function ensureCenterTextPlugin() {
    if (centerTextPluginRegistered || typeof Chart === "undefined") return;

    const centerTextPlugin = {
        id: "centerTextPlugin",
        beforeDraw(chart, args, pluginOptions) {
            const text = pluginOptions && pluginOptions.text;
            if (!text) return;

            const { ctx, chartArea } = chart;
            if (!chartArea) return;

            const { left, right, top, bottom, width, height } = chartArea;

            ctx.save();
            ctx.font = "600 14px Arial, sans-serif";
            ctx.fillStyle = "#111827";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(text, left + width / 2, top + height / 2);
            ctx.restore();
        }
    };

    Chart.register(centerTextPlugin);
    centerTextPluginRegistered = true;
}

// -------------------------------------------------------------------------
// Global chart references
// -------------------------------------------------------------------------
let tierNodesChart = null;
const tierResourceCharts = {};

// -------------------------------------------------------------------------
// Nodes pie chart (Nodes Running Apps By Tier)
// -------------------------------------------------------------------------
function renderTierNodesChart(data) {
    if (typeof Chart === "undefined") return;
    ensureCenterTextPlugin();

    const usage = data.tier_node_usage || {};
    const tiers = ["CUMULUS", "NIMBUS", "STRATUS"];
    const labels = ["Cumulus", "Nimbus", "Stratus"];

    const used = tiers.map(t => (usage[t] && usage[t].used_nodes) || 0);
    const totalUsed = used.reduce((a, b) => a + b, 0);

    const ctx = document.getElementById("tierNodesChart");
    if (!ctx) return;

    if (tierNodesChart) {
        tierNodesChart.destroy();
    }

    tierNodesChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                label: "Nodes running apps",
                data: used,
                backgroundColor: ["#3b82f6", "#8b5cf6", "#10b981"],
                hoverOffset: 4
            }]
        },
        options: {
            cutout: "60%",
            plugins: {
                legend: {
                    display: true,
                    position: "bottom",
                    labels: {
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const label = context.label || "";
                            const value = context.parsed || 0;
                            const tierKey = tiers[context.dataIndex];
                            const tierInfo = usage[tierKey] || {};
                            const totalNodes = tierInfo.total_nodes || 0;
                            const pct = totalNodes ? ((value / totalNodes) * 100).toFixed(1) : 0;
                            return `${label}: ${value} of ${totalNodes} nodes (${pct}%)`;
                        }
                    }
                },
                centerTextPlugin: {
                    text: totalUsed ? `${totalUsed} nodes` : "No nodes"
                }
            }
        }
    });

    // Text summaries below the chart
    function setSummary(id, tierKey, label) {
        const el = document.getElementById(id);
        if (!el) return;
        const tierInfo = usage[tierKey] || {};
        const usedNodes = tierInfo.used_nodes || 0;
        const totalNodes = tierInfo.total_nodes || 0;
        const pct = tierInfo.pct != null ? tierInfo.pct : (totalNodes ? (usedNodes / totalNodes) * 100 : 0);
        el.textContent = `${label}: ${usedNodes.toLocaleString()} / ${totalNodes.toLocaleString()} nodes (${pct.toFixed(1)}%)`;
    }

    setSummary("nodes-cumulus-summary", "CUMULUS", "Cumulus");
    setSummary("nodes-nimbus-summary", "NIMBUS", "Nimbus");
    setSummary("nodes-stratus-summary", "STRATUS", "Stratus");
}

// -------------------------------------------------------------------------
// Tier Resource Doughnuts (one donut per tier, 4 rings)
// -------------------------------------------------------------------------
function renderTierResourceCharts(data) {
    if (typeof Chart === "undefined") return;
    ensureCenterTextPlugin();

    const rtu = data.resources_tier_usage || {};
    const cap = data.tier_capacity || {};
    const totalInstances = data.total_instances || 0;

    const tiers = ["CUMULUS", "NIMBUS", "STRATUS"];
    const tierLabels = {
        CUMULUS: "Cumulus",
        NIMBUS: "Nimbus",
        STRATUS: "Stratus"
    };

    tiers.forEach(tier => {
        const idKey = tier.toLowerCase();
        const usage = rtu[tier] || {};
        const capacity = cap[tier] || {};

        // Values
        const instancesUsed = usage.instances || 0;
        const instancesTotal = totalInstances || instancesUsed; // avoid 0/0
        const instancesFree = Math.max(instancesTotal - instancesUsed, 0);

        const cpuUsed = usage.cpu || 0;
        const cpuCap = capacity.cpu || cpuUsed;
        const cpuFree = Math.max(cpuCap - cpuUsed, 0);

        const ramUsed = usage.ram_gb || 0;
        const ramCap = (capacity.ram_tb || 0) * 1000 || ramUsed;
        const ramFree = Math.max(ramCap - ramUsed, 0);

        const hddUsed = usage.hdd_gb || 0;
        const hddCap = (capacity.hdd_tb || 0) * 1000 || hddUsed;
        const hddFree = Math.max(hddCap - hddUsed, 0);

        // Canvas
        const ctx = document.getElementById(`tier-resource-${idKey}`);
        if (!ctx) return;

        if (tierResourceCharts[tier]) {
            tierResourceCharts[tier].destroy();
        }

        tierResourceCharts[tier] = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Used", "Free"],
                datasets: [
                    {
                        label: "Instances",
                        data: [instancesUsed, instancesFree],
                        backgroundColor: ["#10b981", "#d1fae5"],
                        borderWidth: 0,
                        meta: {
                            total: instancesTotal,
                            unit: "instances"
                        }
                    },
                    {
                        label: "CPU",
                        data: [cpuUsed, cpuFree],
                        backgroundColor: ["#ef4444", "#fee2e2"],
                        borderWidth: 0,
                        meta: {
                            total: cpuCap,
                            unit: "vCPU"
                        }
                    },
                    {
                        label: "RAM",
                        data: [ramUsed, ramFree],
                        backgroundColor: ["#3b82f6", "#dbeafe"],
                        borderWidth: 0,
                        meta: {
                            total: ramCap,
                            unit: "GB RAM"
                        }
                    },
                    {
                        label: "Storage",
                        data: [hddUsed, hddFree],
                        backgroundColor: ["#f59e0b", "#fef3c7"],
                        borderWidth: 0,
                        meta: {
                            total: hddCap,
                            unit: "GB storage"
                        }
                    }
                ]
            },
            options: {
                cutout: "55%",
                plugins: {
                    legend: {
                        display: true,
                        position: "bottom",
                        labels: { usePointStyle: true }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const ds = context.dataset;
                                const meta = ds.meta || {};
                                const total = meta.total || 0;
                                const unit = meta.unit || "";
                                const value = context.parsed || 0;
                                const kind = context.dataIndex === 0 ? "used" : "free";
                                const pct = total ? ((value / total) * 100).toFixed(1) : 0;
                                const valueStr = unit.includes("instances")
                                    ? value.toLocaleString()
                                    : value.toFixed(1);
                                const totalStr = unit.includes("instances")
                                    ? total.toLocaleString()
                                    : total.toFixed(1);
                                return `${ds.label} ${kind}: ${valueStr} of ${totalStr} ${unit} (${pct}%)`;
                            }
                        }
                    },
                    centerTextPlugin: {
                        text: tierLabels[tier]
                    }
                }
            }
        });

        // Mini stats text under each chart
        const instEl = document.getElementById(`tier-mini-${idKey}-instances`);
        const cpuEl = document.getElementById(`tier-mini-${idKey}-cpu`);
        const ramEl = document.getElementById(`tier-mini-${idKey}-ram`);
        const hddEl = document.getElementById(`tier-mini-${idKey}-hdd`);

        if (instEl) {
            const pctInst = instancesTotal ? ((instancesUsed / instancesTotal) * 100).toFixed(1) : 0;
            instEl.textContent = `Instances: ${instancesUsed.toLocaleString()} of ${instancesTotal.toLocaleString()} (${pctInst}%)`;
        }
        if (cpuEl) {
            const pctCpu = cpuCap ? ((cpuUsed / cpuCap) * 100).toFixed(1) : 0;
            cpuEl.textContent = `CPU: ${cpuUsed.toFixed(1)} / ${cpuCap.toFixed(1)} vCPU (${pctCpu}%)`;
        }
        if (ramEl) {
            const pctRam = ramCap ? ((ramUsed / ramCap) * 100).toFixed(1) : 0;
            ramEl.textContent = `RAM: ${ramUsed.toFixed(1)} / ${ramCap.toFixed(1)} GB (${pctRam}%)`;
        }
        if (hddEl) {
            const pctHdd = hddCap ? ((hddUsed / hddCap) * 100).toFixed(1) : 0;
            hddEl.textContent = `Storage: ${hddUsed.toFixed(1)} / ${hddCap.toFixed(1)} GB (${pctHdd}%)`;
        }
    });
}

// -------------------------------------------------------------------------
// Resources filler (numbers + charts)
// -------------------------------------------------------------------------
function fillResources(data) {

    // TOTAL USAGE (real usage from /apps/locations)
    document.getElementById("total-cpu").textContent =
        (data.resources_total_cpu_used ?? 0).toFixed(2) + " vCPU";

    document.getElementById("total-ram").textContent =
        formatStorage(data.resources_total_ram_gb_used ?? 0);

    document.getElementById("total-hdd").textContent =
        formatStorage(data.resources_total_hdd_gb_used ?? 0);

    // GLOBAL UTILIZATION (real, resources-based)
    document.getElementById("cpu-util-pct").textContent =
        (data.resources_cpu_util_pct ?? 0) + "%";

    document.getElementById("ram-util-pct").textContent =
        (data.resources_ram_util_pct ?? 0) + "%";

    document.getElementById("hdd-util-pct").textContent =
        (data.resources_hdd_util_pct ?? 0) + "%";

    // PER-TIER UTILIZATION (%)
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

    // Render tier resource donuts
    renderTierResourceCharts(data);

    // Render nodes chart
    renderTierNodesChart(data);
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

        // RESOURCES (numbers + charts)
        fillResources(data);

        // NETWORK CAPACITY TOTALS
        document.getElementById("network-total-cpu").textContent =
            (data.network_total_cpu ?? 0) + " vCPU";
        document.getElementById("network-total-ram").textContent =
            formatTB(data.network_total_ram_tb);
        document.getElementById("network-total-hdd").textContent =
            formatTB(data.network_total_hdd_tb);

        // Network capacity by tier
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
        (data.top_marketplace_apps || []).forEach(app => {
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
