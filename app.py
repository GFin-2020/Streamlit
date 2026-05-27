import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import json
import re
from urllib.parse import quote

# ─── Configuration page ───────────────────────────────────────────────────────
st.set_page_config(page_title="P&G Chatbot", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600&display=swap');

    html, body, [data-testid="stAppViewContainer"], .stChatMessage, .stChatInput textarea {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px !important;
    }

    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    [data-testid="stAppViewContainer"] {
        padding-bottom: 0rem !important;
    }

    [data-testid="stHeader"], [data-testid="stToolbar"], header {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
    }

    [data-testid="stDecoration"] {
        display: none !important;
    }

    #MainMenu {
        visibility: hidden !important;
        display: none !important;
    }

    footer {
        visibility: hidden !important;
        display: none !important;
    }

    [data-testid="stEmbedFooter"],
    .stEmbedFooter,
    [class*="stEmbedFooter"],
    [class*="EmbedFooter"] {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        padding: 0px !important;
    }

    [data-testid="bundle-hosted-badge"],
    .viewerBadge,
    [class*="viewerBadge"],
    [class*="styled-widgets"],
    a[href*="streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        width: 0px !important;
        padding: 0px !important;
        margin: 0px !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Clé API Gemini ───────────────────────────────────────────────────────────
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = os.environ.get("GEMINI_API_KEY", "")

if not api_key:
    st.error(
        "Clé API Gemini manquante. "
        "En local : ajoutez GEMINI_API_KEY dans .streamlit/secrets.toml. "
        "Sur Cloud Run : ajoutez la variable d'environnement GEMINI_API_KEY."
    )
    st.stop()

genai.configure(api_key=api_key)
gemini = genai.GenerativeModel("gemini-3.1-flash-lite")

# ─── Chargement des données Google Sheets ─────────────────────────────────────
SHEET_ID = "1ZKjInMosxAMvjaO7QDCmCjdgNxiPz1xFKxZwxW48FIM"

@st.cache_data
def load_sheets():
    base = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="
    df_hist = pd.read_csv(base + "Historique")
    df_rt = pd.read_csv(base + quote("Real Time"))
    return df_hist, df_rt

try:
    df_hist, df_rt = load_sheets()
except Exception as e:
    st.error(f"Impossible de charger les données Google Sheets : {e}")
    st.stop()

# ─── Initialisation de la session ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "P&G Assistant, propulsé par Gemini. Comment puis-je vous aider ?"}
    ]

# active_sheet mémorise la feuille en cours dans la conversation (None = pas encore déterminé)
if "active_sheet" not in st.session_state:
    st.session_state.active_sheet = None

# ─── Helpers ──────────────────────────────────────────────────────────────────
def build_history_str(exclude_last=True, max_messages=8):
    """Formate les derniers échanges pour les inclure dans les prompts Gemini."""
    msgs = st.session_state.messages
    if exclude_last:
        msgs = msgs[:-1]
    recent = msgs[-max_messages:] if len(msgs) > max_messages else msgs
    lines = []
    for m in recent:
        role = "Utilisateur" if m["role"] == "user" else "Assistant"
        content = m["content"][:600]  # tronquer les messages trop longs
        lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def build_sheet_schema(name, df):
    """Génère la description complète d'un dataframe pour le prompt."""
    cols = " | ".join(f"{c} ({df[c].dtype})" for c in df.columns)

    # Toutes les valeurs uniques des dimensions pour éviter les hallucinations
    dims = ["Pays", "Marque", "Véhicule", "Source_Traffic"]
    dim_lines = "\n".join(
        f"  {c} : {', '.join(str(v) for v in sorted(df[c].dropna().unique()))}"
        for c in dims if c in df.columns
    )

    # Plage temporelle réelle
    date_col = next((c for c in ["Date", "Timestamp"] if c in df.columns), None)
    date_info = (
        f"  {date_col} : {df[date_col].min()} → {df[date_col].max()}"
        if date_col else "  (aucune colonne temporelle)"
    )

    # Statistiques des métriques
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    metric_lines = "\n".join(
        f"  {c} : total={df[c].sum():,.0f}, moy={df[c].mean():.1f}, min={df[c].min():.0f}, max={df[c].max():.0f}"
        for c in numeric_cols
    )

    return (
        f"Feuille '{name}' ({len(df):,} lignes)\n"
        f"Colonnes : {cols}\n"
        f"Plage temporelle :\n{date_info}\n"
        f"Dimensions (valeurs exactes disponibles) :\n{dim_lines}\n"
        f"Métriques :\n{metric_lines}"
    )

# ─── Passe 1 : routage + génération du code pandas ───────────────────────────
def make_routing_prompt(question):
    hist_schema = build_sheet_schema("Historique", df_hist)
    rt_schema = build_sheet_schema("Real Time", df_rt)

    history_str = build_history_str()
    history_section = f"Historique de la conversation :\n{history_str}\n\n" if history_str else ""

    if st.session_state.active_sheet:
        label = "Historique" if st.session_state.active_sheet == "hist" else "Real Time"
        context_note = (
            f"[Contexte actif : la conversation porte sur '{label}'. "
            f"Continue sur cette feuille sauf si l'utilisateur demande explicitement de changer.]\n\n"
        )
    else:
        context_note = ""

    return f"""Tu es un assistant data analytics dans une conversation continue. Tu n'as pas à te présenter si c'est déjà fait.

{context_note}{history_section}Données disponibles :

{hist_schema}

{rt_schema}

Nouvelle question : "{question}"

Retourne UNIQUEMENT un objet JSON valide, sans markdown, sans texte autour.

Règle de clarification — applique-la dans cet ordre strict :
1. Si un contexte actif est établi (indiqué entre crochets ci-dessus) : utilise cette feuille sans redemander, SAUF si l'utilisateur mentionne explicitement l'autre (ex: "maintenant en historique", "passe sur le real time").
2. Si AUCUN contexte actif n'est établi : tu DOIS retourner {{"action":"clarify"}} à moins que la question contienne un terme sans ambiguïté comme "historique", "journalier", "real time", "temps réel", "real-time". En l'absence de ces termes, retourne TOUJOURS la clarification — ne suppose jamais, ne devine jamais.

Format si clarification nécessaire :
{{"action":"clarify","message":"ta question courte en français"}}

Format si la feuille est déterminée :
{{"action":"query","sheet":"hist" ou "rt","code":"code pandas valide"}}

Règles strictes pour le code pandas :
- Variables disponibles : df (le dataframe complet) et pd
- Résultat TOUJOURS dans une variable nommée result
- Utilise UNIQUEMENT les valeurs de dimensions listées dans le schéma ci-dessus, jamais de valeurs inventées
- Pour les filtres temporels : utilise pd.to_datetime() et les dates réelles du schéma
- Préfère les agrégations aux lignes brutes (.groupby, .agg, .sum, .mean, .count, .value_counts)
- Ne modifie pas df en place ; crée des copies si besoin : sub = df[condition].copy()
- Exemples corrects :
  result = df.groupby('Pays')[['Impressions','Clics']].sum().sort_values('Impressions', ascending=False).reset_index()
  result = df[df['Marque'] == 'NomExact'].groupby('Source_Traffic')['Ventes'].sum().reset_index()
  sub = df.copy(); sub['Mois'] = pd.to_datetime(sub['Date']).dt.to_period('M'); result = sub.groupby('Mois')['Impressions'].sum().reset_index()"""


def route_and_query(question):
    response = gemini.generate_content(make_routing_prompt(question))
    text = response.text.strip()

    # Extraire le JSON même s'il est enrobé dans du markdown
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        text = m.group(1).strip()

    # Fallback : trouver le premier objet JSON dans le texte
    m2 = re.search(r"\{[\s\S]*\}", text)
    if m2:
        text = m2.group(0)

    return json.loads(text)

# ─── Exécution du code pandas ─────────────────────────────────────────────────
def run_pandas_code(code, sheet):
    df = df_hist if sheet == "hist" else df_rt
    ns = {"pd": pd, "df": df, "result": None}
    exec(code, ns)
    return ns["result"]


def format_result(result):
    if isinstance(result, pd.DataFrame):
        n = len(result)
        s = result.head(50).to_string(index=False)
        return s + (f"\n... ({n:,} lignes au total, 50 affichées)" if n > 50 else "")
    if isinstance(result, pd.Series):
        n = len(result)
        s = result.head(50).to_string()
        return s + (f"\n... ({n:,} valeurs, 50 affichées)" if n > 50 else "")
    return str(result)

# ─── Passe 2 : réponse en langage naturel ─────────────────────────────────────
def generate_answer(question, result_str, sheet):
    label = "historiques (données journalières)" if sheet == "hist" else "real-time (données horodatées)"
    history_str = build_history_str()
    history_section = f"Historique de la conversation :\n{history_str}\n\n" if history_str else ""

    prompt = f"""Tu es un assistant data analytics P&G dans une conversation continue. Ne te présente pas si tu l'as déjà fait.

{history_section}Question (données {label}) : "{question}"

Résultat de l'analyse :
{result_str}

Réponds en français, de manière concise et professionnelle. Mets les chiffres clés en valeur. N'évoque pas le code ou la méthode technique."""

    return gemini.generate_content(prompt).text.strip()

# ─── Orchestration ────────────────────────────────────────────────────────────
def process(question):
    try:
        routing = route_and_query(question)

        if routing["action"] == "clarify":
            return routing["message"]

        result = run_pandas_code(routing["code"], routing["sheet"])

        # Mémoriser la feuille active pour les prochains tours
        st.session_state.active_sheet = routing["sheet"]

        if result is None:
            return "Aucune donnée ne correspond à votre requête."
        if hasattr(result, "__len__") and len(result) == 0:
            return "Aucune donnée ne correspond aux critères de votre requête."

        return generate_answer(question, format_result(result), routing["sheet"])

    except json.JSONDecodeError:
        return "Je n'ai pas pu interpréter votre question. Pouvez-vous la reformuler ?"
    except (SyntaxError, KeyError, AttributeError) as e:
        return f"Erreur lors de l'analyse ({type(e).__name__}). Essayez de reformuler votre question."
    except Exception as e:
        return f"Erreur inattendue : {e}"

# ─── Interface chat ───────────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_input := st.chat_input("Posez votre question..."):
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Analyse en cours..."):
            reply = process(user_input)
        st.write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
