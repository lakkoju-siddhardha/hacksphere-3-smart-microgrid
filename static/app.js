/* GridSense AI dashboard
 *
 * Talks to the existing Flask endpoint: POST /api/forecast
 * Request : { ambient_temp_c, humidity_pct, solar_irradiance_wm2 }
 * Response: { forecast: [{ timestamp, predicted_demand_kw, grid_mode,
 *                          critical_overload, alert }], summary: {...} }
 *
 * All API values are written with textContent / createElement (never innerHTML).
 */
(() => {
    "use strict";

    // ───────── Configuration ─────────

    const CONFIG = {
        endpoint: "/api/forecast",
        requestTimeoutMs: 60000,
        // Set to true to request a forecast with the example inputs on page load.
        autoRunOnLoad: false,
        // These mirror grid_controller.py. They are used only to draw the chart
        // threshold lines and to explain the rules. Modes and alerts themselves
        // always come from the backend response.
        demandThresholdKw: 160,
        criticalThresholdKw: 200,
    };

    const MODE_MAIN = "Main Grid Mode";
    const MODE_RENEWABLE = "Renewable Storage Mode";

    const COLORS = {
        teal: "#2dd4bf",
        tealFill: "rgba(45, 212, 191, 0.10)",
        emerald: "#34d399",
        blue: "#7db0ff",
        amber: "#fbbf24",
        red: "#ff7b7b",
        redFill: "rgba(255, 123, 123, 0.08)",
        grid: "rgba(151, 168, 192, 0.14)",
        muted: "#97a8c0",
        text: "#e7eef9",
        surface: "#15233b",
        border: "#2f4465",
        bg: "#101c31",
    };

    const FIELDS = [
        { id: "temperature", key: "ambient_temp_c", label: "Temperature", min: -50, max: 60 },
        { id: "humidity", key: "humidity_pct", label: "Humidity", min: 0, max: 100 },
        { id: "solar", key: "solar_irradiance_wm2", label: "Solar irradiance", min: 0, max: 1500 },
    ];

    const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    // ───────── State ─────────

    let forecast = null;      // last successful, normalised forecast
    let chart = null;         // single Chart.js instance, updated in place
    let chartRows = [];       // rows the chart tooltip reads from
    let busy = false;

    // ───────── DOM helpers ─────────

    const $ = (id) => document.getElementById(id);

    function make(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    const form = $("weatherForm");
    const submitButton = $("forecastButton");
    const submitButtonText = $("forecastButtonText");
    const refreshButton = $("refreshButton");
    const liveWeatherButton = $("liveWeatherButton");
    const formStatus = $("formStatus");
    const formError = $("formError");

    // ───────── Formatting ─────────

    const numberFormat = new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    const fmtKw = (value) => numberFormat.format(value);
    const pad = (n) => String(n).padStart(2, "0");

    function parseTimestamp(value) {
        // Backend format: "YYYY-MM-DD HH:MM:SS" (server local time, no zone).
        const match = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/.exec(String(value));
        if (!match) return null;
        const [, y, mo, d, h, mi, s] = match;
        const parts = {
            year: +y, month: +mo, day: +d, hour: +h, minute: +mi, second: +(s || 0),
        };
        if (parts.month < 1 || parts.month > 12 || parts.day < 1 || parts.day > 31 || parts.hour > 23) return null;
        parts.key = Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second);
        parts.iso = `${y}-${mo}-${d}T${pad(parts.hour)}:${mi}:${pad(parts.second)}`;
        return parts;
    }

    const fmtClock = (t) => `${pad(t.hour)}:${pad(t.minute)}`;
    const fmtDay = (t) => `${t.day} ${MONTHS[t.month - 1]}`;
    const fmtFull = (t) => `${fmtDay(t)} ${t.year}, ${fmtClock(t)}`;

    // ───────── Response handling ─────────

    class ApiError extends Error {}

    function isFiniteNumber(v) {
        return typeof v === "number" && Number.isFinite(v);
    }

    function normalise(data) {
        if (!data || !Array.isArray(data.forecast) || data.forecast.length === 0) {
            throw new ApiError("The server returned a forecast in an unexpected format.");
        }

        const rows = data.forecast.map((raw) => {
            const time = parseTimestamp(raw && raw.timestamp);
            const demand = Number(raw && raw.predicted_demand_kw);
            if (!time || !Number.isFinite(demand) || typeof raw.grid_mode !== "string") {
                throw new ApiError("The server returned a forecast in an unexpected format.");
            }
            return {
    time,
    demand,
    mode: raw.grid_mode,
    critical: raw.critical_overload === true,
    alert: typeof raw.alert === "string" ? raw.alert : null,

    // Battery simulation data
    batterySoc: Number(raw.battery_soc_percent),
    batteryPower: Number(raw.battery_power_kw),
    batteryAction: raw.battery_action || "Unknown",
};
        });

        rows.sort((a, b) => a.time.key - b.time.key);

        const summary = data.summary && typeof data.summary === "object" ? data.summary : {};
        const demands = rows.map((r) => r.demand);
        const count = (predicate) => rows.filter(predicate).length;

        // Prefer the backend summary; fall back to the forecast array if a field is missing.
        const peak = isFiniteNumber(summary.peak_demand_kw) ? summary.peak_demand_kw : Math.max(...demands);
        const renewableHours = isFiniteNumber(summary.renewable_storage_hours)
            ? summary.renewable_storage_hours : count((r) => r.mode === MODE_RENEWABLE);
        const mainHours = isFiniteNumber(summary.main_grid_hours)
            ? summary.main_grid_hours : count((r) => r.mode === MODE_MAIN);
        const criticalAlerts = isFiniteNumber(summary.critical_alerts)
            ? summary.critical_alerts : count((r) => r.critical);

        return {
    rows,
    peak,
    average: demands.reduce((sum, v) => sum + v, 0) / demands.length,
    renewableHours,
    mainHours,
    criticalAlerts,
    total: rows.length,

    minimumBatterySoc: Number(summary.minimum_battery_soc_percent),
    finalBatterySoc: Number(summary.final_battery_soc_percent),
};
    }

    async function requestForecast(payload) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), CONFIG.requestTimeoutMs);

        try {
            const response = await fetch(CONFIG.endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });

            let data = null;
            const text = await response.text();
            try {
                data = JSON.parse(text);
            } catch (_) {
                // Safety net: older app.py versions can emit a bare NaN for empty alerts,
                // which is not valid JSON. Treat it as null instead of failing the request.
                try {
                    data = JSON.parse(text.replace(/:\s*NaN\b/g, ":null"));
                } catch (__) {
                    data = null;
                }
            }

            if (!response.ok) {
                const message = data && typeof data.error === "string"
                    ? data.error
                    : `The forecast request failed (HTTP ${response.status}).`;
                throw new ApiError(message);
            }
            return normalise(data);
        } catch (error) {
            if (error instanceof ApiError) throw error;
            if (error && error.name === "AbortError") {
                throw new ApiError("The forecast request timed out. Try again in a moment.");
            }
            throw new ApiError("Could not reach the GridSense server. Check that the Flask app is running, then try again.");
        } finally {
            clearTimeout(timer);
        }
    }

    // ───────── Form validation ─────────

    function setFieldError(field, message) {
        const input = $(field.id);
        const errorEl = $(`${field.id}Error`);
        if (message) {
            errorEl.textContent = message;
            errorEl.hidden = false;
            input.setAttribute("aria-invalid", "true");
        } else {
            errorEl.textContent = "";
            errorEl.hidden = true;
            input.removeAttribute("aria-invalid");
        }
    }

    function readInputs() {
        const values = {};
        let firstInvalid = null;

        FIELDS.forEach((field) => {
            const raw = $(field.id).value.trim();
            const value = Number(raw);
            let message = "";

            if (raw === "") {
                message = "Enter a value.";
            } else if (!Number.isFinite(value)) {
                message = "Enter a number.";
            } else if (value < field.min || value > field.max) {
                message = `Enter a value between ${field.min} and ${field.max}.`;
            }

            setFieldError(field, message);
            if (message && !firstInvalid) firstInvalid = field;
            values[field.key] = value;
        });

        return { values, firstInvalid };
    }

    // ───────── Status UI ─────────

    function setApiStatus(state, text) {
        const pill = $("apiStatus");
        pill.dataset.state = state;
        $("apiStatusText").textContent = text;
    }

    function setBusy(isBusy) {
        busy = isBusy;
        submitButton.disabled = isBusy;
        refreshButton.disabled = isBusy;
        submitButton.classList.toggle("is-loading", isBusy);
        submitButtonText.textContent = isBusy ? "Generating forecast…" : "Generate 24-Hour Forecast";
        $("kpis").classList.toggle("is-busy", isBusy);
        form.setAttribute("aria-busy", String(isBusy));
        liveWeatherButton.disabled = isBusy;
liveWeatherButton.classList.toggle("is-loading", isBusy);
    }

    function showFormError(message) {
        formError.textContent = message;
        formError.hidden = false;
    }

    function clearFormError() {
        formError.textContent = "";
        formError.hidden = true;
    }

  

function updateAssumptionBadge() {
    const badge = $("assumptionBadge");
    const text = $("assumptionBadgeText");

    if (!forecast) {
        badge.dataset.state = "none";
        text.textContent = "No forecast generated yet";
        return;
    }

    if (forecast.mode === "live") {
        badge.dataset.state = "active";
        text.textContent =
            "Live hourly weather forecast from Open-Meteo. " +
            "Demand values are AI predictions, not live electricity measurements.";
        return;
    }

    const used = forecast.inputs;

    if (!used) {
        badge.dataset.state = "none";
        text.textContent = "Weather assumptions unavailable.";
        return;
    }

    const current = FIELDS.map((field) => {
        const raw = $(field.id).value.trim();
        return raw === "" ? NaN : Number(raw);
    });

    const same = FIELDS.every(
        (field, i) => used[field.key] === current[i]
    );

    if (same) {
        badge.dataset.state = "active";
        text.textContent =
            `Manual scenario: ${used.ambient_temp_c} °C, ` +
            `${used.humidity_pct}% humidity, ` +
            `${used.solar_irradiance_wm2} W/m², ` +
            "applied to all 24 hours.";
    } else {
        badge.dataset.state = "stale";
        text.textContent =
            "Inputs changed since the last forecast. " +
            "Generate a new forecast to update.";
    }
}



    // ───────── Rendering ─────────

    function renderKpis(f) {
        const peakRow = f.rows.reduce((best, row) => (row.demand > best.demand ? row : best), f.rows[0]);

        $("kpiPeak").textContent = fmtKw(f.peak);
        $("kpiPeakNote").textContent = `Hour starting ${fmtDay(peakRow.time)}, ${fmtClock(peakRow.time)}`;

        $("kpiAvg").textContent = fmtKw(f.average);
        $("kpiAvgNote").textContent = `Mean of ${f.total} hourly predictions`;

        $("kpiRenewable").textContent = f.renewableHours;
        $("kpiRenewableNote").textContent = `Of ${f.total} forecast hours. ${f.mainHours} on Main Grid Mode.`;

        $("kpiAlerts").textContent = f.criticalAlerts;
        $("kpiAlertCard").dataset.level = f.criticalAlerts > 0 ? "critical" : "ok";
        $("kpiAlertsNote").textContent = f.criticalAlerts > 0
            ? `Demand at or above ${CONFIG.criticalThresholdKw} kW`
            : "None predicted in this forecast";
    }

    function pointStyles(rows) {
        return {
            radius: rows.map((r) => (r.critical ? 6 : 3.5)),
            fill: rows.map((r) => (r.critical ? COLORS.red : r.mode === MODE_RENEWABLE ? COLORS.emerald : COLORS.blue)),
            border: rows.map((r) => (r.critical ? "#ffd0d0" : COLORS.bg)),
            borderWidth: rows.map((r) => (r.critical ? 2 : 1.5)),
        };
    }

    function tickLabel(row) {
        const clock = fmtClock(row.time);
        const isDayStart = row.time.hour === 0 && row.time.minute === 0;
        return isDayStart || row === chartRows[0] ? [clock, fmtDay(row.time)] : clock;
    }

    function buildChart(canvas) {
        const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
        Chart.defaults.color = COLORS.muted;

        const style = pointStyles(chartRows);
        const constant = (value) => chartRows.map(() => value);

        return new Chart(canvas, {
            type: "line",
            data: {
                labels: chartRows.map((r) => fmtClock(r.time)),
                datasets: [
                    {
                        label: "Predicted demand",
                        data: chartRows.map((r) => r.demand),
                        borderColor: COLORS.teal,
                        backgroundColor: COLORS.tealFill,
                        borderWidth: 2.5,
                        fill: true,
                        tension: 0.3,
                        pointRadius: style.radius,
                        pointHoverRadius: 7,
                        pointBackgroundColor: style.fill,
                        pointBorderColor: style.border,
                        pointBorderWidth: style.borderWidth,
                        order: 1,
                    },
                    {
                        label: `${CONFIG.demandThresholdKw} kW renewable threshold`,
                        data: constant(CONFIG.demandThresholdKw),
                        borderColor: COLORS.amber,
                        borderWidth: 1.75,
                        borderDash: [7, 5],
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        pointHitRadius: 0,
                        fill: false,
                        order: 2,
                    },
                    {
                        label: `${CONFIG.criticalThresholdKw} kW critical overload`,
                        data: constant(CONFIG.criticalThresholdKw),
                        borderColor: COLORS.red,
                        backgroundColor: COLORS.redFill,
                        borderWidth: 1.75,
                        borderDash: [3, 3],
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        pointHitRadius: 0,
                        fill: "end",
                        order: 3,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: reduceMotion ? false : { duration: 350 },
                interaction: { mode: "index", intersect: false },
                scales: {
                    x: {
                        grid: { color: COLORS.grid },
                        title: { display: true, text: "Hour (server local time)", color: COLORS.muted },
                        ticks: {
                            autoSkip: true,
                            maxTicksLimit: 12,
                            maxRotation: 0,
                            callback(value) {
                                const row = chartRows[value];
                                return row ? tickLabel(row) : "";
                            },
                        },
                    },
                    y: {
                        grace: "8%",
                        grid: { color: COLORS.grid },
                        title: { display: true, text: "Demand (kW)", color: COLORS.muted },
                    },
                },
                plugins: {
                    legend: {
                        position: "top",
                        align: "start",
                        labels: { color: COLORS.text, boxWidth: 36, boxHeight: 2, padding: 16 },
                    },
                    tooltip: {
                        filter: (item) => item.datasetIndex === 0,
                        backgroundColor: COLORS.surface,
                        borderColor: COLORS.border,
                        borderWidth: 1,
                        titleColor: COLORS.text,
                        bodyColor: COLORS.text,
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            title: (items) => {
                                const row = chartRows[items[0].dataIndex];
                                return row ? fmtFull(row.time) : "";
                            },
                            label: (ctx) => `Predicted demand: ${fmtKw(ctx.parsed.y)} kW`,
                            afterLabel: (ctx) => {
                                const row = chartRows[ctx.dataIndex];
                                if (!row) return "";
                                const lines = [`Mode: ${row.mode}`];
                                if (row.critical) lines.push(row.alert || "CRITICAL OVERLOAD");
                                return lines;
                            },
                        },
                    },
                },
            },
        });
    }

    // Compact legend and axis title when the chart is narrow (phones).
    function adaptChartToWidth() {
        if (!chart) return;
        const narrow = chart.canvas.parentElement.clientWidth < 520;
        const labels = chart.options.plugins.legend.labels;
        labels.boxWidth = narrow ? 20 : 36;
        labels.padding = narrow ? 10 : 16;
        labels.font = { size: narrow ? 11 : 12 };
        chart.options.scales.x.title.display = !narrow;
        chart.update("none");
    }

    function renderChart(f) {
        const box = $("chartBox");
        const canvas = $("demandChart");
        const empty = $("chartEmpty");

        const first = f.rows[0].time;
        const last = f.rows[f.rows.length - 1].time;
      const weatherDescription = forecast?.mode === "live"
    ? "Hourly weather from Open-Meteo."
    : "Same manual weather assumptions applied to every hour.";

$("chartWindow").textContent =
    `${fmtDay(first)}, ${fmtClock(first)} to ` +
    `${fmtDay(last)}, ${fmtClock(last)}. ${weatherDescription}`;

        if (typeof Chart === "undefined") {
            box.classList.remove("has-data");
            empty.textContent = "The chart library could not be loaded. The metrics, schedule and table still show this forecast.";
            return;
        }

        chartRows = f.rows;

        if (!chart) {
            chart = buildChart(canvas);
        } else {
            // Update the existing instance in place so charts never stack up.
            const style = pointStyles(chartRows);
            const constant = (value) => chartRows.map(() => value);
            const [demand, threshold, critical] = chart.data.datasets;

            chart.data.labels = chartRows.map((r) => fmtClock(r.time));
            demand.data = chartRows.map((r) => r.demand);
            demand.pointRadius = style.radius;
            demand.pointBackgroundColor = style.fill;
            demand.pointBorderColor = style.border;
            demand.pointBorderWidth = style.borderWidth;
            threshold.data = constant(CONFIG.demandThresholdKw);
            critical.data = constant(CONFIG.criticalThresholdKw);
            chart.update();
        }

        box.classList.add("has-data");
        adaptChartToWidth();

        const peakRow = f.rows.reduce((best, row) => (row.demand > best.demand ? row : best), f.rows[0]);
        canvas.setAttribute(
            "aria-label",
            `Line chart of ${f.total} hourly predicted demand values in kilowatts. ` +
            `Peak is ${fmtKw(f.peak)} kW at ${fmtClock(peakRow.time)}. ` +
            `${f.criticalAlerts} hours at or above the ${CONFIG.criticalThresholdKw} kW critical threshold. ` +
            "The hourly forecast table below lists every value."
        );
    }

    function modeClass(mode) {
        if (mode === MODE_RENEWABLE) return "is-renewable";
        if (mode === MODE_MAIN) return "is-main";
        return "";
    }

    function renderTable(f) {
        const tbody = $("forecastTable");
        tbody.replaceChildren();

        f.rows.forEach((row) => {
            const tr = make("tr", row.critical ? "is-critical" : "");

            const tdTime = make("td");
            const time = make("time", "", fmtFull(row.time));
            time.dateTime = row.time.iso;
            tdTime.appendChild(time);

            const tdDemand = make("td", "num", `${fmtKw(row.demand)} kW`);

            const tdMode = make("td");
            tdMode.appendChild(make("span", `mode-tag ${modeClass(row.mode)}`.trim(), row.mode));

            const tdAlert = make("td");
            if (row.critical) {
                tdAlert.appendChild(make("span", "alert-tag", row.alert || "CRITICAL OVERLOAD"));
            } else {
                tdAlert.appendChild(make("span", "muted", "None"));
            }

            tr.append(tdTime, tdDemand, tdMode, tdAlert);
            tbody.appendChild(tr);
        });
    }

    function renderOperations(f) {
        $("modeMainHours").textContent = f.mainHours;
        $("modeRenewHours").textContent = f.renewableHours;

        const total = f.mainHours + f.renewableHours || f.total;
        $("splitMain").style.width = `${(f.mainHours / total) * 100}%`;
        $("splitRenew").style.width = `${(f.renewableHours / total) * 100}%`;
        $("modeSplit").setAttribute(
            "aria-label",
            `${f.renewableHours} of ${f.total} forecast hours in Renewable Storage Mode, ${f.mainHours} in Main Grid Mode.`
        );

        const strip = $("hourStrip");
        strip.replaceChildren();

        f.rows.forEach((row) => {
            const cls = ["hour-cell", modeClass(row.mode), row.critical ? "is-critical" : ""].filter(Boolean).join(" ");
            const li = make("li", cls);
            li.title = `${fmtFull(row.time)}: ${row.mode}, ${fmtKw(row.demand)} kW${row.critical ? ", critical overload" : ""}`;

            li.appendChild(make("span", "", fmtClock(row.time)));
            li.appendChild(make("span", "cell-flag"));
            li.appendChild(make("span", "sr-only",
                `, ${row.mode}, ${fmtKw(row.demand)} kilowatts${row.critical ? ", critical overload" : ""}`));
            strip.appendChild(li);
        });
    }

    function renderAlerts(f) {
        const body = $("alertsBody");
        const badge = $("navAlertBadge");
        body.replaceChildren();

        const critical = f.rows.filter((r) => r.critical);

        if (critical.length === 0) {
            body.appendChild(make("p", "empty-state is-clear", "No critical overloads predicted in this forecast."));
        } else {
            const list = make("ul", "alert-list");
            critical.forEach((row) => {
                const item = make("li", "alert-item");

                const head = make("div", "alert-item-head");
                head.appendChild(make("span", "alert-item-title", row.alert || "CRITICAL OVERLOAD"));
                head.appendChild(make("span", "alert-item-time", fmtFull(row.time)));

                const excess = row.demand - CONFIG.criticalThresholdKw;
                const detail = excess >= 0.005
                    ? `Predicted demand ${fmtKw(row.demand)} kW, ${fmtKw(excess)} kW over the ${CONFIG.criticalThresholdKw} kW threshold.`
                    : `Predicted demand ${fmtKw(row.demand)} kW, at the ${CONFIG.criticalThresholdKw} kW threshold.`;

                item.append(head, make("p", "alert-item-body", `${detail} Grid mode: ${row.mode}.`));
                list.appendChild(item);
            });
            body.appendChild(list);
        }

        if (f.criticalAlerts > 0) {
            badge.textContent = f.criticalAlerts;
            badge.setAttribute("aria-label", `${f.criticalAlerts} critical alerts`);
            badge.hidden = false;
        } else {
            badge.hidden = true;
        }
    }

  function renderAll(f) {
    renderKpis(f);
    renderChart(f);
    renderTable(f);
    renderOperations(f);
    renderAlerts(f);
    updateBatteryCard(f);
    updateAssumptionBadge();
}

    // ───────── Events ─────────

    async function handleSubmit(event) {
        event.preventDefault();
        if (busy) return;
clearFormError();

const mode = event.submitter?.id === "liveWeatherButton"
    ? "live"
    : "manual";

let values = {};

if (mode === "manual") {
    const result = readInputs();
    values = result.values;

    if (result.firstInvalid) {
        formStatus.textContent =
            "Fix the highlighted fields to generate a forecast.";
        $(result.firstInvalid.id).focus();
        return;
    }
}

        setBusy(true);
        setApiStatus("loading", "API: requesting…");
        formStatus.textContent = "Requesting 24 hourly predictions from the QuickML model. This can take a few seconds.";

        try {
           const mode = event.submitter?.id === "liveWeatherButton"
    ? "live"
    : "manual";

const result = await requestForecast(
    mode === "live" ? { mode: "live" } : values
);

result.mode = mode;
result.inputs = mode === "manual" ? values : null;
result.generatedAt = new Date();
forecast = result;

            renderAll(forecast);
            setApiStatus("ok", "API: connected");
            formStatus.textContent =
                `Forecast generated at ${pad(result.generatedAt.getHours())}:${pad(result.generatedAt.getMinutes())}. ` +
                `${result.total} hourly predictions received.`;
        } catch (error) {
            setApiStatus("error", "API: request failed");
            showFormError(error.message);
            formStatus.textContent = forecast
                ? "Showing the last successful forecast. It was not changed by this failed request."
                : "";
        } finally {
            setBusy(false);
        }
    }

    function initNavigation() {
        const links = Array.from(document.querySelectorAll("[data-nav]"));
        const sections = links
            .map((link) => document.getElementById(link.dataset.nav))
            .filter(Boolean);
        let pinned = null;

        function setCurrent(id) {
            links.forEach((link) => {
                if (link.dataset.nav === id) link.setAttribute("aria-current", "true");
                else link.removeAttribute("aria-current");
            });
        }

        function update() {
            // A link the user just clicked stays current while its section is on screen,
            // even if the page cannot scroll far enough to put it at the top.
            if (pinned) {
                const el = document.getElementById(pinned);
                const r = el.getBoundingClientRect();
                if (r.top < window.innerHeight && r.bottom > 0) {
                    setCurrent(pinned);
                    return;
                }
                pinned = null;
            }

            const top = (el) => el.getBoundingClientRect().top;
            const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;

            // Last section whose top has passed the header line. Sections that sit side by side
            // share a top edge, so the first of them wins.
            let candidate = sections[0];
            sections.forEach((section) => {
                if (top(section) <= 140 && (top(section) - top(candidate) > 10 || top(candidate) > 140)) {
                    candidate = section;
                }
            });
            if (atBottom) candidate = sections[sections.length - 1];
            setCurrent(candidate.id);
        }

        let ticking = false;
        window.addEventListener("scroll", () => {
            if (ticking) return;
            ticking = true;
            requestAnimationFrame(() => { update(); ticking = false; });
        }, { passive: true });
        window.addEventListener("resize", update);

        // Manual scrolling hands control back to the scroll position.
        ["wheel", "touchstart", "keydown"].forEach((type) => {
            window.addEventListener(type, () => { pinned = null; }, { passive: true });
        });

        links.forEach((link) => {
            link.addEventListener("click", () => {
                pinned = link.dataset.nav;
                setCurrent(pinned);
            });
        });

        update();
    }

    function init() {
        form.addEventListener("submit", handleSubmit);

        liveWeatherButton.addEventListener("click", () => {
    if (busy) return;

    const event = new Event("submit", { cancelable: true });
    Object.defineProperty(event, "submitter", {
        value: liveWeatherButton
    });

    form.dispatchEvent(event);
});

        refreshButton.addEventListener("click", () => {
            if (busy) return;
            if (typeof form.requestSubmit === "function") form.requestSubmit();
            else form.dispatchEvent(new Event("submit", { cancelable: true }));
        });

        FIELDS.forEach((field) => {
            $(field.id).addEventListener("input", () => {
                setFieldError(field, "");
                updateAssumptionBadge();
            });
        });

        let resizeTimer = null;
        window.addEventListener("resize", () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(adaptChartToWidth, 150);
        });

        initNavigation();
        updateAssumptionBadge();

        if (CONFIG.autoRunOnLoad) form.requestSubmit();
    }

    init();
})();
function updateBatteryCard(f) {
    if (!f || !Array.isArray(f.rows) || f.rows.length === 0) {
        return;
    }

    const first = f.rows[0];

    if (!Number.isFinite(first.batterySoc) ||
        !Number.isFinite(first.batteryPower)) {
        return;
    }

    document.getElementById("batterySoc").textContent =
        first.batterySoc.toFixed(1);

    document.getElementById("batterySocBar").style.width =
        `${Math.max(0, Math.min(100, first.batterySoc))}%`;

    document.getElementById("batteryPower").textContent =
        `${first.batteryPower.toFixed(1)} kW`;

    document.getElementById("batteryActionBadge").textContent =
        first.batteryAction;

    document.getElementById("batteryMinSoc").textContent =
        Number.isFinite(f.minimumBatterySoc)
            ? `${f.minimumBatterySoc.toFixed(1)}%`
            : "--%";

    document.getElementById("batteryFinalSoc").textContent =
        Number.isFinite(f.finalBatterySoc)
            ? `${f.finalBatterySoc.toFixed(1)}%`
            : "--%";
}