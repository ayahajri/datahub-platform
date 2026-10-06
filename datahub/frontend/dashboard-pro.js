// dashboard-pro.js - replaces the whole inline <script> of dashboard-user-PRO.html
const token = localStorage.getItem("token");
const apiBase = "http://localhost:8081/api";
let currentFile = null, currentJobId = null, jobsCache = [], charts = {};

if (!token) window.location.href = "auth.html";

const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const f2 = v => v == null ? "-" : (typeof v === "number" && !Number.isInteger(v) ? v.toFixed(2) : v);
const EMPTY = (icon, text) => `<div class="empty-state"><i class="fas ${icon}"></i><p>${text}</p></div>`;

async function api(path, opts = {}) {
    const r = await fetch(apiBase + "/analysis" + path, { ...opts, headers: { Authorization: "Bearer " + token } });
    if (r.status === 401 || r.status === 403) { localStorage.removeItem("token"); window.location.href = "auth.html"; throw new Error("Session expired"); }
    if (!r.ok) { let t = await r.text(); try { t = JSON.parse(t).message || t; } catch (e) {} throw new Error(t || "Error " + r.status); }
    return r;
}

function getUserEmail() {
    try { $("userDisplay").textContent = "👤 " + (JSON.parse(atob(token.split(".")[1])).sub || "User"); }
    catch (e) { $("userDisplay").textContent = "👤 User"; }
}

function switchTab(tab) {
    document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    $(tab).classList.add("active");
    const btn = document.querySelector(`.tab-btn[onclick="switchTab('${tab}')"]`);
    if (btn) btn.classList.add("active");
    if (tab === "history" || tab === "compare") loadHistory();
}

function showMessage(id, msg, type, ms = 4000) {
    const el = $(id);
    el.innerHTML = `<i class="fas fa-${type === "error" ? "exclamation-circle" : "check-circle"}"></i> ${esc(msg)}`;
    el.className = "message " + type;
    if (ms) setTimeout(() => { el.innerHTML = ""; el.className = ""; }, ms);
}

$("fileInput").addEventListener("change", function () {
    currentFile = this.files[0];
    $("fileName").textContent = currentFile ? "📄 " + currentFile.name : "";
});
$("searchInput").addEventListener("input", renderHistory);

// ================= UPLOAD =================
async function uploadAndAnalyze() {
    if (!currentFile || !$("analysisType").value) { showMessage("uploadMsg", "Please select file and analysis type", "error"); return; }
    const fd = new FormData();
    fd.append("file", currentFile);
    fd.append("analysisType", $("analysisType").value);
    showMessage("uploadMsg", "Analysing...", "success", 0);
    try {
        const job = await (await api("/upload", { method: "POST", body: fd })).json();
        if (job.status !== "DONE") throw new Error(job.errorMessage || "Analysis failed");
        currentJobId = job.id;
        const result = JSON.parse(job.resultJson);
        await showPreview();
        result.quality ? renderQuality(result.quality) : await showQuality();
        renderAnalysis(result);
        renderExport();
        showMessage("uploadMsg", "✅ Analysis completed! See the Analysis and Export tabs.", "success");
        loadHistory();
    } catch (e) { showMessage("uploadMsg", "❌ " + e.message, "error", 8000); }
}

// ================= PREVIEW =================
async function showPreview() {
    if (!currentFile) return;
    try {
        const fd = new FormData(); fd.append("file", currentFile);
        const p = await (await api("/preview", { method: "POST", body: fd })).json();
        $("previewContent").className = "";
        $("previewContent").innerHTML = `
            <div class="grid-3" style="margin-bottom:1.5rem">
                <div class="stat-card"><div class="label">Total Rows</div><div class="value">${p.shape.rows}</div></div>
                <div class="stat-card"><div class="label">Total Columns</div><div class="value">${p.shape.columns}</div></div>
                <div class="stat-card"><div class="label">File</div><div class="value" style="font-size:.9rem">${esc(currentFile.name)}</div></div>
            </div>
            <h3 style="margin:1.5rem 0 1rem;color:#a78bfa">Column Information</h3>
            <div class="table-container"><table><thead><tr><th>Column Name</th><th>Data Type</th></tr></thead><tbody>
                ${p.columns.map(c => `<tr><td>${esc(c)}</td><td><span class="badge badge-success">${esc(p.dtypes[c])}</span></td></tr>`).join("")}
            </tbody></table></div>
            <h3 style="margin:1.5rem 0 1rem;color:#a78bfa">First 10 Rows</h3>
            <div class="table-container" style="max-height:400px;overflow-y:auto"><table><thead><tr>${p.columns.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>
                ${p.preview_rows.map(r => `<tr>${p.columns.map(c => `<td>${esc(String(r[c] ?? "-").substring(0, 30))}</td>`).join("")}</tr>`).join("")}
            </tbody></table></div>`;
    } catch (e) { console.error("Preview error:", e); }
}

// ================= QUALITY =================
async function showQuality() {
    if (!currentFile) return;
    try {
        const fd = new FormData(); fd.append("file", currentFile);
        renderQuality(await (await api("/quality-report", { method: "POST", body: fd })).json());
    } catch (e) { console.error("Quality error:", e); }
}

function renderQuality(q) {
    const s = q.summary;
    $("qualityContent").className = "";
    $("qualityContent").innerHTML = `
        <div class="grid-3" style="margin-bottom:2rem">
            <div class="stat-card"><div class="label">Missing Values</div><div class="value">${s.missing_values} (${s.missing_pct}%)</div></div>
            <div class="stat-card"><div class="label">Duplicate Rows</div><div class="value">${s.duplicate_rows} (${s.duplicate_pct}%)</div></div>
            <div class="stat-card"><div class="label">Completeness</div><div class="value">${(100 - s.missing_pct).toFixed(1)}%</div></div>
        </div>
        <h3 style="margin:1.5rem 0 1rem;color:#a78bfa">Column Statistics</h3>
        <div class="table-container" style="max-height:500px;overflow-y:auto"><table><thead><tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique</th><th>Mean</th><th>Min</th><th>Max</th></tr></thead><tbody>
            ${q.column_stats.map(c => `<tr><td><strong>${esc(c.column)}</strong></td><td><span class="badge badge-success">${esc(c.dtype)}</span></td><td>${c.missing} (${c.missing_pct}%)</td><td>${c.unique}</td><td>${f2(c.mean)}</td><td>${f2(c.min)}</td><td>${f2(c.max)}</td></tr>`).join("")}
        </tbody></table></div>
        <h3 style="margin:1.5rem 0 1rem;color:#a78bfa">Outliers (IQR)</h3>
        <div class="table-container"><table><thead><tr><th>Column</th><th>Count</th><th>%</th></tr></thead><tbody>
            ${Object.entries(q.outliers || {}).map(([k, o]) => `<tr><td>${esc(k)}</td><td>${o.count}</td><td>${o.percentage}%</td></tr>`).join("")}
        </tbody></table></div>`;
}

// ================= ANALYSIS =================
function heatColor(v) {
    if (v == null) return "rgba(255,255,255,.05)";
    const a = Math.min(1, Math.abs(v));
    return v >= 0 ? `rgba(79,70,229,${0.15 + a * 0.75})` : `rgba(236,72,153,${0.15 + a * 0.75})`;
}
function drawChart(id, cfg) {
    if (charts[id]) charts[id].destroy();
    const el = $(id); if (!el) return;
    cfg.options = { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: "#a1a1aa" } } },
        scales: { x: { ticks: { color: "#a1a1aa" } }, y: { ticks: { color: "#a1a1aa" } } }, ...(cfg.options || {}) };
    charts[id] = new Chart(el, cfg);
}

function renderAnalysis(result) {
    const cd = result.chart_data || {};
    let h = "";
    if (result.stats) {
        h += `<h3 style="margin:1.5rem 0 1rem;color:#a78bfa">📊 Statistics</h3>
            <div class="grid-2" style="margin-bottom:1.5rem">
                <div class="stat-card"><div class="label">Total Rows</div><div class="value">${result.stats.row_count}</div></div>
                <div class="stat-card"><div class="label">Total Columns</div><div class="value">${result.stats.column_count}</div></div>
            </div>`;
    }
    if (result.ml) {
        if (result.ml.clusters) {
            const c = {}; result.ml.clusters.forEach(x => c[x] = (c[x] || 0) + 1);
            h += `<h3 style="margin:1.5rem 0 1rem;color:#a78bfa">🤖 K-Means Clusters</h3><div class="grid-3" style="margin-bottom:1.5rem">
                ${Object.entries(c).map(([k, v]) => `<div class="stat-card"><div class="label">Cluster ${k}</div><div class="value">${v}</div></div>`).join("")}</div>`;
        } else h += `<p style="color:#a1a1aa">${esc(result.ml.message || "")}</p>`;
    }
    if (cd.histogram) h += `<h3 style="margin:1.5rem 0 1rem;color:#a78bfa">📈 Distribution - ${esc(cd.histogram.column)}</h3><div class="chart-container"><canvas id="histChart"></canvas></div>`;
    if (cd.scatter) h += `<h3 style="margin:1.5rem 0 1rem;color:#a78bfa">⚬ Scatter - ${esc(cd.scatter.x_column)} vs ${esc(cd.scatter.y_column)}</h3><div class="chart-container"><canvas id="scatterChart"></canvas></div>`;
    if (cd.boxplots) {
        h += `<h3 style="margin:1.5rem 0 1rem;color:#a78bfa">📦 Box Plots</h3>` + Object.entries(cd.boxplots).map(([c, b]) => {
            const span = (b.max - b.min) || 1, p = v => ((v - b.min) / span * 100).toFixed(1);
            return `<div style="display:flex;align-items:center;gap:12px;margin:10px 0;font-size:.85rem">
                <div style="width:120px;overflow:hidden;text-overflow:ellipsis">${esc(c)}</div>
                <div style="position:relative;flex:1;height:24px;background:rgba(255,255,255,.04);border-radius:6px">
                    <div style="position:absolute;top:0;height:100%;left:${p(b.q1)}%;width:${p(b.q3) - p(b.q1)}%;background:rgba(79,70,229,.6);border-radius:4px"></div>
                    <div style="position:absolute;top:0;height:100%;width:2px;left:${p(b.median)}%;background:#ec4899"></div></div>
                <div style="color:#a1a1aa">${f2(b.min)} → ${f2(b.max)}</div></div>`;
        }).join("");
    }
    if (cd.heatmap) {
        const hm = cd.heatmap;
        h += `<h3 style="margin:1.5rem 0 1rem;color:#a78bfa">🔥 Correlation Heatmap</h3><div class="table-container"><table>
            <tr><th>Variables</th>${hm.columns.map(c => `<th>${esc(c)}</th>`).join("")}</tr>
            ${hm.columns.map((name, i) => `<tr><td><strong>${esc(name)}</strong></td>${hm.data[i].map(v => `<td style="background:${heatColor(v)};font-weight:bold">${f2(v)}</td>`).join("")}</tr>`).join("")}
        </table></div>`;
    }
    $("analysisContent").className = "";
    $("analysisContent").innerHTML = h || EMPTY("fa-chart-line", "No result data");

    setTimeout(() => {
        if (cd.histogram) drawChart("histChart", { type: "bar", data: { labels: cd.histogram.labels, datasets: [{ label: cd.histogram.column, data: cd.histogram.values, backgroundColor: "rgba(79,70,229,.6)", borderRadius: 8 }] } });
        if (cd.scatter) drawChart("scatterChart", { type: "scatter", data: { datasets: [{ label: "points", data: cd.scatter.points.map(p => ({ x: p[0], y: p[1] })), backgroundColor: "#ec4899" }] }, options: { plugins: { legend: { display: false } } } });
    }, 100);
}

// ================= EXPORT (PDF = stats + quality + ML + charts) =================
function renderExport() {
    $("exportContent").className = "";
    $("exportContent").innerHTML = `
        <div class="grid-2">
            <div class="stat-card"><div class="label">Full report: stats, quality, ML and charts</div>
                <button class="btn" style="margin-top:1rem" onclick="downloadReport('pdf')"><i class="fas fa-file-pdf"></i> Download PDF</button></div>
            <div class="stat-card"><div class="label">Raw tables</div>
                <div style="display:flex;gap:.6rem;flex-wrap:wrap;justify-content:center;margin-top:1rem">
                    <button class="btn btn-secondary" onclick="downloadReport('csv','stats')">Stats CSV</button>
                    <button class="btn btn-secondary" onclick="downloadReport('csv','quality')">Quality CSV</button>
                    <button class="btn btn-secondary" onclick="downloadReport('csv','outliers')">Outliers CSV</button>
                    <button class="btn btn-secondary" onclick="downloadReport('csv','clusters')">Clusters CSV</button>
                </div></div>
        </div>`;
}

async function downloadReport(kind, type = "stats", id = currentJobId) {
    if (!id) { alert("Run an analysis first, or open one from History."); return; }
    try {
        const path = `/${id}/export/` + (kind === "pdf" ? "pdf" : "csv?type=" + type);
        const blob = await (await api(path)).blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = kind === "pdf" ? `report_${id}.pdf` : `${type}_${id}.csv`;
        document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(a.href);
    } catch (e) { alert("Export failed: " + e.message); }
}

// ================= HISTORY =================
async function loadHistory() {
    try {
        jobsCache = await (await api("/history")).json();
        renderHistory();
        const opts = jobsCache.filter(j => j.status === "DONE").map(j => `<option value="${j.id}">#${j.id} - ${esc(j.originalFileName)}</option>`).join("");
        $("compareId1").innerHTML = '<option value="">Select first...</option>' + opts;
        $("compareId2").innerHTML = '<option value="">Select second...</option>' + opts;
    } catch (e) { console.error("History error:", e); }
}

function renderHistory() {
    const q = $("searchInput").value.trim().toLowerCase(), st = $("filterStatus").value;
    const jobs = jobsCache.filter(j => (!st || j.status === st) && (!q || (j.originalFileName || "").toLowerCase().includes(q)));
    if (!jobs.length) { $("historyContent").className = "empty-state"; $("historyContent").innerHTML = '<i class="fas fa-inbox"></i><p>No analysis found</p>'; return; }
    $("historyContent").className = "";
    $("historyContent").innerHTML = '<div style="display:flex;flex-direction:column;gap:1rem">' + jobs.map(j => `
        <div style="background:rgba(79,70,229,.1);border:1px solid rgba(79,70,229,.2);border-radius:12px;padding:1.2rem;cursor:pointer" onclick="viewJob(${j.id})">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap">
                <div>
                    <div style="font-weight:600;color:#a78bfa">#${j.id} ${esc(j.originalFileName)}</div>
                    <div style="color:#a1a1aa;font-size:.85rem">Type: ${esc(j.fileType)} | Analysis: ${esc(j.analysisType)}</div>
                    <div style="color:#52525b;font-size:.8rem">${j.createdAt ? new Date(j.createdAt).toLocaleString() : ""}</div>
                </div>
                <div style="display:flex;gap:.6rem;align-items:center">
                    ${j.status === "DONE" ? `<button class="btn btn-secondary" onclick="event.stopPropagation();downloadReport('pdf','stats',${j.id})"><i class="fas fa-file-pdf"></i> PDF</button>` : ""}
                    <span class="badge badge-${j.status === "DONE" ? "success" : j.status === "PENDING" ? "warning" : "danger"}">${esc(j.status)}</span>
                </div>
            </div>
        </div>`).join("") + "</div>";
}

function viewJob(id) {
    const job = jobsCache.find(j => j.id === id);
    if (!job) return;
    if (job.status !== "DONE") { alert(job.errorMessage || "This analysis did not finish."); return; }
    currentJobId = id;
    const result = JSON.parse(job.resultJson);
    renderAnalysis(result);
    if (result.quality) renderQuality(result.quality);
    renderExport();
    switchTab("analysis");
}

// ================= COMPARE =================
function compareAnalyses() {
    const a = jobsCache.find(j => String(j.id) === $("compareId1").value);
    const b = jobsCache.find(j => String(j.id) === $("compareId2").value);
    if (!a || !b) { showMessage("uploadMsg", "Select both analyses (then go back to the Compare tab)", "error"); $("compareContent").innerHTML = EMPTY("fa-not-equal", "Select two analyses first"); return; }
    const A = JSON.parse(a.resultJson), B = JSON.parse(b.resultJson);
    const rows = [
        ["File", a.originalFileName, b.originalFileName],
        ["Rows", A.stats?.row_count, B.stats?.row_count],
        ["Columns", A.stats?.column_count, B.stats?.column_count],
        ["Missing %", A.quality?.summary.missing_pct, B.quality?.summary.missing_pct],
        ["Duplicate rows", A.quality?.summary.duplicate_rows, B.quality?.summary.duplicate_rows],
        ["Clusters", A.ml?.cluster_count, B.ml?.cluster_count],
    ];
    const sa = A.stats?.numeric_summary || {}, sb = B.stats?.numeric_summary || {};
    Object.keys(sa).filter(c => c in sb).forEach(c => rows.push([`Mean of ${c}`, sa[c].mean, sb[c].mean]));
    $("compareContent").innerHTML = `<div class="table-container"><table>
        <thead><tr><th>Metric</th><th>#${a.id}</th><th>#${b.id}</th></tr></thead><tbody>
        ${rows.map(r => `<tr><td>${esc(r[0])}</td><td>${esc(f2(r[1]))}</td><td>${esc(f2(r[2]))}</td></tr>`).join("")}
        </tbody></table></div>`;
}

function logout() { localStorage.removeItem("token"); window.location.href = "index.html"; }

getUserEmail();
loadHistory();