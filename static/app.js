document.addEventListener('DOMContentLoaded', () => {
    const deployBtn = document.getElementById('deploy-agent-btn');
    const logsContainer = document.getElementById('logs-container');
    const totalTicketsEl = document.getElementById('total-tickets');
    const resolvedTicketsEl = document.getElementById('resolved-tickets');
    const escalatedTicketsEl = document.getElementById('escalated-tickets');

    let ticketCache = {};

    // Fetch initial tickets to populate summary
    const refreshQueue = () => {
        fetch('/api/tickets')
            .then(res => res.json())
            .then(data => {
                totalTicketsEl.textContent = data.length;
                data.forEach(t => ticketCache[t.ticket_id] = t);
                renderActiveQueue(data);
            });
    };
    
    // Tab functionality
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
            
            btn.classList.add('active');
            document.getElementById(btn.getAttribute('data-target')).style.display = 'flex';
        });
    });

    const renderActiveQueue = (tickets) => {
        const activeContainer = document.getElementById('active-queue');
        activeContainer.innerHTML = '';
        const openTickets = tickets.filter(t => t.status === 'open' || !t.status);
        if (openTickets.length === 0) {
            activeContainer.innerHTML = '<div class="empty-state">No Active Tickets.</div>';
            return;
        }
        openTickets.forEach(t => {
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerHTML = `
                <div class="log-header">
                    <span>Ticket ID: ${t.ticket_id}</span>
                    <span style="color:var(--text-secondary); font-size:0.8rem; font-weight:normal;">${t.customer_email || 'Unknown User'}</span>
                </div>
                <div class="log-result">
                    <strong>Subject:</strong> ${t.subject || 'N/A'}<br/>
                    <strong>Issue:</strong> <em>"${t.body || 'No issue text found.'}"</em>
                </div>
            `;
            activeContainer.appendChild(div);
        });
    };
    refreshQueue();

    const submitBtn = document.getElementById('submit-ticket-btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
            const email = document.getElementById('new-t-email').value;
            const subject = document.getElementById('new-t-subject').value;
            const body = document.getElementById('new-t-body').value;
            
            if (!email || !subject || !body) return alert("Please fill all fields.");
            
            submitBtn.textContent = 'Submitting...';
            const res = await fetch('/api/ticket/new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, subject, body })
            });
            const data = await res.json();
            if (data.status === 'success') {
                alert(`Ticket ${data.ticket.ticket_id} added successfully!`);
                document.getElementById('new-t-email').value = '';
                document.getElementById('new-t-subject').value = '';
                document.getElementById('new-t-body').value = '';
                refreshQueue(); // Refresh queue counter
                submitBtn.textContent = 'Submit Ticket';
            }
        });
    }

    deployBtn.addEventListener('click', async () => {
        deployBtn.disabled = true;
        deployBtn.textContent = 'Agent Processing...';
        deployBtn.style.opacity = '0.7';
        document.getElementById('resolved-queue').innerHTML = '<div class="empty-state">Processing...</div>';
        document.getElementById('escalated-queue').innerHTML = '<div class="empty-state">Processing...</div>';

        try {
            const response = await fetch('/api/run', { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                renderLogs(data.logs);
                refreshQueue(); // Move tickets out of Active Queue if processed
                
                // Animate stats
                let resolved = 0;
                let escalated = 0;
                data.logs.forEach(log => {
                    const status = log.outcome?.status?.toLowerCase() || log.outcome?.action?.toLowerCase() || 'resolved';
                    if (status.includes('escala')) escalated++;
                    else resolved++; 
                });
                
                animateValue(resolvedTicketsEl, 0, resolved, 1000);
                animateValue(escalatedTicketsEl, 0, escalated, 1000);
                
                deployBtn.textContent = 'Run Completed';
                deployBtn.style.background = '#10b981';
            } else {
                logsContainer.innerHTML = `<div class="empty-state" style="color: #ef4444;">Error: ${data.error}</div>`;
                deployBtn.textContent = 'Deployment Failed';
                deployBtn.disabled = false;
            }
        } catch (error) {
            logsContainer.innerHTML = `<div class="empty-state" style="color: #ef4444;">Network Error: ${error.message}</div>`;
            deployBtn.textContent = 'Retry Deployment';
            deployBtn.disabled = false;
        }
    });

    function renderLogs(logs) {
        const resolvedContainer = document.getElementById('resolved-queue');
        const escalatedContainer = document.getElementById('escalated-queue');
        resolvedContainer.innerHTML = '';
        escalatedContainer.innerHTML = '';
        
        let delay = 0;
        
        logs.forEach(log => {
            setTimeout(() => {
                const div = document.createElement('div');
                const tInfo = ticketCache[log.ticket_id] || {};
                
                const stepsCount = log.steps ? log.steps.length : (log.trace ? log.trace.length : 1);
                const outcomeText = log.outcome?.action || log.outcome?.status || 'Processed';
                
                let finalAction = "System Evaluation concluded.";
                if (log.outcome) {
                    finalAction = JSON.stringify(log.outcome?.message || log.outcome?.summary || log.outcome || "Finished");
                }
                
                let cssClass = 'log-entry';
                let isEscalated = false;
                if (outcomeText.includes('escala')) {
                    cssClass += ' escalated';
                    isEscalated = true;
                } else if (outcomeText.includes('replied') || outcomeText.includes('resolv')) {
                    cssClass += ' resolved';
                } else if (outcomeText.includes('failed')) {
                    cssClass += ' failed';
                } else {
                    cssClass += ' resolved';
                }

                div.className = cssClass;
                div.innerHTML = `
                    <div class="log-header">
                        <span>Ticket ID: ${log.ticket_id}</span>
                        <span style="color:var(--text-secondary); font-size:0.8rem; font-weight:normal;">${tInfo.customer_email || 'Unknown User'}</span>
                    </div>
                    <div class="log-result" style="border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 10px;">
                        <strong>Subject:</strong> ${tInfo.subject || 'N/A'}<br/>
                        <strong>Issue:</strong> <em>"${tInfo.body || 'No issue text found.'}"</em>
                    </div>
                    <div class="log-result">
                        <strong>Reasoning Trace:</strong><br/>
                        ${stepsCount} interaction/reasoning steps executed to reach conclusion.
                        <br/><br/>
                        <strong>Final Outcome [${outcomeText.toUpperCase()}]:</strong><br/>
                        ${finalAction}
                    </div>
                `;
                
                if (isEscalated) {
                    escalatedContainer.insertBefore(div, escalatedContainer.firstChild);
                } else {
                    resolvedContainer.insertBefore(div, resolvedContainer.firstChild);
                }
            }, delay);
            delay += 300;
        });
        
        if (resolvedContainer.innerHTML === '') resolvedContainer.innerHTML = '<div class="empty-state">No Resolved Tickets yet.</div>';
        if (escalatedContainer.innerHTML === '') escalatedContainer.innerHTML = '<div class="empty-state">No Escalated Tickets yet.</div>';
    }

    function animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }
});
