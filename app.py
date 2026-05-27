import streamlit as st

# Configuration de la page
st.set_page_config(page_title="P&G Chatbot", layout="centered")

# Injection CSS majeure pour éradiquer la barre blanche et lier le fond au dashboard
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600&display=swap');
    
    /* Application de la police Inter et de la taille 12px partout */
    html, body, [data-testid="stAppViewContainer"], .stChatMessage, .stChatInput textarea {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px !important;
    }

    /* FORCE LE FOND EN TRANSPARENT : Élimine le bloc blanc visuel dans Looker Studio */
    html, body, #root, [data-testid="stAppViewContainer"], .main, [data-testid="stMain"] {
        background-color: transparent !important;
        background: transparent !important;
    }

    /* Maximisation de l'espace interne et suppression des décalages */
    .block-container { 
        padding-top: 0rem !important; 
        padding-bottom: 0rem !important; 
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Suppression stricte des marges et paddings système en bas */
    [data-testid="stAppViewContainer"] {
        padding-bottom: 0rem !important;
        bottom: 0px !important;
    }

    /* Masquer le bandeau supérieur complet (Header avec bouton Deploy) */
    [data-testid="stHeader"] {
        display: none !important;
        height: 0px !important;
    }
    
    /* Masquer la ligne de décoration colorée tout en haut de l'écran */
    [data-testid="stDecoration"] {
        display: none !important;
    }
    
    /* Masquer le menu d'options standard (bouton hamburger) */
    #MainMenu {
        visibility: hidden !important;
        display: none !important;
    }
    
    /* Masquer le footer classique de Streamlit */
    footer {
        visibility: hidden !important;
        display: none !important;
    }
    
    /* BLINDAGE : Suppression totale de la barre d'intégration (?embed=true) et de ses composants */
    [data-testid="stEmbedFooter"], 
    .stEmbedFooter, 
    [class*="stEmbedFooter"], 
    [class*="EmbedFooter"], 
    [class*="viewerBadge"], 
    .viewerBadge,
    a[href*="streamlit.io"],
    [id*="streamlit"] {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        padding: 0px !important;
        margin: 0px !important;
        opacity: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation de l'historique si vide
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider sur vos données Real Time aujourd'hui ?"}
    ]

# Affichage de la conversation en continu
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Zone de saisie
if user_input := st.chat_input("Posez votre question..."):
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Simulation de la réponse statique
    reply = f"Données reçues pour la question : '{user_input}'."
    with st.chat_message("assistant"):
        st.write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})