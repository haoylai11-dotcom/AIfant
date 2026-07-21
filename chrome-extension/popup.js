/**
 * DYKS Analyzer — Extension Popup Logic
 */

let currentData = null;

document.addEventListener("DOMContentLoaded", () => {
  loadStoredData();
  askContentScript();

  document.getElementById("btn-retry").addEventListener("click", askContentScript);
  document.getElementById("btn-send").addEventListener("click", sendToServer);
  document.getElementById("server-url").addEventListener("change", (e) => {
    chrome.storage.local.set({ serverUrl: e.target.value });
  });
});

// ── Load stored server URL ──
chrome.storage.local.get("serverUrl", (r) => {
  if (r.serverUrl) document.getElementById("server-url").value = r.serverUrl;
});

// ── Receive messages from content script ──
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "EXTRACTED_DATA") {
    renderData(msg.data);
  }
});

function askContentScript() {
  showPanel("loading");
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]) { showPanel("nodata"); return; }
    chrome.tabs.sendMessage(tabs[0].id, { type: "EXTRACT" }, (resp) => {
      if (chrome.runtime.lastError) {
        // Try reading from storage
        loadStoredData();
      }
    });
  });
}

function loadStoredData() {
  // Try session storage first (from current page visit)
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.scripting.executeScript(
      {
        target: { tabId: tabs[0].id },
        func: () => {
          const raw = sessionStorage.getItem("__dyks_data");
          return raw ? JSON.parse(raw) : null;
        },
      },
      (results) => {
        if (results && results[0] && results[0].result) {
          renderData(results[0].result);
        } else {
          // Try local storage as fallback
          chrome.storage.local.get("lastExtracted", (r) => {
            if (r.lastExtracted) {
              renderData(r.lastExtracted);
            } else {
              showPanel("nodata");
            }
          });
        }
      }
    );
  });
}

// ── Render extracted data ──
function renderData(data) {
  if (!data) { showPanel("nodata"); return; }
  currentData = data;

  // Platform
  const platformLabel = data.platform === "douyin" ? "抖音" : "快手";
  const platformColor = data.platform === "douyin" ? "#1a56db" : "#f97316";
  document.getElementById("result-platform").innerHTML =
    `<span style="color:${platformColor};font-weight:600;">${platformLabel}</span>`;

  // Title
  document.getElementById("result-title").textContent =
    data.video_title || "（无标题）";

  // Author
  document.getElementById("result-author").textContent =
    data.author_name || "（未知）";

  // URL
  document.getElementById("result-url").textContent = data.url || "";

  // Metrics
  setMetric("likes", data.like_count);
  setMetric("comments", data.comment_count);
  setMetric("shares", data.share_count);
  setMetric("views", data.view_count);

  // Extras
  setText("result-favorites", data.favorite_count);
  setText("result-followers", data.follower_count);
  setText("result-time", data.publish_time);

  showPanel("result");
}

function setMetric(id, val) {
  const el = document.getElementById("metric-" + id);
  if (val != null) {
    el.textContent = formatNum(val);
    el.classList.remove("na");
  } else {
    el.textContent = "—";
    el.classList.add("na");
  }
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (val != null) {
    el.textContent = typeof val === "number" ? formatNum(val) : val;
  } else {
    el.textContent = "—";
  }
}

function formatNum(n) {
  if (n >= 10000) {
    return (n / 10000).toFixed(1).replace(/\.0$/, "") + "万";
  }
  return n.toLocaleString();
}

// ── Panel visibility ──
function showPanel(which) {
  document.getElementById("loading-panel").style.display = which === "loading" ? "block" : "none";
  document.getElementById("result-panel").style.display = which === "result" ? "block" : "none";
  document.getElementById("no-data-panel").style.display = which === "nodata" ? "block" : "none";
}

// ── Toggle advanced section ──
function toggleAdvanced() {
  const el = document.getElementById("advanced-section");
  const fold = document.querySelector(".fold");
  if (el.classList.contains("hidden")) {
    el.classList.remove("hidden");
    fold.textContent = "收起 ▲";
  } else {
    el.classList.add("hidden");
    fold.textContent = "展开更多字段 ▾";
  }
}

// ── Send to server ──
async function sendToServer() {
  if (!currentData) return;

  // Collect editable fields
  const title = document.getElementById("result-title").textContent?.trim() || "";
  const author = document.getElementById("result-author").textContent?.trim() || "";

  if (title) currentData.video_title = title;
  if (author) currentData.author_name = author;

  const serverUrl = document.getElementById("server-url").value.replace(/\/$/, "");

  // Build payload for browser-extract endpoint
  const payload = {
    json_data: {
      url: currentData.url,
      title: currentData.video_title || "",
      description: currentData.video_description || "",
      hashtags: currentData.hashtags || [],
      publish_time: currentData.publish_time || null,
      duration: currentData.duration || null,
      cover_url: currentData.cover_url || null,
      author_name: currentData.author_name || "",
      author_id: currentData.author_id || "",
      follower_count: currentData.follower_count,
      verified: currentData.verified || false,
      verification_text: currentData.verification_text || "",
      bio: currentData.bio || "",
      like_count: currentData.like_count,
      comment_count: currentData.comment_count,
      share_count: currentData.share_count,
      favorite_count: currentData.favorite_count,
      view_count: currentData.view_count,
      comments: currentData.comments || [],
    },
  };

  setStatus("info", "发送中...");

  try {
    const resp = await fetch(serverUrl + "/api/videos/browser-extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const result = await resp.json();

    if (result.success) {
      const msg = result.is_new ? "✓ 新增视频" : "✓ 视频已存在（已更新）";
      setStatus("success", `${msg} · 评论: ${result.comments_imported || 0}条 · 📋 ID: ${result.video_id.substring(0, 8)}...`);

      // Also save the video_id for reference
      currentData._video_id = result.video_id;
    } else {
      setStatus("error", "✗ " + (result.detail || JSON.stringify(result)));
    }
  } catch (err) {
    setStatus("error", "✗ 无法连接到 " + serverUrl + " — 请确认后端已启动");
  }
}

function setStatus(type, msg) {
  const el = document.getElementById("status");
  el.innerHTML = `<div class="toast ${type}">${msg}</div>`;
}
