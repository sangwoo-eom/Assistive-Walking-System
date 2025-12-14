// =======================
// Element Bindings
// =======================

const video = document.getElementById("camera");
const statusDiv = document.getElementById("status");
const objectsDiv = document.getElementById("objects");
const envDiv = document.getElementById("environment");
const alertDiv = document.getElementById("alert");
const resultImage = document.getElementById("resultImage");

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const objectBtn = document.getElementById("objectBtn");
const envBtn = document.getElementById("envBtn");
const envToggleBtn = document.getElementById("envToggleBtn");
const locationBtn = document.getElementById("locationBtn");
const voiceBtn = document.getElementById("voiceBtn");
const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");

const envSafeBtn = document.getElementById("envSafeBtn");
const envDangerBtn = document.getElementById("envDangerBtn");
const envBackBtn = document.getElementById("envBackBtn");

const locSummaryBtn = document.getElementById("locSummaryBtn");
const locAddressBtn = document.getElementById("locAddressBtn");
const locLandmarkBtn = document.getElementById("locLandmarkBtn");
const locFacilityBtn = document.getElementById("locFacilityBtn");
const locBackBtn = document.getElementById("locBackBtn");

const facilityMenu = document.getElementById("facilityMenu");
const facilityButtons = facilityMenu
  ? facilityMenu.querySelectorAll("button[data-category]")
  : [];
const facilityBackBtn = document.getElementById("facilityBackBtn");

const mainMenu = document.getElementById("mainMenu");
const envMenu = document.getElementById("envMenu");
const locationMenu = document.getElementById("locationMenu");

// Speech rate buttons
const slowBtn = document.getElementById("slowBtn");
const normalBtn = document.getElementById("normalBtn");
const fastBtn = document.getElementById("fastBtn");


// =======================
// State
// =======================

let uploadMode = false;
let latencyLog = [];
let stream = null;
let running = false;
let interval = null;

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

const API_URL = "/api/infer";
const INTERVAL_MS = 900;

// Location cache
let lastLocation = null;
let lastLocationTime = 0;
const LOCATION_CACHE_MS = 20000;

// Locks
let apiRequestLock = false;
let locationRequestLock = false;

// Environment state
let envMuted = false;
let currentEnvText = null;
let lastEnvWarnTime = 0;
let lastEnvDetectTime = 0;

// Environment timing rules
const ENV_REPEAT_IGNORE_MS = 30000;
const ENV_WARN_INTERVAL_MS = 12000;
const ENV_RELEASE_MS = 25000;

// TTS
let lastSpoken = "";
let lastSpeakTime = 0;
let speechRate = 1.1;


// =======================
// Latency Logging
// =======================

function recordLatency(tStart, tResponse, tSpeak, serverLatency) {
  const entry = {
    timestamp: new Date().toISOString(),
    e2e_ms: (tSpeak - tStart).toFixed(2),
    network_ms: (tResponse - tStart).toFixed(2),
    client_tts_ms: (tSpeak - tResponse).toFixed(2),
    server: serverLatency || null
  };

  latencyLog.push(entry);
  console.log("[LATENCY]", entry);
}


// =======================
// Network
// =======================

async function safeFetch(url, options) {
  try {
    return await fetch(url, options);
  } catch {
    speak("네트워크 연결이 불안정합니다.", "sys");
    return null;
  }
}


// =======================
// Speech Rate Control
// =======================

function setSpeechRate(delta) {
  speechRate = Math.max(0.7, Math.min(1.6, speechRate + delta));
  speak(`말하는 속도를 ${speechRate.toFixed(1)}배로 조정했습니다.`, "sys");
}

function resetSpeechRate() {
  speechRate = 1.1;
  speak("말하는 속도를 기본값으로 되돌렸습니다.", "sys");
}


// =======================
// Voice Recording
// =======================

async function startVoiceCommand() {
  try {
    const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(audioStream);
    audioChunks = [];
    isRecording = true;

    mediaRecorder.start();
    voiceBtn.innerText = "말하기 종료";

    mediaRecorder.ondataavailable = e => {
      if (e.data.size) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      audioStream.getTracks().forEach(t => t.stop());
      const blob = new Blob(audioChunks, { type: "audio/webm" });
      await sendVoiceToSTT(blob);
      isRecording = false;
      voiceBtn.innerText = "음성 명령";
    };
  } catch {
    speak("마이크 권한이 필요합니다.", "sys");
  }
}

function stopVoiceCommand() {
  if (mediaRecorder && isRecording) mediaRecorder.stop();
}


// =======================
// STT
// =======================

async function sendVoiceToSTT(blob) {
  const form = new FormData();
  form.append("file", blob);

  const res = await safeFetch("/api/stt", { method: "POST", body: form });
  if (!res) return;

  const data = await res.json();
  handleIntent(data.intent || "unknown");
}


// =======================
// Intent Router
// =======================

function handleIntent(intent) {
  switch (intent) {
    case "system_start": return startSystem();
    case "system_stop": return stopSystem();
    case "object_guide": return manualObjectGuide();

    case "env_danger": return fetchEnvDanger();
    case "env_safe": return fetchEnvSafe();
    case "env_menu": return openEnvMenu();

    case "env_alert_off":
      envMuted = true;
      envToggleBtn.innerText = "경고 켜기";
      return speak("경고가 해제되었습니다.", "sys");

    case "env_alert_on":
      envMuted = false;
      envToggleBtn.innerText = "경고 끄기";
      return speak("경고가 다시 시작됩니다.", "sys");

    case "location_menu": return openLocationMenu();
    case "location_summary": return fetchLocation("summary");
    case "location_address": return fetchLocation("address");
    case "location_landmark": return fetchLocation("landmark");
    case "location_facility": return openFacilityMenu();

    case "upload_image": return fileInput.click();
    case "repeat_last": return lastSpoken && speak(lastSpoken);

    case "tts_slower": return setSpeechRate(-0.1);
    case "tts_faster": return setSpeechRate(+0.1);
    case "tts_reset": return resetSpeechRate();

    case "ui_back": return showMenu("main");

    default:
      return speak("다시 말씀해 주세요.", "sys");
  }
}


// =======================
// Text-to-Speech
// =======================

function speak(text, type = "info") {
  if (!window.speechSynthesis || !text) return;

  const now = Date.now();
  if (lastSpoken === text && now - lastSpeakTime < 5000) return;

  lastSpeakTime = now;
  lastSpoken = text;

  const msg = new SpeechSynthesisUtterance(text);
  msg.lang = "ko-KR";
  msg.rate = type === "warn"
    ? Math.min(1.4, speechRate + 0.2)
    : speechRate;

  speechSynthesis.cancel();
  speechSynthesis.speak(msg);
}


// =======================
// UI Helpers
// =======================

function showMenu(menu) {
  [mainMenu, envMenu, locationMenu, facilityMenu].forEach(m => {
    if (m) m.style.display = "none";
  });

  if (menu === "main") mainMenu.style.display = "block";
  if (menu === "env") envMenu.style.display = "block";
  if (menu === "location") locationMenu.style.display = "block";
  if (menu === "facility") facilityMenu.style.display = "block";
}

function openEnvMenu() {
  showMenu("env");
  speak("환경 안내 모드입니다.");
}

function openLocationMenu() {
  showMenu("location");
  speak("위치 안내입니다. 요약, 주소, 건물, 시설 중 선택하세요.");
}

function openFacilityMenu() {
  showMenu("facility");
  speak("주변 시설을 선택하세요.");
}


// =======================
// System Control
// =======================

async function startSystem() {
  await startCamera();
  showMenu("main");

  startBtn.style.display = "none";
  stopBtn.style.display = "inline-block";
  objectBtn.style.display = "inline-block";
  envBtn.style.display = "inline-block";
  envToggleBtn.style.display = "inline-block";
  locationBtn.style.display = "inline-block";

  speak("시스템을 시작합니다.");
}

function stopSystem() {
  stopCamera();
  showMenu("main");

  startBtn.style.display = "inline-block";
  stopBtn.style.display = "none";
  objectBtn.style.display = "none";
  envBtn.style.display = "none";
  envToggleBtn.style.display = "none";
  locationBtn.style.display = "none";

  objectsDiv.innerText = "-";
  envDiv.innerText = "-";
  alertDiv.innerText = "없음";
  statusDiv.innerText = "대기 중";

  resetEnvState();
  speak("시스템을 종료합니다.");
}


// =======================
// Camera
// =======================

async function startCamera() {
  const s = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "environment" }
  });
  stream = s;
  video.srcObject = stream;
  running = true;
  statusDiv.innerText = "감지 중";
  startLoop();
}

function stopCamera() {
  clearInterval(interval);
  stream && stream.getTracks().forEach(t => t.stop());
  running = false;
}

function startLoop() {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");

  interval = setInterval(async () => {
    if (!running) return;

    canvas.width = 640;
    canvas.height = 360;
    ctx.drawImage(video, 0, 0);

    const blob = await new Promise(r =>
      canvas.toBlob(r, "image/jpeg", 0.6)
    );
    await sendFrame(blob);
  }, INTERVAL_MS);
}

async function sendFrame(blob) {
  if (uploadMode) return;

  const tStart = performance.now();
  const form = new FormData();
  form.append("mode", "realtime");
  form.append("file", blob);

  const res = await safeFetch(API_URL, { method: "POST", body: form });
  if (!res) return;

  const tResponse = performance.now();
  const data = await res.json();
  updateUI(data, tStart, tResponse);
}


// =======================
// Environment State Machine
// =======================

function resetEnvState() {
  envMuted = false;
  currentEnvText = null;
  lastEnvWarnTime = 0;
  lastEnvDetectTime = 0;
  envToggleBtn.innerText = "경고 끄기";
}

function processEnv(msg) {
  const now = Date.now();

  if (!msg) {
    if (currentEnvText && now - lastEnvDetectTime > ENV_RELEASE_MS) {
      resetEnvState();
    }
    return;
  }

  lastEnvDetectTime = now;

  if (currentEnvText !== msg) {
    currentEnvText = msg;
    envMuted = false;
    lastEnvWarnTime = now;
    envToggleBtn.innerText = "경고 끄기";
    alertDiv.innerText = msg;
    speak(msg, "warn");
    return;
  }

  if (envMuted) return;
  if (now - lastEnvWarnTime < ENV_REPEAT_IGNORE_MS) return;

  if (now - lastEnvWarnTime >= ENV_WARN_INTERVAL_MS) {
    alertDiv.innerText = msg;
    speak(msg, "warn");
    lastEnvWarnTime = now;
  }
}


// =======================
// UI Update
// =======================

function updateUI(data, tStart = null, tResponse = null) {
  if (!data) return;

  if (uploadMode) {
    if (data.objects?.length) {
      const counts = {};
      data.objects.forEach(o => {
        counts[o.class] = (counts[o.class] || 0) + 1;
      });

      const msg = Object.entries(counts)
        .map(([cls, n]) => `${cls} ${n}개`)
        .join(", ");

      objectsDiv.innerText = `감지된 객체: ${msg}`;
    } else {
      objectsDiv.innerText = "감지된 객체가 없습니다.";
    }

    if (data.environment?.danger_zones?.length) {
      envDiv.innerText = `환경: ${data.environment.danger_zones.join(", ")}`;
    } else {
      envDiv.innerText = "환경: 안전";
    }

    alertDiv.innerText = "사진 분석 결과입니다.";
    return;
  }

  if (data.warnings?.length) {
    const msg = data.warnings[0];
    objectsDiv.innerText = msg;
    speak(msg, "warn");
  } else {
    objectsDiv.innerText = "-";
  }

  const envMsg = data.warnings?.find(w => w.includes("환경")) || null;
  envDiv.innerText = envMsg || "-";
  alertDiv.innerText = envMsg || "없음";
  processEnv(envMsg);

  if (data.image) {
    if (video.srcObject) {
      video.srcObject.getTracks().forEach(t => t.stop());
      video.srcObject = null;
    }

    video.pause();
    video.style.display = "none";

    resultImage.src = "data:image/jpeg;base64," + data.image;
    resultImage.style.display = "block";
    resultImage.offsetHeight;
  } else {
    resultImage.style.display = "none";
    video.style.display = "block";
  }
}


// =======================
// API Calls
// =======================

async function manualObjectGuide() {
  if (apiRequestLock) return;
  apiRequestLock = true;

  const res = await safeFetch("/api/nearby_objects");
  if (!res) return apiRequestLock = false;

  const data = await res.json();
  objectsDiv.innerText = data.message || "-";
  alertDiv.innerText = data.message || "-";
  speak(data.message);

  apiRequestLock = false;
}

async function fetchEnvDanger() {
  if (apiRequestLock) return;
  apiRequestLock = true;

  const res = await safeFetch("/api/env/danger");
  if (!res) return apiRequestLock = false;

  const data = await res.json();
  envDiv.innerText = data.message || "-";
  alertDiv.innerText = data.message || "-";
  speak(data.message, "warn");

  apiRequestLock = false;
}

async function fetchEnvSafe() {
  if (apiRequestLock) return;
  apiRequestLock = true;

  const res = await safeFetch("/api/env/safe");
  if (!res) return apiRequestLock = false;

  const data = await res.json();
  envDiv.innerText = data.message || "-";
  alertDiv.innerText = data.message || "-";
  speak(data.message);

  apiRequestLock = false;
}

async function toggleEnvAlert() {
  envMuted = !envMuted;
  envToggleBtn.innerText = envMuted ? "경고 켜기" : "경고 끄기";
  speak(envMuted ? "경고를 중단합니다." : "경고를 다시 시작합니다.", "sys");
  await safeFetch("/api/env/toggle", { method: "POST" });
}


// =======================
// Location
// =======================

function fetchLocation(mode = "summary", categoryCode = null) {
  if (locationRequestLock) return;
  locationRequestLock = true;

  const perform = async (lat, lng) => {
    let url = "/api/identity/summary";
    let body = { lat, lng };

    if (mode === "address") url = "/api/identity/address";
    if (mode === "landmark") url = "/api/identity/landmark";
    if (mode === "facility") {
      url = "/api/identity/facility";
      body = { lat, lng, category_code: categoryCode };
    }

    const res = await safeFetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    if (!res) return;
    const data = await res.json();
    speak(data.message);
  };

  const now = Date.now();

  if (lastLocation && now - lastLocationTime < LOCATION_CACHE_MS) {
    perform(lastLocation.lat, lastLocation.lng)
      .finally(() => locationRequestLock = false);
    return;
  }

  speak("현재 위치를 확인 중입니다.", "sys");

  navigator.geolocation.getCurrentPosition(
    pos => {
      lastLocation = {
        lat: pos.coords.latitude,
        lng: pos.coords.longitude
      };
      lastLocationTime = Date.now();
      perform(lastLocation.lat, lastLocation.lng)
        .finally(() => locationRequestLock = false);
    },
    () => {
      locationRequestLock = false;
      speak("위치 정보를 가져오지 못했습니다.", "sys");
    }
  );
}


// =======================
// Upload
// =======================

async function uploadImage() {
  const file = fileInput.files[0];
  if (!file) return;

  statusDiv.innerText = "사진 분석 중입니다.";

  const form = new FormData();
  form.append("mode", "upload");
  form.append("file", file);

  const res = await safeFetch(
    `${API_URL}?mode=upload`,
    { method: "POST", body: form }
  );
  if (!res) return;

  const data = await res.json();
  updateUI(data);

  speak("사진 분석이 완료되었습니다.", "sys");

  if (data.image) {
    const link = document.createElement("a");
    link.href = "data:image/jpeg;base64," + data.image;
    link.download = "detection_result.jpg";
    link.click();
  }
}


// =======================
// Bindings
// =======================

startBtn.onclick = startSystem;
stopBtn.onclick = stopSystem;

objectBtn.onclick = manualObjectGuide;

envBtn.onclick = openEnvMenu;
envDangerBtn.onclick = fetchEnvDanger;
envSafeBtn.onclick = fetchEnvSafe;
envBackBtn.onclick = () => showMenu("main");

locationBtn.onclick = openLocationMenu;
locSummaryBtn.onclick = () => fetchLocation("summary");
locAddressBtn.onclick = () => fetchLocation("address");
locLandmarkBtn.onclick = () => fetchLocation("landmark");
locFacilityBtn.onclick = openFacilityMenu;
locBackBtn.onclick = () => showMenu("main");

facilityBackBtn.onclick = openLocationMenu;
facilityButtons.forEach(
  btn => btn.onclick = () => fetchLocation("facility", btn.dataset.category)
);

envToggleBtn.onclick = toggleEnvAlert;
voiceBtn.onclick = () =>
  isRecording ? stopVoiceCommand() : startVoiceCommand();

slowBtn.onclick = () => setSpeechRate(-0.1);
normalBtn.onclick = resetSpeechRate;
fastBtn.onclick = () => setSpeechRate(+0.1);

uploadBtn.onclick = () => {
  uploadMode = true;

  if (running) stopCamera();

  statusDiv.innerText = "사진 분석 모드입니다.";
  speak("사진을 선택해 주세요.", "sys");

  fileInput.value = "";
  fileInput.click();
};

fileInput.onchange = uploadImage;
