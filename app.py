import streamlit as st

# Configuration de la page
st.set_page_config(page_title="P&G Chatbot", layout="centered")

# Injection CSS pour la police, les tailles et le nettoyage de l'interface
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    /* Application de la police Inter et de la taille 12px partout */
    html, body, [data-testid="stAppViewContainer"], .stChatMessage, .stChatInput textarea {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px !important;
    }

    /* Suppression des espaces et marges inutiles */
    .block-container { padding-top: 0rem; padding-bottom: 0rem; }
    
    /* Masquer les menus et footers standards de Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
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