(function () {
  "use strict";

  var tooltip = document.getElementById("word-tooltip");
  var panel = document.getElementById("word-panel");
  var overlay = document.getElementById("panel-overlay");
  var frame = document.getElementById("panel-frame");
  var panelTitle = document.getElementById("panel-title");
  var panelNewTab = document.getElementById("panel-newtab");
  var cheatBtn = document.getElementById("cheatsheet-btn");
  var cheatPanel = document.getElementById("cheatsheet-panel");
  var translationToggle = document.getElementById("translation-toggle");

  function closestWord(el) {
    while (el && el !== document.body) {
      if (el.classList && el.classList.contains("w")) return el;
      el = el.parentNode;
    }
    return null;
  }

  // ---- Hover tooltip (lemma + short English gloss + parse tag) ----

  function showTooltip(el) {
    var lemma = el.dataset.lemma;
    if (!lemma) {
      tooltip.hidden = true;
      return;
    }
    var gloss = el.dataset.gloss;
    var tag = el.dataset.tag;
    var html = "<strong>" + lemma + "</strong>";
    if (gloss) html += " &mdash; " + gloss;
    if (tag) html += '<span class="tt-tag">' + tag + "</span>";
    tooltip.innerHTML = html;
    tooltip.hidden = false;

    var rect = el.getBoundingClientRect();
    var top = rect.top + window.scrollY - tooltip.offsetHeight - 10;
    if (top < window.scrollY + 4) top = rect.bottom + window.scrollY + 10;
    var left = rect.left + window.scrollX + rect.width / 2 - tooltip.offsetWidth / 2;
    left = Math.max(8, Math.min(left, document.documentElement.scrollWidth - tooltip.offsetWidth - 8));
    tooltip.style.top = top + "px";
    tooltip.style.left = left + "px";
  }

  function hideTooltip() {
    tooltip.hidden = true;
  }

  document.addEventListener("mouseover", function (e) {
    var el = closestWord(e.target);
    if (el) showTooltip(el);
  });
  document.addEventListener("mouseout", function (e) {
    var el = closestWord(e.target);
    if (el) hideTooltip();
  });
  document.addEventListener("focusin", function (e) {
    var el = closestWord(e.target);
    if (el) showTooltip(el);
  });
  document.addEventListener("focusout", function (e) {
    var el = closestWord(e.target);
    if (el) hideTooltip();
  });

  // ---- In-page lookup panel (Logeion in an iframe, no new tab) ----

  function openPanel(el) {
    var href = el.getAttribute("href");
    var label = el.dataset.lemma || el.dataset.word || "";
    frame.src = href;
    panelTitle.textContent = label;
    panelNewTab.href = href;
    panel.hidden = false;
    overlay.hidden = false;
    document.body.classList.add("panel-open");
  }

  function closePanel() {
    panel.hidden = true;
    overlay.hidden = true;
    frame.src = "about:blank";
    document.body.classList.remove("panel-open");
  }

  document.addEventListener("click", function (e) {
    var wordEl = closestWord(e.target);
    if (wordEl) {
      e.preventDefault();
      hideTooltip();
      openPanel(wordEl);
      return;
    }
    if (e.target.id === "panel-close" || e.target === overlay) {
      closePanel();
    }
    if (e.target.id === "cheatsheet-btn") {
      cheatPanel.hidden = !cheatPanel.hidden;
    }
    if (e.target.id === "cheatsheet-close") {
      cheatPanel.hidden = true;
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (panel && !panel.hidden) closePanel();
    if (cheatPanel && !cheatPanel.hidden) cheatPanel.hidden = true;
  });

  // ---- English translation toggle (remembered across books) ----

  function applyTranslationVisibility(visible) {
    document.body.classList.toggle("hide-translation", !visible);
    if (translationToggle) {
      translationToggle.textContent = visible ? "Hide translation" : "Show translation";
      translationToggle.setAttribute("aria-pressed", String(visible));
    }
  }

  if (translationToggle) {
    var stored = null;
    try {
      stored = localStorage.getItem("confessions.showTranslation");
    } catch (e) {
      /* private browsing / storage blocked -- default to visible */
    }
    applyTranslationVisibility(stored !== "false");

    translationToggle.addEventListener("click", function () {
      var nowVisible = document.body.classList.contains("hide-translation");
      applyTranslationVisibility(nowVisible);
      try {
        localStorage.setItem("confessions.showTranslation", String(nowVisible));
      } catch (e) {
        /* ignore */
      }
    });
  }
})();
