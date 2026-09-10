# utils/audio_player.py
import re
import json
import streamlit.components.v1 as components

def clean_text_for_speech(text: str) -> str:
    """Nettoie le markdown pour une lecture vocale naturelle et agréable."""
    if not text:
        return ""
    # Retirer les blocs de code, SVG, et diagrammes Mermaid
    t = re.sub(r'```[\s\S]*?```', '', text)
    t = re.sub(r'<svg[\s\S]*?</svg>', '', t)
    t = re.sub(r'<[^>]+>', '', t)
    # Retirer les marqueurs spéciaux
    t = re.sub(r':red\[(.*?)\]', r'\1', t)
    t = re.sub(r':green\[(.*?)\]', r'\1', t)
    # Retirer les liens et symboles markdown
    t = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', t)
    t = re.sub(r'[#*_`~>|]', '', t)
    # Remplacer les tirets et émojis excessifs
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:6000] # Limiter à environ 5 à 7 min de lecture

def render_audio_player(course_text: str):
    """Rendu d'un lecteur vocal Web Speech API fluide, sans latence ni coût serveur."""
    clean_text = clean_text_for_speech(course_text)
    if not clean_text:
        return

    text_json = json.dumps(clean_text)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
            
            * {{
                box-sizing: border-box;
                font-family: 'Plus Jakarta Sans', sans-serif;
                margin: 0;
                padding: 0;
            }}
            
            body {{
                background: transparent;
                display: flex;
                align-items: center;
                padding: 4px;
            }}
            
            .player-card {{
                background: linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%);
                border: 1.5px solid #bae6fd;
                border-radius: 16px;
                padding: 12px 20px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                width: 100%;
                box-shadow: 0 2px 10px rgba(2, 132, 199, 0.06);
            }}
            
            .player-info {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .player-icon {{
                font-size: 1.3rem;
                background: #ffffff;
                width: 38px;
                height: 38px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            }}
            
            .player-text h4 {{
                font-size: 0.9rem;
                font-weight: 700;
                color: #0369a1;
                margin-bottom: 2px;
            }}
            
            .player-text p {{
                font-size: 0.75rem;
                color: #0284c7;
                font-weight: 500;
            }}
            
            .player-controls {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            button {{
                cursor: pointer;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 0.82rem;
                padding: 7px 14px;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            
            .play-btn {{
                background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
                color: #ffffff;
                box-shadow: 0 2px 8px rgba(2, 132, 199, 0.3);
            }}
            
            .play-btn:hover {{
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);
            }}
            
            .stop-btn {{
                background: #ffffff;
                border: 1px solid #cbd5e1;
                color: #475569;
            }}
            
            .stop-btn:hover {{
                background: #fee2e2;
                color: #dc2626;
                border-color: #fca5a5;
            }}
            
            .rate-select {{
                background: #ffffff;
                border: 1px solid #bae6fd;
                border-radius: 8px;
                font-size: 0.78rem;
                font-weight: 700;
                color: #0369a1;
                padding: 6px 10px;
                cursor: pointer;
                outline: none;
            }}
            
            .waveform {{
                display: none;
                align-items: center;
                gap: 3px;
                height: 18px;
            }}
            
            .wave-bar {{
                width: 3px;
                height: 100%;
                background: #0284c7;
                border-radius: 3px;
                animation: wave 0.8s ease-in-out infinite alternate;
            }}
            
            .wave-bar:nth-child(2) {{ animation-delay: 0.2s; height: 60%; }}
            .wave-bar:nth-child(3) {{ animation-delay: 0.4s; height: 90%; }}
            .wave-bar:nth-child(4) {{ animation-delay: 0.1s; height: 50%; }}
            
            @keyframes wave {{
                0% {{ height: 20%; }}
                100% {{ height: 100%; }}
            }}
        </style>
    </head>
    <body>
        <div class="player-card">
            <div class="player-info">
                <div class="player-icon">🎧</div>
                <div class="player-text">
                    <h4>Lecture Vocale du Cours</h4>
                    <p>Écoute la leçon à voix haute pour soulager tes yeux</p>
                </div>
                <div class="waveform" id="waveform">
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                </div>
            </div>
            
            <div class="player-controls">
                <select class="rate-select" id="rateSelect" onchange="changeRate(this.value)" title="Vitesse de lecture">
                    <option value="0.85">0.85x (Calme)</option>
                    <option value="1.0" selected>1.0x (Normal)</option>
                    <option value="1.15">1.15x (Dynamique)</option>
                </select>
                
                <button class="play-btn" id="playBtn" onclick="togglePlay()">
                    <span>▶️</span> Écouter
                </button>
                <button class="stop-btn" onclick="stopAudio()" title="Arrêter">
                    <span>⏹️</span>
                </button>
            </div>
        </div>

        <script>
            const textToRead = {text_json};
            let synth = window.speechSynthesis;
            let utterance = null;
            let isPlaying = false;
            let currentRate = 1.0;
            
            function changeRate(val) {{
                currentRate = parseFloat(val);
                if (isPlaying) {{
                    stopAudio();
                    startReading();
                }}
            }}
            
            function startReading() {{
                if (!synth) return;
                synth.cancel();
                
                utterance = new SpeechSynthesisUtterance(textToRead);
                utterance.lang = 'fr-FR';
                utterance.rate = currentRate;
                
                // Recherche d'une voix française naturelle
                const voices = synth.getVoices();
                const frenchVoice = voices.find(v => v.lang.startsWith('fr') && !v.name.includes('Compact')) 
                                  || voices.find(v => v.lang.startsWith('fr'));
                if (frenchVoice) {{
                    utterance.voice = frenchVoice;
                }}
                
                utterance.onstart = () => {{
                    isPlaying = true;
                    document.getElementById('playBtn').innerHTML = '<span>⏸️</span> Pause';
                    document.getElementById('waveform').style.display = 'flex';
                }};
                
                utterance.onend = () => {{
                    stopAudio();
                }};
                
                utterance.onerror = () => {{
                    stopAudio();
                }};
                
                synth.speak(utterance);
            }}
            
            function togglePlay() {{
                if (!synth) {{
                    alert("La synthèse vocale n'est pas supportée par ce navigateur.");
                    return;
                }}
                
                if (synth.speaking && !synth.paused) {{
                    synth.pause();
                    isPlaying = false;
                    document.getElementById('playBtn').innerHTML = '<span>▶️</span> Reprendre';
                    document.getElementById('waveform').style.display = 'none';
                }} else if (synth.paused) {{
                    synth.resume();
                    isPlaying = true;
                    document.getElementById('playBtn').innerHTML = '<span>⏸️</span> Pause';
                    document.getElementById('waveform').style.display = 'flex';
                }} else {{
                    startReading();
                }}
            }}
            
            function stopAudio() {{
                if (synth) synth.cancel();
                isPlaying = false;
                document.getElementById('playBtn').innerHTML = '<span>▶️</span> Écouter';
                document.getElementById('waveform').style.display = 'none';
            }}
            
            // Préchargement des voix
            if (synth) {{
                synth.onvoiceschanged = () => synth.getVoices();
            }}
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=75)
