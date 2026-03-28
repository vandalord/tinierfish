const statusText = document.getElementById("status-text");
const refreshButton = document.getElementById("refresh-button");
const sourceBadge = document.getElementById("source-badge");
const refreshBadge = document.getElementById("refresh-badge");
const mapSvg = document.getElementById("map-svg");
const issuesList = document.getElementById("issues-list");
const selectionPanel = document.getElementById("selection-panel");
const timelinePanel = document.getElementById("timeline-panel");
const liveHealthPanel = document.getElementById("live-health-panel");

const metricIssues = document.getElementById("metric-issues");
const metricRecommendations = document.getElementById("metric-recommendations");
const metricCritical = document.getElementById("metric-critical");
const metricSources = document.getElementById("metric-sources");

const viewBounds = {
  minLon: 90,
  maxLon: 150,
  minLat: -35,
  maxLat: 25,
};

let dashboardState = null;
let statusPollHandle = null;

function projectPoint(latitude, longitude) {
  const width = 1000;
  const height = 640;
  const x = ((longitude - viewBounds.minLon) / (viewBounds.maxLon - viewBounds.minLon)) * width;
  const y = height - ((latitude - viewBounds.minLat) / (viewBounds.maxLat - viewBounds.minLat)) * height;
  return { x, y };
}

function severityClass(severity) {
  return severity === "critical" || severity === "high" ? "alert" : "safe";
}

function buildRecommendationMarkup(recommendations) {
  if (!recommendations.length) {
    return `<p class="detail-copy">No fallback supplier matched this disruption yet.</p>`;
  }

  return `
    <div class="fallback-list">
      ${recommendations
        .map(
          (item) => `
            <div class="fallback-card">
              <strong>${item.recommended_supplier.supplier_name}</strong>
              <p class="fallback-meta">${item.strategy} • ${item.product} • ${item.recommended_supplier.country}</p>
              <p class="recommendation-copy">${item.rationale}</p>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderSelection(feature) {
  const props = feature.properties;
  const signals = props.negative_signals.length ? props.negative_signals : ["monitoring"];

  selectionPanel.innerHTML = `
    <h2 class="detail-title">${props.title}</h2>
    <p class="detail-copy">${props.region} is flagged for a ${props.risk_type.replaceAll("_", " ")} event with ${props.severity} severity.</p>
    <div class="tag-row">
      ${props.products.map((product) => `<span class="pill">${product}</span>`).join("")}
      ${signals.map((signal) => `<span class="pill ${severityClass(props.severity)}">${signal}</span>`).join("")}
    </div>
    ${buildRecommendationMarkup(props.recommendations)}
  `;
}

function renderTimeline(payload) {
  const timelineItems = [
    ["Source batch", payload.source_batch.created_at],
    ["Issue extraction", payload.issue_batch.created_at],
    ["Recommendations", payload.recommendation_batch.created_at],
    ["Visualization", payload.visualization_batch.created_at],
  ];

  timelinePanel.innerHTML = timelineItems
    .map(
      ([label, value]) => `
        <div class="timeline-item">
          <strong>${label}</strong>
          <div class="detail-copy">${new Date(value).toLocaleString()}</div>
        </div>
      `,
    )
    .join("");
}

function renderMetrics(payload) {
  const issues = payload.issue_batch.issues;
  const recommendations = payload.recommendation_batch.recommendations;
  const criticalCount = issues.filter((issue) => issue.extraction.severity === "critical").length;

  metricIssues.textContent = String(issues.length);
  metricRecommendations.textContent = String(recommendations.length);
  metricCritical.textContent = String(criticalCount);
  metricSources.textContent = String(payload.source_batch.sources.length);
}

function formatMaybeDate(value, fallback = "Not yet") {
  if (!value) {
    return fallback;
  }
  return new Date(value).toLocaleString();
}

function labelizeMode(mode) {
  if (mode === "tinyfish_web") {
    return "TinyFish live";
  }
  if (mode === "fallback_demo") {
    return "Fallback demo";
  }
  return mode ? mode.replaceAll("_", " ") : "Source unknown";
}

function labelizeRefreshStatus(status) {
  if (status === "refreshing") {
    return "Refreshing";
  }
  if (status === "error") {
    return "Refresh error";
  }
  if (status === "idle") {
    return "Idle";
  }
  return status || "Unknown";
}

function updateRuntimeBadges(runtime, sourceMode) {
  sourceBadge.className = `status-badge ${sourceMode || "unknown"}`;
  sourceBadge.textContent = labelizeMode(sourceMode);

  const refreshStatus = runtime?.status || "unknown";
  refreshBadge.className = `status-badge ${refreshStatus}`;
  refreshBadge.textContent = labelizeRefreshStatus(refreshStatus);
}

function renderLiveHealth(runtime) {
  liveHealthPanel.innerHTML = `
    <div class="health-item">
      <span class="health-label">Last live success</span>
      <div class="detail-copy">${formatMaybeDate(runtime?.last_live_success_at)}</div>
      <div class="detail-copy">${runtime?.last_live_success_summary || "No confirmed TinyFish live batch yet."}</div>
    </div>
    <div class="health-item">
      <span class="health-label">Last live error</span>
      <div class="detail-copy">${formatMaybeDate(runtime?.last_live_error_at)}</div>
      <div class="detail-copy">${runtime?.last_live_error || "No recorded live errors."}</div>
    </div>
  `;
}

function renderIssueCards(features) {
  issuesList.innerHTML = features
    .map(
      (feature, index) => `
        <article class="issue-card">
          <button type="button" data-index="${index}">
            <div class="tag-row">
              <span class="pill ${severityClass(feature.properties.severity)}">${feature.properties.severity}</span>
              <span class="pill">${feature.properties.region}</span>
            </div>
            <h3 class="issue-title">${feature.properties.title}</h3>
            <p class="issue-meta">Products: ${feature.properties.products.join(", ")}</p>
            <p class="issue-meta">Signals: ${feature.properties.negative_signals.join(", ") || "monitoring"}</p>
          </button>
        </article>
      `,
    )
    .join("");

  issuesList.querySelectorAll("button[data-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.getAttribute("data-index"));
      renderSelection(features[index]);
    });
  });
}

function drawMap(features) {
  const backdrop = `
    <defs>
      <filter id="glow">
        <feGaussianBlur stdDeviation="8" result="blur"></feGaussianBlur>
        <feMerge>
          <feMergeNode in="blur"></feMergeNode>
          <feMergeNode in="SourceGraphic"></feMergeNode>
        </feMerge>
      </filter>
    </defs>
    <rect x="0" y="0" width="1000" height="640" fill="transparent"></rect>
    <path d="M78 90C168 56 272 90 320 150C388 240 448 250 504 218C566 182 628 174 714 188C796 200 874 246 930 288L930 620L0 620L0 150C20 124 46 104 78 90Z" fill="rgba(239, 228, 196, 0.7)"></path>
    <path d="M572 84C650 56 744 70 844 134C920 182 972 242 1000 284L1000 0L548 0C548 20 552 46 572 84Z" fill="rgba(239, 228, 196, 0.62)"></path>
    <text x="596" y="160" class="map-label">South China Sea</text>
    <text x="454" y="338" class="map-label">Singapore</text>
    <text x="330" y="260" class="map-label">Malaysia</text>
    <text x="404" y="222" class="map-label">Thailand</text>
    <text x="622" y="252" class="map-label">Vietnam</text>
    <text x="706" y="468" class="map-label">Indonesia</text>
    <text x="834" y="574" class="map-label">Australia</text>
  `;

  mapSvg.innerHTML = backdrop;

  const singaporePoint = projectPoint(1.3521, 103.8198);
  const singaporeRing = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  singaporeRing.setAttribute("cx", singaporePoint.x);
  singaporeRing.setAttribute("cy", singaporePoint.y);
  singaporeRing.setAttribute("r", "46");
  singaporeRing.setAttribute("fill", "none");
  singaporeRing.setAttribute("stroke", "rgba(31, 111, 97, 0.28)");
  singaporeRing.setAttribute("stroke-dasharray", "8 10");
  singaporeRing.setAttribute("stroke-width", "2");
  mapSvg.appendChild(singaporeRing);

  features.forEach((feature, index) => {
    const [longitude, latitude] = feature.geometry.coordinates;
    const issuePoint = projectPoint(latitude, longitude);

    const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    ring.setAttribute("cx", issuePoint.x);
    ring.setAttribute("cy", issuePoint.y);
    ring.setAttribute("r", feature.properties.severity === "critical" ? "26" : "20");
    ring.setAttribute("class", "pulse-ring");
    ring.setAttribute("filter", "url(#glow)");
    mapSvg.appendChild(ring);

    const core = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    core.setAttribute("cx", issuePoint.x);
    core.setAttribute("cy", issuePoint.y);
    core.setAttribute("r", "9");
    core.setAttribute("class", "pulse-core");
    mapSvg.appendChild(core);

    feature.properties.recommendations.slice(0, 2).forEach((recommendation) => {
      const supplierPoint = projectPoint(
        recommendation.recommended_supplier.latitude,
        recommendation.recommended_supplier.longitude,
      );

      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", issuePoint.x);
      line.setAttribute("y1", issuePoint.y);
      line.setAttribute("x2", supplierPoint.x);
      line.setAttribute("y2", supplierPoint.y);
      line.setAttribute("class", "map-line");
      mapSvg.appendChild(line);

      const supplierNode = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      supplierNode.setAttribute("cx", supplierPoint.x);
      supplierNode.setAttribute("cy", supplierPoint.y);
      supplierNode.setAttribute("r", "7");
      supplierNode.setAttribute("class", "supplier-node");
      mapSvg.appendChild(supplierNode);
    });

    const hit = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    hit.setAttribute("cx", issuePoint.x);
    hit.setAttribute("cy", issuePoint.y);
    hit.setAttribute("r", "24");
    hit.setAttribute("class", "map-hit");
    hit.setAttribute("data-index", String(index));
    hit.addEventListener("click", () => renderSelection(feature));
    mapSvg.appendChild(hit);
  });
}

async function loadDashboard({ refresh = false } = {}) {
  if (refresh) {
    statusText.textContent = "Queueing a live TinyFish refresh...";
    refreshButton.disabled = true;
    const refreshResponse = await fetch("/api/refresh", {
      method: "POST",
      cache: "no-store",
    });
    const refreshPayload = await refreshResponse.json();
    updateRuntimeBadges(
      { status: refreshPayload.status || "refreshing" },
      dashboardState?.source_mode || "unknown",
    );
    await waitForRefresh();
  }

  if (!refresh) {
    statusText.textContent = "Loading latest batch...";
  }

  const response = await fetch("/api/dashboard", { cache: "no-store" });
  const payload = await response.json();

  dashboardState = payload;
  const features = payload.visualization_batch.geojson.features;

  renderMetrics(payload);
  renderTimeline(payload);
  renderIssueCards(features);
  drawMap(features);
  updateRuntimeBadges(payload.runtime, payload.source_mode);
  renderLiveHealth(payload.runtime);
  statusText.textContent = `Live batch ${payload.batch_root} updated ${new Date(payload.generated_at).toLocaleString()}`;

  if (features.length) {
    renderSelection(features[0]);
  } else {
    selectionPanel.innerHTML = `
      <h2 class="detail-title">No disruptions in this batch</h2>
      <p class="detail-copy">Try another refresh after your data source updates.</p>
    `;
  }

  refreshButton.disabled = false;
}

async function waitForRefresh() {
  if (statusPollHandle) {
    clearTimeout(statusPollHandle);
    statusPollHandle = null;
  }

  while (true) {
    const response = await fetch("/api/status", { cache: "no-store" });
    const payload = await response.json();
    updateRuntimeBadges(payload.refresh, payload.refresh.last_source_mode || dashboardState?.source_mode || "unknown");
    renderLiveHealth(payload.refresh);

    if (payload.refresh.status === "idle") {
      if (payload.refresh.last_error) {
        statusText.textContent = `Refresh failed: ${payload.refresh.last_error}`;
      }
      return;
    }

    if (payload.refresh.status === "error") {
      throw new Error(payload.refresh.last_error || "Background refresh failed.");
    }

    statusText.textContent = "TinyFish refresh is running in the background...";
    await new Promise((resolve) => {
      statusPollHandle = setTimeout(resolve, 2000);
    });
  }
}

refreshButton.addEventListener("click", () => {
  loadDashboard({ refresh: true }).catch((error) => {
    statusText.textContent = `Refresh failed: ${error.message}`;
    updateRuntimeBadges({ status: "error" }, dashboardState?.source_mode || "unknown");
    refreshButton.disabled = false;
  });
});

loadDashboard().catch((error) => {
  statusText.textContent = `Dashboard failed to load: ${error.message}`;
  updateRuntimeBadges({ status: "error" }, "unknown");
  refreshButton.disabled = false;
});

setInterval(() => {
  loadDashboard({ refresh: false }).catch(() => {});
}, 60000);
