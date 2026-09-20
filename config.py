"""
Configuration globale du projet ADITUS (GNC-PASS)
Centralisation des secrets, constantes UI, métadonnées de version et paramètres réseau.
"""

import os
import streamlit as st

# --- Métadonnées de l'Application ---
APP_TITLE = "ADITUS - Portail GNC-PASS"
APP_ICON = "🏢"
APP_VERSION = "v1.1.0"
APP_AUTHOR = "Éric KUTER"
APP_ORGANIZATION = "Gouvernement de la Nouvelle-Calédonie"
APP_RELEASE_DATE = "2026"

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
