"""
Service d'accès à la base de données Supabase pour ADITUS.
Gère la connexion sécurisée et les requêtes métier.
"""

import streamlit as st
from supabase import create_client, Client

from config import (
    SUPABASE_URL,
    SUPABASE_KEY,
    SUPABASE_SERVICE_KEY,
)


@st.cache_resource
def init_supabase_client(use_service_role: bool = False) -> Client:
    """
    Initialise et met en cache le client Supabase.
    """
    key = SUPABASE_SERVICE_KEY if use_service_role else SUPABASE_KEY

    # Initialisation standard recommandée par le SDK Supabase Python
    return create_client(SUPABASE_URL, key)


# Instances globales du client Supabase
supabase: Client = init_supabase_client(use_service_role=False)
supabase_admin: Client = init_supabase_client(use_service_role=True)


def charger_demandes_par_statut(statut: str = None):
    """Récupère les demandes d'accès filtrées par statut si spécifié."""
    try:
        query = supabase.table("Demandes_acces").select("*")
        if statut:
            query = query.eq("statut", statut)

        reponse = query.order("created_at", desc=True).execute()
        return reponse.data if reponse.data else []
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des demandes : {e}")
        return []
