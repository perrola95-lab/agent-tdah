import streamlit as st
from services.auth_service import AuthService

def render_admin_panel():
    """Affiche le panneau d'administration pour la modération et gestion des comptes."""
    auth_service = AuthService()

    pending_users = auth_service.get_pending_users()
    all_users = auth_service.get_all_users()

    badge_count = f"({len(pending_users)} en attente)" if pending_users else ""

    db_badge = "☁️ Google Cloud Firestore (Persistant)" if auth_service.use_firestore else "💾 SQLite Local (Développement)"
    with st.expander(f"🛡️ **Espace Administrateur • Gestion des Comptes {badge_count}**", expanded=bool(pending_users)):
        st.caption(f"Validez ou gérez les accès des utilisateurs. • **Base active :** `{db_badge}`")

        # --- ONGLET 1 : DEMANDES EN ATTENTE ---
        st.subheader(f"🔔 Demandes d'inscription en attente ({len(pending_users)})")

        if not pending_users:
            st.success("✅ Aucune demande en attente. Tous les comptes ont été traités !")
        else:
            for u in pending_users:
                col_info, col_plan, col_act1, col_act2 = st.columns([3, 1.8, 1.2, 1.2], vertical_alignment="center")

                with col_info:
                    st.markdown(f"**👤 {u['name']}** (`{u['email']}`)")
                    st.caption(f"Inscrit le : {u['created_at'][:16] if u['created_at'] else 'Récemment'}")

                with col_plan:
                    selected_plan = st.selectbox(
                        "Formule :",
                        options=["gratuit", "premium", "fondateur"],
                        key=f"plan_select_{u['id']}",
                        label_visibility="collapsed"
                    )

                with col_act1:
                    if st.button("✅ Accepter", key=f"btn_approve_{u['id']}", type="primary", use_container_width=True):
                        auth_service.approve_user(u["id"], plan=selected_plan)
                        st.success(f"Compte {u['name']} validé avec succès !")
                        st.rerun()

                with col_act2:
                    if st.button("🗑️ Refuser", key=f"btn_reject_{u['id']}", type="secondary", use_container_width=True):
                        auth_service.reject_or_delete_user(u["id"])
                        st.warning(f"Demande de {u['name']} rejetée.")
                        st.rerun()

                st.divider()

        # --- ONGLET 2 : UTILISATEURS ACTIFS & ABONNEMENTS ---
        st.subheader(f"👥 Comptes enregistrés ({len(all_users)})")

        with st.expander("Consulter la liste complète des utilisateurs", expanded=False):
            for u in all_users:
                col_u_info, col_u_status, col_u_toggle, col_u_del = st.columns([3, 2, 1.3, 1.2], vertical_alignment="center")

                status_label = "🟢 Actif" if u["is_approved"] else "⏳ En attente"
                admin_badge = " • 👑 Admin" if u["is_admin"] else ""
                plan_badge = f" • Formule : `{u['subscription_plan']}`"

                with col_u_info:
                    st.markdown(f"**{u['name']}** (`{u['email']}`){admin_badge}")
                    st.caption(f"Statut : {status_label}{plan_badge}")

                with col_u_status:
                    last_seen = u['last_login'][:16] if u['last_login'] else "Jamais connecté"
                    st.caption(f"Dernière connexion : {last_seen}")

                with col_u_toggle:
                    if not u["is_admin"]:
                        if u["is_approved"]:
                            if st.button("Suspendre", key=f"btn_susp_{u['id']}", use_container_width=True):
                                auth_service.toggle_user_access(u["id"], 0)
                                st.rerun()
                        else:
                            if st.button("Activer", key=f"btn_act_{u['id']}", use_container_width=True):
                                auth_service.toggle_user_access(u["id"], 1)
                                st.rerun()

                with col_u_del:
                    if not u["is_admin"]:
                        if st.button("Supprimer", key=f"btn_del_{u['id']}", use_container_width=True):
                            auth_service.reject_or_delete_user(u["id"])
                            st.rerun()

                st.write("")
