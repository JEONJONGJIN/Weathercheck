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
const midForecastPanel = document.querySelector("#mid-forecast-panel");
const midForecastTime = document.querySelector("#mid-forecast-time");
const midForecastGrid = document.querySelector("#mid-forecast-grid");

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

  const normalized = typeof value === "string" && /^\d{8}T\d{2}:\d{2}:\d{2}/.test(value)
    ? `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}${value.slice(8)}`
    : value;
  const date = new Date(normalized);
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

function formatMonthDay(value) {
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
    weekday: "short",
  }).format(date);
}

function formatTimeWithLabel(value, label) {
  const formatted = formatDateTime(value);
  if (!label) {
    return formatted;
  }
  return `
    <div>${formatted}</div>
    <div class="provider-subline">${label}</div>
  `;
}

function renderProvider(provider) {
  if (provider.error) {
    return `
      <tr class="error-row">
        <td>${provider.provider}</td>
        <td colspan="9">${provider.error}</td>
      </tr>
    `;
  }

  return `
    <tr>
      <td><a href="${provider.source_url}" target="_blank" rel="noreferrer">${provider.provider}</a></td>
      <td>${formatCell(provider.current_temp_c, "°C")}</td>
      <td>${formatCell(provider.feels_like_c, "°C")}</td>
      <td>${formatCell(provider.condition)}</td>
      <td>${formatCell(provider.wind_speed_ms, "m/s")}</td>
      <td>${formatCell(provider.precipitation_amount_mm, "mm")}</td>
      <td>${formatCell(provider.next_6h_precip_probability, "%")}</td>
      <td>${formatCell(provider.next_24h_low_c, "°C")}</td>
      <td>${formatCell(provider.next_24h_high_c, "°C")}</td>
      <td>${formatTimeWithLabel(provider.forecast_time, provider.time_label)}</td>
    </tr>
  `;
}

function renderMidForecast(midForecast) {
  if (!midForecast || !midForecast.days || !midForecast.days.length) {
    midForecastPanel.classList.add("hidden");
    midForecastGrid.innerHTML = "";
    midForecastTime.textContent = "";
    return;
  }

  midForecastTime.textContent = `${midForecast.time_label || "발표 시각"} ${formatDateTime(midForecast.forecast_time)}`;
  midForecastGrid.innerHTML = midForecast.days
    .map((day) => `
      <article class="mid-card">
        <p class="mid-day">${formatMonthDay(day.target_date)}</p>
        <p class="mid-condition">오전 ${formatCell(day.am_condition)}</p>
        <p class="mid-condition">오후 ${formatCell(day.pm_condition)}</p>
        <p class="mid-temp">${formatCell(day.low_c, "°C")} / ${formatCell(day.high_c, "°C")}</p>
      </article>
    `)
    .join("");
  midForecastPanel.classList.remove("hidden");
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
    renderMidForecast(payload.mid_forecast);
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
