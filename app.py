import streamlit as st

st.set_page_config(page_title="P&G Chatbot", layout="centered")
st.title("🤖 Assistant P&G Next Gen")

# Initialisation de l'historique des messages si vide
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider sur vos données Real Time aujourd'hui ?"}
    ]

# Affichage de tous les messages de la session
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Zone de saisie de l'utilisateur
if user_input := st.chat_input("Posez votre question..."):
    # Affichage du message de l'utilisateur
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Simulation d'une réponse de l'assistant (à connecter plus tard à votre API/LLM)
    reply = f"Voici une simulation de réponse à votre question : '{user_input}'."
    
    with st.chat_message("assistant"):
        st.write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})