/*!
 * ACIP widget loader — the single line a store drops into its site.
 *
 *   <script src="https://api.acip.example/widget/v1.js"
 *           data-acip-key="acip_xxx"
 *           data-acip-base="https://api.acip.example"
 *           async></script>
 *
 * Self-contained, framework-free, no build step. Reads its own data-* config,
 * fetches the store's published widget config, then mounts a floating launcher
 * with hybrid search + grounded chat. Talks only to the public API
 * (/v1/search, /v1/chat) with a shopper-scoped (least-privilege) key.
 */
(function () {
  "use strict";
  if (window.__acipWidgetLoaded) return;
  window.__acipWidgetLoaded = true;

  var script =
    document.currentScript ||
    (function () {
      var s = document.getElementsByTagName("script");
      return s[s.length - 1];
    })();

  var KEY = script.getAttribute("data-acip-key") || "";
  var BASE = (
    script.getAttribute("data-acip-base") ||
    script.src.replace(/\/widget\/v1\.js.*$/, "")
  ).replace(/\/$/, "");

  if (!KEY) {
    console.error("[acip] missing data-acip-key");
    return;
  }

  var CFG = {
    primary_color: script.getAttribute("data-acip-color") || "#1A7A4B",
    position: script.getAttribute("data-acip-position") || "bottom-right",
    chat_enabled: script.getAttribute("data-acip-chat") !== "false",
    search_enabled: script.getAttribute("data-acip-search") !== "false",
    greeting:
      script.getAttribute("data-acip-greeting") ||
      "سلام! چطور می‌تونم در پیدا کردن محصول کمکتون کنم؟",
    placeholder: script.getAttribute("data-acip-placeholder") || "جستجو در فروشگاه…",
    logo_url: script.getAttribute("data-acip-logo") || "",
    title: script.getAttribute("data-acip-title") || "دستیار خرید",
  };

  // Pull the store's published widget config so dashboard settings win over
  // the inline data-* defaults (best-effort; never blocks the widget).
  function loadConfig(done) {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", BASE + "/v1/widget/config", true);
      xhr.setRequestHeader("x-api-key", KEY);
      xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) return;
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            var remote = JSON.parse(xhr.responseText) || {};
            for (var k in remote) {
              if (remote[k] !== null && remote[k] !== undefined && remote[k] !== "") {
                CFG[k] = remote[k];
              }
            }
          } catch (e) {}
        }
        done();
      };
      xhr.send();
    } catch (e) {
      done();
    }
  }

  function api(path, body, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", BASE + path, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.setRequestHeader("x-api-key", KEY);
    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) return;
      var data = {};
      try {
        data = JSON.parse(xhr.responseText);
      } catch (e) {}
      cb(xhr.status >= 200 && xhr.status < 300, data);
    };
    xhr.send(JSON.stringify(body));
  }

  function el(tag, css, text) {
    var n = document.createElement(tag);
    if (css) n.setAttribute("style", css);
    if (text != null) n.textContent = text;
    return n;
  }

  function mount() {
    var color = CFG.primary_color;
    var rtl = "direction:rtl;text-align:right;";
    var side = CFG.position === "bottom-left" ? "left:20px;" : "right:20px;";
    var sessionId;

    // Floating launcher button.
    var launcher = el(
      "button",
      "position:fixed;bottom:20px;" +
        side +
        "z-index:2147483000;width:56px;height:56px;border-radius:50%;border:none;" +
        "cursor:pointer;color:#fff;font-size:24px;box-shadow:0 6px 20px rgba(0,0,0,.25);" +
        "background:" +
        color +
        ";"
    );
    launcher.setAttribute("aria-label", CFG.title);
    launcher.innerHTML = "&#128172;";

    // Panel.
    var panel = el(
      "div",
      "position:fixed;bottom:88px;" +
        side +
        "z-index:2147483000;width:360px;max-width:calc(100vw - 32px);height:520px;" +
        "max-height:calc(100vh - 120px);background:#fff;color:#111;border-radius:14px;" +
        "box-shadow:0 12px 40px rgba(0,0,0,.3);display:none;flex-direction:column;overflow:hidden;" +
        "font-family:system-ui,-apple-system,'Segoe UI',Tahoma,sans-serif;" +
        rtl
    );

    var header = el(
      "div",
      "padding:12px 14px;color:#fff;display:flex;align-items:center;gap:8px;background:" + color + ";"
    );
    if (CFG.logo_url) {
      var logo = el("img", "height:22px;border-radius:4px;");
      logo.src = CFG.logo_url;
      header.appendChild(logo);
    }
    header.appendChild(el("strong", "font-size:15px;", CFG.title));

    var input = el(
      "input",
      "border:none;outline:none;width:100%;padding:12px 14px;font-size:14px;box-sizing:border-box;" +
        "border-bottom:1px solid #eee;" +
        rtl
    );
    input.type = "search";
    input.placeholder = CFG.placeholder;

    var body = el(
      "div",
      "flex:1;overflow-y:auto;padding:10px 14px;font-size:14px;line-height:1.6;"
    );

    panel.appendChild(header);
    if (CFG.search_enabled || CFG.chat_enabled) panel.appendChild(input);
    panel.appendChild(body);

    function addBubble(text, mine) {
      var b = el(
        "div",
        "margin:6px 0;padding:8px 12px;border-radius:12px;max-width:85%;white-space:pre-wrap;" +
          (mine
            ? "background:" + color + ";color:#fff;margin-inline-start:auto;"
            : "background:#f1f1f1;color:#111;")
      );
      b.textContent = text;
      body.appendChild(b);
      body.scrollTop = body.scrollHeight;
      return b;
    }

    function renderResults(results) {
      if (!results || !results.length) return;
      var list = el("div", "margin:6px 0;");
      results.slice(0, CFG.max_results || 8).forEach(function (r) {
        var card = el(
          "a",
          "display:block;padding:8px 10px;margin:4px 0;border:1px solid #eee;border-radius:10px;" +
            "text-decoration:none;color:#111;"
        );
        if (r.url) {
          card.href = r.url;
          card.target = "_blank";
        }
        card.appendChild(el("div", "font-weight:600;", r.title || r.product_id || ""));
        var meta = [];
        if (r.brand) meta.push(r.brand);
        if (r.price != null) meta.push(r.price);
        if (meta.length) card.appendChild(el("div", "color:#666;font-size:12px;", meta.join(" · ")));
        list.appendChild(card);
      });
      body.appendChild(list);
      body.scrollTop = body.scrollHeight;
    }

    function runSearch(q) {
      if (!CFG.search_enabled) return;
      api("/v1/search", { query: q }, function (ok, data) {
        if (ok) renderResults(data.results);
      });
    }

    function ask(q) {
      if (!CFG.chat_enabled) return;
      var typing = addBubble("…", false);
      api("/v1/chat", { message: q, session_id: sessionId }, function (ok, data) {
        body.removeChild(typing);
        if (!ok) {
          addBubble("متأسفم، در حال حاضر نمی‌تونم پاسخ بدم.", false);
          return;
        }
        sessionId = data.session_id || sessionId;
        addBubble(data.answer || "", false);
        if (data.citations && data.citations.length) renderResults(data.citations);
      });
    }

    var greeted = false;
    function openPanel() {
      panel.style.display = "flex";
      if (!greeted && CFG.chat_enabled) {
        addBubble(CFG.greeting, false);
        greeted = true;
      }
      input.focus();
    }

    launcher.addEventListener("click", function () {
      if (panel.style.display === "none") openPanel();
      else panel.style.display = "none";
    });

    input.addEventListener("keydown", function (e) {
      if (e.key !== "Enter") return;
      var q = input.value.trim();
      if (!q) return;
      if (CFG.chat_enabled) addBubble(q, true);
      input.value = "";
      runSearch(q);
      ask(q);
    });

    document.body.appendChild(launcher);
    document.body.appendChild(panel);
  }

  if (document.body) loadConfig(mount);
  else
    document.addEventListener("DOMContentLoaded", function () {
      loadConfig(mount);
    });
})();
