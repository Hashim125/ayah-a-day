(() => {
  "use strict";
  const body = document.body;

  function showHijriDate() {
    const node = document.querySelector("[data-hijri-date]");
    if (!node) return;
    // Use the mosque's timezone, plus its moon-sighting adjustment, not the TV's own clock settings.
    const offsetDays = Number(body.dataset.hijriOffset) || 0;
    const date = new Date(Date.now() + offsetDays * 86400000);
    try {
      const hijri = new Intl.DateTimeFormat("en-GB-u-ca-islamic-umalqura", {day: "numeric", month: "long", year: "numeric", timeZone: body.dataset.timezone}).format(date);
      node.textContent = ` · ${hijri}`;
    } catch (_) { /* Older TV browsers may not support the Islamic calendar. */ }
  }

  // Shrink the verse until it fits the screen; long ayahs such as 2:282 need several steps.
  function fitVerse() {
    const box = document.querySelector("[data-fit]");
    if (!box) return;
    const arabic = box.querySelector(".arabic");
    const translation = box.querySelector(".translation");
    if (!arabic) return;
    arabic.style.fontSize = ""; if (translation) translation.style.fontSize = "";
    let arabicSize = parseFloat(getComputedStyle(arabic).fontSize);
    let translationSize = translation ? parseFloat(getComputedStyle(translation).fontSize) : 0;
    for (let step = 0; step < 40 && box.scrollHeight > box.clientHeight + 1; step++) {
      arabicSize *= 0.93; arabic.style.fontSize = `${arabicSize}px`;
      if (translation && step % 2) { translationSize *= 0.95; translation.style.fontSize = `${translationSize}px`; }
    }
  }

  let wakeLock = null;
  async function keepAwake() {
    if (!("wakeLock" in navigator) || document.visibilityState !== "visible") return;
    try { wakeLock = await navigator.wakeLock.request("screen"); } catch (_) { wakeLock = null; }
  }

  // Reload after local midnight, but only once the server answers, so the TV never lands on an error page.
  async function reloadWhenReady() {
    try {
      const response = await fetch(body.dataset.healthUrl, {cache: "no-store"});
      if (response.ok) { location.reload(); return; }
    } catch (_) { /* Network down: try again shortly. */ }
    window.setTimeout(reloadWhenReady, 60000);
  }

  document.addEventListener("DOMContentLoaded", () => {
    showHijriDate();
    (document.fonts ? document.fonts.ready : Promise.resolve()).then(fitVerse);
    window.addEventListener("resize", fitVerse);
    keepAwake();
    document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && !wakeLock) keepAwake(); });
    const seconds = Number(body.dataset.reloadSeconds) || 3600;
    window.setTimeout(reloadWhenReady, Math.max(60, seconds) * 1000);
  });
})();
