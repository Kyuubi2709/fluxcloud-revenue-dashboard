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
// CHART RENDERING HELPERS
// -------------------------------------------------------------------------
function renderUtilizationDonuts(data) {
    if (typeof Chart === "undefined") return;

    const usedCpuPct = data.resources_cpu_util_pct ?? 0;
    const usedRamPct = data.resources_ram_util_pct ?? 0;
    const usedHddPct = data.resources_hdd_util_pct ?? 0;

    const usedColor = "#2979FF";
    const freeColor = "#E0E0E0";

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
                            label: function (t) {
                                const value = t.raw ?? 0;
                                return `${value.toFixed(1)}%`;
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

// -------------------------------------------------------------------------
// Fill Resources
// -------------------------------------------------------------------------
function fillResources(data) {
    document.getElementById("total-cpu").textContent =
        (data.resources_total_cpu_used ?? 0).toFixed(2) + " vCPU";

    document.getElementById("total-ram").textContent =
        formatStorage(data.resources_total_ram_gb_used);

    document.getElementById("total-hdd").textContent =
        formatStorage(data.resources_total_hdd_gb_used);

    document.getElementById("cpu-util-pct").textContent =
        (data.resources_cpu_util_pct ?? 0) + "%";
    document.getElementById("ram-util-pct").textContent =
        (data.resources_ram_util_pct ?? 0) + "%";
    document.getElementById("hdd-util-pct").textContent =
        (data.resources_hdd_util_pct ?? 0) + "%";

    renderUtilizationDonuts(data);
}

// -------------------------------------------------------------------------
// loadStats()
// -------------------------------------------------------------------------
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

        document.getElementById("total-apps").textContent = data.total_apps;
        document.getElementById("marketplace-apps").textContent = data.marketplace_apps;
        document.getElementById("custom-apps").textContent = data.custom_apps;
        document.getElementById("unique-owners").textContent = data.unique_owners;

        fillResources(data);

        // TOP 5 TABLE
        const tbody = document.querySelector("#top5-table tbody");
        tbody.innerHTML = "";
        data.top_marketplace_apps.forEach(app => {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td>${app.name}</td><td>${app.deployments}</td>`;
            tbody.appendChild(tr);
        });

        // ============================
        // SUBSCRIPTION DURATION TABLE
        // ============================
        const sub = data.subscription_stats || {};
        const tbodySub = document.querySelector("#subscription-table tbody");
        if (tbodySub) {
            tbodySub.innerHTML = "";

            const plans = ["weekly","biweekly","monthly","quarterly","semiannual","annual","unknown"];

            plans.forEach(plan => {
                const a = sub.all?.[plan] || {count: 0, pct: 0};
                const m = sub.marketplace?.[plan] || {count: 0, pct: 0};
                const c = sub.custom?.[plan] || {count: 0, pct: 0};

                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${plan}</td>
                    <td>${a.count} (${a.pct}%)</td>
                    <td>${m.count} (${m.pct}%)</td>
                    <td>${c.count} (${c.pct}%)</td>
                `;
                tbodySub.appendChild(row);
            });
        }

    } catch (err) {
        console.error(err);
        document.getElementById("loading").textContent = "Error loading data.";
    }
}

loadStats();

// --- tab switching -----------------------------------------------------
document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        const tab = btn.dataset.tab;
        document.querySelectorAll(".tab-content").forEach(c => c.classList.add("hidden"));
        document.getElementById("tab-" + tab).classList.remove("hidden");
    });
});
