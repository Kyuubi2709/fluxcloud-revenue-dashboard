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

function formatUSD(val) {
    if (val === null || val === undefined || isNaN(val)) return "–";
    return "$" + Number(val).toFixed(2);
}

// --- Chart.js globals ----------------------------------------------------

let cpuUtilChart = null;
let ramUtilChart = null;
let hddUtilChart = null;
let tierNodesChart = null;

// center text plugin for utilization donuts
const centerTextPlugin = {
    id: "centerTextPlugin",
    beforeDraw(chart, args, opts) {
        const { ctx, chartArea } = chart;
        if (!opts || !opts.text) return;

        ctx.save();
        ctx.font = "bold 14px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "#333";

        const x = (chartArea.left + chartArea.right) / 2;
        const y = (chartArea.top + chartArea.bottom) / 2;

        ctx.fillText(opts.text, x, y);
        ctx.restore();
    }
};

if (typeof Chart !== "undefined") {
    Chart.register(centerTextPlugin);
}

// -------------------------------------------------------------------------
// NEW: ORBIT :latest COUNT LOADER (General tab box)
// -------------------------------------------------------------------------
async function loadOrbitLatestCount() {
    const el = document.getElementById("orbit-latest-count");
    if (!el) return;

    el.textContent = "…";

    try {
        const resp = await fetch("/orbit-latest-count", { credentials: "include" });
        const data = await resp.json();

        if (!resp.ok || data.count === null || data.count === undefined) {
            el.textContent = "ERR";
            return;
        }

        el.textContent = data.count;
    } catch (e) {
        console.error(e);
        el.textContent = "ERR";
    }
}

// -------------------------------------------------------------------------
// CHART RENDERING HELPERS
// -------------------------------------------------------------------------

function renderUtilizationDonuts(data) {
    if (typeof Chart === "undefined") return;

    const usedCpuPct = data.resources_cpu_util_pct ?? 0;
    const usedRamPct = data.resources_ram_util_pct ?? 0;
    const usedHddPct = data.resources_hdd_util_pct ?? 0;

    const usedColor = "#2979FF";
    const freeColor = "#E0E0E0";

    // Helper to create/update a donut
    function upsertDonut(existing, canvasId, usedPct) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return existing;

        const used = Math.max(0, Math.min(100, usedPct));
        const free = Math.max(0, 100 - used);

        if (existing) {
            existing.data.datasets[0].data = [used, free];
            existing.options.plugins.centerTextPlugin.text = used.toFixed(1) + "%";
            existing.update();
            return existing;
        }

        return new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Used", "Free"],
                datasets: [{
                    data: [used, free],
                    backgroundColor: [usedColor, freeColor],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                cutout: "70%",
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                const label = tooltipItem.label || "";
                                const value = tooltipItem.raw ?? 0;
                                return `${label}: ${value.toFixed(1)}%`;
                            }
                        }
                    },
                    centerTextPlugin: {
                        text: used.toFixed(1) + "%"
                    }
                }
            }
        });
    }

    cpuUtilChart = upsertDonut(cpuUtilChart, "cpuUtilChart", usedCpuPct);
    ramUtilChart = upsertDonut(ramUtilChart, "ramUtilChart", usedRamPct);
    hddUtilChart = upsertDonut(hddUtilChart, "hddUtilChart", usedHddPct);
}

function renderTierNodesDonut(data) {
    if (typeof Chart === "undefined") return;

    const tnu = data.tier_node_usage || {};

    const cum = tnu.CUMULUS || {};
    const nim = tnu.NIMBUS || {};
    const str = tnu.STRATUS || {};

    const cUsed = cum.used_nodes ?? 0;
    const nUsed = nim.used_nodes ?? 0;
    const sUsed = str.used_nodes ?? 0;

    const totalUsed = cUsed + nUsed + sUsed;

    // Update center text + legend text
    const centerEl = document.getElementById("tier-nodes-center");
    if (centerEl) {
        centerEl.textContent = totalUsed ? `${totalUsed} nodes` : "No active nodes";
    }

    const fmtNodeText = (obj) => {
        const used = obj.used_nodes ?? 0;
        const total = obj.total_nodes ?? 0;
        const pct = obj.pct ?? 0;
        if (!total) return "–";
        return `${used}/${total} nodes (${pct.toFixed(1)}%)`;
    };

    const cEl = document.getElementById("tier-nodes-cumulus");
    const nEl = document.getElementById("tier-nodes-nimbus");
    const sEl = document.getElementById("tier-nodes-stratus");

    if (cEl) cEl.textContent = fmtNodeText(cum);
    if (nEl) nEl.textContent = fmtNodeText(nim);
    if (sEl) sEl.textContent = fmtNodeText(str);

    const ctx = document.getElementById("tierNodesChart");
    if (!ctx) return;

    const dataArr = [cUsed, nUsed, sUsed];

    if (tierNodesChart) {
        tierNodesChart.data.datasets[0].data = dataArr;
        tierNodesChart.update();
        return;
    }

    tierNodesChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Cumulus", "Nimbus", "Stratus"],
            datasets: [{
                data: dataArr,
                backgroundColor: ["#42A5F5", "#66BB6A", "#FFA726"],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            cutout: "70%",
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (tooltipItem) {
                            const label = tooltipItem.label || "";
                            const value = tooltipItem.raw ?? 0;
                            const total = totalUsed || 1;
                            const pct = (value / total) * 100;
                            return `${label}: ${value} nodes (${pct.toFixed(1)}%)`;
                        }
                    }
                }
            }
        }
    });
}

// -------------------------------------------------------------------------
// RESOURCES FILLER (keeps all existing metrics)
// -------------------------------------------------------------------------
function fillResources(data) {

    // TOTAL USAGE (real usage from /apps/locations)
    const totalCpuUsed = data.resources_total_cpu_used ?? 0;
    const totalRamUsedGb = data.resources_total_ram_gb_used ?? 0;
    const totalHddUsedGb = data.resources_total_hdd_gb_used ?? 0;

    document.getElementById("total-cpu").textContent =
        totalCpuUsed.toFixed(2) + " vCPU";

    document.getElementById("total-ram").textContent =
        formatStorage(totalRamUsedGb);

    document.getElementById("total-hdd").textContent =
        formatStorage(totalHddUsedGb);

    // PER-TIER USAGE (real usage)
    const rtu = data.resources_tier_usage || {};

    function loadTier(prefix, d) {
        d = d || {};
        const instEl = document.getElementById(prefix + "-instances");
        const cpuEl = document.getElementById(prefix + "-cpu");
        const ramEl = document.getElementById(prefix + "-ram");
        const hddEl = document.getElementById(prefix + "-hdd");

        if (instEl) instEl.textContent = d.instances ?? 0;
        if (cpuEl) cpuEl.textContent = ((d.cpu ?? 0).toFixed(2)) + " vCPU";
        if (ramEl) ramEl.textContent = formatStorage(d.ram_gb ?? 0);
        if (hddEl) hddEl.textContent = formatStorage(d.hdd_gb ?? 0);
    }

    loadTier("rtu-cumulus", rtu.CUMULUS);
    loadTier("rtu-nimbus", rtu.NIMBUS);
    loadTier("rtu-stratus", rtu.STRATUS);

    // GLOBAL UTILIZATION (resources-based)
    const cpuPct = data.resources_cpu_util_pct ?? 0;
    const ramPct = data.resources_ram_util_pct ?? 0;
    const hddPct = data.resources_hdd_util_pct ?? 0;

    const cpuPctEl = document.getElementById("cpu-util-pct");
    const ramPctEl = document.getElementById("ram-util-pct");
    const hddPctEl = document.getElementById("hdd-util-pct");

    if (cpuPctEl) cpuPctEl.textContent = cpuPct + "%";
    if (ramPctEl) ramPctEl.textContent = ramPct + "%";
    if (hddPctEl) hddPctEl.textContent = hddPct + "%";

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

    // Charts
    renderUtilizationDonuts(data);
    renderTierNodesDonut(data);
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

        // BASIC COUNTS (GENERAL TAB)
        document.getElementById("total-apps").textContent = data.total_apps;
        document.getElementById("marketplace-apps").textContent = data.marketplace_apps;
        document.getElementById("custom-apps").textContent = data.custom_apps;
        document.getElementById("unique-owners").textContent = data.unique_owners;

        // PERCENTAGES (GENERAL TAB)
        document.getElementById("marketplace-pct").textContent = data.marketplace_pct + "%";
        document.getElementById("custom-pct").textContent = data.custom_pct + "%";

        // INSTANCES (GENERAL TAB)
        document.getElementById("total-instances").textContent = data.total_instances;
        document.getElementById("company-deployments").textContent = data.company_deployments;
        document.getElementById("company-instances").textContent = data.company_instances;

        // CONTACTS (GENERAL TAB)
        document.getElementById("marketplace-with-contacts").textContent = data.marketplace_with_contacts;
        document.getElementById("marketplace-contact-pct").textContent = data.marketplace_contact_pct + "%";
        document.getElementById("total-with-contacts").textContent = data.total_with_contacts;
        document.getElementById("total-contact-pct").textContent = data.total_contact_pct + "%";
        document.getElementById("custom-with-contacts").textContent = data.custom_with_contacts;
        document.getElementById("custom-contact-pct").textContent = data.custom_contact_pct + "%";

        // secrets & static ip (GENERAL TAB)
        document.getElementById("total-with-secrets").textContent = data.total_with_secrets;
        document.getElementById("total-with-staticip").textContent = data.total_with_staticip;
        document.getElementById("marketplace-with-secrets").textContent = data.marketplace_with_secrets;
        document.getElementById("marketplace-with-staticip").textContent = data.marketplace_with_staticip;

        // NEW: auth-related owner metrics
        document.getElementById("sso-owners").textContent = data.sso_owners ?? 0;
        document.getElementById("appleid-app-owners").textContent = data.appleid_app_owners ?? 0;

        // -------------------------------
        // NEW: FINANCES TAB MIRROR METRICS
        // -------------------------------
        const finTotalAppsEl = document.getElementById("fin-total-apps");
        if (finTotalAppsEl) {
            finTotalAppsEl.textContent = data.total_apps;
        }

        const finMarketplaceAppsEl = document.getElementById("fin-marketplace-apps");
        if (finMarketplaceAppsEl) {
            finMarketplaceAppsEl.textContent = data.marketplace_apps;
        }

        const finCustomAppsEl = document.getElementById("fin-custom-apps");
        if (finCustomAppsEl) {
            finCustomAppsEl.textContent = data.custom_apps;
        }

        const finMarketplacePctEl = document.getElementById("fin-marketplace-pct");
        if (finMarketplacePctEl) {
            finMarketplacePctEl.textContent = data.marketplace_pct + "%";
        }

        const finCustomPctEl = document.getElementById("fin-custom-pct");
        if (finCustomPctEl) {
            finCustomPctEl.textContent = data.custom_pct + "%";
        }

        const finCompanyDeploymentsEl = document.getElementById("fin-company-deployments");
        if (finCompanyDeploymentsEl) {
            finCompanyDeploymentsEl.textContent = data.company_deployments;
        }

        // RESOURCES (real usage + per-tier + tier utilization + charts)
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

        // TOP 5 MARKETPLACE APPS
        const tbody = document.querySelector("#top5-table tbody");
        tbody.innerHTML = "";
        (data.top_marketplace_apps || []).forEach(app => {
            const row = document.createElement("tr");
            row.innerHTML = `<td>${app.name}</td><td>${app.deployments}</td>`;
            tbody.appendChild(row);
        });

        // -------------------------------
        // NEW: REVENUE METRICS (FINANCES TAB)
        // -------------------------------
        const totalRevenueEl = document.getElementById("rev-total-usd");
        const fluxRevenueEl = document.getElementById("rev-flux-usd");
        const fiatRevenueEl = document.getElementById("rev-fiat-usd");
        const mktRevenueEl = document.getElementById("rev-marketplace-usd");
        const customRevenueEl = document.getElementById("rev-custom-usd");

        if (totalRevenueEl) totalRevenueEl.textContent = formatUSD(data.total_revenue_usd);
        if (fluxRevenueEl) fluxRevenueEl.textContent = formatUSD(data.flux_revenue_usd);
        if (fiatRevenueEl) fiatRevenueEl.textContent = formatUSD(data.fiat_revenue_usd);
        if (mktRevenueEl) mktRevenueEl.textContent = formatUSD(data.marketplace_revenue_usd);
        if (customRevenueEl) customRevenueEl.textContent = formatUSD(data.custom_revenue_usd);

        // TOP PAYING OWNERS TABLE
        const ownersBody = document.querySelector("#top-owners-table tbody");
        if (ownersBody) {
            ownersBody.innerHTML = "";
            (data.top_paying_owners || []).forEach(entry => {
                const row = document.createElement("tr");
                const owner = entry.owner || "–";
                const rev = formatUSD(entry.revenue_usd);
                row.innerHTML = `<td>${owner}</td><td>${rev}</td>`;
                ownersBody.appendChild(row);
            });

            if (!data.top_paying_owners || data.top_paying_owners.length === 0) {
                const row = document.createElement("tr");
                row.innerHTML = `<td colspan="2">No revenue data (no priced apps or price.json empty).</td>`;
                ownersBody.appendChild(row);
            }
        }

        // NEW: Load orbit repotag count (General tab)
        loadOrbitLatestCount();

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
        try {
            const r = await fetch("/stats", { credentials: "include" });
            const stats = await r.json();
            if (!stats.last_updated) return;

            const newTime = "Last updated: " + new Date(stats.last_updated).toLocaleString();

            if (newTime !== oldTime) {
                clearInterval(poll);
                spinner.classList.add("hidden");
                status.textContent = "";
                loadStats(); // this will also reload orbit count
            }
        } catch (e) {
            console.error(e);
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
