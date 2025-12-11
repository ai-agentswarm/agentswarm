#!/usr/bin/env python3
import json
import os
import sys
import webbrowser
import http.server
import socketserver
import threading
import time
from urllib.parse import urlparse

# Configuration
PORT = 8765
TRACE_FILE_PATH = ""
EVENTS_DATA = []

class TraceRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/":
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            return
            
        if parsed_path.path == "/api/list":
            self.handle_api_list()
            return
            
        if parsed_path.path == "/api/reload":
            load_trace_data(TRACE_FILE_PATH)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
            
        if parsed_path.path.startswith("/api/event/"):
            try:
                event_index = int(parsed_path.path.split("/")[-1])
                self.handle_api_event(event_index)
            except ValueError:
                self.send_error(400, "Invalid event index")
            return

        # Fallback to static files or 404
        super().do_GET()

    def handle_api_list(self):
        """Restituisce la lista leggera degli eventi per la sidebar"""
        lite_events = []
        for i, event in enumerate(EVENTS_DATA):
            lite_event = {
                "id": i,
                "type": event.get("type", "unknown"),
                "timestamp": event.get("timestamp", ""),
                "agent_id": event.get("agent_id"),
                "step_id": event.get("step_id"),
                "parent_step_id": event.get("parent_step_id"),
                "msg_count": len(event.get("messages", [])),
                "has_store": bool(event.get("store")),
                "has_error": (event.get("type") == "agent" and "Error executing agent" in str(event.get("messages", ""))) or \
                             (event.get("error") is not None) or \
                             (event.get("type") == "agent_error")
            }
            lite_events.append(lite_event)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(lite_events).encode('utf-8'))

    def handle_api_event(self, index):
        """Restituisce i dettagli completi di un singolo evento"""
        if 0 <= index < len(EVENTS_DATA):
            event = EVENTS_DATA[index]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(event).encode('utf-8'))
        else:
            self.send_error(404, "Event not found")

    def log_message(self, format, *args):
        pass

def load_trace_data(file_path):
    global EVENTS_DATA
    EVENTS_DATA = []
    print(f"⏳ Loading trace from {file_path}...")
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    EVENTS_DATA.append(json.loads(line))
        print(f"✅ Loaded {len(EVENTS_DATA)} events.")
    except Exception as e:
        print(f"❌ Error loading trace: {e}")
        sys.exit(1)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hierarchical Trace Viewer</title>
    <style>
        :root {
            --bg-sidebar: #1e1e1e;
            --bg-content: #ffffff;
            --text-sidebar: #d4d4d4;
            --text-content: #212529;
            --accent-color: #3b82f6;
            --border-color: #333;
            --item-hover: #2a2d2e;
            --item-selected: #37373d;
            
            --color-agent: #4ec9b0;
            --color-context: #569cd6;
            --color-error: #f48771;
            --color-result: #4caf50;
            --color-timestamp: #858585;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            height: 100vh;
            display: flex;
            color: var(--text-content);
            overflow: hidden;
            background: var(--bg-content);
        }

        /* Sidebar Tree View */
        .sidebar {
            width: 400px;
            background: var(--bg-sidebar);
            color: var(--text-sidebar);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }

        .sidebar-header {
            padding: 15px;
            border-bottom: 1px solid var(--border-color);
            background: #252526;
            box-shadow: 0 1px 4px rgba(0,0,0,0.2);
        }

        .sidebar-title { font-weight: 600; font-size: 1.1rem; color: white; }
        .sidebar-subtitle { font-size: 0.8rem; color: #888; margin-top: 4px; }

        .tree-container {
            flex: 1;
            overflow-y: auto;
            overflow-x: auto;
            padding: 10px 0;
        }

        .tree-node {
            position: relative;
            min-width: max-content;
        }

        .tree-content {
            display: flex;
            align-items: center;
            padding: 6px 10px 6px 0;
            cursor: pointer;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.85rem;
            border-left: 2px solid transparent;
        }

        .tree-content:hover { background: var(--item-hover); }
        .tree-content.selected { 
            background: var(--item-selected); 
            border-left-color: var(--accent-color);
        }

        .tree-indent {
            display: flex;
            flex-shrink: 0;
        }
        
        .indent-guide {
            width: 20px;
            height: 100%;
            border-right: 1px dashed #444;
            opacity: 0.3;
        }

        .toggle-icon {
            width: 20px;
            text-align: center;
            color: #888;
            font-size: 0.7rem;
            transition: transform 0.1s;
        }
        
        .toggle-icon.open { transform: rotate(90deg); }
        .toggle-icon.hidden { visibility: hidden; }

        .node-icon { margin-right: 6px; font-size: 1rem; }
        
        .node-info { flex: 1; overflow: hidden; }
        
        .node-title {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: #e0e0e0;
        }
        
        .node-meta {
            display: flex;
            gap: 8px;
            font-size: 0.7rem;
            color: #888;
            margin-top: 2px;
        }

        .badge {
            padding: 1px 4px;
            border-radius: 3px;
            background: #333;
            font-size: 0.65rem;
        }
        
        .badge.agent { color: var(--color-agent); border: 1px solid #2b5c53; }
        .badge.context { color: var(--color-context); border: 1px solid #264f78; }
        .badge.error { color: var(--color-error); border: 1px solid #8c3b2d; }
        .badge.result { color: var(--color-result); border: 1px solid #2e7d32; }

        /* Main Content */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #f5f5f5;
            overflow: hidden;
        }
        
        .content-scroll {
            flex: 1;
            overflow-y: auto;
            padding: 40px;
            width: 100%;
        }

        .detail-card {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            padding: 30px;
            max-width: 1000px;
            margin: 0 auto;
        }

        .detail-header {
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }

        .detail-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #333;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .detail-meta {
            margin-top: 10px;
            color: #666;
            font-size: 0.9rem;
            display: flex;
            gap: 20px;
        }

        .section { margin-bottom: 30px; }
        .section-title {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 700;
            color: #888;
            margin-bottom: 10px;
        }

        .json-block {
            background: #2d2d2d;
            color: #ccc;
            padding: 15px;
            border-radius: 6px;
            font-family: 'SF Mono', Consolas, monospace;
            font-size: 0.9rem;
            overflow-x: auto;
            white-space: pre-wrap;
        }

        .message {
            border: 1px solid #eee;
            border-radius: 8px;
            margin-bottom: 10px;
            overflow: hidden;
        }

        .message-header {
            padding: 8px 12px;
            background: #f8f9fa;
            border-bottom: 1px solid #eee;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            color: #666;
            display: flex;
            justify-content: space-between;
        }

        .message-body {
            padding: 15px;
            font-family: 'SF Mono', Consolas, monospace;
            font-size: 0.9rem;
            line-height: 1.6;
            white-space: pre-wrap;
            background: white;
        }

        .role-user .message-header { background: #e3f2fd; color: #1565c0; }
        .role-assistant .message-header { background: #e8f5e9; color: #2e7d32; }
        .role-system .message-header { background: #fff3e0; color: #ef6c00; }
        .role-execution .message-header { background: #f3e5f5; color: #7b1fa2; }

        .thought-bubble {
            background: #f0f7ff;
            border-left: 4px solid #3b82f6;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 0 4px 4px 0;
            color: #444;
            font-style: italic;
        }

        .store-key {
            display: inline-block;
            padding: 4px 8px;
            background: #e0f7fa;
            color: #006064;
            border-radius: 4px;
            font-family: monospace;
            margin-right: 5px;
            margin-bottom: 5px;
            font-size: 0.85rem;
            cursor: pointer;
            border: 1px solid #b2ebf2;
        }
        
        /* Modal Styles */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s;
        }
        
        .modal-overlay.active {
            opacity: 1;
            pointer-events: auto;
        }
        
        .modal-content {
            background: white;
            width: 80%;
            height: 80%;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }
        
        .modal-header {
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #f8f9fa;
            border-radius: 8px 8px 0 0;
        }
        
        .modal-title { font-weight: 700; font-family: monospace; color: #333; }
        
        .modal-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #666;
        }
        
        .modal-body {
            flex: 1;
            padding: 20px;
            overflow: auto;
            background: #fff;
            font-family: 'SF Mono', Consolas, monospace;
            font-size: 0.9rem;
            white-space: pre-wrap;
        }

        /* Store List Styles */
        .store-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 10px;
        }
        
        .store-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 10px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .store-card:hover {
            border-color: var(--accent-color);
            transform: translateY(-2px);
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        
        .store-card-key {
            font-family: monospace;
            font-weight: 600;
            color: #2c3e50;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .store-card-meta {
            font-size: 0.75rem;
            color: #999;
            margin-left: 10px;
            white-space: nowrap;
        }

        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #666;
            font-size: 1.2rem;
        }

    </style>
</head>
<body>

<!-- Modal -->
<div class="modal-overlay" id="storeModal" onclick="closeModal(event)">
    <div class="modal-content">
        <div class="modal-header">
            <div class="modal-title" id="modalKey">Key Name</div>
            <button class="modal-close" onclick="closeModal(event)">&times;</button>
        </div>
        <div class="modal-body" id="modalValue">Content...</div>
    </div>
</div>

<div class="sidebar">
    <div class="sidebar-header">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div class="sidebar-title">🔍 Agent Swarm Trace</div>
            <button onclick="refreshTrace()" style="background:none; border:1px solid #444; color:#ccc; padding:2px 8px; cursor:pointer; border-radius:4px;" title="Reload Trace File">↻</button>
        </div>
        <div class="sidebar-subtitle" id="trace-info">Loading...</div>
        </div>
    <div class="tree-container" id="treeContainer"></div>
    </div>
    
<div class="main-content">
    <div class="content-scroll" id="detailView">
        <div class="loading">Select a node to view details</div>
    </div>
</div>
    
    <script>
    let rawEvents = [];
    let eventMap = new Map();
    let stepMap = new Map(); // step_id -> { events: [], children: [] }
    let rootSteps = [];
    
    // Helper for modal
    window.currentStoreData = {}; // To store the data for the modal

    const treeContainer = document.getElementById('treeContainer');
    const detailView = document.getElementById('detailView');
    const traceInfo = document.getElementById('trace-info');
    const modal = document.getElementById('storeModal');
    const modalKey = document.getElementById('modalKey');
    const modalValue = document.getElementById('modalValue');

    function openStoreModal(key) {
        const val = window.currentStoreData[key];
        modalKey.textContent = key;
        modalValue.textContent = typeof val === 'string' ? val : JSON.stringify(val, null, 2);
        modal.classList.add('active');
    }

    function closeModal(e) {
        if (e.target === modal || e.target.classList.contains('modal-close')) {
            modal.classList.remove('active');
        }
    }
    
    // Close on ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            modal.classList.remove('active');
        }
    });

    function refreshTrace() {
        traceInfo.textContent = "Reloading...";
        fetch('/api/reload')
            .then(() => init())
            .catch(err => console.error(err));
    }

    async function init() {
        try {
            const res = await fetch('/api/list');
            rawEvents = await res.json();
            processEventsIntoTree();
            renderTree();
            traceInfo.textContent = `${rawEvents.length} events | ${rootSteps.length} root flows`;
        } catch (e) {
            console.error(e);
            traceInfo.textContent = "Error loading trace";
        }
    }

    function processEventsIntoTree() {
        // Reset data structures
        eventMap = new Map();
        stepMap = new Map();
        rootSteps = [];
        
        rawEvents.forEach(ev => {
            const stepId = ev.step_id || `legacy_step_${ev.id}`; // Fallback for old traces
            const parentId = ev.parent_step_id;

            if (!stepMap.has(stepId)) {
                stepMap.set(stepId, {
                    id: stepId,
                    parentId: parentId,
                    events: [],
                    children: [],
                    // Metadata for the tree node
                    startTime: ev.timestamp,
                    type: ev.type,
                    agentId: ev.agent_id,
                    hasError: ev.has_error
                });
            }
            
            const step = stepMap.get(stepId);
            step.events.push(ev);
            
            // Update metadata if this event has more info (e.g. agent_id might appear later?)
            if (ev.agent_id && !step.agentId) step.agentId = ev.agent_id;
            if (ev.has_error) step.hasError = true;
        });

        // Build Hierarchy
        stepMap.forEach(step => {
            if (step.parentId && stepMap.has(step.parentId)) {
                const parent = stepMap.get(step.parentId);
                parent.children.push(step);
            } else {
                // No parent found in map -> Root
                rootSteps.push(step);
            }
        });

        // Sort children by start time
        stepMap.forEach(step => {
            step.children.sort((a, b) => a.events[0].id - b.events[0].id);
        });
        
        // Sort roots
        rootSteps.sort((a, b) => a.events[0].id - b.events[0].id);
    }

    function renderTree() {
        treeContainer.innerHTML = '';
        rootSteps.forEach(step => {
            treeContainer.appendChild(createTreeNode(step, 0));
        });
    }

    function createTreeNode(step, level) {
        const container = document.createElement('div');
        container.className = 'tree-node';

        // Node Content
        const content = document.createElement('div');
        content.className = 'tree-content';
        content.style.paddingLeft = (level * 15) + 10 + 'px'; // Simple padding fallback
        
        // Helper to get title
        let title = step.agentId || 'System Context';
        let icon = step.agentId ? '🤖' : '📋';
        
        const firstEv = step.events[0];
        if (firstEv.type === 'context') icon = '🧠';
        if (firstEv.type === 'loop_step') {
            icon = '🔄';
        }

        // Badges
        let badges = '';
        if (step.events.length > 1) badges += `<span class="badge context">${step.events.length} steps</span>`;
        if (step.hasError) badges += `<span class="badge error">Error</span>`;
        
        // Check for results in events
        const hasResult = step.events.some(e => e.type === 'agent_result');
        if (hasResult) badges += `<span class="badge result">Result</span>`;

        // Child count badge
        if (step.children.length > 0) {
             badges += `<span class="badge agent" style="background:#333; border:1px solid #555; color:#ccc; margin-left:4px">${step.children.length} sub-steps</span>`;
        }

        // Toggle Icon
        const hasChildren = step.children.length > 0;
        const toggleClass = hasChildren ? '' : 'hidden';
        
        content.innerHTML = `
            <div class="toggle-icon ${toggleClass}">▶</div>
            <span class="node-icon">${icon}</span>
            <div class="node-info">
                <div class="node-title">${title}</div>
                <div class="node-meta">
                    ${step.events[0].timestamp.split('T')[1].split('.')[0]}
                    ${badges}
                </div>
            </div>
        `;

        // Click Handling
        content.onclick = (e) => {
            // Handle Toggle
            if (hasChildren && e.target.closest('.toggle-icon')) {
                e.stopPropagation();
                const childrenContainer = container.querySelector('.children-container');
                const icon = content.querySelector('.toggle-icon');
                
                if (childrenContainer.style.display === 'none') {
                    childrenContainer.style.display = 'block';
                    icon.classList.add('open');
                } else {
                    childrenContainer.style.display = 'none';
                    icon.classList.remove('open');
                }
                return;
            }

            // Select Node
            document.querySelectorAll('.tree-content').forEach(el => el.classList.remove('selected'));
            content.classList.add('selected');
            renderStepDetails(step);
        };

        container.appendChild(content);

        // Children
        if (hasChildren) {
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'children-container';
            // Default open if level < 2
            if (level >= 1) {
                childrenContainer.style.display = 'none';
            } else {
                content.querySelector('.toggle-icon').classList.add('open');
            }
            
            step.children.forEach(child => {
                childrenContainer.appendChild(createTreeNode(child, level + 1));
            });
            container.appendChild(childrenContainer);
        }

        return container;
    }

    async function renderStepDetails(step) {
        detailView.innerHTML = '<div class="loading">Loading step details...</div>';
        
        // Load full details for all events in this step
        const eventDetails = await Promise.all(step.events.map(ev => fetch(`/api/event/${ev.id}`).then(r => r.json())));
        
        // Find the last event with a non-empty store
        let lastStore = {};
        for (let i = eventDetails.length - 1; i >= 0; i--) {
            if (eventDetails[i].store && Object.keys(eventDetails[i].store).length > 0) {
                lastStore = eventDetails[i].store;
                break;
            }
        }

        let typeLabel = step.agentId ? '🤖 Agent Execution' : '🧠 Context Step';
        if (step.events[0].type === 'loop_step') typeLabel = '🔄 Iteration Loop';

        let html = `<div class="detail-card">`;
        
        html += `
            <div class="detail-header">
                <div class="detail-title">
                    <span>${typeLabel}</span>
                </div>
                <div class="detail-meta">
                    <span>Step ID: <span style="font-family:monospace">${step.id.substring(0,8)}...</span></span>
                    <span>Events: ${eventDetails.length}</span>
                </div>
            </div>
        `;

        // STORE SECTION - Always visible at top if data exists
        if (Object.keys(lastStore).length > 0) {
            // Save to global for modal access
            window.currentStoreData = lastStore;
            
            html += `
                <div class="section" style="background:#f8f9fa; padding:20px; border-radius:8px; border:1px solid #e9ecef;">
                    <div class="section-title">📦 Final Store State (${Object.keys(lastStore).length} keys)</div>
                    <div class="store-grid">
            `;
            
            Object.entries(lastStore).forEach(([k, v]) => {
                let valStr = typeof v === 'string' ? v : JSON.stringify(v);
                let sizeStr = valStr.length > 1024 ? (valStr.length / 1024).toFixed(1) + ' KB' : valStr.length + ' B';
                
                html += `
                    <div class="store-card" onclick="openStoreModal('${escapeHtml(k.replace(/'/g, "\\'"))}')">
                        <span class="store-card-key">${escapeHtml(k)}</span>
                        <span class="store-card-meta">${sizeStr}</span>
                    </div>
                `;
            });
            
            html += `</div></div>`;
        }

        eventDetails.forEach((evt, idx) => {
            html += `
                <div class="section">
                    <div class="section-title">Event ${idx + 1}: ${evt.type}</div>
                    ${renderEventBody(evt)}
                </div>
                <hr style="border: 0; border-top: 1px dashed #eee; margin: 30px 0;">
            `;
        });

        html += `</div>`;
        detailView.innerHTML = html;
    }

    function renderEventBody(data) {
        let html = '';
        
        // Show Agent ID specifically if present
        if (data.type === 'agent') {
             html += `<div style="margin-bottom:10px; font-weight:bold; color:#4ec9b0">🤖 Agent: ${data.agent_id}</div>`;
        }
        
        // Agent Result
        if (data.type === 'agent_result') {
             html += `<div style="margin-bottom:10px; font-weight:bold; color:#4caf50">✅ Agent Result: ${data.agent_id}</div>`;
             if (data.result) {
                 html += `<div class="json-block" style="margin-bottom:20px; border-left: 4px solid #4caf50"><div style="color:#888;margin-bottom:5px">// Result</div>${formatJson(data.result)}</div>`;
             }
        }
        
        // Agent Error
        if (data.type === 'agent_error') {
             html += `<div style="margin-bottom:10px; font-weight:bold; color:#f44336">❌ Agent Error: ${data.agent_id}</div>`;
             if (data.error) {
                 html += `<div class="json-block" style="margin-bottom:20px; border-left: 4px solid #f44336; background: #3e2020"><div style="color:#ff8a80;margin-bottom:5px">// Error</div>${escapeHtml(String(data.error))}</div>`;
             }
        }

        // Arguments (if agent)
        if (data.type === 'agent' && data.arguments) {
            html += `<div class="json-block" style="margin-bottom:20px"><div style="color:#888;margin-bottom:5px">// Arguments</div>${formatJson(data.arguments)}</div>`;
        }

        // Thoughts
        if (data.thoughts && data.thoughts.length > 0) {
             html += `<div class="section"><div class="section-title">💭 Thoughts</div><div class="message-container">`;
             data.thoughts.forEach(t => {
                 html += `<div class="thought-bubble">${escapeHtml(t)}</div>`;
             });
             html += `</div></div>`;
        }

        // Messages
        if (data.messages && data.messages.length > 0) {
            html += `<div class="section"><div class="section-title">💬 Messages (${data.messages.length})</div><div class="message-container">`;
            data.messages.forEach(msg => {
                html += `
                    <div class="message">
                        <div class="message-header role-${msg.t || msg.type}">
                            <span>${msg.t || msg.type}</span>
                        </div>
                        <div class="message-body">${escapeHtml(formatContent(msg.c || msg.content))}</div>
                    </div>
                `;
            });
            html += `</div></div>`;
        }

        return html;
    }

    function formatJson(obj) {
        try { return JSON.stringify(obj, null, 2); } 
        catch (e) { return String(obj); }
    }

    function formatContent(content) {
        if (typeof content === 'object') return JSON.stringify(content, null, 2);
        return String(content);
    }

    function escapeHtml(text) {
        if (!text) return '';
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    init();
    </script>

</body>
</html>
"""

def main():
    global TRACE_FILE_PATH
    if len(sys.argv) < 2:
        print("❌ Usage: python trace_view.py <trace_id>")
        sys.exit(1)
    
    trace_id = sys.argv[1]
    
    if trace_id == "last":
        try:
            traces_dir = "traces"
            files = [os.path.join(traces_dir, f) for f in os.listdir(traces_dir) if f.endswith('.json')]
            if not files:
                print("❌ No trace files found in 'traces/' directory.")
                sys.exit(1)
            latest_file = max(files, key=os.path.getmtime)
            TRACE_FILE_PATH = latest_file
            print(f"📂 Loading latest trace: {latest_file}")
        except Exception as e:
            print(f"❌ Error finding latest trace: {e}")
            sys.exit(1)
    elif trace_id.endswith(".json"):
        TRACE_FILE_PATH = os.path.join("traces", trace_id)
    else:
        TRACE_FILE_PATH = os.path.join("traces", f"{trace_id}.json")
    
    load_trace_data(TRACE_FILE_PATH)
    
    with socketserver.TCPServer(("", PORT), TraceRequestHandler) as httpd:
        print(f"🚀 Trace Viewer running at http://localhost:{PORT}")
        threading.Thread(target=lambda: (time.sleep(1), webbrowser.open(f"http://localhost:{PORT}"))).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
