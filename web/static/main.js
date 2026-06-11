// Global App State
const state = {
    activeTab: 'dashboard',
    
    // Directory pagination & filters
    directory: {
        page: 1,
        limit: 20,
        search: '',
        region: '',
        stage: '',
        visa: '',
        sortBy: 'Company',
        sortDir: 'asc'
    },
    
    // Outreach review queue
    outreach: {
        companies: [],
        activeCompany: null
    },
    
    // CRM
    applications: []
};

// Initialize app when DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    initTabNavigation();
    loadConfigStatus();
    loadDashboardData();
    initDirectoryListeners();
    initCrmFormListener();
    
    // Initialize Lucide icons
    lucide.createIcons();
    
    // Periodic background task checker (polls every 5s if any task is running)
    setInterval(pollPipelineTasks, 5000);
});

// ---------------------------------------------------------------------------
// 1. Tab Navigation
// ---------------------------------------------------------------------------
function initTabNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');
            
            // Update active states
            navButtons.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            btn.classList.add('active');
            const targetPane = document.getElementById(`tab-${tabId}`);
            if (targetPane) {
                targetPane.classList.add('active');
            }
            
            state.activeTab = tabId;
            
            // Trigger tab-specific loads
            if (tabId === 'dashboard') {
                loadDashboardData();
            } else if (tabId === 'directory') {
                loadDirectoryData();
            } else if (tabId === 'outreach') {
                loadOutreachQueue();
            } else if (tabId === 'crm') {
                loadCrmBoard();
            }
        });
    });
}

// ---------------------------------------------------------------------------
// 2. Configuration & Dashboard Loading
// ---------------------------------------------------------------------------
async function loadConfigStatus() {
    try {
        const response = await fetch('/api/config-status');
        const data = await response.json();
        
        const dot = document.querySelector('.indicator-dot');
        const text = document.getElementById('creds-status-text');
        
        dot.className = 'indicator-dot'; // Reset
        
        if (data.gmail_token_exists && data.gmail_credentials_exists) {
            dot.classList.add('green');
            text.textContent = 'Gmail API Active';
        } else if (data.gmail_credentials_exists) {
            dot.classList.add('yellow');
            text.textContent = 'Gmail Setup Incomplete';
        } else {
            dot.classList.add('red');
            text.textContent = 'Credentials Missing';
        }
    } catch (err) {
        console.error("Failed to load config status:", err);
    }
}

async function loadDashboardData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // Populate core stats
        document.getElementById('stat-total-companies').textContent = data.database.total.toLocaleString();
        document.getElementById('stat-database-progress').textContent = `vs ${data.database.plan_min.toLocaleString()} plan minimum`;
        document.getElementById('bar-db-progress').style.width = `${data.database.percentage}%`;
        
        document.getElementById('stat-visa-confirmed').textContent = data.visa_signals.confirmed.toLocaleString();
        const visaRatio = data.database.total > 0 ? Math.round(data.visa_signals.confirmed / data.database.total * 100) : 0;
        document.getElementById('stat-visa-ratio').textContent = `${visaRatio}% of database`;
        
        document.getElementById('stat-shortlisted').textContent = data.shortlist.total.toLocaleString();
        document.getElementById('stat-score-range').textContent = `Avg Score: ${data.shortlist.avg_score}`;
        
        document.getElementById('stat-outreach-sent').textContent = data.outreach.total_contacted.toLocaleString();
        document.getElementById('stat-reply-rate').textContent = `${data.outreach.reply_rate}% reply rate`;
        
        // Populate regions
        const regionList = document.getElementById('region-metrics-list');
        regionList.innerHTML = '';
        data.regions.forEach(r => {
            regionList.innerHTML += `
                <div class="chart-item">
                    <div class="chart-header">
                        <span class="chart-label">${r.name}</span>
                        <span class="chart-value">${r.percentage}% <span class="chart-target">(${r.count.toLocaleString()} companies)</span></span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill primary" style="width: ${r.percentage}%"></div>
                    </div>
                </div>
            `;
        });
        
        // Populate stages
        const stageList = document.getElementById('stage-metrics-list');
        stageList.innerHTML = '';
        data.stages.forEach(s => {
            stageList.innerHTML += `
                <div class="chart-item">
                    <div class="chart-header">
                        <span class="chart-label">${s.name}</span>
                        <span class="chart-value">${s.percentage}% <span class="chart-target">(${s.count.toLocaleString()} companies)</span></span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill green" style="width: ${s.percentage}%"></div>
                    </div>
                </div>
            `;
        });
        
        // Populate visa signals list
        const visaList = document.getElementById('visa-signals-list');
        visaList.innerHTML = `
            <div class="visa-signal-pill green">
                <i data-lucide="check-circle-2"></i>
                <div class="visa-signal-info">
                    <span class="visa-signal-val">${data.visa_signals.confirmed}</span>
                    <span class="visa-signal-lbl">Confirmed Visa Sponsors</span>
                </div>
            </div>
            <div class="visa-signal-pill blue">
                <i data-lucide="help-circle"></i>
                <div class="visa-signal-info">
                    <span class="visa-signal-val">${data.visa_signals.possible}</span>
                    <span class="visa-signal-lbl">EU Blue Card Possible</span>
                </div>
            </div>
            <div class="visa-signal-pill yellow">
                <i data-lucide="globe"></i>
                <div class="visa-signal-info">
                    <span class="visa-signal-val">${data.visa_signals.remote}</span>
                    <span class="visa-signal-lbl">Remote / EOR Friendly</span>
                </div>
            </div>
            <div class="visa-signal-pill muted">
                <i data-lucide="alert-circle"></i>
                <div class="visa-signal-info">
                    <span class="visa-signal-val">${data.visa_signals.unknown}</span>
                    <span class="visa-signal-lbl">Visa Sponsorship Unknown</span>
                </div>
            </div>
        `;
        
        // Populate next steps
        const stepsList = document.getElementById('next-steps-list');
        stepsList.innerHTML = '';
        data.next_steps.forEach(step => {
            stepsList.innerHTML += `<li>${step}</li>`;
        });
        
        // Populate logs
        const logsList = document.getElementById('recent-logs-list');
        logsList.innerHTML = '';
        if (data.recent_runs.length === 0) {
            logsList.innerHTML = '<p class="editor-tip">No recent run history found.</p>';
        } else {
            data.recent_runs.forEach(log => {
                logsList.innerHTML += `
                    <div class="log-entry">
                        <div>
                            <div class="log-entry-source">${log.source}</div>
                            <div class="log-entry-date">${log.run_date}</div>
                        </div>
                        <div class="log-entry-added">+${log.added}</div>
                    </div>
                `;
            });
        }
        
        lucide.createIcons();
    } catch (err) {
        console.error("Error loading dashboard:", err);
    }
}

// ---------------------------------------------------------------------------
// 3. Employer Directory (Table)
// ---------------------------------------------------------------------------
function initDirectoryListeners() {
    const search = document.getElementById('directory-search');
    const region = document.getElementById('filter-region');
    const stage = document.getElementById('filter-stage');
    const visa = document.getElementById('filter-visa');
    const reset = document.getElementById('btn-reset-filters');
    
    // Add debounce to search
    let timeout = null;
    search.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            state.directory.search = search.value;
            state.directory.page = 1;
            loadDirectoryData();
        }, 300);
    });
    
    region.addEventListener('change', () => {
        state.directory.region = region.value;
        state.directory.page = 1;
        loadDirectoryData();
    });
    
    stage.addEventListener('change', () => {
        state.directory.stage = stage.value;
        state.directory.page = 1;
        loadDirectoryData();
    });
    
    visa.addEventListener('change', () => {
        state.directory.visa = visa.value;
        state.directory.page = 1;
        loadDirectoryData();
    });
    
    reset.addEventListener('click', () => {
        search.value = '';
        region.value = '';
        stage.value = '';
        visa.value = '';
        
        state.directory = {
            page: 1,
            limit: 20,
            search: '',
            region: '',
            stage: '',
            visa: '',
            sortBy: 'Company',
            sortDir: 'asc'
        };
        loadDirectoryData();
    });
    
    // Sorting headers listeners
    const headers = document.querySelectorAll('#directory-table th[data-sort]');
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const field = header.getAttribute('data-sort');
            if (state.directory.sortBy === field) {
                state.directory.sortDir = state.directory.sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                state.directory.sortBy = field;
                state.directory.sortDir = 'asc';
            }
            loadDirectoryData();
        });
    });
    
    // Pagination listeners
    document.getElementById('btn-pagination-prev').addEventListener('click', () => {
        if (state.directory.page > 1) {
            state.directory.page--;
            loadDirectoryData();
        }
    });
    
    document.getElementById('btn-pagination-next').addEventListener('click', () => {
        state.directory.page++;
        loadDirectoryData();
    });
}

async function loadDirectoryData() {
    const params = new URLSearchParams({
        page: state.directory.page,
        limit: state.directory.limit,
        sort_by: state.directory.sortBy,
        sort_dir: state.directory.sortDir
    });
    
    if (state.directory.search) params.append('search', state.directory.search);
    if (state.directory.region) params.append('region', state.directory.region);
    if (state.directory.stage) params.append('stage', state.directory.stage);
    if (state.directory.visa) params.append('visa', state.directory.visa);
    
    try {
        const response = await fetch(`/api/employers?${params.toString()}`);
        const data = await response.json();
        
        // Render headers state
        const headers = document.querySelectorAll('#directory-table th[data-sort]');
        headers.forEach(h => {
            const field = h.getAttribute('data-sort');
            const icon = h.querySelector('i');
            h.style.color = '';
            
            if (field === state.directory.sortBy) {
                h.style.color = 'var(--primary)';
                if (icon) {
                    icon.setAttribute('data-lucide', state.directory.sortDir === 'asc' ? 'chevron-up' : 'chevron-down');
                }
            } else {
                if (icon) {
                    icon.setAttribute('data-lucide', 'chevrons-up-down');
                }
            }
        });
        lucide.createIcons();
        
        // Render rows
        const tbody = document.getElementById('directory-table-body');
        tbody.innerHTML = '';
        
        if (data.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No matching employers found in the database.</td></tr>';
            document.getElementById('pagination-info').textContent = 'Showing 0-0 of 0 entries';
            document.getElementById('btn-pagination-prev').disabled = true;
            document.getElementById('btn-pagination-next').disabled = true;
            return;
        }
        
        data.data.forEach(row => {
            // Render Tech stack tags
            let techHTML = '';
            if (row.Tech_Stack && row.Tech_Stack !== 'Unknown') {
                const techs = row.Tech_Stack.split(/,|;/).map(t => t.trim()).slice(0, 4);
                techs.forEach(t => {
                    if (t) techHTML += `<span class="tech-tag">${t}</span>`;
                });
            } else {
                techHTML = '<span style="color: var(--text-muted)">Unknown</span>';
            }
            
            // Visa sponsorship label
            let visaHTML = '';
            const vs = row.Visa_Sponsorship ? row.Visa_Sponsorship.toLowerCase() : '';
            if (vs === 'yes') {
                visaHTML = `<span class="contact-status-lbl replied">Confirmed</span>`;
            } else if (vs === 'possible') {
                visaHTML = `<span class="contact-status-lbl sent">Blue Card</span>`;
            } else if (row.Remote && row.Remote.toLowerCase() === 'yes') {
                visaHTML = `<span class="contact-status-lbl sent" style="background-color: var(--info-bg); color: var(--info);">Remote</span>`;
            } else {
                visaHTML = `<span style="color: var(--text-muted)">Unknown</span>`;
            }
            
            // Score Badge
            const sc = parseInt(row.Score || 0);
            let scoreClass = 'low';
            if (sc >= 80) scoreClass = 'high';
            else if (sc >= 20) scoreClass = 'medium';
            
            tbody.innerHTML += `
                <tr>
                    <td><strong>${row.Company}</strong></td>
                    <td>${row.Sector || '<span style="color: var(--text-muted)">Unknown</span>'}</td>
                    <td>${row.Country || 'Global'}</td>
                    <td><div style="max-width: 250px">${techHTML}</div></td>
                    <td>${visaHTML}</td>
                    <td><span class="score-badge ${scoreClass}">${row.Score || '?'}</span></td>
                    <td><button class="table-action-btn" onclick="directAddCrm('${row.Company.replace(/'/g, "\\'")}', '${(row.Sector || '').replace(/'/g, "\\'")}')">Add to CRM</button></td>
                </tr>
            `;
        });
        
        // Render pagination state
        const start = (state.directory.page - 1) * state.directory.limit + 1;
        const end = Math.min(start + data.data.length - 1, data.total);
        document.getElementById('pagination-info').textContent = `Showing ${start}-${end} of ${data.total.toLocaleString()} entries`;
        
        document.getElementById('btn-pagination-prev').disabled = state.directory.page === 1;
        document.getElementById('btn-pagination-next').disabled = end >= data.total;
        
    } catch (err) {
        console.error("Error loading directory:", err);
    }
}

function directAddCrm(company, sector) {
    document.getElementById('crm-company').value = company;
    document.getElementById('crm-role').value = 'AI/Data Engineer';
    document.getElementById('crm-status').value = 'Shortlisted';
    document.getElementById('crm-notes').value = `Manually added from Master Database directory. Sector: ${sector}`;
    
    document.getElementById('modal-title').textContent = 'Add Application';
    document.getElementById('crm-modal').showModal();
}

// ---------------------------------------------------------------------------
// 4. Outreach Review Station (Personalization & Send)
// ---------------------------------------------------------------------------
async function loadOutreachQueue() {
    try {
        const response = await fetch('/api/shortlist');
        const data = await response.json();
        
        state.outreach.companies = data;
        
        document.getElementById('outreach-queue-count').textContent = data.length;
        
        const listContainer = document.getElementById('outreach-companies-list');
        listContainer.innerHTML = '';
        
        if (data.length === 0) {
            listContainer.innerHTML = '<p class="editor-tip" style="padding: 10px;">Queue is empty. Scrape and score companies to generate drafts.</p>';
            return;
        }
        
        data.forEach((comp, idx) => {
            let statusClass = 'unsent';
            let statusText = 'Unsent';
            
            if (comp.Outreach_Status === 'Sent' || comp.Outreach_Status === 'FollowedUp') {
                statusClass = 'sent';
                statusText = 'Sent';
            } else if (comp.Outreach_Status === 'Replied') {
                statusClass = 'replied';
                statusText = 'Replied';
            }
            
            const isSelected = state.outreach.activeCompany && state.outreach.activeCompany.Company === comp.Company;
            
            const card = document.createElement('div');
            card.className = `outreach-company-card ${isSelected ? 'selected' : ''}`;
            card.id = `outreach-card-${idx}`;
            card.innerHTML = `
                <div class="card-top">
                    <span class="card-name">${comp.Company}</span>
                    <span class="card-score">★ ${comp.Score || '?'}</span>
                </div>
                <div class="card-bottom">
                    <span>${comp.Country || 'Global'}</span>
                    <span class="contact-status-lbl ${statusClass}">${statusText}</span>
                </div>
            `;
            
            card.addEventListener('click', () => {
                // Remove previous selected
                document.querySelectorAll('.outreach-company-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                selectOutreachCompany(comp);
            });
            
            listContainer.appendChild(card);
        });
        
        // Re-select active company if still exists
        if (state.outreach.activeCompany) {
            const current = data.find(c => c.Company === state.outreach.activeCompany.Company);
            if (current) {
                selectOutreachCompany(current);
            }
        }
    } catch (err) {
        console.error("Error loading outreach shortlist:", err);
    }
}

function selectOutreachCompany(comp) {
    state.outreach.activeCompany = comp;
    
    // Toggle composer view
    document.getElementById('outreach-composer-placeholder').style.display = 'none';
    const composer = document.getElementById('outreach-composer-panel');
    composer.style.display = 'flex';
    
    // Fill fields
    document.getElementById('composer-company-name').textContent = comp.Company;
    document.getElementById('composer-company-details').textContent = `${comp.Sector || 'Tech'} · ${comp.Country || 'Global'} · Score ${comp.Score || '?'}`;
    
    const careersLink = document.getElementById('composer-careers-link');
    const jobUrl = comp.Best_Job_URL || comp.Careers_URL;
    if (jobUrl && jobUrl !== 'Unknown') {
        careersLink.href = jobUrl;
        careersLink.style.display = 'flex';
    } else {
        careersLink.style.display = 'none';
    }
    
    document.getElementById('composer-to').value = comp.To_Email || '';
    
    // Construct dynamic subject header
    const indiaTerms = ["india", "hyderabad", "bangalore", "bengaluru", "mumbai"];
    const isIndia = comp.Country && indiaTerms.some(t => comp.Country.toLowerCase().includes(t));
    const subject = isIndia 
        ? `AI/Data Engineer — ${comp.Company} | Hyderabad-Based, Immediate Joiner` 
        : `AI/Data Engineer — ${comp.Company} | EU Blue Card Eligible`;
        
    document.getElementById('composer-subject').value = subject;
    document.getElementById('composer-body').value = comp.Cold_Email_Draft || '';
    
    // Clear status log
    const statusLog = document.getElementById('composer-status-log');
    statusLog.textContent = '';
    statusLog.className = 'email-status-indicator';
    
    // Reset buttons state
    const sendBtn = document.getElementById('btn-send-email');
    sendBtn.disabled = false;
    
    if (comp.Outreach_Status === 'Sent' || comp.Outreach_Status === 'Replied') {
        statusLog.textContent = `✓ outreach previously sent on: ${comp.Outreach_Sent_At || 'date unknown'}`;
        statusLog.classList.add('replied');
    }
}

async function saveActiveDraft() {
    if (!state.outreach.activeCompany) return;
    
    const company = state.outreach.activeCompany.Company;
    const toEmail = document.getElementById('composer-to').value;
    const body = document.getElementById('composer-body').value;
    const careersLink = document.getElementById('composer-careers-link').href;
    
    const statusLog = document.getElementById('composer-status-log');
    statusLog.textContent = 'Saving draft...';
    statusLog.className = 'email-status-indicator';
    
    try {
        const response = await fetch(`/api/shortlist/${encodeURIComponent(company)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                to_email: toEmail,
                email_draft: body,
                job_url: careersLink
            })
        });
        
        if (response.ok) {
            statusLog.textContent = '✓ Draft saved successfully';
            statusLog.classList.add('replied');
            
            // Reload sidebar list to update email address in model memory
            loadOutreachQueue();
        } else {
            const err = await response.json();
            statusLog.textContent = `✗ Save failed: ${err.detail || 'unknown error'}`;
            statusLog.classList.add('failed');
        }
    } catch (err) {
        statusLog.textContent = `✗ Save error: ${err.message}`;
        statusLog.className = 'email-status-indicator failed';
    }
}

async function sendActiveEmail() {
    if (!state.outreach.activeCompany) return;
    
    const comp = state.outreach.activeCompany;
    const toEmail = document.getElementById('composer-to').value.trim();
    const subject = document.getElementById('composer-subject').value;
    const body = document.getElementById('composer-body').value;
    
    if (!toEmail || !toEmail.includes('@')) {
        alert("Please specify a valid recipient email address.");
        return;
    }
    
    if (!confirm(`Are you sure you want to send this cold email to ${comp.Company} (${toEmail}) via your Gmail account?`)) {
        return;
    }
    
    const sendBtn = document.getElementById('btn-send-email');
    const statusLog = document.getElementById('composer-status-log');
    
    sendBtn.disabled = true;
    statusLog.textContent = 'Connecting to Gmail API & sending email...';
    statusLog.className = 'email-status-indicator';
    
    try {
        const response = await fetch('/api/outreach/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                company: comp.Company,
                to_email: toEmail,
                subject: subject,
                body: body
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusLog.textContent = '✓ Outreach email sent successfully! Logged to tracker & CRM.';
            statusLog.classList.add('replied');
            
            // Reload outreach list to show new 'Sent' status
            loadOutreachQueue();
            loadConfigStatus(); // Update gmail connection dot
        } else {
            statusLog.textContent = `✗ Send failed: ${data.detail || 'Gmail API connection failed'}`;
            statusLog.classList.add('failed');
            sendBtn.disabled = false;
        }
    } catch (err) {
        statusLog.textContent = `✗ Network error: ${err.message}`;
        statusLog.className = 'email-status-indicator failed';
        sendBtn.disabled = false;
    }
}

// ---------------------------------------------------------------------------
// 5. Kanban Applications CRM
// ---------------------------------------------------------------------------
async function loadCrmBoard() {
    try {
        const response = await fetch('/api/applications');
        const data = await response.json();
        
        state.applications = data;
        renderKanbanBoard();
    } catch (err) {
        console.error("Error loading CRM board data:", err);
    }
}

const STAGES = ["Shortlisted", "Applied", "Email Sent", "Phone Screen", "Interview", "Technical Test", "Offer", "Rejected"];

function renderKanbanBoard() {
    // Reset columns
    STAGES.forEach(stage => {
        const colId = stage.replace(' ', '-');
        const container = document.getElementById(`column-${colId}`);
        if (container) {
            container.innerHTML = '';
        }
        
        const badge = document.getElementById(`badge-${colId}`);
        if (badge) {
            badge.textContent = '0';
        }
    });
    
    // Group and count
    const grouped = {};
    STAGES.forEach(s => { grouped[s] = []; });
    
    state.applications.forEach(app => {
        const stage = app.Status || 'Shortlisted';
        // Map any extra status categories onto standard stages
        let mapped = stage;
        if (stage === 'Final Round') mapped = 'Interview';
        if (stage === 'Withdrawn' || stage === 'On Hold') mapped = 'Rejected';
        
        if (grouped[mapped]) {
            grouped[mapped].push(app);
        } else {
            // Default
            grouped["Shortlisted"].push(app);
        }
    });
    
    const todayStr = new Date().toISOString().split('T')[0];
    
    // Render cards
    STAGES.forEach(stage => {
        const colId = stage.replace(' ', '-');
        const container = document.getElementById(`column-${colId}`);
        const badge = document.getElementById(`badge-${colId}`);
        
        const apps = grouped[stage];
        if (badge) {
            badge.textContent = apps.length;
        }
        
        if (apps.length === 0) {
            container.innerHTML = '<div class="editor-tip" style="text-align: center; padding: 20px 0; color: var(--text-muted);">Empty</div>';
            return;
        }
        
        apps.forEach(app => {
            // Overdue check
            let fuHTML = '';
            let isOverdue = false;
            
            if (app.Follow_Up_Date && app.Follow_Up_Date !== 'None') {
                isOverdue = app.Follow_Up_Date <= todayStr && !['Offer', 'Rejected', 'Withdrawn'].includes(app.Status);
                fuHTML = `<span class="follow-up-pill ${isOverdue ? 'overdue' : ''}">⚑ ${app.Follow_Up_Date}</span>`;
            }
            
            const card = document.createElement('div');
            card.className = 'kanban-card';
            card.innerHTML = `
                <div class="kanban-card-title">${app.Company}</div>
                <div class="kanban-card-sub">${app.Role}</div>
                <div class="kanban-card-meta">
                    ${fuHTML}
                    <button class="kanban-card-edit-btn" onclick="openEditApplicationModal('${app.Company.replace(/'/g, "\\'")}')">
                        <i data-lucide="edit-3" style="width: 14px; height: 14px;"></i>
                    </button>
                </div>
            `;
            
            container.appendChild(card);
        });
    });
    
    lucide.createIcons();
}

// CRM Modal Add/Edit Functions
function openAddApplicationModal() {
    document.getElementById('crm-form').reset();
    document.getElementById('crm-company').disabled = false;
    document.getElementById('modal-title').textContent = 'Add Application Opportunity';
    document.getElementById('crm-modal').showModal();
}

function openEditApplicationModal(companyName) {
    const app = state.applications.find(a => a.Company.toLowerCase().strip() === companyName.toLowerCase().strip());
    if (!app) return;
    
    document.getElementById('crm-company').value = app.Company;
    document.getElementById('crm-company').disabled = true; // Key index
    
    document.getElementById('crm-role').value = app.Role || 'AI/Data Engineer';
    document.getElementById('crm-url').value = app.Job_URL || '';
    document.getElementById('crm-status').value = app.Status || 'Shortlisted';
    document.getElementById('crm-follow-up').value = app.Follow_Up_Date || '';
    document.getElementById('crm-notes').value = app.Notes || '';
    
    document.getElementById('modal-title').textContent = 'Edit Application Details';
    document.getElementById('crm-modal').showModal();
}

function closeCrmModal() {
    document.getElementById('crm-modal').close();
}

function initCrmFormListener() {
    const form = document.getElementById('crm-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const payload = {
            company: document.getElementById('crm-company').value,
            role: document.getElementById('crm-role').value,
            url: document.getElementById('crm-url').value,
            status: document.getElementById('crm-status').value,
            follow_up: document.getElementById('crm-follow-up').value || null,
            notes: document.getElementById('crm-notes').value
        };
        
        try {
            const response = await fetch('/api/applications', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (response.ok) {
                closeCrmModal();
                loadCrmBoard();
                loadDashboardData(); // Refresh overview numbers
            } else {
                const err = await response.json();
                alert(`Error saving opportunity: ${err.detail || 'unknown error'}`);
            }
        } catch (err) {
            console.error("Failed to submit crm update:", err);
        }
    });
}

// String helper extension for whitespace stripping
String.prototype.strip = function() {
    return this.replace(/^\s+|\s+$/g, '');
};

// ---------------------------------------------------------------------------
// 6. Pipeline background script triggers & Log monitor
// ---------------------------------------------------------------------------
let logPollingInterval = null;

async function triggerPipeline(scriptName) {
    const runBtn = document.getElementById(`btn-run-${scriptName === 'run_scrapers' ? 'scrapers' : (scriptName === 'score_shortlist' ? 'scoring' : (scriptName === 'enrich_shortlist' ? 'enrich' : 'visa'))}`);
    
    if (runBtn) runBtn.disabled = true;
    toggleLogBox(true);
    
    const logsTitle = document.getElementById('running-script-title');
    const logsContent = document.getElementById('running-log-content');
    
    logsTitle.textContent = `Triggering ${scriptName}.py...`;
    logsContent.textContent = 'Awaiting subprocess launch response...';
    
    try {
        const response = await fetch(`/api/pipeline/run/${scriptName}`, { method: 'POST' });
        const data = await response.json();
        
        logsTitle.textContent = `Running ${scriptName}.py`;
        logsContent.textContent = data.task.output || 'Launched...';
        
        // Start polling active logs immediately
        if (logPollingInterval) clearInterval(logPollingInterval);
        logPollingInterval = setInterval(() => pollSpecificTaskLog(scriptName), 1500);
        
    } catch (err) {
        logsTitle.textContent = 'Launcher Fail';
        logsContent.textContent = `Error connecting to FastAPI script trigger: ${err.message}`;
        if (runBtn) runBtn.disabled = false;
    }
}

async function pollSpecificTaskLog(scriptName) {
    try {
        const response = await fetch('/api/pipeline/status');
        const tasks = await response.json();
        
        const task = tasks[scriptName];
        if (!task) return;
        
        const logsTitle = document.getElementById('running-script-title');
        const logsContent = document.getElementById('running-log-content');
        
        logsContent.textContent = task.output || 'Reading logs...';
        // Auto scroll
        logsContent.scrollTop = logsContent.scrollHeight;
        
        if (task.status === 'Completed' || task.status.startsWith('Failed')) {
            clearInterval(logPollingInterval);
            logPollingInterval = null;
            
            logsTitle.textContent = `${scriptName}.py Status: ${task.status}`;
            
            // Re-enable buttons
            const runBtn = document.getElementById(`btn-run-${scriptName === 'run_scrapers' ? 'scrapers' : (scriptName === 'score_shortlist' ? 'scoring' : (scriptName === 'enrich_shortlist' ? 'enrich' : 'visa'))}`);
            if (runBtn) runBtn.disabled = false;
            
            // Refresh data since script altered backend files
            loadDashboardData();
            if (state.activeTab === 'directory') loadDirectoryData();
            if (state.activeTab === 'outreach') loadOutreachQueue();
            if (state.activeTab === 'crm') loadCrmBoard();
        } else {
            logsTitle.textContent = `Running ${scriptName}.py (${task.status})`;
        }
    } catch (err) {
        console.error("Error polling logs:", err);
    }
}

// Global tasks poller
async function pollPipelineTasks() {
    if (logPollingInterval) return; // Already polling specifically
    
    try {
        const response = await fetch('/api/pipeline/status');
        const tasks = await response.json();
        
        // Find if any task is running
        for (const [scriptName, task] of Object.entries(tasks)) {
            if (task.status === 'Running') {
                toggleLogBox(true);
                document.getElementById('running-script-title').textContent = `Running ${scriptName}.py`;
                document.getElementById('running-log-content').textContent = task.output;
                
                // Re-init specific logger
                logPollingInterval = setInterval(() => pollSpecificTaskLog(scriptName), 1500);
                break;
            }
        }
    } catch (err) {
        console.error("Error during global tasks check:", err);
    }
}

function toggleLogBox(show) {
    const box = document.getElementById('running-log-box');
    box.style.display = show ? 'block' : 'none';
    
    if (!show && logPollingInterval) {
        clearInterval(logPollingInterval);
        logPollingInterval = null;
    }
}
