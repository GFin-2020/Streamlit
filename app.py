import streamlit as st

# Configuration de la page
st.set_page_config(page_title="P&G Chatbot", layout="centered")

# Injection CSS pour nettoyer l'interface de fond en comble
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600&display=swap');
    
    /* Application de la police Inter et de la taille 12px partout */
    html, body, [data-testid="stAppViewContainer"], .stChatMessage, .stChatInput textarea {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px !important;
    }

    /* Ajustement des marges internes pour optimiser l'espace dans l'iframe */
    .block-container { 
        padding-top: 1rem !important; 
        padding-bottom: 1rem !important; 
    }
    
    /* Masquer le bandeau supérieur complet (Header avec bouton Deploy) */
    [data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Masquer la ligne de décoration colorée tout en haut de l'écran */
    [data-testid="stDecoration"] {
        display: none !important;
    }
    
    /* Masquer le menu d'options standard (bouton hamburger / trois points) */
    #MainMenu {
        visibility: hidden !important;
        display: none !important;
    }
    
    /* Masquer le footer classique de Streamlit ('Made with Streamlit') */
    footer {
        visibility: hidden !important;
        display: none !important;
    }
    
    /* Masquer la barre d'intégration blanche (Built with Streamlit / Fullscreen) */
    div[data-testid="stEmbedFooter"] {
        display: none !important;
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