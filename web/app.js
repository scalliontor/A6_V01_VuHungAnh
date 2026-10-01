const state = { mode: "image", meta: null, recognition: null, listening: false, voiceResultReceived: false, voiceError: false };
const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
})[character]);

function setMode(mode) {
  if (state.listening && mode !== "voice") state.recognition.abort();
  state.mode = mode;
  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
    button.setAttribute("aria-selected", button.dataset.mode === mode ? "true" : "false");
  });
  $("textField").hidden = mode === "image";
  $("voiceControl").hidden = mode !== "voice";
  $("imageField").hidden = mode === "text" || mode === "voice";
  $("queryText").value = mode === "voice" ? "find tomato mushroom pasta sauce" : "Tomato Mushroom Pasta Sauce";
  $("textHint").textContent = mode === "voice"
    ? "The recognized words appear here. You can also type or edit the transcript."
    : "Searches product title, brand, and category text.";
  $("resultSummary").textContent = "Run the query to see the top five products.";
  $("queryInfo").innerHTML = "";
  $("sampleLabel").innerHTML = "";
  $("results").innerHTML = "";
  $("status").textContent = "";
}

function voiceStatus(message, error = false) {
  $("voiceStatus").textContent = message;
  $("voiceStatus").classList.toggle("error", error);
}

function updateMicrophoneButton() {
  const button = $("micButton");
  button.classList.toggle("listening", state.listening);
  button.setAttribute("aria-pressed", String(state.listening));
  button.innerHTML = state.listening
    ? '<span aria-hidden="true">■</span> Stop microphone'
    : '<span aria-hidden="true">🎙</span> Start microphone';
}

function setupMicrophone() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    $("micButton").disabled = true;
    voiceStatus("Microphone recognition is unavailable in this browser. You can type a transcript instead.", true);
    return;
  }
  const recognition = new Recognition();
  recognition.lang = "en-US";
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  state.recognition = recognition;
  recognition.onstart = () => {
    state.listening = true;
    updateMicrophoneButton();
    voiceStatus("Listening… speak an English product name.");
  };
  recognition.onresult = (event) => {
    let transcript = "";
    let hasFinal = false;
    for (let index = 0; index < event.results.length; index++) {
      const result = event.results[index];
      transcript += result[0].transcript;
      hasFinal ||= result.isFinal;
    }
    transcript = transcript.trim();
    if (transcript) $("queryText").value = transcript;
    if (hasFinal && transcript && !state.voiceResultReceived) {
      state.voiceResultReceived = true;
      voiceStatus(`Recognized: “${transcript}”. Searching now…`);
      if (state.mode === "voice") search();
    } else if (!hasFinal && transcript) {
      voiceStatus(`Hearing: “${transcript}”`);
    }
  };
  recognition.onerror = (event) => {
    state.voiceError = true;
    const messages = {
      "not-allowed": "Microphone access was denied. Allow access in the browser, or type a transcript.",
      "service-not-allowed": "Speech recognition was blocked by the browser. Type a transcript instead.",
      "no-speech": "No speech was heard. Try again or type a transcript.",
      "audio-capture": "No microphone is available. Check your device or type a transcript.",
      "network": "The browser's speech service is unavailable. Check the connection or type a transcript.",
    };
    voiceStatus(messages[event.error] || `Speech recognition failed (${event.error}). Type a transcript instead.`, true);
  };
  recognition.onend = () => {
    state.listening = false;
    updateMicrophoneButton();
    if (!state.voiceResultReceived && !state.voiceError) voiceStatus("Microphone stopped. Try again or type a transcript.");
  };
  $("micButton").addEventListener("click", () => {
    if (state.listening) {
      recognition.stop();
      return;
    }
    state.voiceResultReceived = false;
    state.voiceError = false;
    $("queryText").value = "";
    voiceStatus("Starting microphone…");
    try {
      recognition.start();
    } catch (error) {
      voiceStatus(`Could not start recognition: ${error.message}`, true);
    }
  });
}

function selectedSample() {
  return state.meta?.featured_queries.find((item) => item.id === $("sampleSelect").value);
}

function updatePreview() {
  const file = $("uploadImage").files[0];
  if (file) {
    $("queryPreview").src = URL.createObjectURL(file);
    $("previewName").textContent = file.name;
  } else {
    const sample = selectedSample();
    $("queryPreview").src = sample?.image || "";
    $("previewName").textContent = sample?.name || "Select a sample";
  }
}

function renderMeta(meta) {
  state.meta = meta;
  $("datasetStats").innerHTML = `<div><strong>${meta.product_count}</strong><span>catalog products</span></div><div><strong>${meta.query_count}</strong><span>other-view photos</span></div>`;
  $("sampleSelect").innerHTML = meta.featured_queries.map((item) =>
    `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("");
  $("labelGrid").innerHTML = [
    ["Product ID / barcode", "500 known identities; the same barcode is the image query's correct answer."],
    ["Product name", "A title is available for every selected product."],
    ["Brand", `${meta.brand_count} of ${meta.product_count} records have a brand.`],
    ["Broad category", `${meta.category_count} of ${meta.product_count} records have a usable broad category.`],
  ].map(([title, detail]) => `<div class="label-card"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></div>`).join("");
  $("categories").innerHTML = meta.categories.map((item) =>
    `<span>${escapeHtml(item.label)} · ${item.count}</span>`).join("");
  updatePreview();
}

async function fileDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Could not read the image"));
    reader.readAsDataURL(file);
  });
}

function renderResult(data) {
  $("status").textContent = "";
  $("status").className = "status";
  $("resultSummary").textContent = `${data.results.length} product${data.results.length === 1 ? "" : "s"} returned · sorted by ranking score`;
  const info = [`mode: ${data.mode}`, `input: ${data.query.raw}`];
  if (data.query.tokens?.length) info.push(`tokens: ${data.query.tokens.join(", ")}`);
  for (const key of ["category", "brand", "color", "max_price"]) {
    if (data.query[key] !== null && data.query[key] !== undefined) info.push(`${key}: ${data.query[key]}`);
  }
  $("queryInfo").innerHTML = info.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
  $("sampleLabel").innerHTML = "";
  if (data.sample_label) {
    const label = data.sample_label;
    const match = label.top1_match;
    $("sampleLabel").innerHTML = `<div class="sample-label ${match ? "" : "miss"}"><strong>Known label:</strong> ${escapeHtml(label.name)} · barcode ${escapeHtml(label.barcode)}<br><strong>Top result:</strong> ${match ? "Same product" : "Different product"} ${match ? "✓" : "· this is a real method error"}</div>`;
  }
  $("results").innerHTML = data.results.length ? data.results.map((item, index) =>
    `<article class="result"><span class="rank">${String(index + 1).padStart(2, "0")}</span><img src="${escapeHtml(item.image)}" alt=""><div><span class="product-name">${escapeHtml(item.name)}</span><span class="product-meta">${escapeHtml(item.brand || "Brand missing")} · ${escapeHtml(item.category || "Category missing")} · ${escapeHtml(item.id)}</span></div><div class="score"><strong>${item.score.toFixed(3)}</strong><small>score</small></div></article>`).join("") : `<p class="hint">No matching products. The Open Food Facts sample has no shop prices or color labels.</p>`;
}

async function search(event) {
  event?.preventDefault();
  const button = $("searchButton");
  button.disabled = true;
  $("status").className = "status";
  $("status").textContent = state.mode === "image" || state.mode === "multimodal"
    ? "Computing Apple Vision features and ranking photos…" : "Normalizing the query and ranking products…";
  try {
    const payload = { mode: state.mode, text: $("queryText").value };
    if (state.mode === "image" || state.mode === "multimodal") {
      const file = $("uploadImage").files[0];
      if (file) {
        if (file.size > 5_000_000) throw new Error("Image must be 5 MB or smaller");
        payload.upload = await fileDataURL(file);
      } else {
        payload.sample_id = $("sampleSelect").value;
      }
    }
    const response = await fetch("/api/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Search failed");
    renderResult(data);
  } catch (error) {
    $("status").textContent = error.message;
    $("status").className = "status error";
  } finally {
    button.disabled = false;
  }
}

document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.mode)));
$("sampleSelect").addEventListener("change", () => { $("uploadImage").value = ""; updatePreview(); });
$("uploadImage").addEventListener("change", updatePreview);
$("searchForm").addEventListener("submit", search);
setupMicrophone();
fetch("/api/meta").then((response) => response.json()).then((meta) => {
  renderMeta(meta);
  const requestedMode = new URLSearchParams(location.search).get("mode");
  setMode(["text", "voice", "image", "multimodal"].includes(requestedMode) ? requestedMode : "image");
  search();
}).catch((error) => {
  $("status").textContent = `Could not load dataset: ${error.message}`;
  $("status").className = "status error";
});
