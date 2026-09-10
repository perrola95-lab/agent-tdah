# utils/progress_tracker.py
import streamlit as st

def get_session_progress() -> tuple[int, list[dict]]:
    """Calcule le pourcentage d'avancement de la séance et la liste des étapes."""
    steps = [
        {
            "id": "course",
            "name": "1. Fiche générée",
            "icon": "📚",
            "done": 'course_markdown' in st.session_state and bool(st.session_state['course_markdown'])
        },
        {
            "id": "mindmap",
            "name": "2. Carte explorée",
            "icon": "🗺️",
            "done": 'mermaid_code' in st.session_state and bool(st.session_state['mermaid_code'])
        },
        {
            "id": "tutor",
            "name": "3. Défi guidé",
            "icon": "🎯",
            "done": st.session_state.get('tutor_completed', False) or len(st.session_state.get('tutor_history', [])) >= 4
        },
        {
            "id": "quiz",
            "name": "4. Quiz validé",
            "icon": "❓",
            "done": st.session_state.get('quiz_submitted', False)
        }
    ]
    
    done_count = sum(1 for s in steps if s["done"])
    percentage = int((done_count / len(steps)) * 100)
    return percentage, steps

def render_progress_banner():
    """Affiche le bandeau de progression dynamique et valorisant en haut de page."""
    percentage, steps = get_session_progress()

    step_chips = []
    for s in steps:
        bg = "#dcfce7" if s["done"] else "#f8fafc"
        color = "#15803d" if s["done"] else "#94a3b8"
        border = "1px solid #86efac" if s["done"] else "1px solid #e2e8f0"
        check = "✅" if s["done"] else s["icon"]
        chip = (
            f'<div style="background:{bg}; border:{border}; color:{color}; '
            f'padding:5px 12px; border-radius:30px; font-size:0.82rem; font-weight:700; '
            f'display:flex; align-items:center; gap:6px;">'
            f'<span>{check}</span> {s["name"]}</div>'
        )
        step_chips.append(chip)

    chips_html = "".join(step_chips)

    progress_html = (
        f'<div style="background:#ffffff; border:1.5px solid #e2e8f0; border-radius:16px; '
        f'padding:14px 20px; margin-bottom:1.2rem; box-shadow:0 2px 8px rgba(0,0,0,0.03);">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
        f'<div style="display:flex; align-items:center; gap:8px;">'
        f'<span style="font-size:1.1rem;">🚀</span>'
        f'<span style="font-weight:800; font-size:0.95rem; color:#1e1b4b;">Progression de ta séance</span>'
        f'</div>'
        f'<span style="font-weight:800; font-size:0.85rem; color:#4f46e5; background:#f5f7ff; '
        f'padding:4px 10px; border-radius:50px;">{percentage}% terminé</span>'
        f'</div>'
        f'<div style="background:#f1f5f9; border-radius:10px; height:10px; overflow:hidden; margin-bottom:12px;">'
        f'<div style="width:{percentage}%; height:100%; background:linear-gradient(90deg, #4f46e5 0%, #10b981 100%); '
        f'border-radius:10px; transition:width 0.4s ease-in-out;"></div>'
        f'</div>'
        f'<div style="display:flex; justify-content:space-between; gap:6px; flex-wrap:wrap;">'
        f'{chips_html}'
        f'</div>'
        f'</div>'
    )
    st.markdown(progress_html, unsafe_allow_html=True)

def render_learning_missions():
    """Affiche une checklist interactive de 3 missions motivantes pour l'élève."""
    if 'course_markdown' not in st.session_state:
        return

    if 'mission_1' not in st.session_state:
        st.session_state['mission_1'] = False
    if 'mission_2' not in st.session_state:
        st.session_state['mission_2'] = False
    if 'mission_3' not in st.session_state:
        st.session_state['mission_3'] = False

    with st.expander("🎯 **Mes 3 Missions Clés du Jour** (à cocher au fil de ta lecture)", expanded=True):
        st.caption("Coche chaque défi dès que tu te sens prêt. C'est toi qui valides tes progrès !")
        
        m1 = st.checkbox("1. 💡 J'ai bien compris la notion et la formule principale", value=st.session_state['mission_1'], key="chk_m1")
        m2 = st.checkbox("2. ⚠️ J'ai repéré le piège classique à ne surtout pas faire", value=st.session_state['mission_2'], key="chk_m2")
        m3 = st.checkbox("3. 🏆 Je suis capable de l'expliquer avec un exemple concret", value=st.session_state['mission_3'], key="chk_m3")
        
        st.session_state['mission_1'] = m1
        st.session_state['mission_2'] = m2
        st.session_state['mission_3'] = m3

        if m1 and m2 and m3:
            st.success("🎉 **Incroyable ! Tu as validé tes 3 missions de cours !** Tu es paré pour les exercices.")

def render_badges_shelf():
    """Affiche les badges débloqués sous forme d'étagère de trophées."""
    badges = []
    if 'course_markdown' in st.session_state:
        badges.append({"icon": "🚀", "title": "Explorateur", "desc": "Cours généré"})
    if 'mermaid_code' in st.session_state and st.session_state['mermaid_code']:
        badges.append({"icon": "🎨", "title": "Vision Totale", "desc": "Carte explorée"})
    if st.session_state.get('tutor_completed', False):
        badges.append({"icon": "🧠", "title": "Cerveau d'Acier", "desc": "Tuteur validé"})
    if st.session_state.get('quiz_submitted', False):
        badges.append({"icon": "🏆", "title": "Maître du Quiz", "desc": "Quiz complété"})

    if not badges:
        return

    st.divider()
    st.subheader("🏅 Ta Galerie de Trophées du Jour")
    cols = st.columns(len(badges))
    for idx, b in enumerate(badges):
        with cols[idx]:
            card_html = (
                f'<div style="background:#ffffff; border:2px solid #e0e7ff; border-radius:14px; '
                f'padding:12px; text-align:center; box-shadow:0 4px 12px rgba(99, 102, 241, 0.08);">'
                f'<div style="font-size:1.8rem; margin-bottom:4px;">{b["icon"]}</div>'
                f'<div style="font-weight:800; font-size:0.9rem; color:#3730a3;">{b["title"]}</div>'
                f'<div style="font-size:0.75rem; color:#6b7280;">{b["desc"]}</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
