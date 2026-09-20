"""
ADITUS (Portail GNC-PASS)
Point d'entrée principal de l'application Streamlit.
"""

import streamlit as st

from config import (
    APP_TITLE,
    APP_ICON,
    APP_VERSION,
    APP_AUTHOR,
    APP_ORGANIZATION,
)
from services.auth import (
    initialiser_session_auth,
    afficher_ecran_connexion,
    deconnexion,
)
from views.nouvelle_demande import afficher_onglet_nouvelle_demande
from views.historique import afficher_onglet_historique
from views.acces_actifs import afficher_onglet_acces_actifs
from views.valideur import afficher_onglet_valideur
from views.administration import afficher_onglet_administration

# 1. Configuration de la page
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

# 2. Initialisation de la session & Contrôle d'accès OTP
initialiser_session_auth()

if not st.session_state.get("user_authenticated"):
    afficher_ecran_connexion()
    st.stop()

# 3. Barre latérale (Profil, Métadonnées & Déconnexion)
with st.sidebar:
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.markdown(f"👤 **Connecté :** `{st.session_state.get('user_email')}`")

    # Badges de rôles
    roles_str = []
    if st.session_state.get("is_admin"):
        roles_str.append("👑 Admin")
    if st.session_state.get("is_valideur"):
        roles_str.append("⚖️ Valideur")
    if not roles_str:
        roles_str.append("👤 Demandeur")

    st.caption("Rôle(s) : " + " | ".join(roles_str))
    st.divider()

    if st.button("Se déconnecter 🚪", type="secondary", use_container_width=True):
        deconnexion()

    # --- INFORMATIONS DE VERSION (Pied de barre latérale) ---
    st.divider()
    st.caption(f"📦 Version : `{APP_VERSION}`")
    st.caption(f"🏢 {APP_ORGANIZATION}")
    st.caption(f"👨‍💻 {APP_AUTHOR}")

# 4. Construction dynamique des Onglets basés sur les rôles
onglets_titres = ["➕ Nouvelle demande", "📋 Suivi & Historique", "✅ Mes accès actifs"]

if st.session_state.get("is_valideur") or st.session_state.get("is_admin"):
    onglets_titres.append("⚖️ Espace Valideur")

if st.session_state.get("is_admin"):
    onglets_titres.append("⚙️ Administration")

onglets = st.tabs(onglets_titres)

# 5. Routage vers les Vues correspondantes
with onglets[0]:
    afficher_onglet_nouvelle_demande()

with onglets[1]:
    afficher_onglet_historique()

with onglets[2]:
    afficher_onglet_acces_actifs()

idx_current = 3
if st.session_state.get("is_valideur") or st.session_state.get("is_admin"):
    with onglets[idx_current]:
        afficher_onglet_valideur()
    idx_current += 1

if st.session_state.get("is_admin"):
    with onglets[idx_current]:
        afficher_onglet_administration()
