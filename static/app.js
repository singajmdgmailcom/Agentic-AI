document.addEventListener('DOMContentLoaded', () => {
    const deployBtn = document.getElementById('deploy-agent-btn');
    const logsContainer = document.getElementById('logs-container');
    const totalTicketsEl = document.getElementById('total-tickets');
    const resolvedTicketsEl = document.getElementById('resolved-tickets');
    const escalatedTicketsEl = document.getElementById('escalated-tickets');

    // Fetch initial tickets to populate summary
    fetch('/api/tickets')
        .then(res => res.json())
        .then(data => {
            totalTicketsEl.textContent = data.length;
        });

    deployBtn.addEventListener('click', async () => {
        deployBtn.disabled = true;
        deployBtn.textContent = 'Agent Processing...';
        deployBtn.style.opacity = '0.7';
        logsContainer.innerHTML = '<div class="empty-state">Initializing ReAct Engine... Fetching LLM Inference...</div>';

        try {
            const response = await fetch('/api/run', { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                renderLogs(data.logs);
                
                // Animate stats
                let resolved = 0;
                let escalated = 0;
                data.logs.forEach(log => {
                    const status = log.outcome?.status?.toLowerCase() || log.outcome?.action?.toLowerCase() || '';
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
        logsContainer.innerHTML = '';
        let delay = 0;
        
        logs.forEach(log => {
            setTimeout(() => {
                const div = document.createElement('div');
                const outcomeText = log.outcome?.action || log.outcome?.status || 'Processed';
                
                let cssClass = 'log-entry';
                if (outcomeText.includes('escala')) cssClass += ' escalated';
                else if (outcomeText.includes('replied')) cssClass += ' resolved';
                else if (outcomeText.includes('failed')) cssClass += ' failed';

                div.className = cssClass;
                div.innerHTML = `
                    <div class="log-header">
                        <span>Ticket ID: ${log.ticket_id}</span>
                        <span>Outcome: ${outcomeText.toUpperCase()}</span>
                    </div>
                    <div class="log-result">
                        <strong>Reasoning Trace:</strong><br/>
                        ${log.steps.length} interaction steps detected.
                        <br/><br/>
                        <strong>Final Action:</strong><br/>
                        ${JSON.stringify(log.outcome?.message || log.outcome?.summary || log.outcome || "Finished", null, 2)}
                    </div>
                `;
                logsContainer.insertBefore(div, logsContainer.firstChild);
            }, delay);
            delay += 300; // staggering logic for cool visual effect
        });
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
