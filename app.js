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
  var sectionJump = document.getElementById("section-jump");
  var backToTop = document.getElementById("back-to-top");

  // Devices with a real hovering pointer (mouse/trackpad) get the preview
  // tooltip on hover and a single click opens the dictionary panel
  // straight away. Touch devices have no hover at all, so the first tap
  // has to do the tooltip's job -- see the click handler below.
  var hasHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  function closestWord(el) {
    while (el && el !== document.body) {
      if (el.classList && el.classList.contains("w")) return el;
      el = el.parentNode;
    }
    return null;
  }

  // ---- Tooltip (lemma + short English gloss + parse tag) ----
  // On hover-capable devices it's a transient preview. On touch, tapping a
  // word pins it open (with an explicit "open" affordance) instead of
  // jumping straight to the panel.

  var pinnedWord = null;

  function tooltipHTML(el, pinned) {
    var lemma = el.dataset.lemma;
    if (!lemma) return "";
    var gloss = el.dataset.gloss;
    var tag = el.dataset.tag;
    var out = "<strong>" + lemma + "</strong>";
    if (gloss) out += " &mdash; " + gloss;
    if (tag) out += '<span class="tt-tag">' + tag + "</span>";
    if (pinned) out += '<button type="button" class="tt-open">Open full entry &#8599;</button>';
    return out;
  }

  function positionTooltip(el) {
    var rect = el.getBoundingClientRect();
    var top = rect.top + window.scrollY - tooltip.offsetHeight - 10;
    if (top < window.scrollY + 4) top = rect.bottom + window.scrollY + 10;
    var left = rect.left + window.scrollX + rect.width / 2 - tooltip.offsetWidth / 2;
    left = Math.max(8, Math.min(left, document.documentElement.scrollWidth - tooltip.offsetWidth - 8));
    tooltip.style.top = top + "px";
    tooltip.style.left = left + "px";
  }

  function showTooltip(el) {
    var html = tooltipHTML(el, false);
    if (!html) {
      tooltip.hidden = true;
      return;
    }
    tooltip.innerHTML = html;
    tooltip.hidden = false;
    tooltip.classList.remove("pinned");
    positionTooltip(el);
  }

  function pinTooltip(el) {
    var html = tooltipHTML(el, true);
    if (!html) return;
    pinnedWord = el;
    tooltip.innerHTML = html;
    tooltip.hidden = false;
    tooltip.classList.add("pinned");
    positionTooltip(el);
  }

  function hideTooltip() {
    tooltip.hidden = true;
    tooltip.classList.remove("pinned");
    pinnedWord = null;
  }

  if (hasHover) {
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
  }

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
    frame.src = "about:blank";
    document.body.classList.remove("panel-open");
    if (cheatPanel.hidden) overlay.hidden = true;
  }

  function openCheatsheet() {
    cheatPanel.hidden = false;
    overlay.hidden = false;
  }

  function closeCheatsheet() {
    cheatPanel.hidden = true;
    if (panel.hidden) overlay.hidden = true;
  }

  document.addEventListener("click", function (e) {
    var wordEl = closestWord(e.target);

    if (e.target.classList && e.target.classList.contains("tt-open") && pinnedWord) {
      hideTooltip();
      openPanel(pinnedWord);
      return;
    }

    if (wordEl) {
      e.preventDefault();
      if (hasHover) {
        hideTooltip();
        openPanel(wordEl);
      } else if (pinnedWord === wordEl) {
        // second tap on the same word -> go straight to the entry
        hideTooltip();
        openPanel(wordEl);
      } else {
        pinTooltip(wordEl);
      }
      return;
    }

    if (!hasHover && pinnedWord && e.target !== tooltip && !tooltip.contains(e.target)) {
      hideTooltip();
    }

    if (e.target.id === "panel-close" || e.target === overlay) {
      closePanel();
      closeCheatsheet();
    }
    if (e.target.id === "cheatsheet-btn") {
      if (cheatPanel.hidden) openCheatsheet();
      else closeCheatsheet();
    }
    if (e.target.id === "cheatsheet-close") {
      closeCheatsheet();
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (panel && !panel.hidden) closePanel();
    if (cheatPanel && !cheatPanel.hidden) closeCheatsheet();
    if (!hasHover) hideTooltip();
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

  // ---- Jump to chapter (navigates to that chapter's page) ----

  if (sectionJump) {
    sectionJump.addEventListener("change", function () {
      var target = sectionJump.value;
      if (!target) return;
      window.location.href = target;
    });
  }

  // ---- Back to top ----

  if (backToTop) {
    window.addEventListener(
      "scroll",
      function () {
        backToTop.hidden = window.scrollY < 600;
      },
      { passive: true }
    );
    backToTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
})();
