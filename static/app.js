const app = document.querySelector("#app");

const reagentRules = {
  "염산": { formula: "HCl", category: "산", risk: "부식성", storage: "산 전용 보관함", warning: "염기성 물질과 분리 보관이 필요합니다." },
  "황산": { formula: "H2SO4", category: "산", risk: "강한 부식성", storage: "산 전용 보관함", warning: "물과 반응 시 발열할 수 있으므로 취급에 주의합니다." },
  "질산": { formula: "HNO3", category: "산화성 산", risk: "부식성 · 산화성", storage: "산화성 물질 전용 보관함", warning: "유기물, 환원제와 분리 보관합니다." },
  "수산화나트륨": { formula: "NaOH", category: "염기", risk: "부식성", storage: "염기 전용 보관함", warning: "산성 물질과 분리 보관합니다." },
  "암모니아수": { formula: "NH4OH", category: "염기", risk: "자극성", storage: "염기 전용 보관함", warning: "휘발성 냄새가 강하므로 환기가 필요합니다." },
  "에탄올": { formula: "C2H5OH", category: "유기용매", risk: "인화성", storage: "인화성 물질 보관함", warning: "화기 근처 보관을 피합니다." },
  "메탄올": { formula: "CH3OH", category: "유기용매", risk: "인화성 · 유해성", storage: "인화성 물질 보관함", warning: "흡입과 피부 접촉을 피하고 밀폐 보관합니다." },
  "아세톤": { formula: "C3H6O", category: "유기용매", risk: "높은 인화성", storage: "인화성 물질 보관함", warning: "증기가 쉽게 발생하므로 뚜껑을 닫아 보관합니다." },
  "과산화수소": { formula: "H2O2", category: "산화제", risk: "산화성", storage: "산화제 전용 보관함", warning: "환원제, 금속분말, 유기물과 분리 보관합니다." },
  "질산칼륨": { formula: "KNO3", category: "산화제", risk: "산화성", storage: "산화제 전용 보관함", warning: "가연성 물질과 함께 보관하지 않습니다." },
};

const state = {
  role: null,
  student: null,
  reagents: [],
  requests: [],
  query: "",
  editingId: null,
};

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || "요청을 처리하지 못했습니다.");
  }
  return data;
}

function getTodayStart() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

function daysUntil(dateString) {
  if (!dateString) return 9999;
  const target = new Date(`${dateString}T00:00:00`);
  return Math.ceil((target - getTodayStart()) / (1000 * 60 * 60 * 24));
}

function getMinimumDate() {
  const min = getTodayStart();
  min.setDate(min.getDate() + 3);
  return min.toISOString().slice(0, 10);
}

function analyzeReagent(name) {
  const key = Object.keys(reagentRules).find((item) => name.includes(item) || item.includes(name));
  if (!key) {
    return {
      formula: "정보 없음",
      category: "미분류",
      risk: "추가 확인 필요",
      riskLevel: "판단 보류",
      storage: "담당 교사 확인 후 지정",
      protectiveGear: "보안경, 장갑 착용 권장",
      disposal: "SDS 확인 후 폐기",
      incompatible: "정보 부족",
      aiSummary: "시약명이 기본 데이터에 없어 실제 사용 전 SDS 자료와 담당 교사의 확인이 필요합니다.",
      warning: "SDS 자료를 확인한 뒤 위험성과 보관 조건을 입력해야 합니다.",
    };
  }

  const data = reagentRules[key];
  let riskLevel = "낮음";
  let protectiveGear = "보안경, 실험복 착용";
  let disposal = "소량은 담당 교사 지시에 따라 분리 폐기";
  let incompatible = "일반 시약과 분리 여부 확인";
  let aiSummary = "AI가 시약명을 분석하여 기본 위험성과 보관 조건을 자동 분류했습니다.";

  if (data.risk.includes("강한") || data.risk.includes("높은") || data.risk.includes("산화성")) riskLevel = "높음";
  else if (data.risk.includes("부식") || data.risk.includes("인화") || data.risk.includes("유해")) riskLevel = "중간";

  if (data.category.includes("산")) {
    protectiveGear = "보안경, 내화학 장갑, 실험복 착용";
    disposal = "산성 폐액통에 분리 배출";
    incompatible = "염기, 금속, 유기물과 분리";
    aiSummary = "산성 시약으로 판단되어 부식 위험과 혼합 보관 위험을 우선 경고합니다.";
  }
  if (data.category.includes("염기")) {
    protectiveGear = "보안경, 내화학 장갑, 실험복 착용";
    disposal = "염기성 폐액통에 분리 배출";
    incompatible = "산성 물질과 분리";
    aiSummary = "염기성 시약으로 판단되어 피부·눈 손상 위험과 산과의 반응 가능성을 경고합니다.";
  }
  if (data.category.includes("유기용매")) {
    protectiveGear = "보안경, 장갑 착용 및 환기 필요";
    disposal = "유기용매 폐액통에 분리 배출";
    incompatible = "화기, 산화제와 분리";
    aiSummary = "유기용매로 판단되어 인화 위험과 휘발성에 따른 환기 필요성을 경고합니다.";
  }
  if (data.category.includes("산화제")) {
    protectiveGear = "보안경, 장갑, 실험복 착용";
    disposal = "산화제 폐기 지침에 따라 별도 폐기";
    incompatible = "가연성 물질, 환원제, 유기물과 분리";
    aiSummary = "산화제로 판단되어 다른 물질의 연소를 촉진할 수 있으므로 분리 보관을 권장합니다.";
  }

  return { ...data, riskLevel, protectiveGear, disposal, incompatible, aiSummary };
}

function analyzeExperimentPlan(reagentsText, safetyPlan) {
  const names = Object.keys(reagentRules).filter((name) => reagentsText.includes(name));
  const infos = names.map((name) => analyzeReagent(name));
  const highRisk = infos.filter((info) => info.riskLevel === "높음").length;
  const mediumRisk = infos.filter((info) => info.riskLevel === "중간").length;
  const hasSafety = safetyPlan.trim().length >= 10;

  let level = "낮음";
  if (highRisk > 0) level = "높음";
  else if (mediumRisk > 0) level = "중간";

  let summary = "AI가 제출된 시약 목록과 안전 계획을 분석했습니다.";
  if (!hasSafety) summary = "안전 계획이 너무 짧습니다. 보호구, 폐액 처리, 사고 대응 방법을 더 자세히 작성해야 합니다.";
  else if (level === "높음") summary = "위험도가 높은 시약이 포함되어 있어 교사의 사전 확인과 보호구 착용 계획이 중요합니다.";
  else if (level === "중간") summary = "부식성 또는 인화성 시약이 포함되어 있어 보관 위치와 폐액 처리를 확인해야 합니다.";

  return { detected: names.length ? names.join(", ") : "자동 인식된 시약 없음", level, summary };
}

async function loadData() {
  const [session, reagents, requests] = await Promise.all([
    requestJson("/api/session"),
    requestJson(`/api/reagents${state.query ? `?q=${encodeURIComponent(state.query)}` : ""}`),
    requestJson("/api/requests"),
  ]);
  state.role = session.role;
  state.student = session.student;
  state.reagents = reagents;
  state.requests = requests;
}

function dangerCount() {
  return state.reagents.filter((item) => {
    const risk = analyzeReagent(item.name).risk;
    return risk.includes("인화") || risk.includes("부식") || risk.includes("산화");
  }).length;
}

function expiringSoonCount() {
  return state.reagents.filter((item) => daysUntil(item.expiry) <= 30).length;
}

function pendingCount() {
  return state.requests.filter((item) => item.status === "대기").length;
}

function renderHome() {
  const template = document.querySelector("#homeTemplate");
  app.replaceChildren(template.content.cloneNode(true));

  document.querySelector("#statReagents").textContent = state.reagents.length;
  document.querySelector("#statDanger").textContent = dangerCount();
  document.querySelector("#statExpiry").textContent = expiringSoonCount();
  document.querySelector("#statPending").textContent = pendingCount();

  document.querySelector("#studentModeButton").addEventListener("click", () => {
    document.querySelector("#studentLoginPanel").hidden = false;
    document.querySelector("#teacherLoginPanel").hidden = true;
  });
  document.querySelector("#teacherModeButton").addEventListener("click", () => {
    document.querySelector("#teacherLoginPanel").hidden = false;
    document.querySelector("#studentLoginPanel").hidden = true;
  });

  document.querySelector("#studentLoginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await requestJson("/api/login/student", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(form)),
      });
      await refresh();
    } catch (error) {
      alert(error.message);
    }
  });

  document.querySelector("#teacherLoginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await requestJson("/api/login/teacher", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(form)),
      });
      await refresh();
    } catch (error) {
      alert(error.message);
    }
  });
}

function renderDashboard() {
  const template = document.querySelector("#dashboardTemplate");
  app.replaceChildren(template.content.cloneNode(true));

  const isStudent = state.role === "student";
  document.querySelector("#dashboardTitle").textContent = isStudent ? `${state.student.name} 학생` : "선생님 관리자";
  document.querySelector("#dashboardSubtitle").textContent = isStudent
    ? "시약 정보를 조회하고 과학실 사용 신청서를 제출합니다."
    : "시약 목록과 학생 실험 계획서를 관리합니다.";
  document.querySelector("#logoutButton").addEventListener("click", async () => {
    await requestJson("/api/logout", { method: "POST" });
    state.query = "";
    await refresh();
  });

  if (isStudent) renderStudentDashboard();
  else renderTeacherDashboard();
}

function renderStudentDashboard() {
  const body = document.querySelector("#dashboardBody");
  body.className = "app-shell dashboard-grid two-col";
  body.innerHTML = `
    <section class="panel" id="studentSearchPanel"></section>
    <section class="panel">
      <div class="panel-heading"><div><p class="eyebrow">Request</p><h2>과학실 사용 신청 및 계획서 제출</h2></div></div>
      <p class="muted">실험일 기준 최소 3일 전부터 신청 가능합니다. 오늘 기준 신청 가능 시작일: ${getMinimumDate()}</p>
      <form id="requestForm" class="stack-form">
        <label>실험 날짜<input name="lab_date" type="date" min="${getMinimumDate()}" required /></label>
        <label>실험 시간<input name="lab_time" type="time" required /></label>
        <label>실험 제목<input name="experiment_title" placeholder="예: 산염기 중화 반응" required /></label>
        <label>실험 목적<textarea name="purpose" placeholder="실험을 통해 확인하고 싶은 내용을 작성하세요." required></textarea></label>
        <label>사용 예정 시약<textarea name="reagents" placeholder="예: 염산, 수산화나트륨, 에탄올" required></textarea></label>
        <label>안전 계획<textarea name="safety_plan" placeholder="보호구, 폐액 처리, 사고 예방 방법을 작성하세요." required></textarea></label>
        <div class="analysis-box" id="planAnalysis" hidden></div>
        <button type="submit">신청서 제출하기</button>
      </form>
      <h3 class="section-title">내 신청 현황</h3>
      <div id="requestList"></div>
    </section>
  `;
  renderSearchPanel(document.querySelector("#studentSearchPanel"), false);
  renderRequestList(false);

  const requestForm = document.querySelector("#requestForm");
  requestForm.addEventListener("input", () => {
    const data = Object.fromEntries(new FormData(requestForm));
    const box = document.querySelector("#planAnalysis");
    if (!data.reagents && !data.safety_plan) {
      box.hidden = true;
      return;
    }
    const analysis = analyzeExperimentPlan(data.reagents || "", data.safety_plan || "");
    box.hidden = false;
    box.innerHTML = `<strong>AI 계획서 분석</strong><p>인식된 시약: ${analysis.detected}</p><p>실험 위험도: ${analysis.level}</p><p>${analysis.summary}</p>`;
  });
  requestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await requestJson("/api/requests", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(new FormData(requestForm))),
      });
      requestForm.reset();
      await refresh();
      alert("과학실 사용 신청서와 실험 계획서가 제출되었습니다.");
    } catch (error) {
      alert(error.message);
    }
  });
}

function renderTeacherDashboard() {
  const body = document.querySelector("#dashboardBody");
  body.className = "app-shell dashboard-grid teacher-grid";
  body.innerHTML = `
    <section class="panel">
      <div class="panel-heading"><div><p class="eyebrow">Admin</p><h2>시약 등록 및 수정</h2></div></div>
      <form id="reagentForm" class="stack-form">
        <label>시약명<input name="name" placeholder="예: 염산" required /></label>
        <label>영문명<input name="english_name" placeholder="예: Hydrochloric acid" /></label>
        <label>약품 코드<input name="chemical_code" placeholder="예: HCl / CAS 7647-01-0" /></label>
        <label>약품 유해도<select name="hazard_level"><option value="">선택 안 함</option><option>낮음</option><option>주의</option><option>높음</option><option>위험</option></select></label>
        <label>위험성<textarea name="risk_notes" placeholder="예: 부식성, 인화성, 흡입 주의"></textarea></label>
        <label>용량<input name="quantity" placeholder="예: 450 mL" /></label>
        <label>보관 위치<input name="location" placeholder="예: A-1" required /></label>
        <label>유효기간<input name="expiry" type="date" /></label>
        <label>담당자<input name="manager" placeholder="예: 과학부" /></label>
        <div class="analysis-box" id="reagentAnalysis" hidden></div>
        <button type="submit" id="saveReagentButton">시약 추가하기</button>
      </form>
    </section>
    <section class="panel" id="teacherSearchPanel"></section>
    <section class="panel full-span">
      <div class="panel-heading"><div><p class="eyebrow">Review</p><h2>학생 과학실 사용 신청 확인</h2></div></div>
      <div id="requestList"></div>
    </section>
  `;
  renderSearchPanel(document.querySelector("#teacherSearchPanel"), true);
  renderRequestList(true);

  const reagentForm = document.querySelector("#reagentForm");
  reagentForm.name.addEventListener("input", () => {
    const box = document.querySelector("#reagentAnalysis");
    if (!reagentForm.name.value) {
      box.hidden = true;
      return;
    }
    const info = analyzeReagent(reagentForm.name.value);
    box.hidden = false;
    box.innerHTML = `<strong>AI 분석 결과</strong><p>위험성: ${info.risk}</p><p>AI 위험도: ${info.riskLevel}</p><p>권장 보관 위치: ${info.storage}</p><p>주의: ${info.warning}</p>`;
  });
  reagentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(reagentForm));
    const url = state.editingId ? `/api/reagents/${state.editingId}` : "/api/reagents";
    const method = state.editingId ? "PUT" : "POST";
    try {
      await requestJson(url, { method, body: JSON.stringify(payload) });
      state.editingId = null;
      reagentForm.reset();
      await refresh();
    } catch (error) {
      alert(error.message);
    }
  });
}

function renderSearchPanel(container, isTeacher) {
  container.innerHTML = `
    <div class="panel-heading"><div><p class="eyebrow">Search</p><h2>${isTeacher ? "시약 목록 관리" : "시약 검색"}</h2></div></div>
    <input id="searchInput" type="search" placeholder="시약명 또는 위치 검색" value="${state.query}" />
    <div class="reagent-list" id="reagentList"></div>
  `;
  container.querySelector("#searchInput").addEventListener("input", async (event) => {
    state.query = event.target.value;
    await loadData();
    renderReagentList(container.querySelector("#reagentList"), isTeacher);
  });
  renderReagentList(container.querySelector("#reagentList"), isTeacher);
}

function renderReagentList(container, isTeacher) {
  if (!state.reagents.length) {
    container.innerHTML = `<p class="empty">검색 결과가 없습니다.</p>`;
    return;
  }
  container.innerHTML = state.reagents.map((item) => reagentCardHtml(item, isTeacher)).join("");
  if (!isTeacher) return;

  container.querySelectorAll("[data-edit]").forEach((button) => {
    button.addEventListener("click", () => startEdit(Number(button.dataset.edit)));
  });
  container.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!confirm("이 시약을 삭제할까요?")) return;
      await requestJson(`/api/reagents/${button.dataset.delete}`, { method: "DELETE" });
      await refresh();
    });
  });
}

function reagentCardHtml(item, isTeacher) {
  const info = analyzeReagent(item.name);
  const days = daysUntil(item.expiry);
  const status = days < 0 ? "유효기간 경과" : days <= 30 ? "만료 임박" : "정상";
  return `
    <article class="reagent-card">
      <div class="card-head">
        <div>
          <h3>${item.name} <span>${item.chemical_code || info.formula}</span></h3>
          <p class="english-name">${item.english_name || "영문명 미입력"}</p>
        </div>
        <span class="hazard-badge" data-level="${item.hazard_level || info.riskLevel}">${item.hazard_level || info.riskLevel}</span>
      </div>
      <p class="muted">현재량 ${item.quantity || "미입력"} · 담당 ${item.manager || "미지정"} · 위치 ${item.location}</p>
      <div class="mini-grid">
        <div><small>위험성</small><strong>${item.risk_notes || info.risk}</strong></div>
        <div><small>권장 위치</small><strong>${info.storage}</strong></div>
        <div><small>유효기간</small><strong>${item.expiry || "미입력"} (${status})</strong></div>
      </div>
      <div class="analysis-box">
        <p>함께 보관하면 위험한 물질: ${info.incompatible}</p>
        <p>권장 보호구: ${info.protectiveGear}</p>
        <p>폐기 방법: ${info.disposal}</p>
        <p>AI 요약: ${info.aiSummary}</p>
      </div>
      ${isTeacher ? `<div class="button-row"><button data-edit="${item.id}" type="button">수정</button><button class="danger" data-delete="${item.id}" type="button">삭제</button></div>` : ""}
    </article>
  `;
}

function startEdit(id) {
  const item = state.reagents.find((reagent) => reagent.id === id);
  const form = document.querySelector("#reagentForm");
  if (!item || !form) return;
  state.editingId = id;
  Object.entries(item).forEach(([key, value]) => {
    if (form.elements[key]) form.elements[key].value = value || "";
  });
  document.querySelector("#saveReagentButton").textContent = "수정 완료하기";
  form.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderRequestList(isTeacher) {
  const container = document.querySelector("#requestList");
  if (!state.requests.length) {
    container.innerHTML = `<p class="empty">신청 내역이 없습니다.</p>`;
    return;
  }
  container.innerHTML = state.requests.map((item) => requestCardHtml(item, isTeacher)).join("");
  if (!isTeacher) return;

  container.querySelectorAll("[data-status]").forEach((button) => {
    button.addEventListener("click", async () => {
      await requestJson(`/api/requests/${button.dataset.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: button.dataset.status }),
      });
      await refresh();
    });
  });
}

function requestCardHtml(item, isTeacher) {
  const analysis = analyzeExperimentPlan(item.reagents, item.safety_plan);
  return `
    <article class="request-card">
      <div class="card-head">
        <div>
          <h3>${item.experiment_title}</h3>
          <p class="muted">${item.student_name} (${item.student_id}) · ${item.lab_date} ${item.lab_time}</p>
        </div>
        <span class="status-badge" data-status="${item.status}">${item.status}</span>
      </div>
      <div class="mini-grid two">
        <div><small>사용 예정 시약</small><strong>${item.reagents}</strong></div>
        <div><small>AI 실험 위험도</small><strong>${analysis.level}</strong></div>
      </div>
      <div class="analysis-box">
        <p><strong>실험 목적:</strong> ${item.purpose}</p>
        <p><strong>안전 계획:</strong> ${item.safety_plan}</p>
        <p>AI 계획서 분석: ${analysis.summary} / 인식된 시약: ${analysis.detected}</p>
      </div>
      ${isTeacher ? `<div class="button-row"><button data-id="${item.id}" data-status="승인" type="button">승인</button><button class="danger" data-id="${item.id}" data-status="반려" type="button">반려</button></div>` : ""}
    </article>
  `;
}

async function refresh() {
  await loadData();
  if (!state.role) renderHome();
  else renderDashboard();
}

refresh().catch((error) => {
  app.innerHTML = `<section class="app-shell"><div class="panel"><h1>앱을 불러오지 못했습니다.</h1><p>${error.message}</p></div></section>`;
});
