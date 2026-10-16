/**
 * Book Reservation Assistant - Frontend Controller
 * Handles chat communication, telemetry display, and live database synchronization.
 */

let currentSessionId = sessionStorage.getItem('book_agent_session_id');
if (!currentSessionId) {
    currentSessionId = 'sess-' + Math.random().toString(36).substring(2, 10);
    sessionStorage.setItem('book_agent_session_id', currentSessionId);
}

let allBooksCache = [];
let allReservationsCache = [];

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('sessionDisplay').textContent = `Session: ${currentSessionId.substring(0, 10)}...`;
    
    // Auto-expand textarea on typing
    const textarea = document.getElementById('userInput');
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.getElementById('chatForm').dispatchEvent(new Event('submit'));
        }
    });

    // Reset button handler
    document.getElementById('resetDemoBtn').addEventListener('click', resetDemoData);

    // Initial fetch of catalogue and reservations
    loadCatalogue();
    loadReservations();
});

// Switch tabs on side panel
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    if (tabName === 'catalogue') {
        document.querySelectorAll('.tab-btn')[0].classList.add('active');
        document.getElementById('tab-catalogue').classList.add('active');
        loadCatalogue();
    } else {
        document.querySelectorAll('.tab-btn')[1].classList.add('active');
        document.getElementById('tab-reservations').classList.add('active');
        loadReservations();
    }
}

// Send prompt from suggestion pills
function sendPrompt(text) {
    const input = document.getElementById('userInput');
    input.value = text;
    document.getElementById('chatForm').dispatchEvent(new Event('submit'));
}

// Form submit handler
async function handleChatSubmit(event) {
    event.preventDefault();
    const input = document.getElementById('userInput');
    const userText = input.value.trim();
    if (!userText) return;

    // Append user message
    appendMessage('user', userText);
    input.value = '';

    // Show typing state
    const typingId = appendTypingIndicator();
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: userText,
                session_id: currentSessionId
            })
        });

        const data = await response.json();
        removeTypingIndicator(typingId);
        sendBtn.disabled = false;

        if (response.ok) {
            // Append assistant reply
            appendMessage('assistant', data.reply);
            // Update telemetry drawer
            updateTelemetry(data.thoughts, data.tools_called);
            // Refresh inventory and reservations
            loadCatalogue();
            loadReservations();
        } else {
            appendMessage('assistant', `**System Notice:** ${data.error || 'Unable to connect to the agent server.'}`);
        }
    } catch (err) {
        removeTypingIndicator(typingId);
        sendBtn.disabled = false;
        appendMessage('assistant', '**Error:** Could not connect to the agent backend service. Please ensure `app.py` is running.');
        console.error(err);
    }
}

// Append message card
function appendMessage(sender, markdownText) {
    const container = document.getElementById('chatMessages');
    const card = document.createElement('div');
    card.className = `message-card ${sender}`;

    const avatar = sender === 'assistant' ? '🏛️' : '👤';
    const senderName = sender === 'assistant' ? 'Book Reservation Assistant' : 'You (Student)';

    const htmlContent = marked.parse(markdownText);

    card.innerHTML = `
        <div class="msg-avatar">${avatar}</div>
        <div class="msg-content">
            <div class="msg-sender">${senderName}</div>
            <div class="msg-body">${htmlContent}</div>
        </div>
    `;

    container.appendChild(card);
    container.scrollTop = container.scrollHeight;
}

// Typing indicator
function appendTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const id = 'typing-' + Date.now();
    const card = document.createElement('div');
    card.id = id;
    card.className = 'message-card assistant';
    card.innerHTML = `
        <div class="msg-avatar">🏛️</div>
        <div class="msg-content">
            <div class="msg-sender">Book Reservation Assistant</div>
            <div class="msg-body" style="font-style: italic; color: #79857d;">
                Checking catalogue & verifying reservation rules...
            </div>
        </div>
    `;
    container.appendChild(card);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const elem = document.getElementById(id);
    if (elem) elem.remove();
}

// Update telemetry box
function updateTelemetry(thoughts, toolsCalled) {
    const summarySpan = document.getElementById('lastToolSummary');
    const contentBox = document.getElementById('telemetryContent');

    if (!toolsCalled || toolsCalled.length === 0) {
        summarySpan.innerHTML = 'Direct Reasoning (No external tool needed)';
    } else {
        const toolNames = toolsCalled.map(t => `<span class="tool-badge">${t.tool || 'Tool'}</span>`).join(' ');
        summarySpan.innerHTML = `Invoked: ${toolNames}`;
    }

    let html = '';
    if (thoughts && thoughts.length > 0) {
        html += `<div style="margin-bottom: 8px;"><strong>Reasoning Steps:</strong><ul>`;
        thoughts.forEach(t => {
            html += `<li>${t}</li>`;
        });
        html += `</ul></div>`;
    }

    if (toolsCalled && toolsCalled.length > 0) {
        html += `<div><strong>Tool Execution Results:</strong><pre style="background: #faf8f3; padding: 8px; border-radius: 4px; overflow-x: auto; margin-top: 4px;">${JSON.stringify(toolsCalled, null, 2)}</pre></div>`;
    }

    contentBox.innerHTML = html || '<p class="text-muted">No tool telemetry recorded for this step.</p>';
}

// Fetch live book catalogue
async function loadCatalogue() {
    try {
        const res = await fetch('/api/books');
        const data = await res.json();
        allBooksCache = data.books || [];
        document.getElementById('catCount').textContent = allBooksCache.length;
        renderCatalogue(allBooksCache);
    } catch (e) {
        console.error('Failed to load catalogue', e);
    }
}

// Render catalogue list
function renderCatalogue(books) {
    const list = document.getElementById('catalogueList');
    if (!books || books.length === 0) {
        list.innerHTML = '<div style="padding: 12px; color: #79857d; font-size: 13px;">No books found matching criteria.</div>';
        return;
    }

    list.innerHTML = books.map(b => `
        <div class="book-item-card">
            <div class="book-item-title">${b.title}</div>
            <div class="book-item-author">By ${b.author} • <span style="font-family: monospace;">${b.book_id}</span></div>
            <div class="book-item-meta">
                <span style="color: #515c54;">📍 ${b.shelf_location}</span>
                <span class="status-badge status-${b.status}">${b.status}</span>
            </div>
        </div>
    `).join('');
}

// Filter catalogue via search box
function filterCatalogue() {
    const query = document.getElementById('catalogueFilter').value.toLowerCase().trim();
    if (!query) {
        renderCatalogue(allBooksCache);
        return;
    }
    const filtered = allBooksCache.filter(b => 
        b.title.toLowerCase().includes(query) ||
        b.author.toLowerCase().includes(query) ||
        b.category.toLowerCase().includes(query) ||
        b.book_id.toLowerCase().includes(query)
    );
    renderCatalogue(filtered);
}

// Fetch active reservations
async function loadReservations() {
    try {
        const res = await fetch('/api/reservations');
        const data = await res.json();
        allReservationsCache = data.reservations || [];
        document.getElementById('resCount').textContent = allReservationsCache.length;
        renderReservations(allReservationsCache);
    } catch (e) {
        console.error('Failed to load reservations', e);
    }
}

// Render reservations list
function renderReservations(reservations) {
    const list = document.getElementById('reservationsList');
    if (!reservations || reservations.length === 0) {
        list.innerHTML = '<div style="padding: 12px; color: #79857d; font-size: 13px;">No active reservations recorded.</div>';
        return;
    }

    list.innerHTML = reservations.map(r => `
        <div class="res-item-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="res-id-badge">${r.reservation_id}</span>
                <span class="status-badge status-${r.status}">${r.status}</span>
            </div>
            <div class="res-book-name">${r.book_title}</div>
            <div class="res-details">
                <span>👤 ${r.user_name} (${r.student_id})</span>
                <span>📅 ${r.reservation_date}</span>
            </div>
        </div>
    `).join('');
}

// Reset Demo Data
async function resetDemoData() {
    if (!confirm('Reset sample library catalogue and reservations to default demonstration state?')) return;
    try {
        const res = await fetch('/api/reset', { method: 'POST' });
        const data = await res.json();
        loadCatalogue();
        loadReservations();
        appendMessage('assistant', `ℹ️ **Demo Environment Reset:** ${data.message}`);
    } catch (e) {
        alert('Failed to reset demo data');
    }
}
