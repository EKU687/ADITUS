"""
Configuration globale du projet ADITUS (GNC-PASS)
Centralisation des secrets, constantes UI, et paramètres réseau.
"""

import os
import streamlit as st

# --- Paramètres de l'Application ---
APP_TITLE = "ADITUS - Portail GNC-PASS"
APP_ICON = "🛡️"
TIMEZONE_NC = "Pacific/Noumea"

# --- Rôles Utilisateurs ---
ROLE_DEMANDEUR = "Demandeur"
ROLE_VALIDEUR = "Valideur"
ROLE_ADMIN = "Administrateur"

# --- Timeouts & Réseau ---
HTTP_TIMEOUT_SECONDS = 30.0


# --- Récupération Sécurisée des Secrets ---
def get_secret(key_name: str, default: str = "") -> str:
    """Récupère une variable depuis st.secrets ou les variables d'environnement OS."""
    if key_name in st.secrets:
        return st.secrets[key_name]
    return os.environ.get(key_name, default)


SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = get_secret("SUPABASE_SERVICE_KEY", SUPABASE_KEY)
BREVO_API_KEY = get_secret("BREVO_API_KEY")
