# utils/focus_timer.py
import streamlit.components.v1 as components

def render_focus_timer():
    """Rendu d'un mini-timer interactif client-side (Sprint Pomodoro adapté ado)."""
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
            
            * {
                box-sizing: border-box;
                font-family: 'Plus Jakarta Sans', sans-serif;
                margin: 0;
                padding: 0;
            }
            
            body {
                background: transparent;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 4px;
            }
            
            .timer-card {
                background: #ffffff;
                border: 1.5px solid #e2e8f0;
                border-radius: 16px;
                padding: 12px 18px;
                display: flex;
                align-items: center;
                gap: 16px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.04);
                max-width: 580px;
                width: 100%;
            }
            
            .timer-badge {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 0.8rem;
                font-weight: 700;
                color: #4f46e5;
                background: #f5f7ff;
                padding: 6px 12px;
                border-radius: 50px;
                white-space: nowrap;
            }
            
            .time-display {
                font-size: 1.5rem;
                font-weight: 800;
                color: #1e1b4b;
                letter-spacing: 0.05em;
                min-width: 80px;
                text-align: center;
            }
            
            .btn-group {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            button {
                cursor: pointer;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 0.82rem;
                padding: 6px 12px;
                transition: all 0.2s ease;
            }
            
            .preset-btn {
                background: #f1f5f9;
                color: #475569;
            }
            
            .preset-btn.active {
                background: #4f46e5;
                color: #ffffff;
            }
            
            .action-btn {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: #ffffff;
                padding: 6px 14px;
                box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
            }
            
            .action-btn.running {
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            }
            
            .reset-btn {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                color: #64748b;
            }
            
            .reset-btn:hover {
                background: #fee2e2;
                color: #ef4444;
                border-color: #fca5a5;
            }
            
            .alert-msg {
                display: none;
                color: #059669;
                font-size: 0.8rem;
                font-weight: 700;
                animation: pulse 1s infinite alternate;
            }
            
            @keyframes pulse {
                from { opacity: 0.7; transform: scale(0.98); }
                to { opacity: 1; transform: scale(1.02); }
            }
        </style>
    </head>
    <body>
        <div class="timer-card">
            <div class="timer-badge">
                <span>⏱️</span> Sprint Focus
            </div>
            
            <div class="btn-group">
                <button class="preset-btn active" onclick="setDuration(5, this)">5 min</button>
                <button class="preset-btn" onclick="setDuration(10, this)">10 min</button>
                <button class="preset-btn" onclick="setDuration(15, this)">15 min</button>
            </div>
            
            <div class="time-display" id="time">05:00</div>
            
            <div class="btn-group">
                <button class="action-btn" id="startBtn" onclick="toggleTimer()">▶️ Go !</button>
                <button class="reset-btn" onclick="resetTimer()" title="Réinitialiser">🔄</button>
            </div>
            
            <div class="alert-msg" id="alertMsg">🎉 Pause méritée !</div>
        </div>

        <script>
            let durationSeconds = 5 * 60;
            let remainingSeconds = durationSeconds;
            let timerInterval = null;
            let isRunning = false;
            
            function updateDisplay() {
                const mins = Math.floor(remainingSeconds / 60);
                const secs = remainingSeconds % 60;
                document.getElementById('time').innerText = 
                    String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
            }
            
            function setDuration(mins, btn) {
                if (isRunning) return;
                durationSeconds = mins * 60;
                remainingSeconds = durationSeconds;
                document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('alertMsg').style.display = 'none';
                updateDisplay();
            }
            
            function toggleTimer() {
                const btn = document.getElementById('startBtn');
                if (isRunning) {
                    clearInterval(timerInterval);
                    isRunning = false;
                    btn.innerText = '▶️ Reprendre';
                    btn.classList.remove('running');
                } else {
                    document.getElementById('alertMsg').style.display = 'none';
                    isRunning = true;
                    btn.innerText = '⏸️ Pause';
                    btn.classList.add('running');
                    
                    timerInterval = setInterval(() => {
                        if (remainingSeconds > 0) {
                            remainingSeconds--;
                            updateDisplay();
                        } else {
                            clearInterval(timerInterval);
                            isRunning = false;
                            btn.innerText = '▶️ Go !';
                            btn.classList.remove('running');
                            document.getElementById('alertMsg').style.display = 'block';
                            
                            // Signal sonore doux
                            try {
                                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                                const osc = ctx.createOscillator();
                                const gain = ctx.createGain();
                                osc.connect(gain);
                                gain.connect(ctx.destination);
                                osc.frequency.value = 587.33; // Note Ré5
                                gain.gain.setValueAtTime(0.2, ctx.currentTime);
                                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);
                                osc.start();
                                osc.stop(ctx.currentTime + 0.8);
                            } catch(e) {}
                        }
                    }, 1000);
                }
            }
            
            function resetTimer() {
                clearInterval(timerInterval);
                isRunning = false;
                remainingSeconds = durationSeconds;
                const btn = document.getElementById('startBtn');
                btn.innerText = '▶️ Go !';
                btn.classList.remove('running');
                document.getElementById('alertMsg').style.display = 'none';
                updateDisplay();
            }
            
            updateDisplay();
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=75)
