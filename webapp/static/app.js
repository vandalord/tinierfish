const statusText = document.getElementById("status-text");
const refreshButton = document.getElementById("refresh-button");
const sourceBadge = document.getElementById("source-badge");
const refreshBadge = document.getElementById("refresh-badge");
const mapCanvas = document.getElementById("map-canvas");
const issuesList = document.getElementById("issues-list");
const selectionPanel = document.getElementById("selection-panel");
const timelinePanel = document.getElementById("timeline-panel");
const liveHealthPanel = document.getElementById("live-health-panel");

const metricIssues = document.getElementById("metric-issues");
const metricRecommendations = document.getElementById("metric-recommendations");
const metricCritical = document.getElementById("metric-critical");
const metricSources = document.getElementById("metric-sources");

let dashboardState = null;
let statusPollHandle = null;
let issueMap = null;
let issueLayer = null;

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
              ${buildSourceMarkup(item.source_label, item.source_url)}
              <p class="fallback-meta">${item.strategy} • ${item.product} • ${item.recommended_supplier.country}</p>
              <p class="recommendation-copy">${item.rationale}</p>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function buildSourceMarkup(label, url) {
  if (url) {
    return `<p class="source-line">Source: <a class="source-link" href="${url}" target="_blank" rel="noreferrer">${label || url}</a></p>`;
  }
  return `<p class="source-line">Source: ${label || "Unknown source"}</p>`;
}

function renderSelection(feature) {
  const props = feature.properties;
  const signals = props.negative_signals.length ? props.negative_signals : ["monitoring"];

  selectionPanel.innerHTML = `
    <h2 class="detail-title">${props.title}</h2>
    ${buildSourceMarkup(props.source_publisher, props.source_url)}
    <p class="detail-copy">${props.region} is flagged for a ${props.risk_type.replaceAll("_", " ")} event with ${props.severity} severity.</p>
    <p class="detail-copy">${props.narrative || "No extracted narrative available."}</p>
    <div class="tag-row">
      ${props.products.map((product) => `<span class="pill">${product}</span>`).join("")}
      ${signals.map((signal) => `<span class="pill ${severityClass(props.severity)}">${signal}</span>`).join("")}
    </div>
    <p><a class="detail-link" href="${props.source_url}" target="_blank" rel="noreferrer">Read article</a></p>
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

function renderLiveHealth(runtime, payload = null) {
  const recommendationMetadata = payload?.recommendation_batch?.metadata || {};
  const liveRecommendationCount = recommendationMetadata.live_recommendation_count ?? null;
  const fallbackRecommendationCount = recommendationMetadata.fallback_recommendation_count ?? null;
  const recommendationErrors = recommendationMetadata.live_errors || [];

  const recommendationStatusMarkup =
    liveRecommendationCount === null && fallbackRecommendationCount === null
      ? ""
      : `
        <div class="health-item">
          <span class="health-label">Recommendation engine</span>
          <div class="detail-copy">${
            liveRecommendationCount > 0 ? "TinyFish live recommendations active." : "Fallback supplier catalog in use."
          }</div>
          <div class="detail-copy">Live recommendations: ${liveRecommendationCount || 0}</div>
          <div class="detail-copy">Fallback recommendations: ${fallbackRecommendationCount || 0}</div>
          <div class="detail-copy">${recommendationErrors[0] || "No recommendation engine errors recorded."}</div>
        </div>
      `;

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
    ${recommendationStatusMarkup}
  `;
}

function renderIssueCards(features) {
  issuesList.innerHTML = features
    .map(
      (feature, index) => `
        <article class="issue-card" data-index="${index}">
            <div class="tag-row">
              <span class="pill ${severityClass(feature.properties.severity)}">${feature.properties.severity}</span>
              <span class="pill">${feature.properties.region}</span>
            </div>
            <h3 class="issue-title">${feature.properties.title}</h3>
            ${buildSourceMarkup(feature.properties.source_publisher, feature.properties.source_url)}
            <p class="issue-meta">Products: ${feature.properties.products.join(", ")}</p>
            <p class="issue-meta">Signals: ${feature.properties.negative_signals.join(", ") || "monitoring"}</p>
          </button>
          <div class="issue-actions">
            <span class="issue-meta">${feature.properties.recommendations.length} recommendations</span>
            <a class="issue-link" href="${feature.properties.source_url}" target="_blank" rel="noreferrer">Open article</a>
          </div>
        </article>
      `,
    )
    .join("");

  issuesList.querySelectorAll("article[data-index]").forEach((card) => {
    card.addEventListener("click", (event) => {
      if (event.target instanceof Element && event.target.closest("a")) {
        return;
      }
      const index = Number(card.getAttribute("data-index"));
      renderSelection(features[index]);
    });
  });
}

function drawMap(features) {
  if (!window.L) {
    mapCanvas.innerHTML = `<div class="detail-copy" style="padding: 24px;">Map library failed to load.</div>`;
    return;
  }

  if (!issueMap) {
    issueMap = window.L.map(mapCanvas, {
      zoomControl: true,
      scrollWheelZoom: false,
    }).setView([4.5, 108], 4);

    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 8,
      minZoom: 3,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(issueMap);
  }

  if (issueLayer) {
    issueLayer.remove();
  }

  issueLayer = window.L.layerGroup().addTo(issueMap);
  const bounds = [];

  const singapore = [1.3521, 103.8198];
  window.L.circle(singapore, {
    radius: 120000,
    color: "#1f6f61",
    weight: 2,
    dashArray: "6 8",
    fillOpacity: 0.04,
  }).addTo(issueLayer);
  bounds.push(singapore);

  features.forEach((feature, index) => {
    const [longitude, latitude] = feature.geometry.coordinates;
    const latLng = [latitude, longitude];
    bounds.push(latLng);

    const marker = window.L.circleMarker(latLng, {
      radius: feature.properties.severity === "critical" ? 11 : 8,
      color: "#ffffff",
      weight: 2,
      fillColor: "#bf493d",
      fillOpacity: 0.92,
    })
      .addTo(issueLayer)
      .bindPopup(
        `<strong>${feature.properties.title}</strong><br>${feature.properties.region}<br><a href="${feature.properties.source_url}" target="_blank" rel="noreferrer">Read article</a>`,
      );

    marker.on("click", () => renderSelection(feature));

    feature.properties.recommendations.slice(0, 2).forEach((recommendation) => {
      const supplierLatLng = [
        recommendation.recommended_supplier.latitude,
        recommendation.recommended_supplier.longitude,
      ];
      bounds.push(supplierLatLng);

      window.L.polyline([latLng, supplierLatLng], {
        color: "#1f6f61",
        weight: 2,
        opacity: 0.45,
        dashArray: "6 8",
      }).addTo(issueLayer);

      window.L.circleMarker(supplierLatLng, {
        radius: 6,
        color: "#ffffff",
        weight: 2,
        fillColor: "#1f6f61",
        fillOpacity: 0.95,
      })
        .addTo(issueLayer)
        .bindPopup(
          `<strong>${recommendation.recommended_supplier.supplier_name}</strong><br>${recommendation.product}<br>${recommendation.recommended_supplier.country}`,
        );
    });
  });

  issueMap.fitBounds(bounds, { padding: [36, 36], maxZoom: 5 });
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
  renderLiveHealth(payload.runtime, payload);
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
    renderLiveHealth(payload.refresh, dashboardState);

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
