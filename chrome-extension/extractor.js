/**
 * DYKS Analyzer — 抖音/快手页面数据提取器
 *
 * 合规声明：仅提取研究者已打开的公开页面中浏览器可见的文字和数字，
 * 不注入Cookie、不伪造请求、不绕过任何访问控制。
 */

(function () {
  // 防止重复注入
  if (window.__dyks_extractor_loaded) return;
  window.__dyks_extractor_loaded = true;

  const host = window.location.hostname;
  const isDouyin = host.includes("douyin.com");
  const isKuaishou = host.includes("kuaishou.com");

  if (!isDouyin && !isKuaishou) return;

  // ── 提取函数 ──

  function extractDouyin() {
    const data = {
      url: window.location.href,
      platform: "douyin",
      short_url: null,
      video_title: null,
      video_description: null,
      hashtags: [],
      publish_time: null,
      duration: null,
      cover_url: null,
      author_name: null,
      author_id: null,
      follower_count: null,
      verified: false,
      verification_text: null,
      bio: null,
      like_count: null,
      comment_count: null,
      share_count: null,
      favorite_count: null,
      view_count: null,
      comments: [],
    };

    // ── 方式1: 从 __UNIVERSAL_INITIAL_STATE__ 提取（网页内嵌JSON数据） ──
    try {
      const scripts = document.querySelectorAll("script");
      for (const s of scripts) {
        if (s.id === "RENDER_DATA") continue; // Rendering-only data
        const text = s.textContent || "";
        // Look for the big JSON state blob
        const match = text.match(/self\.__pace_f\s*=\s*\[.*"video":.*\]/);
        if (match) continue;

        // Try window.__INITIAL_STATE__ approach
        try {
          const stateEl = document.getElementById("__UNIVERSAL_DATA_ID");
          if (stateEl && stateEl.textContent) {
            const raw = stateEl.textContent.replace(/^window\.__UNIVERSAL_INITIAL_STATE__\s*=/, "");
            if (raw && raw.length > 100) {
              const parsed = JSON.parse(raw);
              extractFromUniversalState(parsed, data);
            }
          }
        } catch (_) {}
      }
    } catch (_) {}

    // ── 方式2: 从页面 DOM 文本提取 ──
    extractFromDOM(data);

    // Try to extract video ID
    const vidMatch = location.href.match(/video\/(\d+)/);
    if (vidMatch) data.platform_video_id = vidMatch[1];

    // Try to extract from pathname
    const pathParts = location.pathname.split("/");
    const vidIdx = pathParts.indexOf("video");
    if (vidIdx >= 0 && vidIdx + 1 < pathParts.length) {
      data.platform_video_id = pathParts[vidIdx + 1];
    }

    return data;
  }

  function extractFromUniversalState(state, data) {
    // Walk through the state tree to find video data
    try {
      if (state && state.router) {
        // This varies by douyin version, try common paths
      }
    } catch (_) {}
  }

  function extractFromDOM(data) {
    // ── 抖音 DOM 选择器 ──
    // 这些选择器基于抖音公开页面结构，不同版本可能不同

    // Seek video title — try aria-label, meta tags, heading elements
    const titleSelectors = [
      'meta[property="og:title"]',
      'meta[name="twitter:title"]',
      'h1[data-e2e="video-title"]',
      '[data-e2e="video-detail-title"]',
    ];
    for (const sel of titleSelectors) {
      const el = document.querySelector(sel);
      if (el) {
        data.video_title = el.getAttribute("content") || el.textContent?.trim();
        if (data.video_title) break;
      }
    }

    // If still no title, use document.title but strip " - 抖音"
    if (!data.video_title && document.title) {
      data.video_title = document.title.replace(/\s*[-–—]\s*抖音.*$/, "").trim();
    }

    // Description
    const descEl =
      document.querySelector('meta[property="og:description"]') ||
      document.querySelector('meta[name="description"]');
    if (descEl) {
      data.video_description = descEl.getAttribute("content");
    }

    // Publish time — try time elements
    const timeEl = document.querySelector("time");
    if (timeEl) {
      data.publish_time = timeEl.getAttribute("datetime") || timeEl.textContent?.trim();
    }

    // Cover image
    const ogImg = document.querySelector('meta[property="og:image"]');
    if (ogImg) data.cover_url = ogImg.getAttribute("content");

    // ── Interaction counts ──
    // Walk all elements looking for number patterns near like/comment/share labels
    // Douyin typically uses aria-label on action buttons
    const allEls = document.body.querySelectorAll("*");
    for (const el of allEls) {
      const text = (el.textContent || "").trim();
      const aria = el.getAttribute("aria-label") || "";

      // Like count — "1234 赞" pattern
      if (aria.includes("赞") && !aria.includes("收藏") && !aria.includes("评论")) {
        const num = parseInt(aria.replace(/[^0-9]/g, ""));
        if (!isNaN(num) && data.like_count === null) data.like_count = num;
      }
      // Comment count
      if (aria.includes("评论") && !aria.includes("回复")) {
        const num = parseInt(aria.replace(/[^0-9]/g, ""));
        if (!isNaN(num) && data.comment_count === null) data.comment_count = num;
      }
      // Share count
      if (aria.includes("分享")) {
        const num = parseInt(aria.replace(/[^0-9]/g, ""));
        if (!isNaN(num) && data.share_count === null) data.share_count = num;
      }
      // Favorite/Collect count
      if (aria.includes("收藏")) {
        const num = parseInt(aria.replace(/[^0-9]/g, ""));
        if (!isNaN(num) && data.favorite_count === null) data.favorite_count = num;
      }
    }

    // ── Author info ──
    // Try meta tags
    const authorMeta = document.querySelector('meta[name="author"]');
    if (authorMeta) data.author_name = authorMeta.getAttribute("content");

    // Author name — typical douyin author link
    const authorLinks = document.querySelectorAll(
      'a[href*="/user/" i], [data-e2e="video-author-name"]'
    );
    for (const a of authorLinks) {
      const name = a.textContent?.trim();
      if (name && name.length > 1 && name.length < 50) {
        data.author_name = name;
        // Extract author ID from href
        const href = a.getAttribute("href") || "";
        const uidMatch = href.match(/\/user\/([a-zA-Z0-9_-]+)/i);
        if (uidMatch) data.author_id = uidMatch[1];
        break;
      }
    }

    // Follower count — look for "粉丝" pattern near author elements
    const fanPatterns = document.body.innerText.match(/([0-9.]+万?)\s*粉丝/);
    if (fanPatterns && data.follower_count === null) {
      data.follower_count = parseChineseNumber(fanPatterns[1]);
    }
  }

  // ── 快手提取 ──

  function extractKuaishou() {
    const data = {
      url: window.location.href,
      platform: "kuaishou",
      short_url: null,
      video_title: null,
      video_description: null,
      hashtags: [],
      publish_time: null,
      duration: null,
      cover_url: null,
      author_name: null,
      author_id: null,
      follower_count: null,
      verified: false,
      verification_text: null,
      bio: null,
      like_count: null,
      comment_count: null,
      share_count: null,
      favorite_count: null,
      view_count: null,
      comments: [],
    };

    // ── Title ──
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) data.video_title = ogTitle.getAttribute("content");

    if (!data.video_title && document.title) {
      data.video_title = document.title.replace(/\s*[-–—]\s*快手.*$/, "").trim();
    }

    // ── Description ──
    const ogDesc = document.querySelector('meta[property="og:description"]') ||
                   document.querySelector('meta[name="description"]');
    if (ogDesc) data.video_description = ogDesc.getAttribute("content");

    // ── Cover ──
    const ogImg = document.querySelector('meta[property="og:image"]');
    if (ogImg) data.cover_url = ogImg.getAttribute("content");

    // ── Extract video ID from URL ──
    const shortMatch = location.href.match(/\/f\/([A-Za-z0-9_-]+)/);
    if (shortMatch) data.platform_video_id = shortMatch[1];
    const normalMatch = location.href.match(/\/short-video\/([A-Za-z0-9_-]+)/);
    if (normalMatch) data.platform_video_id = normalMatch[1];
    const photoMatch = location.href.match(/\/photo\/([A-Za-z0-9_-]+)/);
    if (photoMatch) data.platform_video_id = photoMatch[1];

    // ── Interaction numbers ──
    // Kuaishou uses aria-labels on action buttons
    const allEls = document.body.querySelectorAll("*");
    for (const el of allEls) {
      const aria = el.getAttribute("aria-label") || "";
      const text = (el.textContent || "").trim();

      // Like
      if (aria.includes("赞") && !aria.includes("收藏")) {
        const num = parseInt(aria.replace(/[^0-9]/g, ""));
        if (!isNaN(num) && data.like_count === null) data.like_count = num;
      }
      // Comment
      if (aria.includes("评论") || aria.includes("条评论")) {
        const num = parseInt(aria.replace(/[^0-9]/g, ""));
        if (!isNaN(num) && data.comment_count === null) data.comment_count = num;
      }
      // Share
      if (aria.includes("分享")) {
        const num = parseInt(aria.replace(/[^0-9]/g, ""));
        if (!isNaN(num) && data.share_count === null) data.share_count = num;
      }
    }

    // ── Author name ──
    const authorSelectors = [
      '[class*="author" i]',
      '[class*="profile" i]',
      '[class*="user" i]',
      'a[href*="/profile/" i]',
    ];
    for (const sel of authorSelectors) {
      const el = document.querySelector(sel);
      if (el) {
        const text = el.textContent?.trim();
        if (text && text.length > 1 && text.length < 40 && !/赞|评论|分享|关注/.test(text)) {
          data.author_name = text;
          break;
        }
      }
    }

    // ── Follower count ──
    const fanMatch = document.body.innerText.match(/([0-9.]+万?)\s*粉丝/);
    if (fanMatch && data.follower_count === null) {
      data.follower_count = parseChineseNumber(fanMatch[1]);
    }

    // ── View count ──
    // Kuaishou play count often in page text: "播放" pattern
    const playMatch = document.body.innerText.match(/([0-9.]+万?)\s*(播放|次播放)/);
    if (playMatch && data.view_count === null) {
      data.view_count = parseChineseNumber(playMatch[1]);
    }

    return data;
  }

  // ── Utilities ──

  function parseChineseNumber(str) {
    if (!str) return null;
    str = str.trim();
    if (str.endsWith("万")) {
      const n = parseFloat(str.replace("万", ""));
      return isNaN(n) ? null : Math.round(n * 10000);
    }
    const n = parseFloat(str.replace(/,/g, ""));
    return isNaN(n) ? null : Math.round(n);
  }

  // ── Execute extraction ──

  const extracted = isDouyin ? extractDouyin() : extractKuaishou();

  // Send to popup via storage
  chrome.runtime.sendMessage({
    type: "EXTRACTED_DATA",
    data: extracted,
  }).catch(() => {
    // Popup might not be open — store for later
    chrome.storage.local.set({ lastExtracted: extracted });
  });

  // Also store in session storage for popup to read
  sessionStorage.setItem("__dyks_data", JSON.stringify(extracted));

  console.log("[DYKS] 数据提取完成:", extracted);
  console.log("[DYKS] 提取时间:", new Date().toLocaleString());
  console.log("[DYKS] 点击工具栏图标打开面板，发送到数据管理工具");
})();
