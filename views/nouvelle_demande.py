"""
Vue : Nouvelle Demande d'Accès
Permet aux utilisateurs de formuler une demande d'accès piéton ou véhicule.
"""

import datetime
from zoneinfo import ZoneInfo
import streamlit as st

from services.db import supabase
from services.mailer import envoyer_email_notification


def obtenir_date_nc() -> datetime.date:
    """Renvoie la date actuelle à Nouméa."""
    return datetime.datetime.now(ZoneInfo("Pacific/Noumea")).date()


def _formater_date_fr(valeur) -> str:
    """Formatage ISO pour la base de données YYYY-MM-DD."""
    if isinstance(valeur, (datetime.date, datetime.datetime)):
        return valeur.strftime("%Y-%m-%d")
    return str(valeur)


def charger_liste_sites() -> list:
    """Récupère la liste dynamique des sites actifs depuis la table 'Sites'."""
    try:
        req = (
            supabase.table("Sites")
            .select("nom_site")
            .eq("actif", True)
            .order("nom_site", desc=False)
            .execute()
        )

        if req.data:
            sites = [row["nom_site"] for row in req.data if row.get("nom_site")]
            if sites:
                return sites
    except Exception as e:
        st.warning(f"⚠️ Erreur lors de la lecture de la table 'Sites' : {e}")

    return ["DINUM", "DOUMER", "HABITAT", "OUEMO", "AUTRE"]


def afficher_onglet_nouvelle_demande():
    """Rendu de l'onglet de création d'une nouvelle demande d'accès."""
    st.subheader("➕ Nouvelle demande d'autorisation d'accès")
    st.caption(
        "Remplissez le formulaire ci-dessous pour soumettre votre demande aux valideurs."
    )

    email_user = st.session_state.get("user_email", "").strip().lower()
    liste_sites = charger_liste_sites()

    # 1. Choix du mode d'accès hors formulaire pour la réactivité dynamique
    mode_acces = st.radio(
        "🚶‍♂️ / 🚗 Mode d'accès :",
        ["Piéton", "Véhicule"],
        horizontal=True,
        key="radio_mode_acces",
    )

    with st.form("form_nouvelle_demande", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            site_concerne = st.selectbox("📍 Site GNC concerné :", liste_sites, index=0)
            organisme = st.text_input(
                "🏢 Organisme / Direction / Société :",
                placeholder="Ex : DINUM / OPT / Prestataire",
            )
            motif_demande = st.text_area(
                "📝 Motif de la demande :",
                placeholder="Ex : Intervention technique sur serveur, réunion...",
            )

        with col2:
            nombre_personnes = st.number_input(
                "👥 Nombre de personnes concernées :",
                min_value=1,
                max_value=50,
                value=1,
            )

            c_date1, c_date2 = st.columns(2)
            with c_date1:
                date_entree = st.date_input(
                    "📅 Date de début :",
                    min_value=obtenir_date_nc(),
                    format="DD/MM/YYYY",
                )
            with c_date2:
                date_sortie = st.date_input(
                    "📅 Date de fin :", min_value=date_entree, format="DD/MM/YYYY"
                )

            c_h1, c_h2 = st.columns(2)
            with c_h1:
                heure_entree = st.time_input(
                    "🕒 Heure d'arrivée :", value=datetime.time(8, 0)
                )
            with c_h2:
                heure_sortie = st.time_input(
                    "🕒 Heure de départ :", value=datetime.time(17, 0)
                )

        # 2. Section véhicule conditionnelle
        vehicule_immat = ""
        vehicule_type = ""
        vehicule_conducteur = ""

        if mode_acces == "Véhicule":
            st.divider()
            st.markdown("##### 🚗 Informations du véhicule & Conducteur")

            col_v1, col_v2, col_v3 = st.columns(3)
            with col_v1:
                vehicule_immat = (
                    st.text_input("🆔 Immatriculation :", placeholder="Ex : 456913NC")
                    .strip()
                    .upper()
                )
            with col_v2:
                vehicule_type = st.text_input(
                    "🚘 Marque / Modèle / Couleur :",
                    placeholder="Ex : Peugeot 208 Blanche",
                )
            with col_v3:
                vehicule_conducteur = st.text_input(
                    "🪪 Nom du conducteur :", placeholder="Nom et Prénom du conducteur"
                )

        st.divider()
        soumis = st.form_submit_button(
            "Soumettre la demande 🚀", type="primary", use_container_width=True
        )

        if soumis:
            if not organisme or not motif_demande:
                st.warning(
                    "⚠️ Veuillez remplir tous les champs obligatoires (Organisme et Motif)."
                )
            elif mode_acces == "Véhicule" and not vehicule_immat:
                st.warning(
                    "⚠️ L'immatriculation est obligatoire pour un accès véhicule."
                )
            else:
                donnees_demande = {
                    "email_demandeur": email_user,
                    "site_id": site_concerne,
                    "organisme": organisme,
                    "motif": motif_demande or "Motif non précisé",
                    "mode_acces": mode_acces,
                    "nombre_personnes": nombre_personnes,
                    "date_entree": _formater_date_fr(date_entree),
                    "date_sortie": _formater_date_fr(date_sortie),
                    "heure_entree": heure_entree.strftime("%H:%M:%S"),
                    "heure_sortie": heure_sortie.strftime("%H:%M:%S"),
                    "vehicule_immatriculation": (
                        vehicule_immat if mode_acces == "Véhicule" else ""
                    ),
                    "vehicule_type": vehicule_type if mode_acces == "Véhicule" else "",
                    "vehicule_conducteur": (
                        vehicule_conducteur if mode_acces == "Véhicule" else ""
                    ),
                    "statut": "En attente",
                    "created_at": datetime.datetime.now(
                        ZoneInfo("Pacific/Noumea")
                    ).isoformat(),
                }

                try:
                    res = (
                        supabase.table("Demandes_acces")
                        .insert(donnees_demande)
                        .execute()
                    )
                    if res.data:
                        st.success(
                            "✅ Votre demande d'accès a été enregistrée avec succès !"
                        )
                        try:
                            # Appel simplifié et propre passant le dictionnaire complet
                            envoyer_email_notification(donnees_demande)
                        except Exception as e_mail:
                            st.info(
                                f"ℹ️ Demande créée, mais notification e-mail non transmise : {e_mail}"
                            )
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'enregistrement de la demande : {e}")
