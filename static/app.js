const statusBox = document.querySelector("#status");
const resultSection = document.querySelector("#result");
const tableBody = document.querySelector("#forecast-table");
const locationName = document.querySelector("#location-name");
const latitude = document.querySelector("#latitude");
const longitude = document.querySelector("#longitude");
const refreshButton = document.querySelector("#refresh-button");
const metricProviderCount = document.querySelector("#metric-provider-count");
const metricCurrentSpread = document.querySelector("#metric-current-spread");
const metricPrecipSpread = document.querySelector("#metric-precip-spread");
const timelineHead = document.querySelector("#timeline-head");
const timelineBody = document.querySelector("#timeline-body");

function formatCell(value, suffix = "") {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return `${value}${suffix}`;
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ko-KR", {
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function renderProvider(provider) {
  if (provider.error) {
    return `
      <tr class="error-row">
        <td>${provider.provider}</td>
        <td colspan="7">${provider.error}</td>
      </tr>
    `;
  }

  return `
    <tr>
      <td><a href="${provider.source_url}" target="_blank" rel="noreferrer">${provider.provider}</a></td>
      <td>${formatCell(provider.current_temp_c, "°C")}</td>
      <td>${formatCell(provider.feels_like_c, "°C")}</td>
      <td>
        ${formatCell(provider.condition)}
        ${provider.humidity || provider.wind_speed_ms ? `
          <div class="provider-subline">
            ${provider.humidity ? `습도 ${provider.humidity}%` : ""}
            ${provider.humidity && provider.wind_speed_ms ? " / " : ""}
            ${provider.wind_speed_ms ? `풍속 ${provider.wind_speed_ms}m/s` : ""}
          </div>
        ` : ""}
      </td>
      <td>${formatCell(provider.next_6h_precip_probability, "%")}</td>
      <td>${formatCell(provider.next_24h_low_c, "°C")}</td>
      <td>${formatCell(provider.next_24h_high_c, "°C")}</td>
      <td>${formatDateTime(provider.forecast_time)}</td>
    </tr>
  `;
}

function renderTimelineHeader(consensus) {
  const columns = (consensus.timeline || [])
    .map((entry) => `<th>${formatDateTime(entry.time)}</th>`)
    .join("");

  timelineHead.innerHTML = `
    <tr>
      <th>Provider</th>
      ${columns}
    </tr>
  `;
}

function renderTimelineCell(entry) {
  if (!entry) {
    return "<td>-</td>";
  }

  const temp = formatCell(entry.temperature_c, "°C");
  const precip = formatCell(entry.precip_probability, "%");
  const condition = entry.condition ? `<span class="mini-note">${entry.condition}</span>` : "";

  return `
    <td>
      <div class="timeline-cell">
        <strong>${temp}</strong>
        <span>${precip}</span>
        ${condition}
      </div>
    </td>
  `;
}

function renderTimelineRows(providers, consensus) {
  const expectedColumnCount = (consensus.timeline || []).length || 1;
  const providerRows = providers.map((provider) => {
    if (provider.error) {
      return `
        <tr class="error-row">
          <td>${provider.provider}</td>
          <td colspan="${expectedColumnCount}">${provider.error}</td>
        </tr>
      `;
    }

    const cells = [];
    for (let index = 0; index < expectedColumnCount; index += 1) {
      cells.push(renderTimelineCell((provider.timeline || [])[index]));
    }

    return `
      <tr>
        <td>${provider.provider}</td>
        ${cells.join("")}
      </tr>
    `;
  });

  const spreadCells = (consensus.timeline || [])
    .map((entry) => `
      <td class="spread-cell">
        <div class="timeline-cell">
          <strong>${formatCell(entry.temperature_spread_c, "°C")}</strong>
          <span>${formatCell(entry.precip_spread_probability, "%")}</span>
          <span class="mini-note">편차</span>
        </div>
      </td>
    `)
    .join("");

  providerRows.push(`
    <tr class="spread-row">
      <td>Consensus spread</td>
      ${spreadCells}
    </tr>
  `);

  timelineBody.innerHTML = providerRows.join("");
}

function renderMetrics(consensus) {
  metricProviderCount.textContent = `${consensus.successful_provider_count} / ${consensus.successful_provider_count + consensus.failed_provider_count}`;
  metricCurrentSpread.textContent = formatCell(consensus.current_temp_spread_c, "°C");
  metricPrecipSpread.textContent = formatCell(consensus.next_6h_precip_spread_probability, "%");
}

async function loadForecast() {
  statusBox.textContent = "무료 API들을 조회하는 중입니다...";
  resultSection.classList.add("hidden");
  tableBody.innerHTML = "";
  timelineHead.innerHTML = "";
  timelineBody.innerHTML = "";

  try {
    const response = await fetch("/api/forecast");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "조회에 실패했습니다.");
    }

    locationName.textContent = payload.location.display_name;
    latitude.textContent = payload.location.latitude.toFixed(4);
    longitude.textContent = payload.location.longitude.toFixed(4);
    tableBody.innerHTML = payload.providers.map(renderProvider).join("");
    renderMetrics(payload.consensus);
    renderTimelineHeader(payload.consensus);
    renderTimelineRows(payload.providers, payload.consensus);
    resultSection.classList.remove("hidden");
    statusBox.textContent = `${payload.providers.length}개 소스를 조회했습니다. ${payload.consensus.failed_provider_count}개는 실패했습니다.`;
  } catch (error) {
    statusBox.textContent = error.message;
  }
}

refreshButton.addEventListener("click", () => {
  loadForecast();
});
