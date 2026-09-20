"""
Vue : Mes Accès Actifs
Affiche les autorisations en cours de validité pour l'utilisateur connecté.
"""

import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from services.db import supabase


def obtenir_date_nc() -> str:
    """Renvoie la date du jour au format ISO YYYY-MM-DD à Nouméa."""
    return datetime.datetime.now(ZoneInfo("Pacific/Noumea")).date().strftime("%Y-%m-%d")


def afficher_onglet_acces_actifs():
    """Rendu des autorisations d'accès actives."""
    st.subheader("✅ Vos autorisations en cours de validité")
    st.info(
        "💡 Seules les demandes validées dont la date de fin n'est pas dépassée s'affichent ici."
    )

    email_user = st.session_state.get("user_email", "").strip().lower()
    date_aujourdhui = obtenir_date_nc()

    try:
        # Recherche robuste : ilike pour l'e-mail (ignore majuscules/minuscules)
        req = (
            supabase.table("Demandes_acces")
            .select("*")
            .eq("statut", "Validé")
            .ilike("email_demandeur", email_user)
            .gte("date_sortie", date_aujourdhui)
            .order("date_entree", desc=False)
            .execute()
        )

        acces_actifs = req.data if req.data else []

        if not acces_actifs:
            st.warning("Vous n'avez actuellement aucun accès actif sur un site GNC.")
            return

        for a in acces_actifs:
            with st.expander(
                f"📍 Site : {a.get('site_id')} | Du {a.get('date_entree')} au {a.get('date_sortie')}",
                expanded=True,
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"🏢 **Organisme :** {a.get('organisme')}")
                    st.markdown(f"🚶‍♂️ / 🚗 **Mode d'accès :** {a.get('mode_acces')}")
                    st.markdown(f"📝 **Motif :** {a.get('motif')}")

                with c2:
                    st.markdown(
                        f"🕒 **Horaires :** de {str(a.get('heure_entree'))[:5]} à {str(a.get('heure_sortie'))[:5]}"
                    )
                    if a.get("mode_acces") == "Véhicule":
                        st.markdown(
                            f"🆔 **Plaque :** `{a.get('vehicule_immatriculation')}`"
                        )
                        st.markdown(f"🚘 **Véhicule :** {a.get('vehicule_type')}")
                        st.markdown(
                            f"🪪 **Conducteur :** {a.get('vehicule_conducteur')}"
                        )

    except Exception as e:
        st.error(f"❌ Erreur lors de la récupération des accès actifs : {e}")
