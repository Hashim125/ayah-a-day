(() => {
  "use strict";
  const BOOKMARK_KEY = "ayah-bookmarks";
  const THEME_KEY = "ayah-theme";
  const FONT_KEY = "ayah-arabic-size";

  function readBookmarks() {
    try {
      const value = JSON.parse(localStorage.getItem(BOOKMARK_KEY) || "[]");
      return Array.isArray(value) ? [...new Set(value.filter(v => /^\d{1,3}:\d{1,3}$/.test(v)))] : [];
    } catch (_) { return []; }
  }
  function writeBookmarks(items) { localStorage.setItem(BOOKMARK_KEY, JSON.stringify([...new Set(items)])); }
  function toast(message) {
    const node = document.querySelector(".toast");
    if (!node) return;
    node.textContent = message; node.hidden = false;
    window.clearTimeout(toast.timer); toast.timer = window.setTimeout(() => { node.hidden = true; }, 2600);
  }
  function updateBookmarkButtons() {
    const saved = new Set(readBookmarks());
    document.querySelectorAll("[data-bookmark]").forEach(button => {
      const active = saved.has(button.dataset.bookmark);
      button.setAttribute("aria-pressed", String(active));
      const icon = button.querySelector("span"); if (icon) icon.textContent = active ? "★" : "☆";
    });
  }
  function toggleBookmark(key) {
    const saved = readBookmarks(); const index = saved.indexOf(key);
    if (index < 0) { saved.push(key); toast("Verse saved"); } else { saved.splice(index, 1); toast("Verse removed"); }
    writeBookmarks(saved); updateBookmarkButtons(); return index >= 0;
  }
  async function copyLink(key) {
    const url = `${location.origin}/verse/${key}`;
    try { await navigator.clipboard.writeText(url); } catch (_) {
      const field = document.createElement("textarea"); field.value = url; document.body.append(field); field.select(); document.execCommand("copy"); field.remove();
    }
    toast("Link copied");
  }
  async function shareVerse(key) {
    const response = await fetch(`/api/verse/${encodeURIComponent(key)}?include_tafsir=0`);
    if (!response.ok) { toast("Could not load sharing details"); return; }
    const verse = await response.json();
    const data = {title: `Quran ${key}`, text: `${verse.clean_ayah_text}\n\n“${verse.translation_text}”`, url: `${location.origin}/verse/${key}`};
    if (navigator.share) { try { await navigator.share(data); return; } catch (error) { if (error.name === "AbortError") return; } }
    const message = encodeURIComponent(`${data.text}\n\n${data.url}`);
    window.open(`https://wa.me/?text=${message}`, "_blank", "noopener,noreferrer");
  }
  async function shareProvider(key, provider) {
    const response = await fetch(`/api/verse/${encodeURIComponent(key)}?include_tafsir=0`);
    if (!response.ok) return toast("Could not load sharing details");
    const verse = await response.json(); const link = `${location.origin}/verse/${key}`;
    const message = encodeURIComponent(`${verse.translation_text} — Quran ${key}\n${link}`);
    const url = provider === "x" ? `https://twitter.com/intent/tweet?text=${message}` : `https://wa.me/?text=${message}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }
  function wrappedLines(context, text, width) {
    const words=text.split(/\s+/); const lines=[]; let line="";
    words.forEach(word=>{const candidate=line?`${line} ${word}`:word;if(context.measureText(candidate).width>width&&line){lines.push(line);line=word;}else line=candidate;});
    if(line) lines.push(line); return lines;
  }
  async function downloadImageCard(key) {
    const response=await fetch(`/api/verse/${encodeURIComponent(key)}?include_tafsir=0`); if(!response.ok)return toast("Could not create image"); const verse=await response.json();
    await document.fonts.ready; const image=new Image(); image.src="/static/mosque-share.jpg"; await image.decode();
    const canvas=document.createElement("canvas"); canvas.width=1080; canvas.height=1350; const ctx=canvas.getContext("2d");
    const scale=Math.max(canvas.width/image.width,canvas.height/image.height); const width=image.width*scale,height=image.height*scale; ctx.drawImage(image,(canvas.width-width)/2,(canvas.height-height)/2,width,height);
    ctx.fillStyle="rgba(11,31,26,.72)";ctx.fillRect(0,0,canvas.width,canvas.height);ctx.fillStyle="rgba(255,253,248,.94)";ctx.fillRect(75,110,930,1130);ctx.textAlign="center";ctx.fillStyle="#173f35";ctx.font="700 28px Georgia";ctx.fillText(`${verse.surah_name} · ${key}`,540,180);
    ctx.direction="rtl";ctx.font="400 52px Amiri";const arabic=wrappedLines(ctx,verse.clean_ayah_text,790);arabic.slice(0,7).forEach((line,i)=>ctx.fillText(line,540,300+i*78));
    const dividerY=350+Math.min(arabic.length,7)*78;ctx.direction="ltr";ctx.strokeStyle="#aa7d35";ctx.beginPath();ctx.moveTo(440,dividerY);ctx.lineTo(640,dividerY);ctx.stroke();ctx.font="34px Georgia";ctx.fillStyle="#26352f";const translation=wrappedLines(ctx,`“${verse.translation_text}”`,790);translation.slice(0,8).forEach((line,i)=>ctx.fillText(line,540,dividerY+80+i*52));ctx.font="22px Georgia";ctx.fillStyle="#aa7d35";ctx.fillText("AYAH · A QUIET DAILY PAUSE",540,1170);
    canvas.toBlob(blob=>{const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=`quran-${key.replace(":","-")}.png`;link.click();URL.revokeObjectURL(url);toast("Verse image downloaded");},"image/png");
  }
  function setupTheme() {
    const root = document.documentElement; const stored = localStorage.getItem(THEME_KEY) || "system";
    root.dataset.theme = stored;
    document.querySelector("[data-theme-toggle]")?.addEventListener("click", () => {
      const next = root.dataset.theme === "system" ? "light" : root.dataset.theme === "light" ? "dark" : "system";
      root.dataset.theme = next; localStorage.setItem(THEME_KEY, next); toast(`Theme: ${next}`);
    });
  }
  function setupFontSize() {
    const select = document.querySelector("[data-font-size]"); if (!select) return;
    const sizes = {small:"clamp(1.85rem,4.8vw,3.25rem)",medium:"clamp(2.15rem,5.6vw,4rem)",large:"clamp(2.6rem,6.5vw,4.7rem)"};
    const saved = localStorage.getItem(FONT_KEY) || "medium"; select.value = saved; document.documentElement.style.setProperty("--arabic-size", sizes[saved]);
    select.addEventListener("change", () => { localStorage.setItem(FONT_KEY, select.value); document.documentElement.style.setProperty("--arabic-size", sizes[select.value]); });
  }
  function setupAccordions() {
    document.querySelectorAll(".result-summary").forEach(button => button.addEventListener("click", () => {
      const detail = document.getElementById(button.getAttribute("aria-controls")); const open = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", String(!open)); detail.hidden = open;
    }));
  }
  function setDisclosure(button, target, expanded, labels) {
    button.setAttribute("aria-expanded", String(expanded)); target.hidden = !expanded;
    const text = button.firstChild; if (text) text.nodeValue = `${expanded ? labels[1] : labels[0]} `;
  }
  function setupDisclosures() {
    const tafsirButton=document.querySelector("[data-tafsir-toggle]"); const preview=document.querySelector("[data-tafsir-preview]");
    if(tafsirButton&&preview){
      if(preview.scrollHeight<=preview.clientHeight+2){tafsirButton.closest(".disclosure-row").hidden=true;preview.classList.add("is-expanded");}
      else tafsirButton.addEventListener("click",()=>{const expanded=tafsirButton.getAttribute("aria-expanded")==="true";tafsirButton.setAttribute("aria-expanded",String(!expanded));preview.classList.toggle("is-expanded",!expanded);const text=tafsirButton.firstChild;if(text)text.nodeValue=`${expanded?"Read full Tafsir":"Show less"} `;});
    }
    const contextButton=document.querySelector("[data-context-toggle]"); const context=document.getElementById("nearby-verses");
    if(contextButton&&context)contextButton.addEventListener("click",()=>setDisclosure(contextButton,context,contextButton.getAttribute("aria-expanded")!=="true",["Show nearby ayahs","Hide nearby ayahs"]));
  }
  function setupShareMenu() {
    const trigger=document.querySelector(".share-more"); const menu=document.querySelector(".share-menu"); if(!trigger||!menu)return;
    const close=(focus=false)=>{trigger.setAttribute("aria-expanded","false");menu.hidden=true;if(focus)trigger.focus();};
    trigger.addEventListener("click",()=>{const open=trigger.getAttribute("aria-expanded")!=="true";trigger.setAttribute("aria-expanded",String(open));menu.hidden=!open;if(open)menu.querySelector("button")?.focus();});
    menu.addEventListener("click",()=>close());
    document.addEventListener("click",event=>{if(!event.target.closest(".share-menu-wrap"))close();});
    document.addEventListener("keydown",event=>{if(event.key==="Escape"&&!menu.hidden){event.preventDefault();close(true);}});
  }
  async function renderBookmarks() {
    const container = document.getElementById("bookmarks-container"); const template = document.getElementById("bookmark-template");
    if (!container || !template) return;
    const keys = readBookmarks(); container.replaceChildren();
    if (!keys.length) { const empty = document.createElement("div"); empty.className="empty-state"; const title=document.createElement("h2"); title.textContent="No saved verses yet"; const text=document.createElement("p"); text.textContent="Use the Save button on any verse to keep it here."; empty.append(title,text); container.append(empty); return; }
    const verses = await Promise.all(keys.map(key => fetch(`/api/verse/${encodeURIComponent(key)}`).then(r => r.ok ? r.json() : null).catch(() => null)));
    verses.filter(Boolean).forEach(verse => {
      const card = template.content.cloneNode(true); card.querySelector("[data-surah]").textContent = verse.surah_name; const link=card.querySelector("[data-link]"); link.textContent=verse.verse_key; link.href=`/verse/${verse.verse_key}`; card.querySelector("[data-arabic]").textContent=verse.clean_ayah_text; card.querySelector("[data-translation]").textContent=verse.translation_text; card.querySelector("[data-remove]").addEventListener("click",()=>{toggleBookmark(verse.verse_key);renderBookmarks();}); container.append(card);
    });
  }
  function exportBookmarks() {
    const data={version:1,exported_at:new Date().toISOString(),verse_keys:readBookmarks()}; const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"})); const link=document.createElement("a"); link.href=url; link.download="ayah-bookmarks.json"; link.click(); URL.revokeObjectURL(url);
  }
  async function importBookmarks(file, replace=false) {
    try { const data=JSON.parse(await file.text()); if(data.version!==1||!Array.isArray(data.verse_keys)) throw new Error(); const valid=data.verse_keys.filter(v=>/^\d{1,3}:\d{1,3}$/.test(v)); if(replace&&!confirm("Replace all current bookmarks with this file?"))return; writeBookmarks(replace?valid:[...readBookmarks(),...valid]); toast(`${valid.length} bookmarks imported`); renderBookmarks(); } catch(_){ toast("That bookmark file is not valid"); }
  }
  document.addEventListener("DOMContentLoaded", () => {
    setupTheme(); setupFontSize(); setupAccordions(); setupDisclosures(); setupShareMenu(); updateBookmarkButtons(); renderBookmarks();
    document.addEventListener("click", event => { const bookmark=event.target.closest("[data-bookmark]"); if(bookmark) toggleBookmark(bookmark.dataset.bookmark); const copy=event.target.closest("[data-copy]"); if(copy) copyLink(copy.dataset.copy); const share=event.target.closest("[data-share]"); if(share) shareVerse(share.dataset.share); const wa=event.target.closest("[data-share-whatsapp]");if(wa)shareProvider(wa.dataset.shareWhatsapp,"whatsapp");const x=event.target.closest("[data-share-x]");if(x)shareProvider(x.dataset.shareX,"x");const card=event.target.closest("[data-image-card]");if(card)downloadImageCard(card.dataset.imageCard); });
    document.querySelector("[data-export-bookmarks]")?.addEventListener("click",exportBookmarks);
    document.querySelector("[data-import-bookmarks]")?.addEventListener("change",event=>{if(event.target.files[0]) importBookmarks(event.target.files[0]);});
    document.querySelector("[data-replace-bookmarks]")?.addEventListener("change",event=>{if(event.target.files[0]) importBookmarks(event.target.files[0],true);});
    document.querySelector("[data-clear-bookmarks]")?.addEventListener("click",()=>{if(confirm("Remove all saved verses from this browser?")){writeBookmarks([]);renderBookmarks();toast("Bookmarks cleared");}});
  });
})();
