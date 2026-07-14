// app.js - Lead Dashboard Front-end Application

document.addEventListener("DOMContentLoaded", () => {
    // --- State ---
    let currentUser = null;
    let accountsList = [];

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

    // --- Dashboard & Leads ---
    async function loadDashboardData() {
        leadsTableBody.innerHTML = `<tr><td colspan="7" class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Ładowanie leadów...</td></tr>`;
        
        // Ponieważ API /leads wymaga nagłówka X-API-Token, pobierzemy go z bazy poprzez proxy /api/settings lub podamy token jeśli jest dostępny.
        // Jednak na Dashboardzie wygodniej pobrać listę z naszego endpointu. Stwórzmy małe obejście. Dla wygody Dashboardu
        // możemy bezpośrednio pobrać leady. Nasz endpoint /leads wymaga verify_token (API token).
        // Aby to uprościć, w backendzie GET /leads używa X-API-Token. Pobierzemy token z ustawień API na front-endzie.
        try {
            // Najpierw pobierzmy token API z bazy
            const settings = await apiRequest("/api/settings");
            const tokenSetting = settings.find(s => s.key === "API_TOKEN");
            const token = tokenSetting ? tokenSetting.value : "";
            
            // Pobieramy leady
            const res = await fetch("/leads?limit=100", {
                headers: { "X-API-Token": token }
            });
            const data = await res.json();
            
            // Wyświetlamy
            renderLeads(data.leads || []);
        } catch (e) {
            leadsTableBody.innerHTML = `<tr><td colspan="7" class="loading-state text-error">Błąd ładowania danych: ${e.message}</td></tr>`;
        }
    }

    function renderLeads(leads) {
        if (leads.length === 0) {
            leadsTableBody.innerHTML = `<tr><td colspan="7" class="loading-state">Brak znalezionych leadów.</td></tr>`;
            statTotalLeads.textContent = "0";
            statAutoScales.textContent = "0";
            statOdooLeads.textContent = "0";
            return;
        }

        statTotalLeads.textContent = leads.length;
        statAutoScales.textContent = leads.filter(l => l.tytul.toLowerCase().includes("waga") || l.zakres.toLowerCase().includes("waga")).length;
        statOdooLeads.textContent = leads.filter(l => l.odoo_id !== null).length;

        leadsTableBody.innerHTML = leads.map(l => {
            const dateStr = l.created_at ? l.created_at.slice(0, 10) : "N/A";
            const priorityClass = `priority-${l.priorytet}`;
            const odooBadge = l.odoo_id 
                ? `<span class="badge badge-active" title="Odoo ID: ${l.odoo_id}"><i class="fa-solid fa-cloud-arrow-up"></i> Odoo (${l.odoo_id})</span>`
                : `<span class="badge badge-inactive"><i class="fa-solid fa-cloud-arrow-down"></i> Brak</span>`;

            return `
                <tr>
                    <td><strong>${l.tytul}</strong></td>
                    <td>${l.inwestor || "Prywatny"}</td>
                    <td>${l.lokalizacja || "N/A"}</td>
                    <td>${odooBadge}</td>
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
        } catch (e) {
            accountsContainer.innerHTML = `<div class="loading-state text-error">Nie udało się załadować kont.</div>`;
        }
    }

    function renderAccounts(accounts) {
        if (accounts.length === 0) {
            accountsContainer.innerHTML = `<div class="loading-state">Brak aktywnych kampanii. Dodaj pierwszą klikając „Dodaj Kampanię”.</div>`;
            return;
        }

        accountsContainer.innerHTML = accounts.map(acc => {
            const cpvs = acc.target_cpvs.join(", ") || "Brak";
            const keywords = acc.target_keywords.join(", ") || "Brak";
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
                            <span>Odoo Company ID:</span>
                            <span>${acc.odoo_company_id || "Brak"}</span>
                        </div>
                        <div class="detail-row">
                            <span>Odoo User ID:</span>
                            <span>${userIdDisplay}</span>
                        </div>
                        <div class="detail-row">
                            <span>Odoo Team ID:</span>
                            <span>${acc.odoo_team_id || "Brak"}</span>
                        </div>
                    </div>
                    
                    <div class="account-card-actions">
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
            const defaultPromptData = await apiRequest("/api/settings/default-prompt");
            document.getElementById("acc-prompt").value = defaultPromptData ? defaultPromptData.default_prompt : "";
        }
        
        accountModal.classList.remove("hidden");
    }

    function closeAccountModal() {
        accountModal.classList.add("hidden");
    }

    // Submit Account Form (Create/Update)
    accountForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const accountId = accountIdInput.value;
        const cpvs = document.getElementById("acc-cpvs").value.split(",").map(s => s.trim()).filter(Boolean);
        const keywords = document.getElementById("acc-keywords").value.split(",").map(s => s.trim()).filter(Boolean);
        const tags = document.getElementById("acc-tag-ids").value.split(",").map(s => parseInt(s.trim())).filter(n => !isNaN(n));
        
        const companyIdVal = document.getElementById("acc-company-id").value;
        const userIdVal = document.getElementById("acc-user-id").value;
        const teamIdVal = document.getElementById("acc-team-id").value;
        const sourceIdVal = document.getElementById("acc-source-id").value;

        const payload = {
            name: document.getElementById("acc-name").value,
            target_cpvs: cpvs,
            target_keywords: keywords,
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

    sandboxForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const btn = document.getElementById("run-sandbox-btn");
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Analizowanie przez AI...`;
        
        sandboxOutput.textContent = "Wysyłanie danych do Gemini...";

        const payload = {
            raw_text: document.getElementById("sandbox-text").value,
            prompt: document.getElementById("sandbox-prompt").value,
            llm_model: document.getElementById("sandbox-model").value,
            llm_temperature: parseFloat(sandboxTemp.value),
            llm_max_tokens: 4096
        };

        try {
            const res = await apiRequest("/api/sandbox/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            
            if (res && res.success) {
                sandboxOutput.textContent = res.output;
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
    async function loadLogsData() {
        logsTableBody.innerHTML = `<tr><td colspan="7" class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Ładowanie rejestru...</td></tr>`;
        try {
            const logs = await apiRequest("/api/logs");
            renderLogs(logs);
        } catch (e) {
            logsTableBody.innerHTML = `<tr><td colspan="7" class="loading-state text-error">Błąd pobierania rejestru.</td></tr>`;
        }
    }

    function renderLogs(logs) {
        if (logs.length === 0) {
            logsTableBody.innerHTML = `<tr><td colspan="7" class="loading-state">Brak wpisów w rejestrze.</td></tr>`;
            return;
        }

        logsTableBody.innerHTML = logs.map(log => {
            const timeStr = log.timestamp.replace("T", " ").slice(0, 19);
            const statusClass = log.response_status_code === 200 ? "priority-sredni" : "priority-high";
            const shortHash = log.raw_response_hash ? log.raw_response_hash.slice(0, 8) + "..." : "brak";
            
            return `
                <tr>
                    <td>${timeStr}</td>
                    <td><strong>${log.account_name}</strong></td>
                    <td><span class="badge badge-active">${log.source}</span></td>
                    <td title="Pełny Hash SHA-256: ${log.raw_response_hash}"><code>${shortHash}</code></td>
                    <td><span class="${statusClass}">${log.response_status_code}</span></td>
                    <td>${log.leads_found_count}</td>
                    <td>${log.leads_created_count}</td>
                </tr>
            `;
        }).join("");
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
                showToast(`Skan ukończony! Znaleziono: ${s.found}, Nowe: ${s.new}, Odoo OK: ${s.odoo_ok}`);
                loadDashboardData();
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

    // --- Start ---
    checkSession();
});
