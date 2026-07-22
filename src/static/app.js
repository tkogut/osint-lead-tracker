// app.js - Lead Dashboard Front-end Application

document.addEventListener("DOMContentLoaded", () => {
    // --- State ---
    let currentUser = null;
    let accountsList = [];
    let allLeads = [];

    // --- DOM Elements ---
    const loginContainer = document.getElementById("login-container");
    const appContainer = document.getElementById("app-container");
    const loginForm = document.getElementById("login-form");
    const loginError = document.getElementById("login-error");
    
    const logoutBtn = document.getElementById("logout-btn");
    const userDisplayName = document.getElementById("user-display-name");
    const triggerScanBtn = document.getElementById("trigger-scan-btn");

    const navItems = document.querySelectorAll(".nav-item");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const tabTitle = document.getElementById("current-tab-title");
    const tabDesc = document.getElementById("current-tab-desc");

    // Modal elements
    const accountModal = document.getElementById("account-modal");
    const addAccountBtn = document.getElementById("add-account-btn");
    const modalCloseBtn = document.getElementById("modal-close-btn");
    const modalCancelBtn = document.getElementById("modal-cancel-btn");
    const accountForm = document.getElementById("account-form");
    const accountIdInput = document.getElementById("account-id");
    const modalTitle = document.getElementById("modal-title");

    // Tabs specific elements
    const leadsTableBody = document.getElementById("leads-table-body");
    const accountsContainer = document.getElementById("accounts-container");
    const logsTableBody = document.getElementById("logs-table-body");
    const settingsFieldsContainer = document.getElementById("settings-fields-container");
    const settingsForm = document.getElementById("settings-form");

    // Sandbox specific elements
    const sandboxForm = document.getElementById("sandbox-form");
    const sandboxOutput = document.getElementById("sandbox-output");
    const sandboxTemp = document.getElementById("sandbox-temperature");
    const sandboxTempval = document.getElementById("sandbox-temp-val");

    // Stat counters
    const statTotalLeads = document.getElementById("stat-total-leads");
    const statAutoScales = document.getElementById("stat-auto-scales");
    const statOdooLeads = document.getElementById("stat-odoo-leads");

    // --- Tab Navigation Mapping ---
    const tabMetas = {
        dashboard: { title: "Dashboard", desc: "Przegląd pozyskanych leadów i statystyki" },
        accounts: { title: "Kampanie / Konta", desc: "Zarządzanie kampaniami wyszukiwania i integracją (Multi-tenancy)" },
        sandbox: { title: "Piaskownica LLM", desc: "Testowanie promptów i parametrów modelu na surowym tekście" },
        logs: { title: "Rejestr i Logi", desc: "Twarde dowody wykonania zadań researchu (ResearchLog)" },
        settings: { title: "Konfiguracja Systemu", desc: "Zarządzanie zmiennymi środowiskowymi i kluczami API" }
    };

    // --- Toast Notifications ---
    function showToast(message, type = "success") {
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        
        let icon = "fa-circle-check";
        if (type === "error") icon = "fa-circle-exclamation";
        if (type === "warning") icon = "fa-triangle-exclamation";
        
        toast.innerHTML = `
            <i class="fa-solid ${icon}"></i>
            <span>${message}</span>
        `;
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = "slideIn 0.3s ease-out reverse";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // --- API Fetch Helpers ---
    async function apiRequest(url, options = {}) {
        try {
            const res = await fetch(url, options);
            if (res.status === 401) {
                // Session expired or unauthorized
                showLoginScreen();
                return null;
            }
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Błąd serwera.");
            }
            return await res.json();
        } catch (err) {
            showToast(err.message, "error");
            throw err;
        }
    }

    // --- Authentication ---
    async function checkSession() {
        try {
            const user = await apiRequest("/api/auth/me");
            if (user && user.username) {
                currentUser = user;
                showAppScreen();
            } else {
                showLoginScreen();
            }
        } catch (e) {
            showLoginScreen();
        }
    }

    function showLoginScreen() {
        loginContainer.classList.remove("hidden");
        appContainer.classList.add("hidden");
        document.body.classList.add("centered-layout");
    }

    function showAppScreen() {
        loginContainer.classList.add("hidden");
        appContainer.classList.remove("hidden");
        document.body.classList.remove("centered-layout");
        userDisplayName.textContent = currentUser.username;
        loadDashboardData();
        checkNotificationGate();
    }

    // Login Submit
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        loginError.classList.add("hidden");
        
        const usernameInput = document.getElementById("username").value;
        const passwordInput = document.getElementById("password").value;

        try {
            const res = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: usernameInput, password: passwordInput })
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.detail || "Błąd logowania.");
            }

            const data = await res.json();
            currentUser = { username: data.username, role: data.role };
            showToast(`Witaj ponownie, ${data.username}!`);
            showAppScreen();
        } catch (err) {
            loginError.textContent = err.message;
            loginError.classList.remove("hidden");
        }
    });

    // Logout Click
    logoutBtn.addEventListener("click", async () => {
        try {
            await fetch("/api/auth/logout", { method: "POST" });
            currentUser = null;
            showToast("Wylogowano pomyślnie.");
            showLoginScreen();
        } catch (e) {
            showLoginScreen();
        }
    });

    // --- Tab Switching ---
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetTab = item.dataset.tab;
            
            navItems.forEach(nav => nav.classList.remove("active"));
            item.classList.add("active");

            tabPanes.forEach(pane => pane.classList.remove("active"));
            document.getElementById(`tab-${targetTab}`).classList.add("active");

            // Update header title & desc
            const meta = tabMetas[targetTab];
            tabTitle.textContent = meta.title;
            tabDesc.textContent = meta.desc;

            // Load tab specific data
            if (targetTab === "dashboard") loadDashboardData();
            if (targetTab === "accounts") loadAccountsData();
            if (targetTab === "logs") loadLogsData();
            if (targetTab === "settings") loadSettingsData();
        });
    });

    const leadSearch = document.getElementById("lead-search");
    const leadFilterStatus = document.getElementById("lead-filter-status");
    const leadSort = document.getElementById("lead-sort");

    if (leadSearch) leadSearch.addEventListener("input", filterAndRenderLeads);
    if (leadFilterStatus) leadFilterStatus.addEventListener("change", filterAndRenderLeads);
    if (leadSort) leadSort.addEventListener("change", filterAndRenderLeads);

    // --- Dashboard & Leads ---
    async function loadDashboardData() {
        leadsTableBody.innerHTML = `<tr><td colspan="8" class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Ładowanie leadów...</td></tr>`;
        
        try {
            // Pobieramy leady za pomocą sesyjnie zabezpieczonego endpointu /api/leads
            const data = await apiRequest("/api/leads?limit=100");
            allLeads = data.leads || [];
            
            // Wyświetlamy
            filterAndRenderLeads();
            
            // Faza 3: Pobieramy KPIs, Oś Czasu oraz status Notification Gate
            loadAnalyticsKPIs();
            loadAnalyticsTimeline();
            checkNotificationGate();
            populateSandboxSources();
        } catch (e) {
            leadsTableBody.innerHTML = `<tr><td colspan="8" class="loading-state text-error">Błąd ładowania danych: ${e.message}</td></tr>`;
        }
    }

    async function loadAnalyticsKPIs() {
        try {
            const kpis = await apiRequest("/api/analytics/kpis");
            if (kpis) {
                document.getElementById("stat-total-scans").textContent = kpis.total_scans;
                document.getElementById("stat-success-rate").textContent = `${kpis.success_rate}%`;
                document.getElementById("stat-failed-scans").textContent = kpis.failed_scans;
            }
        } catch (e) {
            console.error("Error loading KPIs", e);
        }

        // Fetch Phase 6 analytics KPIs (Yield 7d, Yield/Chunk, Queries, Quarantine)
        try {
            const kpis = await apiRequest("/api/analytics/dashboard");
            if (kpis) {
                const yieldPerChunkEl = document.getElementById("stat-yield-per-chunk");
                const queriesEl = document.getElementById("stat-queries-fired");
                const pendingEl = document.getElementById("stat-pending-count");
                const pendingCard = document.getElementById("kpi-pending-card");
                if (yieldPerChunkEl) yieldPerChunkEl.textContent = kpis.yield_per_chunk !== undefined ? kpis.yield_per_chunk : "0.000";
                if (queriesEl) queriesEl.textContent = kpis.total_queries_fired_7d !== undefined ? kpis.total_queries_fired_7d : "0";
                if (pendingEl) pendingEl.textContent = kpis.pending_approval_count !== undefined ? kpis.pending_approval_count : "0";
                if (pendingCard) {
                    if (kpis.pending_approval_count > 0) {
                        pendingCard.style.display = "";
                    } else {
                        pendingCard.style.display = "none";
                    }
                }
                if (kpis.pending_approval_count > 0) {
                    loadPendingLeads();
                } else {
                    const section = document.getElementById("pending-leads-section");
                    if (section) section.classList.add("hidden");
                }
            }
        } catch(e) {
            console.error("Error loading Phase 6 dashboard KPIs", e);
        }
    }

    async function loadAnalyticsTimeline() {
        const container = document.getElementById("analytics-timeline-chart");
        container.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Ładowanie osi czasu...</div>`;
        
        try {
            const timeline = await apiRequest("/api/analytics/timeline");
            if (!timeline || timeline.length === 0) {
                container.innerHTML = `<div class="loading-state">Brak danych historycznych do wyświetlenia.</div>`;
                return;
            }
            
            const maxVal = Math.max(...timeline.map(d => Math.max(d.scans, d.leads_created)), 1);
            
            container.innerHTML = timeline.map(d => {
                const scanWidth = (d.scans / maxVal) * 100;
                const leadWidth = (d.leads_created / maxVal) * 100;
                
                return `
                    <div class="timeline-row">
                        <span class="timeline-date">${d.date}</span>
                        <div class="timeline-bars">
                            <div class="timeline-bar-group">
                                <div class="timeline-bar bar-scans" style="width: ${scanWidth}%;" title="Skanowania: ${d.scans}"></div>
                                <span class="bar-val" title="Skanowania">${d.scans}</span>
                            </div>
                            <div class="timeline-bar-group">
                                <div class="timeline-bar bar-leads" style="width: ${leadWidth}%;" title="Zapisane Szanse: ${d.leads_created}"></div>
                                <span class="bar-val" title="Zapisane Szanse">${d.leads_created}</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join("");
        } catch (e) {
            container.innerHTML = `<div class="loading-state text-error">Błąd pobierania osi czasu.</div>`;
        }
    }

    async function checkNotificationGate() {
        try {
            // Pobieramy limit 20 logów, aby mieć pewność, że uwzględnimy wszystkie skonfigurowane źródła
            const logs = await apiRequest("/api/logs?limit=20");
            if (!logs || logs.length === 0) {
                updateStatusIndicator(true);
                return;
            }
            
            // Wyciągamy tylko najnowszy log dla każdego źródła
            const latestLogsBySource = {};
            logs.forEach(log => {
                if (!(log.source in latestLogsBySource)) {
                    latestLogsBySource[log.source] = log;
                }
            });
            
            // Sprawdzamy czy ostatni skan dla któregokolwiek źródła zakończył się błędem
            const failedScan = Object.values(latestLogsBySource).find(log => log.response_status_code !== 200);
            const banner = document.getElementById("api-failure-banner");
            
            if (failedScan) {
                const msgSpan = document.getElementById("api-failure-msg");
                msgSpan.textContent = `Skan z dnia ${failedScan.timestamp.replace("T", " ").slice(0, 19)} dla źródła ${failedScan.source} zakończył się statusem ${failedScan.response_status_code}.`;
                if (banner) banner.classList.remove("hidden");
                updateStatusIndicator(false, `Błąd API (${failedScan.source}: ${failedScan.response_status_code})`);
            } else {
                if (banner) banner.classList.add("hidden");
                updateStatusIndicator(true);
            }
        } catch (e) {
            console.error("Error checking notification gate:", e);
        }
    }

    function updateStatusIndicator(isOk, text = "Status: OK") {
        const dot = document.querySelector(".status-dot");
        const statusText = document.getElementById("status-text");
        if (dot && statusText) {
            if (isOk) {
                dot.className = "status-dot dot-green";
                statusText.textContent = text;
            } else {
                dot.className = "status-dot dot-red";
                statusText.textContent = text;
            }
        }
    }

    function filterAndRenderLeads() {
        let filtered = [...allLeads];

        // Search
        const query = leadSearch ? leadSearch.value.toLowerCase().trim() : "";
        if (query) {
            filtered = filtered.filter(l => 
                (l.tytul || "").toLowerCase().includes(query) ||
                (l.inwestor || "").toLowerCase().includes(query) ||
                (l.lokalizacja || "").toLowerCase().includes(query) ||
                (l.zakres || "").toLowerCase().includes(query)
            );
        }

        // Status
        const statusVal = leadFilterStatus ? leadFilterStatus.value : "";
        if (statusVal) {
            filtered = filtered.filter(l => l.status === statusVal);
        }

        // Sort
        const sortVal = leadSort ? leadSort.value : "newest";
        if (sortVal === "newest") {
            filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        } else if (sortVal === "oldest") {
            filtered.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        } else if (sortVal === "priority") {
            const priorityWeight = { high: 3, medium: 2, low: 1 };
            filtered.sort((a, b) => {
                const wA = priorityWeight[(a.priorytet || "").toLowerCase()] || 0;
                const wB = priorityWeight[(b.priorytet || "").toLowerCase()] || 0;
                if (wB !== wA) return wB - wA;
                return new Date(b.created_at) - new Date(a.created_at);
            });
        }

        renderLeads(filtered);
    }

    function renderLeads(leads) {
        if (leads.length === 0) {
            leadsTableBody.innerHTML = `<tr><td colspan="8" class="loading-state">Brak znalezionych leadów.</td></tr>`;
            statTotalLeads.textContent = "0";
            if (statAutoScales) statAutoScales.textContent = "0";
            if (statOdooLeads) statOdooLeads.textContent = "0";
            return;
        }

        statTotalLeads.textContent = leads.length;

        leadsTableBody.innerHTML = leads.map(l => {
            const dateStr = l.created_at ? l.created_at.slice(0, 10) : "N/A";
            const priorityClass = `priority-${l.priorytet}`;
            const odooBadge = l.odoo_id 
                ? `<span class="badge badge-active" title="Odoo ID: ${l.odoo_id}"><i class="fa-solid fa-cloud-arrow-up"></i> Odoo (${l.odoo_id})</span>`
                : `<span class="badge badge-inactive"><i class="fa-solid fa-cloud-arrow-down"></i> Brak</span>`;

            let statusBadge = '';
            if (l.status === 'new') {
                statusBadge = `<span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3);">Nowy</span>`;
            } else if (l.status === 'in_progress') {
                statusBadge = `<span class="badge" style="background:rgba(245,158,11,0.15); color:#fbbf24; border:1px solid rgba(245,158,11,0.3);">W toku</span>`;
            } else if (l.status === 'won') {
                statusBadge = `<span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3);">Wygrany</span>`;
            } else if (l.status === 'lost') {
                statusBadge = `<span class="badge" style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3);">Przegrany</span>`;
            } else {
                statusBadge = `<span class="badge" style="background:rgba(255,255,255,0.1); color:#aaa; border:1px solid rgba(255,255,255,0.2);">${l.status || 'N/A'}</span>`;
            }

            return `
                <tr>
                    <td><strong>${l.tytul}</strong></td>
                    <td>${l.inwestor || "Prywatny"}</td>
                    <td>${l.lokalizacja || "N/A"}</td>
                    <td>${odooBadge}</td>
                    <td>${statusBadge}</td>
                    <td>${dateStr}</td>
                    <td><span class="${priorityClass}">${l.priorytet}</span></td>
                    <td>
                        <a href="${l.url}" target="_blank" class="btn-secondary" style="padding: 6px 12px; font-size: 12px; text-decoration: none;">
                            <i class="fa-solid fa-external-link"></i> Źródło
                        </a>
                    </td>
                </tr>
            `;
        }).join("");
    }

    // --- Accounts & Multi-tenancy CRUD ---
    async function loadAccountsData() {
        accountsContainer.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Ładowanie kampanii...</div>`;
        try {
            const accounts = await apiRequest("/api/accounts");
            accountsList = accounts;
            renderAccounts(accounts);
            populateCampaignFilter(accounts);
            populateSandboxCampaigns(accounts);
        } catch (e) {
            accountsContainer.innerHTML = `<div class="loading-state text-error">Nie udało się załadować kont.</div>`;
        }
    }

    async function loadPendingLeads() {
        const section = document.getElementById("pending-leads-section");
        const tbody = document.getElementById("pending-leads-table-body");
        if (!section || !tbody) return;
        try {
            const data = await apiRequest("/api/leads/pending");
            if (data.count === 0) {
                section.classList.add("hidden");
                return;
            }
            section.classList.remove("hidden");
            tbody.innerHTML = data.leads.map(l => `
                <tr>
                    <td><strong>${l.tytul}</strong></td>
                    <td>${l.inwestor || 'N/A'}</td>
                    <td>${l.lokalizacja || 'N/A'}</td>
                    <td><span class="priority-${l.priorytet}">${l.priorytet}</span></td>
                    <td>
                        <button class="btn-primary approve-lead-btn" data-id="${l.id}" style="padding: 5px 10px; font-size: 12px;">
                            <i class="fa-solid fa-check"></i> Zatwierdź
                        </button>
                        <a href="${l.url}" target="_blank" class="btn-secondary" style="padding: 5px 10px; font-size: 12px; text-decoration: none; margin-left: 4px;">
                            <i class="fa-solid fa-external-link"></i>
                        </a>
                    </td>
                </tr>
            `).join("");
            document.querySelectorAll(".approve-lead-btn").forEach(btn => {
                btn.addEventListener("click", async () => {
                    const leadId = parseInt(btn.dataset.id);
                    btn.disabled = true;
                    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
                    try {
                        const res = await apiRequest(`/api/leads/${leadId}/approve`, { method: "POST" });
                        if (res.approved) {
                            showToast(`Lead #${leadId} zatwierdzony i wysłany do Odoo (ID: ${res.odoo_id || 'brak'}).`);
                            loadPendingLeads();
                            loadDashboardData();
                        }
                    } catch(e) {
                        showToast(`Błąd zatwierdzania: ${e.message}`, "error");
                        btn.disabled = false;
                        btn.innerHTML = `<i class="fa-solid fa-check"></i> Zatwierdź`;
                    }
                });
            });
        } catch(e) {
            section.classList.add("hidden");
        }
    }

    async function scanAccount(accountId, btn) {
        const acc = accountsList.find(a => a.id === accountId);
        const campaignName = acc ? acc.name : `ID ${accountId}`;
        
        btn.disabled = true;
        const originalHtml = btn.innerHTML;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ...`;
        showToast(`Rozpoczęto skanowanie dla kampanii: ${campaignName}...`, "warning");

        try {
            const settings = await apiRequest("/api/settings");
            const tokenSetting = settings.find(s => s.key === "API_TOKEN");
            const token = tokenSetting ? tokenSetting.value : "";
            
            const res = await fetch(`/trigger-osint?account_id=${accountId}`, {
                method: "POST",
                headers: { "X-API-Token": token }
            });
            const data = await res.json();
            
            if (data.triggered) {
                const s = data.stats;
                showToast(`Skan kampanii "${campaignName}" ukończony! Znaleziono: ${s.leads_found}, Nowe: ${s.leads_new}, Odoo OK: ${s.odoo_ok}`);
                loadDashboardData();
                checkNotificationGate();
            }
        } catch (e) {
            showToast(`Błąd skanowania: ${e.message}`, "error");
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }

    function renderAccounts(accounts) {
        populateSandboxCampaigns(accountsList);
        if (accounts.length === 0) {
            accountsContainer.innerHTML = `<div class="loading-state">Brak aktywnych kampanii. Dodaj pierwszą klikając „Dodaj Kampanię”.</div>`;
            return;
        }

        accountsContainer.innerHTML = accounts.map(acc => {
            const cpvs = acc.target_cpvs.join(", ") || "Brak";
            const keywords = acc.target_keywords.join(", ") || "Brak";
            let sourcesList = acc.enabled_sources;
            if (typeof sourcesList === "string") {
                try { sourcesList = JSON.parse(sourcesList); } catch(e) { sourcesList = null; }
            }
            const sourcesDisplay = Array.isArray(sourcesList) && sourcesList.length > 0 ? sourcesList.join(", ") : "BZP, Google, GUNB";
            const statusBadge = acc.is_active 
                ? `<span class="badge badge-active">Aktywna</span>` 
                : `<span class="badge badge-inactive">Nieaktywna</span>`;
                
            const userIdDisplay = acc.odoo_user_id !== null ? acc.odoo_user_id : "<i>Nieprzypisane (Puste)</i>";

            return `
                <div class="account-card glass-card">
                    <div class="account-card-header">
                        <div>
                            <h4>${acc.name}</h4>
                            <small>${acc.llm_model} | Temp: ${acc.llm_temperature}</small>
                        </div>
                        ${statusBadge}
                    </div>
                    
                    <div class="account-details">
                        <div class="detail-row">
                            <span>Kody CPV:</span>
                            <span title="${cpvs}">${cpvs.length > 25 ? cpvs.slice(0, 25) + "..." : cpvs}</span>
                        </div>
                        <div class="detail-row">
                            <span>Słowa kluczowe:</span>
                            <span title="${keywords}">${keywords.length > 25 ? keywords.slice(0, 25) + "..." : keywords}</span>
                        </div>
                        <div class="detail-row">
                            <span>Źródła:</span>
                            <span>${sourcesDisplay}</span>
                        </div>
                        <div class="detail-row">
                            <span>Odoo Company ID:</span>
                            <span>${acc.odoo_company_id || "Brak"}</span>
                        </div>
                        <div class="detail-row">
                            <span>Odoo User ID:</span>
                            <span>${userIdDisplay}</span>
                        </div>
                        <div class="detail-row">
                            <span>Odoo Tag IDs:</span>
                            <span>${acc.odoo_tag_ids && acc.odoo_tag_ids.length > 0 ? acc.odoo_tag_ids.join(", ") : "Brak"}</span>
                        </div>
                        <div class="detail-row">
                            <span>Odoo Team ID:</span>
                            <span>${acc.odoo_team_id || "Brak"}</span>
                        </div>
                    </div>
                    
                    <div class="account-card-actions">
                        <button class="btn-primary scan-acc-btn" data-id="${acc.id}" style="padding: 6px 12px; font-size: 13px;">
                            <i class="fa-solid fa-play"></i> Skanuj
                        </button>
                        <button class="btn-secondary edit-acc-btn" data-id="${acc.id}">
                            <i class="fa-solid fa-pen-to-square"></i> Edytuj
                        </button>
                        <button class="btn-secondary btn-logout delete-acc-btn" data-id="${acc.id}">
                            <i class="fa-solid fa-trash"></i> Usuń
                        </button>
                    </div>
                </div>
            `;
        }).join("");

        // Attach listeners
        document.querySelectorAll(".scan-acc-btn").forEach(btn => {
            btn.addEventListener("click", () => scanAccount(parseInt(btn.dataset.id), btn));
        });
        document.querySelectorAll(".edit-acc-btn").forEach(btn => {
            btn.addEventListener("click", () => openAccountModal(parseInt(btn.dataset.id)));
        });
        document.querySelectorAll(".delete-acc-btn").forEach(btn => {
            btn.addEventListener("click", () => deleteAccount(parseInt(btn.dataset.id)));
        });
    }

    // Modal Add/Edit
    addAccountBtn.addEventListener("click", () => openAccountModal());
    modalCloseBtn.addEventListener("click", closeAccountModal);
    modalCancelBtn.addEventListener("click", closeAccountModal);

    async function renderSourcesCheckboxes(enabledSources = null) {
        const container = document.getElementById("search-sources-container");
        if (!container) return;

        try {
            const sources = await apiRequest("/api/sources");
            if (!Array.isArray(sources)) return;

            container.innerHTML = sources.map(source => {
                const isChecked = enabledSources === null 
                    ? true 
                    : (Array.isArray(enabledSources) && enabledSources.includes(source.id));
                const sanitizedId = (source.id || "").toLowerCase().replace(/[^a-z0-9]/g, "-");
                return `
                    <div class="checkbox-option" style="margin-bottom: 8px;">
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="src-${sanitizedId}" value="${source.id}" ${isChecked ? 'checked' : ''}>
                            <strong>${source.name}</strong>
                        </label>
                        <small style="color: var(--text-muted); display: block; margin-left: 24px;">${source.description}</small>
                    </div>
                `;
            }).join("");
        } catch (err) {
            console.error("Błąd podczas renderowania źródeł OSINT:", err);
        }
    }

    async function openAccountModal(accountId = null) {
        accountForm.reset();
        accountIdInput.value = "";
        
        if (accountId) {
            const acc = accountsList.find(a => a.id === accountId);
            if (acc) {
                modalTitle.textContent = "Edytuj Kampanię";
                accountIdInput.value = acc.id;
                document.getElementById("acc-name").value = acc.name;
                document.getElementById("acc-model").value = acc.llm_model;
                document.getElementById("acc-temperature").value = acc.llm_temperature;
                document.getElementById("acc-max-tokens").value = acc.llm_max_tokens;
                document.getElementById("acc-cpvs").value = acc.target_cpvs.join(", ");
                document.getElementById("acc-keywords").value = acc.target_keywords.join(", ");
                
                let sources = acc.enabled_sources || ["BZP", "Google", "GUNB"];
                if (typeof sources === "string") {
                    try { sources = JSON.parse(sources); } catch(e) { sources = ["BZP", "Google", "GUNB"]; }
                }
                await renderSourcesCheckboxes(sources);

                document.getElementById("acc-company-id").value = acc.odoo_company_id || "";
                document.getElementById("acc-user-id").value = acc.odoo_user_id !== null ? acc.odoo_user_id : "";
                document.getElementById("acc-tag-ids").value = acc.odoo_tag_ids.join(", ");
                document.getElementById("acc-team-id").value = acc.odoo_team_id || "";
                document.getElementById("acc-source-id").value = acc.odoo_source_id || "";
                document.getElementById("acc-active").checked = acc.is_active;
                
                if (acc.custom_prompt) {
                    document.getElementById("acc-prompt").value = acc.custom_prompt;
                } else {
                    const defaultPromptData = await apiRequest("/api/settings/default-prompt");
                    document.getElementById("acc-prompt").value = defaultPromptData ? defaultPromptData.default_prompt : "";
                }
            }
        } else {
            modalTitle.textContent = "Dodaj Nową Kampanię";
            await renderSourcesCheckboxes(null);
            const defaultPromptData = await apiRequest("/api/settings/default-prompt");
            document.getElementById("acc-prompt").value = defaultPromptData ? defaultPromptData.default_prompt : "";
        }

        // Load prompt version history
        if (accountId) {
            loadPromptVersionHistory(accountId);
            document.getElementById('prompt-version-section').classList.remove('hidden');
        } else {
            document.getElementById('prompt-version-section').classList.add('hidden');
        }

        accountModal.classList.remove("hidden");
    }

    function closeAccountModal() {
        accountModal.classList.add("hidden");
    }

    async function loadPromptVersionHistory(accountId) {
        const listEl = document.getElementById('prompt-version-list');
        try {
            const versions = await apiRequest(`/api/analytics/prompts?account_id=${accountId}`);
            if (!versions || versions.length === 0) {
                listEl.innerHTML = '<div style="color:var(--text-muted);font-size:0.8rem;">Brak historii wersji promptu.</div>';
                return;
            }
            listEl.innerHTML = versions.map(v => `
                <div class="version-item" style="padding:8px 10px;border-radius:6px;background:rgba(255,255,255,0.04);margin-bottom:6px;font-size:0.8rem; position:relative;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px; padding-right:80px;">
                        <span style="color:var(--accent-primary);font-weight:600;">v${v.version}</span>
                        <span style="color:var(--text-muted);">${new Date(v.created_at).toLocaleDateString('pl-PL')}</span>
                    </div>
                    <div style="color:var(--text-secondary);margin-bottom:4px; padding-right:80px;">
                        ${v.total_leads} leadów | 🏆 ${v.won_leads} wygranych (${v.conversion_rate}%)
                    </div>
                    <div style="color:var(--text-muted);font-size:0.75rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; padding-right:80px;">${v.prompt_preview}...</div>
                    <button type="button" class="btn-primary restore-prompt-btn" 
                            data-version="${v.version}"
                            style="position:absolute; right:8px; top:50%; transform:translateY(-50%); padding:4px 8px; font-size:11px; height:auto; width:auto;">
                        Przywróć
                    </button>
                </div>
            `).join('');

            // Wire event listeners to the Restore buttons
            const buttons = listEl.querySelectorAll('.restore-prompt-btn');
            buttons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const versionNum = parseInt(btn.getAttribute('data-version'));
                    const found = versions.find(v => v.version === versionNum);
                    if (found && found.prompt_text) {
                        const promptTextarea = document.getElementById('acc-prompt');
                        if (promptTextarea) {
                            promptTextarea.value = found.prompt_text;
                            showToast(`Przywrócono treść promptu z wersji v${found.version}!`, "success");
                        }
                    }
                });
            });
        } catch(e) {
            listEl.innerHTML = '<div style="color:var(--text-muted);font-size:0.8rem;">Błąd ładowania historii.</div>';
        }
    }

    // Submit Account Form (Create/Update)
    accountForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const accountId = accountIdInput.value;
        const cpvs = document.getElementById("acc-cpvs").value.split(",").map(s => s.trim()).filter(Boolean);
        const keywords = document.getElementById("acc-keywords").value.split(",").map(s => s.trim()).filter(Boolean);
        
        const enabledSources = Array.from(
            document.querySelectorAll(".search-sources-group input[type='checkbox']:checked")
        ).map(cb => cb.value);

        if (enabledSources.length === 0) {
            showToast("Wybierz co najmniej jedno źródło wyszukiwania.", "error");
            return;
        }

        const tags = document.getElementById("acc-tag-ids").value.split(",").map(s => parseInt(s.trim())).filter(n => !isNaN(n));
        
        const companyIdVal = document.getElementById("acc-company-id").value;
        const userIdVal = document.getElementById("acc-user-id").value;
        const teamIdVal = document.getElementById("acc-team-id").value;
        const sourceIdVal = document.getElementById("acc-source-id").value;

        const payload = {
            name: document.getElementById("acc-name").value,
            target_cpvs: cpvs,
            target_keywords: keywords,
            enabled_sources: enabledSources,
            custom_prompt: document.getElementById("acc-prompt").value || null,
            llm_model: document.getElementById("acc-model").value,
            llm_temperature: parseFloat(document.getElementById("acc-temperature").value),
            llm_max_tokens: parseInt(document.getElementById("acc-max-tokens").value),
            odoo_company_id: companyIdVal ? parseInt(companyIdVal) : null,
            odoo_user_id: userIdVal ? parseInt(userIdVal) : null, // Pozwala pozostać pustym
            odoo_tag_ids: tags,
            odoo_team_id: teamIdVal ? parseInt(teamIdVal) : null,
            odoo_source_id: sourceIdVal ? parseInt(sourceIdVal) : null,
            is_active: document.getElementById("acc-active").checked
        };

        const method = accountId ? "PUT" : "POST";
        const url = accountId ? `/api/accounts/${accountId}` : "/api/accounts";

        try {
            await apiRequest(url, {
                method: method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            showToast(accountId ? "Kampania zaktualizowana." : "Kampania utworzona pomyślnie.");
            closeAccountModal();
            loadAccountsData();
        } catch (e) {
            // Error managed by apiRequest toast
        }
    });

    // Delete Account
    async function deleteAccount(accountId) {
        if (!confirm("Czy na pewno chcesz trwale usunąć tę kampanię? Spowoduje to również usunięcie jej logów.")) return;
        try {
            await apiRequest(`/api/accounts/${accountId}`, { method: "DELETE" });
            showToast("Kampania usunięta.");
            loadAccountsData();
        } catch (e) {}
    }

    // --- Sandbox (Piaskownica promptów) ---
    sandboxTemp.addEventListener("input", (e) => {
        sandboxTempval.textContent = e.target.value;
    });
    
    function populateSandboxCampaigns(accounts) {
        const select = document.getElementById("sandbox-campaign-select");
        if (!select) return;
        select.innerHTML = '<option value="">Wybierz kampanię (opcjonalnie)</option>';
        accounts.filter(a => a.is_active).forEach(acc => {
            const opt = document.createElement("option");
            opt.value = acc.id;
            opt.textContent = acc.name;
            select.appendChild(opt);
        });
    }

    async function populateSandboxSources() {
        const select = document.getElementById("sandbox-source-select");
        if (!select) return;
        try {
            const sources = await apiRequest("/api/sources");
            if (Array.isArray(sources)) {
                select.innerHTML = '';
                sources.forEach(src => {
                    const opt = document.createElement("option");
                    opt.value = src.id;
                    opt.textContent = src.name;
                    select.appendChild(opt);
                });
                const defOpt = document.createElement("option");
                defOpt.value = "DOMSanitizer";
                defOpt.textContent = "Domyślny scraper";
                select.appendChild(defOpt);
            }
        } catch (err) {
            console.error("Failed to load sandbox sources", err);
        }
    }

    const sandboxCampaignSelect = document.getElementById("sandbox-campaign-select");
    if (sandboxCampaignSelect) {
        sandboxCampaignSelect.addEventListener("change", async (e) => {
            const accId = e.target.value;
            const promptArea = document.getElementById("sandbox-prompt");
            if (!accId) {
                const defaultPromptData = await apiRequest("/api/settings/default-prompt");
                promptArea.value = defaultPromptData ? defaultPromptData.default_prompt : "";
                return;
            }
            const acc = accountsList.find(a => a.id === parseInt(accId));
            if (acc) {
                if (acc.custom_prompt) {
                    promptArea.value = acc.custom_prompt;
                } else {
                    const defaultPromptData = await apiRequest("/api/settings/default-prompt");
                    promptArea.value = defaultPromptData ? defaultPromptData.default_prompt : "";
                }
            }
        });
    }

    const sandboxFetchBtn = document.getElementById("sandbox-fetch-btn");
    if (sandboxFetchBtn) {
        sandboxFetchBtn.addEventListener("click", async () => {
            const urlInput = document.getElementById("sandbox-url").value;
            if (!urlInput) {
                showToast("Podaj URL do pobrania.", "error");
                return;
            }
            const textArea = document.getElementById("sandbox-text");
            const originalHtml = sandboxFetchBtn.innerHTML;
            sandboxFetchBtn.disabled = true;
            sandboxFetchBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            try {
                const sourceSelect = document.getElementById("sandbox-source-select");
                const res = await apiRequest("/api/sandbox/fetch-url", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url: urlInput, source: sourceSelect ? sourceSelect.value : "DOMSanitizer" })
                });
                if (res && res.success) {
                    textArea.value = res.clean_text;
                    showToast("Treść pobrana i wyczyszczona z HTML.");
                } else {
                    showToast(`Błąd pobierania: ${res.error || "Nieznany"}`, "error");
                }
            } catch (err) {
                showToast(`Błąd: ${err.message}`, "error");
            } finally {
                sandboxFetchBtn.disabled = false;
                sandboxFetchBtn.innerHTML = originalHtml;
            }
        });
    }

    sandboxForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const btn = document.getElementById("run-sandbox-btn");
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Analizowanie przez AI...`;
        
        sandboxOutput.textContent = "Wysyłanie danych do Gemini...";

        const payload = {
            raw_text: document.getElementById("sandbox-text").value || null,
            url: document.getElementById("sandbox-url").value || null,
            prompt: document.getElementById("sandbox-prompt").value,
            llm_model: document.getElementById("sandbox-model").value,
            llm_temperature: parseFloat(sandboxTemp.value),
            llm_max_tokens: 4096,
            source: document.getElementById("sandbox-source-select") ? document.getElementById("sandbox-source-select").value : "DOMSanitizer"
        };

        try {
            const res = await apiRequest("/api/sandbox/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            
            if (res && res.success) {
                sandboxOutput.textContent = res.output;
                if (res.fetched_text && !document.getElementById("sandbox-text").value) {
                    document.getElementById("sandbox-text").value = res.fetched_text;
                }
            } else {
                sandboxOutput.textContent = `Błąd: ${res.error || "Nieznany błąd."}`;
            }
        } catch (err) {
            sandboxOutput.textContent = `Błąd połączenia z API: ${err.message}`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-play"></i> Uruchom Test AI`;
        }
    });

    // --- Logs (Hard Proof Viewer) ---
    let allLogs = [];

    async function loadLogsData() {
        logsTableBody.innerHTML = `<tr><td colspan="9" class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Ładowanie rejestru...</td></tr>`;
        try {
            // Ensure accounts list is loaded to populate the campaign dropdown
            if (accountsList.length === 0) {
                const accounts = await apiRequest("/api/accounts");
                accountsList = accounts || [];
                populateCampaignFilter(accountsList);
            }
            
            const logs = await apiRequest("/api/logs");
            allLogs = logs || [];
            applyLogFilters();
        } catch (e) {
            logsTableBody.innerHTML = `<tr><td colspan="9" class="loading-state text-error">Błąd pobierania rejestru.</td></tr>`;
        }
    }

    function populateCampaignFilter(accounts) {
        const select = document.getElementById("log-filter-campaign");
        if (!select) return;
        
        select.innerHTML = '<option value="">Wszystkie kampanie</option>';
        accounts.forEach(acc => {
            const opt = document.createElement("option");
            opt.value = acc.id;
            opt.textContent = acc.name;
            select.appendChild(opt);
        });
    }

    function applyLogFilters() {
        const searchText = document.getElementById("log-search").value.toLowerCase();
        const campaignFilter = document.getElementById("log-filter-campaign").value;
        const statusFilter = document.getElementById("log-filter-status").value;
        const sourceFilter = document.getElementById("log-filter-source").value;
        const dateStart = document.getElementById("log-filter-date-start").value;
        const dateEnd = document.getElementById("log-filter-date-end").value;

        const filtered = allLogs.filter(log => {
            // 1. Text search
            if (searchText) {
                const campaignName = (log.account_name || "").toLowerCase();
                const logText = (log.log_text || "").toLowerCase();
                const source = (log.source || "").toLowerCase();
                const hash = (log.raw_response_hash || "").toLowerCase();
                
                const match = campaignName.includes(searchText) || 
                              logText.includes(searchText) || 
                              source.includes(searchText) || 
                              hash.includes(searchText);
                if (!match) return false;
            }

            // 2. Campaign filter
            if (campaignFilter && String(log.account_id) !== String(campaignFilter)) {
                return false;
            }

            // 3. Status filter (success = 200, error != 200)
            if (statusFilter) {
                const isSuccess = log.response_status_code === 200;
                if (statusFilter === "success" && !isSuccess) return false;
                if (statusFilter === "error" && isSuccess) return false;
            }

            // 4. Source filter
            if (sourceFilter && log.source !== sourceFilter) {
                return false;
            }

            // 5. Date range filter
            if (dateStart || dateEnd) {
                const logDate = log.timestamp.split("T")[0]; // YYYY-MM-DD
                if (dateStart && logDate < dateStart) return false;
                if (dateEnd && logDate > dateEnd) return false;
            }

            return true;
        });

        renderLogs(filtered);
    }

    function renderLogs(logs) {
        if (logs.length === 0) {
            logsTableBody.innerHTML = `<tr><td colspan="9" class="loading-state">Brak wpisów w rejestrze spełniających kryteria.</td></tr>`;
            return;
        }

        logsTableBody.innerHTML = logs.map(log => {
            const timeStr = log.timestamp.replace("T", " ").slice(0, 19);
            const statusClass = log.response_status_code === 200 ? "priority-sredni" : "priority-high";
            const shortHash = log.raw_response_hash ? log.raw_response_hash.slice(0, 8) + "..." : "brak";
            
            // Odoo Mapping details for multicompany compliance checking
            const companyDisplay = log.odoo_company_id !== null ? log.odoo_company_id : "—";
            const userDisplay = log.odoo_user_id !== null ? log.odoo_user_id : "—";
            const tagsDisplay = log.odoo_tag_ids && log.odoo_tag_ids.length > 0 ? log.odoo_tag_ids.join(",") : "—";
            const odooMapStr = `Co: ${companyDisplay} / Usr: ${userDisplay} / Tags: ${tagsDisplay}`;

            return `
                <tr>
                    <td>${timeStr}</td>
                    <td><strong>${log.account_name}</strong></td>
                    <td><span class="badge badge-active">${log.source}</span></td>
                    <td title="Pełny Hash SHA-256: ${log.raw_response_hash}"><code>${shortHash}</code></td>
                    <td><span class="${statusClass}">${log.response_status_code}</span></td>
                    <td>${log.leads_found_count}</td>
                    <td>${log.leads_created_count}</td>
                    <td><small style="color: var(--text-muted); font-family: monospace;">${odooMapStr}</small></td>
                    <td>
                        <button class="btn-secondary view-log-details-btn" data-id="${log.id}" style="padding: 6px 12px; font-size: 12px;">
                            <i class="fa-solid fa-eye"></i> Szczegóły
                        </button>
                    </td>
                </tr>
            `;
        }).join("");

        // Bind details buttons
        document.querySelectorAll(".view-log-details-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const logId = parseInt(btn.dataset.id);
                openLogDetailsModal(logId);
            });
        });
    }

    function openLogDetailsModal(logId) {
        const log = allLogs.find(l => l.id === logId);
        if (!log) return;

        document.getElementById("log-detail-campaign").textContent = log.account_name;
        document.getElementById("log-detail-timestamp").textContent = log.timestamp.replace("T", " ").slice(0, 19);
        document.getElementById("log-detail-source").textContent = log.source;
        
        const statusSpan = document.getElementById("log-detail-status");
        statusSpan.textContent = log.response_status_code;
        statusSpan.className = log.response_status_code === 200 ? "badge badge-active" : "badge priority-high";
        
        document.getElementById("log-detail-found").textContent = log.leads_found_count;
        document.getElementById("log-detail-created").textContent = log.leads_created_count;
        document.getElementById("log-detail-hash").textContent = log.raw_response_hash || "Brak hasha";
        
        document.getElementById("log-detail-params").textContent = JSON.stringify(log.query_params, null, 2);
        
        document.getElementById("log-detail-odoo-company").textContent = log.odoo_company_id !== null ? log.odoo_company_id : "Nieprzypisane (Puste)";
        document.getElementById("log-detail-odoo-user").textContent = log.odoo_user_id !== null ? log.odoo_user_id : "Nieprzypisane (Puste)";
        document.getElementById("log-detail-odoo-tags").textContent = log.odoo_tag_ids && log.odoo_tag_ids.length > 0 ? log.odoo_tag_ids.join(", ") : "Brak tagów";
        document.getElementById("log-detail-odoo-team").textContent = log.odoo_team_id !== null ? log.odoo_team_id : "Nieprzypisane (Puste)";
        document.getElementById("log-detail-odoo-source").textContent = log.odoo_source_id !== null ? log.odoo_source_id : "Nieprzypisane (Puste)";
        
        document.getElementById("log-detail-text").textContent = log.log_text || "Brak dodatkowego tekstu logu.";

        document.getElementById("log-modal").classList.remove("hidden");
    }

    function closeLogDetailsModal() {
        document.getElementById("log-modal").classList.add("hidden");
    }

    // --- Settings (.env) ---
    async function loadSettingsData() {
        settingsFieldsContainer.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Ładowanie ustawień...</div>`;
        try {
            const settings = await apiRequest("/api/settings");
            renderSettings(settings);
        } catch (e) {
            settingsFieldsContainer.innerHTML = `<div class="loading-state text-error">Błąd pobierania ustawień.</div>`;
        }
    }

    function renderSettings(settings) {
        settingsFieldsContainer.innerHTML = settings.map(s => {
            let type = "text";
            if (s.key.includes("KEY") || s.key.includes("PASSWORD") || s.key.includes("TOKEN")) {
                type = "password";
            }
            
            return `
                <div class="form-group">
                    <label for="setting-${s.key}"><code>${s.key}</code></label>
                    <input type="${type}" id="setting-${s.key}" data-key="${s.key}" value="${s.value}" placeholder="Podaj nową wartość dla ${s.key}">
                </div>
            `;
        }).join("");
    }

    settingsForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const inputs = settingsFieldsContainer.querySelectorAll("input");
        let savedCount = 0;
        
        for (const input of inputs) {
            const key = input.dataset.key;
            const val = input.value;
            
            // Jeśli użytkownik nie edytował zamaskowanego pola (zaczyna się od kropki), pomijamy
            if (val.startsWith("...") || val.endsWith("...")) {
                continue;
            }
            
            try {
                await apiRequest("/api/settings", {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ key: key, value: val })
                });
                savedCount++;
            } catch (err) {}
        }
        
        if (savedCount > 0) {
            showToast(`Zapisano ${savedCount} ustawień.`);
            loadSettingsData();
        } else {
            showToast("Brak zmian do zapisu.", "warning");
        }
    });

    // --- Trigger OSINT Scan ---
    triggerScanBtn.addEventListener("click", async () => {
        triggerScanBtn.disabled = true;
        triggerScanBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Wyszukiwanie leadów...`;
        showToast("Rozpoczęto skanowanie OSINT w tle...", "warning");

        try {
            const settings = await apiRequest("/api/settings");
            const tokenSetting = settings.find(s => s.key === "API_TOKEN");
            const token = tokenSetting ? tokenSetting.value : "";
            
            const res = await fetch("/trigger-osint", {
                method: "POST",
                headers: { "X-API-Token": token }
            });
            const data = await res.json();
            
            if (data.triggered) {
                const s = data.stats;
                showToast(`Skan ukończony! Znaleziono: ${s.leads_found}, Nowe: ${s.leads_new}, Odoo OK: ${s.odoo_ok}`);
                loadDashboardData();
                checkNotificationGate();
            }
        } catch (e) {
            showToast(`Błąd skanowania: ${e.message}`, "error");
        } finally {
            triggerScanBtn.disabled = false;
            triggerScanBtn.innerHTML = `<i class="fa-solid fa-bolt"></i> Uruchom Skanowanie`;
        }
    });

    // --- Change Password Form ---
    const changePasswordForm = document.getElementById("change-password-form");
    if (changePasswordForm) {
        changePasswordForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const oldPwd = document.getElementById("old-password").value;
            const newPwd = document.getElementById("new-password").value;
            
            try {
                const res = await apiRequest("/api/auth/change-password", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ old_password: oldPwd, new_password: newPwd })
                });
                if (res && res.success) {
                    showToast("Hasło zostało pomyślnie zmienione.");
                    changePasswordForm.reset();
                }
            } catch (err) {
                // error alert handled by apiRequest
            }
        });
    }

    // --- Faza 3 Event Listeners for Filters ---
    const logSearchInput = document.getElementById("log-search");
    if (logSearchInput) logSearchInput.addEventListener("input", applyLogFilters);
    
    const logFilterCamp = document.getElementById("log-filter-campaign");
    if (logFilterCamp) logFilterCamp.addEventListener("change", applyLogFilters);
    
    const logFilterStat = document.getElementById("log-filter-status");
    if (logFilterStat) logFilterStat.addEventListener("change", applyLogFilters);
    
    const logFilterSrc = document.getElementById("log-filter-source");
    if (logFilterSrc) logFilterSrc.addEventListener("change", applyLogFilters);
    
    const logFilterStart = document.getElementById("log-filter-date-start");
    if (logFilterStart) logFilterStart.addEventListener("change", applyLogFilters);
    
    const logFilterEnd = document.getElementById("log-filter-date-end");
    if (logFilterEnd) logFilterEnd.addEventListener("change", applyLogFilters);

    // Modal close listeners for log details
    const logModalCloseBtn = document.getElementById("log-modal-close-btn");
    if (logModalCloseBtn) logModalCloseBtn.addEventListener("click", closeLogDetailsModal);
    
    const logModalOkBtn = document.getElementById("log-modal-ok-btn");
    if (logModalOkBtn) logModalOkBtn.addEventListener("click", closeLogDetailsModal);

    // --- Start ---
    checkSession();
});
