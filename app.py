import streamlit as st
import re
import pandas as pd
import datetime
import httpx
from supabase import create_client, Client
from services.auth import (
    initialiser_session_auth,
    afficher_ecran_connexion,
    deconnexion,
)

# Import des fonctions d'envoi d'e-mail depuis le module dédié
from services.mailer import envoyer_email_notification, envoyer_email_decision


# ==========================================
# 0. INITIALISATION DE LA BASE DE DONNÉES
# ==========================================
@st.cache_resource
def init_connection() -> Client:
    """Initialise la connexion à Supabase avec un timeout réseau de 30s."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    client = create_client(url, key)
    client.postgrest.timeout = 30

    return client


# Création de l'instance supabase
supabase = init_connection()


# ==========================================
# 0_1. FONCTIONS GLOBALES DE L'APPLICATION
# ==========================================
@st.cache_data(ttl=3600)
def charger_sites_refero():
    """Charge la liste des codes sites depuis REFERO en supprimant les doublons."""
    try:
        reponse = supabase.table("Sites").select("code_site").execute()
        liste_brute = [
            ligne["code_site"] for ligne in reponse.data if ligne.get("code_site")
        ]
        liste_sites_uniques = list(set(liste_brute))
        liste_sites_uniques.sort()
        return ["Sélectionnez un site..."] + liste_sites_uniques
    except Exception as e:
        st.error(f"⚠️ Impossible de charger les sites depuis REFERO : {e}")
        return ["Sélectionnez un site..."]


def normaliser_immatriculation(immat_brute: str, est_nc: bool = True) -> str:
    """Transforme n'importe quelle saisie (123 456 nc, 123-456-NC) en format strict : 123456NC"""
    if not immat_brute:
        return ""

    immat_nettoyee = re.sub(r"[^A-Z0-9]", "", immat_brute.strip().upper())

    if est_nc:
        chiffres = re.sub(r"\D", "", immat_nettoyee)
        if chiffres:
            return f"{chiffres}NC"

    return immat_nettoyee


def verifier_roles_utilisateur(email_utilisateur):
    """Vérifie si l'e-mail appartient à un valideur ou un administrateur."""
    LISTE_ADMINS = ["admin.acces@gouv.nc", "eric.kuter@gouv.nc"]

    est_admin = email_utilisateur in LISTE_ADMINS
    est_valideur = False

    try:
        req = (
            supabase.table("Valideurs_sites")
            .select("valideur_email")
            .eq("valideur_email", email_utilisateur)
            .execute()
        )
        if len(req.data) > 0:
            est_valideur = True
    except Exception as e:
        st.warning(f"⚠️ Impossible de vérifier le rôle valideur : {e}")

    return est_admin, est_valideur


# ==========================================
# 1. CONFIGURATION DE L'INTERFACE & AUTHENTIFICATION
# ==========================================
st.set_page_config(page_title="Demandes d'accès - GNC", page_icon="🏢", layout="wide")

# 1. Initialiser les variables de session
initialiser_session_auth()

# 2. Si non authentifié, afficher l'écran de connexion et stopper l'exécution du reste
if not st.session_state["user_authenticated"]:
    afficher_ecran_connexion()
    st.stop()

# 3. Barre latérale de déconnexion
with st.sidebar:
    st.markdown("👤 **Agent connecté :**")
    st.caption(f"`{st.session_state['user_email']}`")
    st.divider()
    if st.button("Se déconnecter 🚪", type="secondary", use_container_width=True):
        deconnexion()

# ==========================================
# 3. NAVIGATION DYNAMIQUE SELON LES RÔLES
# ==========================================
titres_onglets = ["➕ Nouvelle demande", "📋 Suivi & Historique", "✅ Mes accès actifs"]

if st.session_state.get("is_valideur") or st.session_state.get("is_admin"):
    titres_onglets.append("👑 Espace Valideur")

if st.session_state.get("is_admin"):
    titres_onglets.append("⚙️ Administration")

onglets = st.tabs(titres_onglets)

onglet_nouvelle = onglets[0]
onglet_historique = onglets[1]
onglet_actifs = onglets[2]

idx = 3
if st.session_state.get("is_valideur") or st.session_state.get("is_admin"):
    onglet_valideur = onglets[idx]
    idx += 1
else:
    onglet_valideur = None

if st.session_state.get("is_admin"):
    onglet_admin = onglets[idx]
else:
    onglet_admin = None

# --- ONGLET 1 : Formulaire de demande ---
with onglet_nouvelle:
    st.subheader("Effectuer une nouvelle demande d'accès")

    sites_disponibles = charger_sites_refero()
    site_choisi = st.selectbox("Site GNC concerné", sites_disponibles)

    st.divider()

    st.markdown("**Comment s'effectuera l'accès ?**")
    mode_acces = st.radio(
        "Véhicule ou piéton ?",
        ["Véhicule", "Piéton"],
        horizontal=True,
        label_visibility="collapsed",
    )

    with st.form("form_demande_acces", clear_on_submit=True):

        if mode_acces == "Véhicule":
            st.markdown("### 🚗 Informations Véhicule")
            conducteur = st.text_input("Prénom et Nom du conducteur *")

            col_immat1, col_immat2 = st.columns([1, 3])
            with col_immat1:
                immat_nc = st.toggle("Immat. NC ?", value=True)
            with col_immat2:
                immatriculation = st.text_input("Immatriculation *")

            type_vehicule = st.text_input(
                "Type de véhicule (marque / modèle / couleur) *"
            )
            st.divider()
        else:
            conducteur = None
            immat_nc = None
            immatriculation = None
            type_vehicule = None

        st.markdown("### 👤 Détails de la demande")

        col_PMR, col_personnes = st.columns(2)
        with col_PMR:
            pmr_choix = st.radio(
                "Personne à mobilité réduite ?", ["Oui", "Non"], horizontal=True
            )
            pmr_booleen = True if pmr_choix == "Oui" else False

        with col_personnes:
            nombre_personnes = st.number_input(
                "Nombre de personnes *", min_value=1, value=1, step=1
            )

        col_orga, col_email = st.columns(2)
        with col_orga:
            organisme = st.text_input("Raison sociale ou organisme *")
        with col_email:
            email_demandeur = st.text_input(
                "Email du demandeur *", value=st.session_state["user_email"]
            )

        motif = st.text_area("Motif de la demande *")

        st.markdown("### 📅 Période d'accès")
        col_date_entree, col_heure_entree = st.columns(2)
        with col_date_entree:
            date_entree = st.date_input("Date d'entrée", value=datetime.date.today())
        with col_heure_entree:
            heure_entree = st.time_input("Heure d'entrée", value=datetime.time(8, 0))

        col_date_sortie, col_heure_sortie = st.columns(2)
        with col_date_sortie:
            date_sortie = st.date_input("Date de sortie", value=datetime.date.today())
        with col_heure_sortie:
            heure_sortie = st.time_input("Heure de sortie", value=datetime.time(17, 0))

        st.info("Les champs marqués d'un astérisque (*) sont requis.")

        submit = st.form_submit_button("Soumettre la demande", type="primary")

        if submit:
            if site_choisi == "Sélectionnez un site...":
                st.error("⚠️ Veuillez sélectionner un site.")
            elif not organisme or not email_demandeur or not motif:
                st.error(
                    "⚠️ Veuillez remplir tous les champs obligatoires (Organisme, Email, Motif)."
                )
            elif mode_acces == "Véhicule" and (
                not conducteur or not immatriculation or not type_vehicule
            ):
                st.error(
                    "⚠️ Veuillez remplir toutes les informations liées au véhicule."
                )
            elif date_sortie < date_entree:
                st.error(
                    "⚠️ La date de sortie ne peut pas être antérieure à la date d'entrée."
                )
            else:
                email_du_valideur = None
                try:
                    req_valideur = (
                        supabase.table("Valideurs_sites")
                        .select("valideur_email")
                        .eq("site_nom", site_choisi.strip())
                        .execute()
                    )
                    if req_valideur.data and len(req_valideur.data) > 0:
                        email_du_valideur = req_valideur.data[0]["valideur_email"]
                    else:
                        email_du_valideur = "admin.acces@gouv.nc"
                except Exception:
                    email_du_valideur = "admin.acces@gouv.nc"

                immat_strict = (
                    normaliser_immatriculation(immatriculation, immat_nc)
                    if mode_acces == "Véhicule"
                    else None
                )

                donnees_a_inserer = {
                    "site_id": site_choisi,
                    "organisme": organisme,
                    "email_demandeur": email_demandeur,
                    "motif": motif,
                    "nombre_personnes": nombre_personnes,
                    "pmr": pmr_booleen,
                    "mode_acces": mode_acces,
                    "vehicule_conducteur": conducteur,
                    "vehicule_immat_nc": immat_nc,
                    "vehicule_immatriculation": immat_strict,
                    "vehicule_type": type_vehicule,
                    "date_entree": date_entree.strftime("%Y-%m-%d"),
                    "heure_entree": heure_entree.strftime("%H:%M:%S"),
                    "date_sortie": date_sortie.strftime("%Y-%m-%d"),
                    "heure_sortie": heure_sortie.strftime("%H:%M:%S"),
                    "statut": "En attente",
                    "valideur_assigne": email_du_valideur,
                }

                try:
                    reponse = (
                        supabase.table("Demandes_acces")
                        .insert(donnees_a_inserer)
                        .execute()
                    )

                    if len(reponse.data) > 0:
                        # Appel propre à la fonction importée depuis mailer.py
                        envoyer_email_notification(
                            destinataire_email=email_du_valideur,
                            site_nom=site_choisi,
                            demandeur_email=email_demandeur,
                            motif_demande=motif,
                        )

                        st.success(
                            f"✅ Votre demande pour **{site_choisi}** a été soumise avec succès et transmise à **{email_du_valideur}** pour validation !"
                        )
                    else:
                        st.error("Une erreur s'est produite lors de l'enregistrement.")

                except Exception as e:
                    st.error(f"❌ Erreur technique lors de l'insertion : {e}")

# --- ONGLET 2 : Historique & Suivi des demandes ---
with onglet_historique:
    st.subheader("📋 Suivi de vos demandes d'accès")
    st.info("Retrouvez ici l'état d'avancement de toutes vos demandes soumises.")

    try:
        email_session = st.session_state.get("user_email")

        if st.session_state.get("is_admin"):
            reponse_historique = (
                supabase.table("Demandes_acces")
                .select("*")
                .order("id", desc=True)
                .execute()
            )
        else:
            reponse_historique = (
                supabase.table("Demandes_acces")
                .select("*")
                .eq("email_demandeur", email_session)
                .order("id", desc=True)
                .execute()
            )

        donnees_demandes = reponse_historique.data

        if not donnees_demandes:
            st.warning(
                "Vous n'avez encore soumis aucune demande d'accès avec cette adresse e-mail."
            )
        else:
            df = pd.DataFrame(donnees_demandes)

            colonnes_a_afficher = {
                "site_id": "Site concerné",
                "date_entree": "Date d'entrée",
                "date_sortie": "Date de sortie",
                "mode_acces": "Mode",
                "statut": "Statut de la demande",
                "valideur_assigne": "Valideur en charge",
            }

            cols_existantes = [
                col for col in colonnes_a_afficher.keys() if col in df.columns
            ]
            df_affiche = df[cols_existantes].rename(columns=colonnes_a_afficher)

            if "Date d'entrée" in df_affiche.columns:
                df_affiche["Date d'entrée"] = pd.to_datetime(
                    df_affiche["Date d'entrée"]
                ).dt.strftime("%d/%m/%Y")
            if "Date de sortie" in df_affiche.columns:
                df_affiche["Date de sortie"] = pd.to_datetime(
                    df_affiche["Date de sortie"]
                ).dt.strftime("%d/%m/%Y")

            st.dataframe(df_affiche, use_container_width=True, hide_index=True)

            st.divider()
            col_stat, col_nb = st.columns([2, 1])
            with col_stat:
                nb_en_attente = len(df[df["statut"] == "En attente"])
                nb_valide = len(df[df["statut"] == "Validé"])
                nb_refuse = len(df[df["statut"] == "Refusé"])

                st.caption(
                    f"📊 **Statistiques :** ⏳ {nb_en_attente} En attente | ✅ {nb_valide} Validée(s) | ❌ {nb_refuse} Refusée(s)"
                )

    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de l'historique : {e}")

# --- ONGLET 3 : Les accès en cours ---
with onglet_actifs:
    st.subheader("Vos autorisations en cours de validité")
    st.info(
        "💡 Seules les demandes validées dont la date de fin n'est pas dépassée s'affichent ici."
    )

    try:
        email_session = st.session_state.get("user_email")
        aujourdhui = datetime.date.today()

        if st.session_state.get("is_admin"):
            reponse_actifs = (
                supabase.table("Demandes_acces")
                .select("*")
                .eq("statut", "Validé")
                .order("id", desc=True)
                .execute()
            )
        else:
            reponse_actifs = (
                supabase.table("Demandes_acces")
                .select("*")
                .eq("statut", "Validé")
                .eq("email_demandeur", email_session)
                .order("id", desc=True)
                .execute()
            )

        donnees_brutes = reponse_actifs.data or []
        donnees_actives = []

        for acces in donnees_brutes:
            date_sortie_str = acces.get("date_sortie")
            if date_sortie_str:
                try:
                    date_sortie_obj = datetime.datetime.strptime(
                        date_sortie_str[:10], "%Y-%m-%d"
                    ).date()

                    if date_sortie_obj >= aujourdhui:
                        donnees_actives.append(acces)
                except ValueError:
                    continue

        if not donnees_actives:
            st.warning("Vous n'avez actuellement aucun accès actif sur un site GNC.")
        else:
            cols = st.columns(3)
            for i, acces in enumerate(donnees_actives):
                with cols[i % 3]:
                    d_ent = acces["date_entree"]
                    d_ent_fr = (
                        f"{d_ent[8:10]}/{d_ent[5:7]}/{d_ent[0:4]}"
                        if d_ent and len(d_ent) >= 10
                        else "N/C"
                    )

                    d_sor = acces["date_sortie"]
                    d_sor_fr = (
                        f"{d_sor[8:10]}/{d_sor[5:7]}/{d_sor[0:4]}"
                        if d_sor and len(d_sor) >= 10
                        else "N/C"
                    )

                    st.success(f"""
                    **Site : {acces['site_id']}**  
                    📅 *Du {d_ent_fr} au {d_sor_fr}*  
                    👤 Valideur : {acces.get('valideur_assigne', 'Non assigné')}  
                    🚗 Accès : {acces['mode_acces']}
                    """)
    except Exception as e:
        st.error(f"Erreur lors de la lecture des accès actifs : {e}")

# --- ONGLET 4 : Espace Valideur (Seulement si autorisé) ---
if onglet_valideur is not None:
    with onglet_valideur:
        st.subheader("👑 Espace de Validation des Accès")
        st.info("💡 Les demandes en attente de traitement apparaissent ci-dessous.")

        try:
            if st.session_state.get("is_admin"):
                reponse_attente = (
                    supabase.table("Demandes_acces")
                    .select("*")
                    .eq("statut", "En attente")
                    .order("id", desc=True)
                    .execute()
                )
            else:
                email_connecte = st.session_state.get("user_email")
                req_sites = (
                    supabase.table("Valideurs_sites")
                    .select("site_nom")
                    .eq("valideur_email", email_connecte)
                    .execute()
                )
                sites_assignes = (
                    [ligne["site_nom"] for ligne in req_sites.data]
                    if req_sites.data
                    else []
                )

                if sites_assignes:
                    reponse_attente = (
                        supabase.table("Demandes_acces")
                        .select("*")
                        .eq("statut", "En attente")
                        .in_("site_id", sites_assignes)
                        .order("id", desc=True)
                        .execute()
                    )
                else:
                    reponse_attente = type("obj", (object,), {"data": []})()

            demandes = reponse_attente.data

            if not demandes:
                st.success(
                    "🎉 Aucune demande en attente de validation pour vos sites pour le moment !"
                )
            else:
                for demande in demandes:
                    d_ent = demande["date_entree"]
                    d_ent_fr = (
                        f"{d_ent[8:10]}/{d_ent[5:7]}/{d_ent[0:4]}"
                        if d_ent and len(d_ent) >= 10
                        else "N/C"
                    )

                    d_sor = demande["date_sortie"]
                    d_sor_fr = (
                        f"{d_sor[8:10]}/{d_sor[5:7]}/{d_sor[0:4]}"
                        if d_sor and len(d_sor) >= 10
                        else "N/C"
                    )

                    titre_carte = f"📍 Site : {demande['site_id']} | Demandeur : {demande['email_demandeur']} (Du {d_ent_fr} au {d_sor_fr})"

                    with st.expander(titre_carte, expanded=True):
                        col_info1, col_info2 = st.columns(2)

                        with col_info1:
                            st.markdown(f"**Organisme :** {demande['organisme']}")
                            st.markdown(f"**Motif de la demande :** {demande['motif']}")
                            st.markdown(
                                f"**Personnes :** {demande['nombre_personnes']} (PMR : {'Oui' if demande['pmr'] else 'Non'})"
                            )

                        with col_info2:
                            st.markdown(f"**Mode d'accès :** {demande['mode_acces']}")
                            if demande["mode_acces"] == "Véhicule":
                                st.markdown(
                                    f"🚗 **Immatriculation :** {demande.get('vehicule_immatriculation', 'N/C')} ({demande.get('vehicule_type', 'N/C')})"
                                )
                                st.markdown(
                                    f"👤 **Conducteur :** {demande.get('vehicule_conducteur', 'N/C')}"
                                )

                        st.divider()

                        champ_refus = st.text_input(
                            "Motif du refus (obligatoire en cas de rejet)",
                            key=f"motif_refus_{demande['id']}",
                            placeholder="Ex : Site fermé pour travaux à cette date...",
                        )

                        col_btn1, col_btn2 = st.columns(2)

                        with col_btn1:
                            if st.button(
                                "✅ Approuver la demande",
                                key=f"valider_{demande['id']}",
                                type="primary",
                            ):
                                supabase.table("Demandes_acces").update(
                                    {"statut": "Validé"}
                                ).eq("id", demande["id"]).execute()

                                # Appel propre à la fonction importée depuis mailer.py
                                envoyer_email_decision(
                                    destinataire_email=demande["email_demandeur"],
                                    site_nom=demande["site_id"],
                                    decision="Validé",
                                    date_entree=demande["date_entree"],
                                    heure_entree=demande["heure_entree"],
                                    date_sortie=demande["date_sortie"],
                                    heure_sortie=demande["heure_sortie"],
                                )

                                st.success(
                                    "Accès validé et notification envoyée au demandeur !"
                                )
                                st.rerun()

                        with col_btn2:
                            if st.button(
                                "❌ Refuser la demande", key=f"refuser_{demande['id']}"
                            ):
                                if not champ_refus.strip():
                                    st.error(
                                        "⚠️ Veuillez indiquer un motif de refus avant de rejeter la demande."
                                    )
                                else:
                                    supabase.table("Demandes_acces").update(
                                        {"statut": "Refusé"}
                                    ).eq("id", demande["id"]).execute()

                                    # Appel propre à la fonction importée depuis mailer.py
                                    envoyer_email_decision(
                                        destinataire_email=demande["email_demandeur"],
                                        site_nom=demande["site_id"],
                                        decision="Refusé",
                                        motif_refus=champ_refus,
                                    )

                                    st.error(
                                        "Accès refusé et notification envoyée au demandeur."
                                    )
                                    st.rerun()

        except Exception as e:
            st.error(f"❌ Erreur lors du chargement des demandes : {e}")

# --- ONGLET 5 : Administration des Valideurs (Seulement si Admin) ---
if onglet_admin is not None:
    with onglet_admin:
        st.subheader("⚙️ Gestion des Valideurs par Site")
        st.info(
            "Espace réservé aux administrateurs pour configurer qui valide l'accès à quel bâtiment."
        )

        col_form, col_liste = st.columns([1, 1.5])

        with col_form:
            st.markdown("### ➕ Assigner un valideur")

            sites_disponibles_admin = charger_sites_refero()

            with st.form("form_ajout_valideur", clear_on_submit=True):
                site_a_configurer = st.selectbox(
                    "Sélectionnez le site", sites_disponibles_admin
                )
                nouvel_email_valideur = st.text_input(
                    "Email du responsable (Valideur)", placeholder="prenom.nom@gouv.nc"
                )

                submit_valideur = st.form_submit_button(
                    "Enregistrer le valideur", type="primary"
                )

                if submit_valideur:
                    if (
                        site_a_configurer == "Sélectionnez un site..."
                        or not nouvel_email_valideur
                    ):
                        st.error("Veuillez sélectionner un site et saisir un email.")
                    else:
                        try:
                            verification = (
                                supabase.table("Valideurs_sites")
                                .select("*")
                                .eq("site_nom", site_a_configurer.strip())
                                .execute()
                            )

                            if len(verification.data) > 0:
                                id_existant = verification.data[0]["id"]
                                supabase.table("Valideurs_sites").update(
                                    {"valideur_email": nouvel_email_valideur.strip()}
                                ).eq("id", id_existant).execute()
                                st.success(
                                    f"🔄 Mise à jour réussie pour {site_a_configurer} !"
                                )
                            else:
                                donnees = {
                                    "site_nom": site_a_configurer.strip(),
                                    "valideur_email": nouvel_email_valideur.strip(),
                                }
                                supabase.table("Valideurs_sites").insert(
                                    donnees
                                ).execute()
                                st.success(
                                    f"✅ Enregistrement réussi pour {site_a_configurer} !"
                                )

                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur d'enregistrement : {e}")

        with col_liste:
            st.markdown("### 📋 Liste des assignations actuelles")
            try:
                reponse_valideurs = (
                    supabase.table("Valideurs_sites").select("*").execute()
                )

                if reponse_valideurs.data:
                    df_valideurs = pd.DataFrame(reponse_valideurs.data)
                    df_valideurs = df_valideurs[["site_nom", "valideur_email"]]
                    df_valideurs.columns = ["Site", "Email du Valideur"]

                    st.dataframe(
                        df_valideurs, use_container_width=True, hide_index=True
                    )
                else:
                    st.warning("Aucun valideur n'a encore été configuré dans la base.")

            except Exception as e:
                st.error(f"Erreur lors de la lecture des valideurs : {e}")
