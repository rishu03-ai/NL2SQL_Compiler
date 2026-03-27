/**
 * NL2SQL Compiler - Chat Application JavaScript
 * Sprint 3: Minimal UI + Database Upload
 */

// ==========================================
// State Management
// ==========================================

const state = {
    currentSessionId: null,
    sessions: [],
    isLoading: false,
    currentChartData: null,
    chartInstance: null
};

// ==========================================
// DOM Elements
// ==========================================

const elements = {
    // Sidebar
    sidebar: document.getElementById('sidebar'),
    sidebarOverlay: document.getElementById('sidebarOverlay'),
    closeSidebar: document.getElementById('closeSidebar'),
    sessionsList: document.getElementById('sessionsList'),
    schemaBtn: document.getElementById('schemaBtn'),

    // Chat
    chatMessages: document.getElementById('chatMessages'),
    welcomeContainer: document.getElementById('welcomeContainer'),
    suggestions: document.getElementById('suggestions'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),

    // Bottom links
    newChatBtn: document.getElementById('newChatBtn'),
    historyBtn: document.getElementById('historyBtn'),
    statusText: document.getElementById('statusText'),
    statusDot: document.getElementById('statusDot'),

    // Modals
    schemaModal: document.getElementById('schemaModal'),
    closeSchemaModal: document.getElementById('closeSchemaModal'),
    schemaContent: document.getElementById('schemaContent'),
    chartModal: document.getElementById('chartModal'),
    closeChartModal: document.getElementById('closeChartModal'),
    chartType: document.getElementById('chartType'),
    dataChart: document.getElementById('dataChart'),

    // Database Upload
    dbInfoCard: document.getElementById('dbInfoCard'),
    dbName: document.getElementById('dbName'),
    dbMeta: document.getElementById('dbMeta'),
    resetDbBtn: document.getElementById('resetDbBtn'),
    uploadDbBtn: document.getElementById('uploadDbBtn'),
    dbFileInput: document.getElementById('dbFileInput')
};

// ==========================================
// API Functions
// ==========================================

const api = {
    async chat(message, sessionId = null) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, session_id: sessionId })
        });
        return response.json();
    },

    async getSessions() {
        const response = await fetch('/api/sessions');
        return response.json();
    },

    async getSession(sessionId) {
        const response = await fetch(`/api/sessions/${sessionId}`);
        return response.json();
    },

    async deleteSession(sessionId) {
        const response = await fetch(`/api/sessions/${sessionId}`, {
            method: 'DELETE'
        });
        return response.json();
    },

    async getSchema() {
        const response = await fetch('/api/schema');
        return response.json();
    },

    async exportCsv(columns, rows, filename = 'export') {
        const response = await fetch('/api/export/csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ columns, rows, filename })
        });
        return response.blob();
    },

    async uploadDatabase(file) {
        const formData = new FormData();
        formData.append('file', file);
        const response = await fetch('/api/upload-database', {
            method: 'POST',
            body: formData
        });
        return response.json();
    },

    async resetDatabase() {
        const response = await fetch('/api/reset-database', {
            method: 'POST'
        });
        return response.json();
    },

    async getDatabaseInfo() {
        const response = await fetch('/api/database-info');
        return response.json();
    },

    async healthCheck() {
        const response = await fetch('/api/health');
        return response.json();
    }
};

// ==========================================
// Sidebar Functions
// ==========================================

function openSidebar() {
    elements.sidebar.classList.add('open');
    elements.sidebarOverlay.classList.add('active');
}

function closeSidebar() {
    elements.sidebar.classList.remove('open');
    elements.sidebarOverlay.classList.remove('active');
}

// ==========================================
// UI Rendering
// ==========================================

function renderSessions() {
    if (state.sessions.length === 0) {
        elements.sessionsList.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <p>No conversations yet</p>
            </div>
        `;
        return;
    }

    const html = state.sessions.map(session => `
        <div class="session-item ${session.session_id === state.currentSessionId ? 'active' : ''}" 
             data-session-id="${session.session_id}">
            <div class="session-info">
                <div class="session-title">${session.title || 'New Chat'}</div>
                <div class="session-date">${formatDate(session.updated_at)}</div>
            </div>
            <button class="session-delete" data-session-id="${session.session_id}" title="Delete">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
            </button>
        </div>
    `).join('');

    elements.sessionsList.innerHTML = html;

    // Add click handlers
    elements.sessionsList.querySelectorAll('.session-item').forEach(item => {
        item.addEventListener('click', async (e) => {
            if (e.target.closest('.session-delete')) {
                e.stopPropagation();
                const sessionId = e.target.closest('.session-delete').dataset.sessionId;
                await deleteSession(sessionId);
            } else {
                const sessionId = item.dataset.sessionId;
                await loadSession(sessionId);
            }
        });
    });
}

function renderMessage(role, content, sqlQuery = null, sqlExplanation = null, data = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatarIcon = role === 'user'
        ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
        : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';

    let extraContent = '';

    // SQL display
    if (sqlQuery) {
        extraContent += `
            <div class="sql-display">
                <div class="sql-header">
                    <span class="sql-label">Generated SQL</span>
                    <button class="copy-btn" onclick="copyToClipboard(\`${escapeHtml(sqlQuery)}\`)" title="Copy">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                        </svg>
                    </button>
                </div>
                <div class="sql-code">${escapeHtml(sqlQuery)}</div>
            </div>
        `;

        if (sqlExplanation) {
            extraContent += `
                <div class="sql-explanation">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="16" x2="12" y2="12"/>
                        <line x1="12" y1="8" x2="12.01" y2="8"/>
                    </svg>
                    ${escapeHtml(sqlExplanation)}
                </div>
            `;
        }
    }

    // Data table
    if (data && data.columns && data.rows && data.rows.length > 0) {
        const maxRows = 10;
        const displayRows = data.rows.slice(0, maxRows);

        extraContent += `
            <div class="data-table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            ${data.columns.map(col => `<th>${escapeHtml(col)}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${displayRows.map(row => `
                            <tr>
                                ${row.map(cell => `<td>${escapeHtml(String(cell ?? ''))}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        if (data.rows.length > maxRows) {
            extraContent += `
                <div class="row-count-badge">
                    Showing ${maxRows} of ${data.row_count} rows
                </div>
            `;
        }

        extraContent += `
            <div class="data-actions">
                <button class="action-btn" onclick='exportData(${JSON.stringify(data.columns)}, ${JSON.stringify(data.rows)})'>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Export CSV
                </button>
                <button class="action-btn primary" onclick='showChart(${JSON.stringify(data.columns)}, ${JSON.stringify(data.rows)})'>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="20" x2="18" y2="10"/>
                        <line x1="12" y1="20" x2="12" y2="4"/>
                        <line x1="6" y1="20" x2="6" y2="14"/>
                    </svg>
                    Visualize
                </button>
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarIcon}</div>
        <div class="message-content">
            <div class="message-bubble">${formatMessage(content)}</div>
            ${extraContent}
        </div>
    `;

    return messageDiv;
}

function renderTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = 'typingIndicator';

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
        </div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;

    return messageDiv;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

function renderSuggestions(suggestions) {
    const html = suggestions.map(suggestion =>
        `<button class="suggestion-chip">${escapeHtml(suggestion)}</button>`
    ).join('');

    elements.suggestions.innerHTML = html;

    elements.suggestions.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            elements.messageInput.value = chip.textContent;
            elements.sendBtn.disabled = false;
            elements.messageInput.focus();
        });
    });
}

// ==========================================
// Chart Functions
// ==========================================

function showChart(columns, rows) {
    state.currentChartData = { columns, rows };
    elements.chartModal.classList.add('active');
    renderChart('bar');
}

function renderChart(type) {
    const { columns, rows } = state.currentChartData;

    if (state.chartInstance) {
        state.chartInstance.destroy();
    }

    let labelColumn = 0;
    let dataColumns = [];

    if (rows.length > 0) {
        columns.forEach((col, idx) => {
            const value = rows[0][idx];
            if (typeof value === 'number' || !isNaN(parseFloat(value))) {
                dataColumns.push(idx);
            } else if (dataColumns.length === 0) {
                labelColumn = idx;
            }
        });
    }

    if (dataColumns.length === 0) {
        dataColumns = [1];
    }

    const labels = rows.slice(0, 20).map(row => String(row[labelColumn] || '').substring(0, 20));
    const datasets = dataColumns.slice(0, 3).map((colIdx, i) => {
        const colors = [
            { bg: 'rgba(74, 124, 255, 0.7)', border: 'rgb(74, 124, 255)' },
            { bg: 'rgba(61, 214, 140, 0.7)', border: 'rgb(61, 214, 140)' },
            { bg: 'rgba(240, 168, 64, 0.7)', border: 'rgb(240, 168, 64)' }
        ];

        return {
            label: columns[colIdx],
            data: rows.slice(0, 20).map(row => parseFloat(row[colIdx]) || 0),
            backgroundColor: type === 'pie' || type === 'doughnut'
                ? generateColors(rows.length)
                : colors[i % colors.length].bg,
            borderColor: type === 'pie' || type === 'doughnut'
                ? generateColors(rows.length, 1)
                : colors[i % colors.length].border,
            borderWidth: 2
        };
    });

    const ctx = elements.dataChart.getContext('2d');

    state.chartInstance = new Chart(ctx, {
        type: type,
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: type === 'pie' || type === 'doughnut' ? 'right' : 'top',
                    labels: {
                        color: '#8a8a9a',
                        font: { family: 'Inter' }
                    }
                },
                title: {
                    display: true,
                    text: 'Data Visualization',
                    color: '#e4e4e9',
                    font: { family: 'Inter', size: 14 }
                }
            },
            scales: type === 'pie' || type === 'doughnut' ? {} : {
                x: {
                    ticks: { color: '#55556a' },
                    grid: { color: 'rgba(255, 255, 255, 0.04)' }
                },
                y: {
                    ticks: { color: '#55556a' },
                    grid: { color: 'rgba(255, 255, 255, 0.04)' }
                }
            }
        }
    });
}

function generateColors(count, alpha = 0.7) {
    const baseColors = [
        `rgba(74, 124, 255, ${alpha})`,
        `rgba(61, 214, 140, ${alpha})`,
        `rgba(240, 168, 64, ${alpha})`,
        `rgba(240, 80, 80, ${alpha})`,
        `rgba(168, 85, 247, ${alpha})`,
        `rgba(34, 211, 238, ${alpha})`,
        `rgba(236, 72, 153, ${alpha})`,
        `rgba(59, 130, 246, ${alpha})`
    ];

    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}

// ==========================================
// Export Functions
// ==========================================

async function exportData(columns, rows) {
    try {
        const blob = await api.exportCsv(columns, rows, 'query_results');

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'query_results.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        showToast('CSV exported successfully!', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showToast('Failed to export CSV', 'error');
    }
}

function showToast(message, type = 'success') {
    document.querySelectorAll('.toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==========================================
// Core Functions
// ==========================================

async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message || state.isLoading) return;

    state.isLoading = true;
    elements.sendBtn.disabled = true;

    // Hide welcome container
    if (elements.welcomeContainer) {
        elements.welcomeContainer.style.display = 'none';
    }

    // Add user message
    elements.chatMessages.appendChild(renderMessage('user', message));
    elements.messageInput.value = '';
    autoResize();

    // Add typing indicator
    elements.chatMessages.appendChild(renderTypingIndicator());
    scrollToBottom();

    try {
        const response = await api.chat(message, state.currentSessionId);

        removeTypingIndicator();

        if (response.session_id) {
            state.currentSessionId = response.session_id;
        }

        elements.chatMessages.appendChild(
            renderMessage('assistant', response.message, response.sql_query, response.sql_explanation, response.data)
        );

        await loadSessions();

    } catch (error) {
        removeTypingIndicator();
        console.error('Chat error:', error);
        elements.chatMessages.appendChild(
            renderMessage('assistant', 'Sorry, I encountered an error. Please try again.')
        );
    }

    state.isLoading = false;
    elements.sendBtn.disabled = false;
    scrollToBottom();
}

async function loadSessions() {
    try {
        state.sessions = await api.getSessions();
        renderSessions();
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

async function loadSession(sessionId) {
    try {
        const session = await api.getSession(sessionId);

        state.currentSessionId = sessionId;

        // Clear messages
        elements.chatMessages.innerHTML = '';

        // Hide welcome
        if (elements.welcomeContainer) {
            elements.welcomeContainer.style.display = 'none';
        }

        // Render all messages
        for (const msg of session.messages) {
            const sqlQuery = msg.metadata?.sql_query || null;
            elements.chatMessages.appendChild(renderMessage(msg.role, msg.content, sqlQuery));
        }

        scrollToBottom();
        renderSessions();
        closeSidebar();

    } catch (error) {
        console.error('Error loading session:', error);
    }
}

async function deleteSession(sessionId) {
    try {
        await api.deleteSession(sessionId);

        if (state.currentSessionId === sessionId) {
            startNewChat();
        }

        await loadSessions();
        showToast('Session deleted', 'success');
    } catch (error) {
        console.error('Error deleting session:', error);
        showToast('Failed to delete session', 'error');
    }
}

function startNewChat() {
    state.currentSessionId = null;

    // Reset chat area
    elements.chatMessages.innerHTML = '';

    // Show welcome container
    if (elements.welcomeContainer) {
        elements.welcomeContainer.style.display = 'flex';
        elements.chatMessages.appendChild(elements.welcomeContainer);
    }

    renderSessions();
    closeSidebar();
}

async function showSchema() {
    elements.schemaModal.classList.add('active');

    try {
        const data = await api.getSchema();

        let html = `<pre>${escapeHtml(data.schema)}</pre>`;

        if (data.suggested_questions && data.suggested_questions.length > 0) {
            html += '<h3 style="margin-top: 1.5rem; margin-bottom: 1rem; font-weight: 500;">Suggested Questions</h3>';
            html += '<div class="suggestions">';
            html += data.suggested_questions.map(q =>
                `<button class="suggestion-chip" onclick="useSuggestion('${escapeHtml(q)}')">${escapeHtml(q)}</button>`
            ).join('');
            html += '</div>';
        }

        elements.schemaContent.innerHTML = html;

    } catch (error) {
        elements.schemaContent.innerHTML = '<p>Error loading schema</p>';
    }
}

function useSuggestion(text) {
    elements.messageInput.value = text;
    elements.sendBtn.disabled = false;
    elements.schemaModal.classList.remove('active');
    elements.messageInput.focus();
}

// ==========================================
// Database Upload Functions
// ==========================================

async function loadDatabaseInfo() {
    try {
        const info = await api.getDatabaseInfo();
        elements.dbName.textContent = info.filename;
        elements.dbMeta.textContent = `${info.table_count} tables • ${info.total_rows.toLocaleString()} rows`;

        elements.resetDbBtn.style.display = info.is_default ? 'none' : 'flex';

        if (info.is_default) {
            elements.dbInfoCard.classList.remove('custom-db');
        } else {
            elements.dbInfoCard.classList.add('custom-db');
        }
    } catch (error) {
        console.error('Error loading database info:', error);
        elements.dbMeta.textContent = 'Error loading info';
    }
}

async function handleDatabaseUpload(file) {
    if (!file || !file.name.endsWith('.db')) {
        showToast('Please upload a .db (SQLite) file', 'error');
        return;
    }

    elements.uploadDbBtn.disabled = true;
    elements.uploadDbBtn.innerHTML = `<div class="upload-spinner"></div> Uploading...`;

    try {
        const result = await api.uploadDatabase(file);

        if (result.success) {
            showToast(result.message, 'success');
            await loadDatabaseInfo();

            if (result.suggested_questions && elements.welcomeContainer) {
                renderSuggestions(result.suggested_questions);
            }

            startNewChat();
        } else {
            showToast(result.detail || 'Upload failed', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast('Failed to upload database', 'error');
    }

    elements.uploadDbBtn.disabled = false;
    elements.uploadDbBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        Upload Database
    `;
}

async function resetToDefaultDatabase() {
    try {
        elements.resetDbBtn.disabled = true;
        const result = await api.resetDatabase();

        if (result.success) {
            showToast(result.message, 'success');
            await loadDatabaseInfo();

            if (result.suggested_questions && elements.welcomeContainer) {
                renderSuggestions(result.suggested_questions);
            }

            startNewChat();
        } else {
            showToast(result.detail || 'Reset failed', 'error');
        }
    } catch (error) {
        console.error('Reset error:', error);
        showToast('Failed to reset database', 'error');
    }
    elements.resetDbBtn.disabled = false;
}

// ==========================================
// Utility Functions
// ==========================================

function scrollToBottom() {
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function formatMessage(content) {
    return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;

    return date.toLocaleDateString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    });
}

function autoResize() {
    const textarea = elements.messageInput;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

// ==========================================
// Event Listeners
// ==========================================

// Input handling
elements.messageInput.addEventListener('input', () => {
    elements.sendBtn.disabled = !elements.messageInput.value.trim();
    autoResize();
});

elements.messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

elements.sendBtn.addEventListener('click', sendMessage);

// Bottom links
elements.newChatBtn.addEventListener('click', startNewChat);
elements.historyBtn.addEventListener('click', openSidebar);

// Sidebar
elements.closeSidebar.addEventListener('click', closeSidebar);
elements.sidebarOverlay.addEventListener('click', closeSidebar);

// Schema
elements.schemaBtn.addEventListener('click', showSchema);
elements.closeSchemaModal.addEventListener('click', () => {
    elements.schemaModal.classList.remove('active');
});

// Chart modal
elements.closeChartModal.addEventListener('click', () => {
    elements.chartModal.classList.remove('active');
});

elements.chartType.addEventListener('change', (e) => {
    if (state.currentChartData) {
        renderChart(e.target.value);
    }
});

// Close modals on background click
elements.schemaModal.addEventListener('click', (e) => {
    if (e.target === elements.schemaModal) {
        elements.schemaModal.classList.remove('active');
    }
});

elements.chartModal.addEventListener('click', (e) => {
    if (e.target === elements.chartModal) {
        elements.chartModal.classList.remove('active');
    }
});

// Upload database
elements.uploadDbBtn.addEventListener('click', () => {
    elements.dbFileInput.click();
});

elements.dbFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleDatabaseUpload(file);
        e.target.value = '';
    }
});

elements.resetDbBtn.addEventListener('click', resetToDefaultDatabase);

// ==========================================
// Initialization
// ==========================================

async function init() {
    // Load sessions
    await loadSessions();

    // Load database info
    await loadDatabaseInfo();

    // Check server health
    try {
        const health = await api.healthCheck();
        if (health.status === 'healthy') {
            elements.statusDot.classList.add('online');
            elements.statusText.innerHTML = `<span class="status-dot online" id="statusDot"></span> Connected`;
        }
    } catch (error) {
        elements.statusText.innerHTML = `<span class="status-dot" id="statusDot"></span> Server offline`;
    }

    // Load suggestions
    try {
        const data = await api.getSchema();
        if (data.suggested_questions) {
            renderSuggestions(data.suggested_questions);
        }
    } catch (error) {
        console.error('Error loading initial data:', error);
    }

    // Focus input
    elements.messageInput.focus();
}

// Start the app
init();
