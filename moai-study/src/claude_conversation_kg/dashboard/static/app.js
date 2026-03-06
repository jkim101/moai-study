/* KG Dashboard - Frontend Logic */

document.addEventListener("DOMContentLoaded", function () {
    loadStats();
    loadAudit();
    loadGraph();
});

/**
 * Fetch /api/stats and update metric cards + type distribution.
 */
async function loadStats() {
    try {
        const resp = await fetch("/api/stats");
        const data = await resp.json();

        // Update metric cards
        setText("entity-count", formatNumber(data.total_entities));
        setText("relationship-count", formatNumber(data.total_relationships));

        // Render entity type distribution bars
        renderTypeDistribution(data.entities_by_type);

        // Populate graph filter checkboxes from stats data
        loadGraphFilters(data);
    } catch (err) {
        setText("entity-count", "--");
        setText("relationship-count", "--");
    }
}

/**
 * Fetch /api/audit and update top entities table + top mention card.
 */
async function loadAudit() {
    try {
        const resp = await fetch("/api/audit");
        const data = await resp.json();

        // Update top mention card with #1 entity
        if (data.top_entities && data.top_entities.length > 0) {
            var top = data.top_entities[0];
            setText("top-mention", String(top.mention_count));
            setText("top-mention-name", top.name);
        } else {
            setText("top-mention", "--");
            setText("top-mention-name", "");
        }

        // Render top entities table
        renderTopEntities(data.top_entities || []);
    } catch (err) {
        setText("top-mention", "--");
        setText("top-mention-name", "");
    }
}

/**
 * Render horizontal bars for entity type distribution.
 */
function renderTypeDistribution(entitiesByType) {
    var container = document.getElementById("type-distribution");
    if (!container) return;

    // Sort types by count descending
    var entries = Object.entries(entitiesByType).sort(function (a, b) {
        return b[1] - a[1];
    });

    if (entries.length === 0) {
        container.innerHTML = '<p class="loading">No data available.</p>';
        return;
    }

    var maxCount = entries[0][1];
    var html = "";

    entries.forEach(function (entry) {
        var typeName = entry[0];
        var count = entry[1];
        var pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
        html +=
            '<div class="type-bar-row">' +
            '<span class="type-bar-label">' + escapeHtml(typeName) + "</span>" +
            '<div class="type-bar-track">' +
            '<div class="type-bar-fill" style="width:' + pct + '%"></div>' +
            "</div>" +
            '<span class="type-bar-count">' + formatNumber(count) + "</span>" +
            "</div>";
    });

    container.innerHTML = html;
}

/**
 * Render top entities as a table.
 */
function renderTopEntities(entities) {
    var tbody = document.getElementById("top-entities-body");
    if (!tbody) return;

    if (entities.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading">No data available.</td></tr>';
        return;
    }

    var html = "";
    entities.forEach(function (entity, idx) {
        html +=
            "<tr>" +
            '<td class="rank-cell">' + (idx + 1) + "</td>" +
            "<td>" + escapeHtml(entity.name) + "</td>" +
            '<td><span class="type-badge">' + escapeHtml(entity.type) + "</span></td>" +
            "<td>" + formatNumber(entity.mention_count) + "</td>" +
            "</tr>";
    });

    tbody.innerHTML = html;
}

/**
 * Set text content of an element by ID.
 */
function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
}

/**
 * Format a number with locale-aware separators.
 */
function formatNumber(n) {
    if (n == null) return "--";
    return Number(n).toLocaleString();
}

/**
 * Escape HTML special characters to prevent XSS.
 */
function escapeHtml(str) {
    if (!str) return "";
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

/**
 * Convert simple markdown to HTML (no external library needed).
 * Handles bold, italic, inline code, bullet/numbered lists, and line breaks.
 */
function simpleMarkdown(text) {
    if (!text) return "";
    // Escape HTML first to prevent XSS
    var html = escapeHtml(text);
    // Bold: **text**
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // Italic: *text* (not inside bold)
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
    // Inline code: `code`
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Convert line-based formatting
    var lines = html.split("\n");
    var result = [];
    var inList = false;
    var listType = "";

    for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        var bulletMatch = line.match(/^[\-\*]\s+(.+)/);
        var numMatch = line.match(/^\d+\.\s+(.+)/);

        if (bulletMatch) {
            if (!inList || listType !== "ul") {
                if (inList) result.push("</" + listType + ">");
                result.push("<ul>");
                inList = true;
                listType = "ul";
            }
            result.push("<li>" + bulletMatch[1] + "</li>");
        } else if (numMatch) {
            if (!inList || listType !== "ol") {
                if (inList) result.push("</" + listType + ">");
                result.push("<ol>");
                inList = true;
                listType = "ol";
            }
            result.push("<li>" + numMatch[1] + "</li>");
        } else {
            if (inList) {
                result.push("</" + listType + ">");
                inList = false;
            }
            if (line.trim() === "") {
                result.push("<br>");
            } else {
                result.push(line);
            }
        }
    }
    if (inList) result.push("</" + listType + ">");

    return result.join("\n");
}

/**
 * Populate graph filter checkboxes from stats data.
 */
function loadGraphFilters(statsData) {
    var container = document.getElementById("type-checkboxes");
    if (!container || !statsData.entities_by_type) return;

    container.innerHTML = "";
    var entries = Object.entries(statsData.entities_by_type).sort(function (a, b) {
        return b[1] - a[1];
    });

    entries.forEach(function (entry) {
        var typeName = entry[0];
        var count = entry[1];
        var label = document.createElement("label");
        label.className = "checkbox-label";
        var checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = typeName;
        checkbox.checked = true;
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(" " + typeName + " (" + count + ")"));
        container.appendChild(label);
    });
}

/* ── Graph Rendering (vis.js) ── */

// Entity type colors (matching Python ENTITY_COLORS in visualization/styles.py)
var ENTITY_COLORS = {
    "Technology": "#4A90D9",
    "Library": "#7ED321",
    "Pattern": "#F5A623",
    "Decision": "#BD10E0",
    "Problem": "#D0021B",
    "Solution": "#417505",
    "File": "#9B9B9B",
    "Function": "#50E3C2",
    "Concept": "#B8E986"
};
var DEFAULT_COLOR = "#CCCCCC";

var graphNetwork = null;

/**
 * Build API URL from current filter state and load graph data.
 */
function applyGraphFilters() {
    var checkboxes = document.querySelectorAll("#type-checkboxes input:checked");
    var types = Array.from(checkboxes).map(function (cb) { return cb.value; }).join(",");
    var minMentions = document.getElementById("min-mentions-slider").value;
    var maxNodesEl = document.getElementById("max-nodes-slider");
    var maxNodes = maxNodesEl ? parseInt(maxNodesEl.value) : 0;

    var params = [];
    if (maxNodes > 0) params.push("limit=" + maxNodes);
    if (types) params.push("types=" + encodeURIComponent(types));
    if (minMentions > 0) params.push("min_mentions=" + minMentions);
    var url = "/api/graph/data" + (params.length ? "?" + params.join("&") : "");

    loadGraph(url);
}

/**
 * Fetch graph data from the API and render with vis.js.
 */
async function loadGraph(url) {
    url = url || "/api/graph/data";
    var container = document.getElementById("graph-canvas");
    if (!container) return;

    try {
        var resp = await fetch(url);
        var data = await resp.json();
        renderGraph(container, data);
    } catch (err) {
        container.innerHTML = '<p style="padding:20px;color:#999;">Failed to load graph.</p>';
    }
}

/**
 * Render graph data into a vis.js Network.
 */
function renderGraph(container, data) {
    var nodes = new vis.DataSet(data.nodes.map(function (n) {
        var size = Math.max(10, Math.min(60, 10 + Math.log(1 + n.mentions) * 8));
        var baseColor = ENTITY_COLORS[n.type] || DEFAULT_COLOR;
        return {
            id: n.id,
            label: n.label,
            shape: "dot",
            size: size,
            color: {
                background: baseColor,
                border: baseColor,
                highlight: { background: baseColor, border: "#333" },
                hover: { background: baseColor, border: "#333" }
            },
            borderWidth: 2,
            borderWidthSelected: 3,
            title: n.label + " (" + n.type + ") — " + n.mentions + "x",
            font: { size: 12, color: "#333", face: "arial" }
        };
    }));

    var edges = new vis.DataSet(data.edges.map(function (e) {
        return {
            from: e.from,
            to: e.to,
            label: e.label,
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
            color: { color: "#bbb", highlight: "#666", hover: "#888" },
            width: 1,
            font: { size: 9, color: "#999", strokeWidth: 2, strokeColor: "#fff" },
            smooth: { type: "continuous" }
        };
    }));

    var options = {
        physics: {
            stabilization: { iterations: 150, updateInterval: 25 },
            barnesHut: {
                gravitationalConstant: -4000,
                centralGravity: 0.3,
                springLength: 120,
                springConstant: 0.04,
                damping: 0.09,
                avoidOverlap: 0.2
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 100,
            navigationButtons: false,
            keyboard: false
        },
        edges: {
            smooth: { type: "continuous" }
        }
    };

    // Destroy previous network if it exists
    if (graphNetwork) {
        graphNetwork.destroy();
    }

    graphNetwork = new vis.Network(container, { nodes: nodes, edges: edges }, options);

    // Stop physics after stabilization so nodes stay still
    graphNetwork.on("stabilized", function () {
        graphNetwork.setOptions({ physics: { enabled: false } });
    });

    // Re-enable physics briefly when dragging to rebalance, then stop again
    graphNetwork.on("dragEnd", function () {
        graphNetwork.setOptions({ physics: { enabled: true } });
        setTimeout(function () {
            graphNetwork.setOptions({ physics: { enabled: false } });
        }, 1000);
    });
}

/* ── Entity Search ── */

/**
 * Debounce helper to limit the rate of function invocations.
 */
function debounce(fn, delay) {
    var timer = null;
    return function () {
        var context = this;
        var args = arguments;
        clearTimeout(timer);
        timer = setTimeout(function () {
            fn.apply(context, args);
        }, delay);
    };
}

// Live search with debounce
var searchInput = document.getElementById("search-input");
if (searchInput) {
    searchInput.addEventListener(
        "input",
        debounce(function (e) {
            var query = e.target.value.trim();
            if (query.length < 2) {
                document.getElementById("search-results").innerHTML = "";
                return;
            }
            searchEntities(query);
        }, 300)
    );
}

/**
 * Fetch search results from the API and render them.
 */
async function searchEntities(query) {
    try {
        var resp = await fetch("/api/search?q=" + encodeURIComponent(query));
        var results = await resp.json();
        renderSearchResults(results);
    } catch (err) {
        document.getElementById("search-results").innerHTML =
            '<div class="search-empty">Search failed.</div>';
    }
}

/**
 * Render search result items as a dropdown list.
 */
function renderSearchResults(results) {
    var container = document.getElementById("search-results");
    if (!results.length) {
        container.innerHTML = '<div class="search-empty">No results found</div>';
        return;
    }
    var html = "";
    results.forEach(function (entity) {
        html +=
            '<div class="search-result-item" data-id="' +
            escapeHtml(entity.id) +
            '">' +
            '<span class="result-name">' +
            escapeHtml(entity.name) +
            "</span>" +
            '<span class="type-badge">' +
            escapeHtml(entity.type) +
            "</span>" +
            '<span class="result-count">' +
            entity.mention_count +
            "x</span>" +
            "</div>";
    });
    container.innerHTML = html;

    // Click handlers for each result item
    container.querySelectorAll(".search-result-item").forEach(function (item) {
        item.addEventListener("click", function () {
            loadEntityDetail(this.getAttribute("data-id"));
        });
    });
}

/**
 * Fetch entity detail and connections from the API.
 */
async function loadEntityDetail(entityId) {
    try {
        var resp = await fetch(
            "/api/entity/" + encodeURIComponent(entityId) + "/connections"
        );
        if (!resp.ok) return;
        var data = await resp.json();
        renderEntityDetail(data);
    } catch (err) {
        // Silently ignore fetch errors
    }
}

/**
 * Render entity detail panel with connections.
 */
function renderEntityDetail(data) {
    var detail = document.getElementById("entity-detail");
    detail.style.display = "block";

    setText("entity-name", data.entity.name);
    setText("entity-type", data.entity.type);
    setText("entity-mentions", String(data.entity.mention_count));
    setText("entity-first-seen", data.entity.first_seen || "Unknown");

    // Clear search results when showing detail
    document.getElementById("search-results").innerHTML = "";

    // Render connections
    var container = document.getElementById("entity-connections");
    if (!data.connections.length) {
        container.innerHTML = "<p>No connections found.</p>";
        return;
    }

    var html = "";
    data.connections.forEach(function (conn) {
        var arrow = conn.direction === "outgoing" ? "\u2192" : "\u2190";
        html +=
            '<div class="connection-item" data-id="' +
            escapeHtml(conn.entity.id) +
            '">' +
            '<span class="connection-rel">' +
            arrow +
            " " +
            escapeHtml(conn.relationship) +
            "</span>" +
            '<span class="connection-name">' +
            escapeHtml(conn.entity.name) +
            "</span>" +
            '<span class="type-badge">' +
            escapeHtml(conn.entity.type) +
            "</span>" +
            '<span class="result-count">' +
            conn.entity.mention_count +
            "x</span>" +
            "</div>";
    });
    container.innerHTML = html;

    // Click on connection navigates to that entity
    container.querySelectorAll(".connection-item").forEach(function (item) {
        item.addEventListener("click", function () {
            loadEntityDetail(this.getAttribute("data-id"));
        });
    });
}

/* ── Chat Interface ── */

var chatInput = document.getElementById("chat-input");
var chatSend = document.getElementById("chat-send");
var chatMessageId = 0;

if (chatInput && chatSend) {
    chatSend.addEventListener("click", sendChatMessage);
    chatInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") sendChatMessage();
    });
}

/**
 * Send the user's question to the /api/ask endpoint and display the response.
 */
async function sendChatMessage() {
    var input = document.getElementById("chat-input");
    var question = input.value.trim();
    if (!question) return;

    input.value = "";
    appendChatMessage("user", question);

    var loadingId = appendChatMessage("ai", "Thinking...", true);

    try {
        var resp = await fetch("/api/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question }),
        });

        if (!resp.ok) {
            var error = await resp.json();
            updateChatMessage(loadingId, "Error: " + (error.detail || "Unknown error"));
            return;
        }

        var data = await resp.json();

        var html = simpleMarkdown(data.answer);

        if (data.cypher) {
            html +=
                '<details class="cypher-details"><summary>Show Cypher query</summary>' +
                '<pre class="cypher-code">' +
                escapeHtml(data.cypher) +
                "</pre></details>";
        }

        if (data.usage) {
            html +=
                '<div class="chat-cost">Cost: $' +
                data.usage.estimated_cost_usd.toFixed(4) +
                " | Tokens: " +
                data.usage.input_tokens +
                " in / " +
                data.usage.output_tokens +
                " out</div>";
        }

        updateChatMessage(loadingId, html, true);

        // Add error styling when the server reports a query error
        if (data.error) {
            var el = document.getElementById(loadingId);
            if (el) el.classList.add("chat-error");
        }
    } catch (err) {
        updateChatMessage(loadingId, "Error: Could not reach the server.");
    }
}

/**
 * Append a chat bubble and return its DOM id.
 * When isLoading is true, adds the chat-loading class for styling.
 */
function appendChatMessage(role, content, isLoading) {
    var messages = document.getElementById("chat-messages");
    var id = "chat-msg-" + ++chatMessageId;
    var div = document.createElement("div");
    div.id = id;
    div.className = "chat-bubble chat-" + role;
    if (isLoading) div.classList.add("chat-loading");
    div.textContent = content;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return id;
}

/**
 * Update an existing chat bubble by id.
 * Removes loading state when content is updated.
 */
function updateChatMessage(id, content, isHtml) {
    var el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("chat-loading");
    if (isHtml) {
        el.innerHTML = content;
    } else {
        el.textContent = content;
    }
    var messages = document.getElementById("chat-messages");
    messages.scrollTop = messages.scrollHeight;
}

// Slider value displays
var slider = document.getElementById("min-mentions-slider");
if (slider) {
    slider.addEventListener("input", function (e) {
        var display = document.getElementById("min-mentions-value");
        if (display) display.textContent = e.target.value;
    });
}

var maxNodesSlider = document.getElementById("max-nodes-slider");
if (maxNodesSlider) {
    maxNodesSlider.addEventListener("input", function (e) {
        var display = document.getElementById("max-nodes-value");
        if (display) display.textContent = e.target.value === "0" ? "All" : e.target.value;
    });
}

// Apply button
var applyBtn = document.getElementById("apply-filters");
if (applyBtn) {
    applyBtn.addEventListener("click", applyGraphFilters);
}
