"""
Service d'accès à la base de données Supabase pour ADITUS.
Gère la connexion sécurisée et les requêtes métier.
"""

import hashlib

import streamlit as st
from supabase import create_client, Client

from config import (
    SUPABASE_URL,
    SUPABASE_KEY,
    SUPABASE_SERVICE_KEY,
)


def _fingerprint(key: str) -> str:
    """Empreinte courte d'une clé (jamais affichée) pour invalider le cache si la clé change."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@st.cache_resource
def init_supabase_client(use_service_role: bool = False, key_fingerprint: str = "") -> Client:
    """
    Initialise et met en cache le client Supabase.
    key_fingerprint : si la clé change, le cache est invalidé automatiquement.
    """
    key = SUPABASE_SERVICE_KEY if use_service_role else SUPABASE_KEY

    # Initialisation standard recommandée par le SDK Supabase Python
    return create_client(SUPABASE_URL, key)


# Instances globales du client Supabase
supabase: Client = init_supabase_client(
    use_service_role=False, key_fingerprint=_fingerprint(SUPABASE_KEY)
)
supabase_admin: Client = init_supabase_client(
    use_service_role=True, key_fingerprint=_fingerprint(SUPABASE_SERVICE_KEY)
)

# Sécurité : si la clé service est absente ou identique à la clé anon,
# le client admin retombe sur le rôle anon et la RLS bloquera les écritures.
if not SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_KEY == SUPABASE_KEY:
    st.warning(
        "⚠️ SUPABASE_SERVICE_KEY absente ou identique à SUPABASE_KEY : "
        "le client 'supabase_admin' retombe sur la clé anon — les écritures seront bloquées par la RLS."
    )


def charger_demandes_par_statut(statut: str = None):
    """Récupère les demandes d'accès filtrées par statut si spécifié."""
    try:
        query = supabase_admin.table("Demandes_acces").select("*")
        if statut:
            query = query.eq("statut", statut)

        reponse = query.order("created_at", desc=True).execute()
        return reponse.data if reponse.data else []
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des demandes : {e}")
        return []
