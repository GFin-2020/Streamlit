import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import json
import re
import math
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFilter
import streamlit.components.v1 as components

# ─── Avatar : LED frame + étoile 4 branches (design issu du React) ────────────
def _make_avatar(size: int = 200) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    c = (208, 212, 218, 255)
    lw = 16                      # traits épais — très visibles une fois scalés
    cs = round(size * 0.30)      # longueur bracket = 30% de la taille

    # Coins LED (4 brackets)
    for x0, x1, y0, y1 in [
        (0, cs, 0, 0), (0, 0, 0, cs),
        (size - cs, size, 0, 0), (size, size, 0, cs),
        (0, 0, size - cs, size), (0, cs, size, size),
        (size - cs, size, size, size), (size, size, size - cs, size),
    ]:
        draw.line([(x0, y0), (x1, y1)], fill=c, width=lw)

    # Étoile Gemini 4 branches — bras effilés, ratio 12:1
    cx = cy = size // 2
    outer, inner = round(size * 0.32), round(size * 0.026)
    pts = []
    for i in range(8):
        angle = math.pi / 4 * i - math.pi / 2
        r = outer if i % 2 == 0 else inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

    # Halo doux sous l'étoile
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(glow).polygon(pts, fill=(208, 212, 218, 140))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=size // 16))
    img.alpha_composite(glow)

    # Étoile nette par-dessus
    draw.polygon(pts, fill=c)

    return img

AVATAR_IMG = _make_avatar()

# ─── Configuration page ───────────────────────────────────────────────────────
st.set_page_config(page_title="P&G Chatbot", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    /* ── Variables CSS ───────────────────────────────────────────────── */
    :root {
        --primary-color: rgba(208, 212, 218, 0.35) !important;
        --background-color: #000000 !important;
        --secondary-background-color: #000000 !important;
    }

    /* ── Typographie ─────────────────────────────────────────────────── */
    html, body, * {
        font-family: 'Inter', sans-serif !important;
        font-size: 12px !important;
        color: #d0d4da;
    }

    /* ── Layout ──────────────────────────────────────────────────────── */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* ── Masquer le chrome Streamlit ─────────────────────────────────── */
    [data-testid="stHeader"], [data-testid="stToolbar"],
    [data-testid="stDecoration"], header, #MainMenu, footer,
    [data-testid="stEmbedFooter"], .stEmbedFooter,
    [class*="stEmbedFooter"], [class*="EmbedFooter"],
    [data-testid="bundle-hosted-badge"], .viewerBadge,
    [class*="viewerBadge"], [class*="styled-widgets"],
    a[href*="streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* ── Backgrounds transparents ────────────────────────────────────── */
    html, body, #root,
    [data-testid="stApp"],
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stBottom"],
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid^="stChat"],
    .main, .block-container,
    .appview-container {
        background: #000000 !important;
        background-color: #000000 !important;
    }

    /* ── Couleur texte globale ───────────────────────────────────────── */
    [data-testid="stChatMessage"] *,
    [data-testid="stMarkdownContainer"] *,
    [data-testid="stChatInput"] textarea,
    [data-testid="stSpinner"] * {
        color: #d0d4da !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: rgba(208, 212, 218, 0.4) !important;
    }

    [data-testid="stChatInput"] textarea {
        caret-color: #d0d4da !important;
        background: transparent !important;
    }

    /* ── Champ saisie : pas de bordure rouge ─────────────────────────── */
    [data-testid="stChatInputContainer"] > div {
        border-color: rgba(208, 212, 218, 0.18) !important;
        box-shadow: none !important;
        background: transparent !important;
    }

    [data-testid="stChatInputContainer"] > div:focus-within {
        border-color: rgba(208, 212, 218, 0.4) !important;
        box-shadow: none !important;
    }

    [data-testid="stChatInputContainer"] textarea:focus,
    [data-testid="stChatInputContainer"] textarea:active,
    [data-baseweb="textarea"]:focus-within {
        border-color: rgba(208, 212, 218, 0.4) !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* ── Bouton envoi : pas de rouge ─────────────────────────────────── */
    [data-testid="stChatInputContainer"] button,
    [data-testid="stChatInputContainer"] button:hover,
    [data-testid="stChatInputContainer"] button:focus,
    [data-testid="stChatInputContainer"] button:active,
    [data-testid="stChatInputContainer"] button:not([disabled]) {
        background: transparent !important;
        background-color: transparent !important;
        border-color: rgba(208, 212, 218, 0.35) !important;
        box-shadow: none !important;
        outline: none !important;
        color: #d0d4da !important;
    }

    [data-testid="stChatInputContainer"] button svg,
    [data-testid="stChatInputContainer"] button svg path {
        fill: #d0d4da !important;
    }

    *:focus, *:focus-visible {
        outline: none !important;
    }

    /* ── Messages user à droite via :has (sans JS, sans race condition) ── */
    [data-testid="stChatMessage"]:has(.msg-user) {
        flex-direction: row-reverse !important;
    }

    [data-testid="stChatMessage"]:has(.msg-user) > div:first-child {
        display: none !important;
    }

    [data-testid="stChatMessage"]:has(.msg-user) [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"]:has(.msg-user) p {
        text-align: right !important;
    }

    .msg-user {
        display: none !important;
    }

    /* ── Coins LED — positionnés aux bords réels du composant ────────── */
    html::before, html::after, body::before, body::after {
        content: '';
        position: fixed;
        width: 20px;
        height: 20px;
        z-index: 99999;
        pointer-events: none;
        transition: border-color 0.4s ease, filter 0.4s ease;
    }

    html::before {
        top: 0; left: 0;
        border-top: 1.5px solid rgba(208, 212, 218, 0.2);
        border-left: 1.5px solid rgba(208, 212, 218, 0.2);
    }
    html::after {
        top: 0; right: 18px;
        border-top: 1.5px solid rgba(208, 212, 218, 0.2);
        border-right: 1.5px solid rgba(208, 212, 218, 0.2);
    }
    body::before {
        bottom: 0; left: 0;
        border-bottom: 1.5px solid rgba(208, 212, 218, 0.2);
        border-left: 1.5px solid rgba(208, 212, 218, 0.2);
    }
    body::after {
        bottom: 0; right: 18px;
        border-bottom: 1.5px solid rgba(208, 212, 218, 0.2);
        border-right: 1.5px solid rgba(208, 212, 218, 0.2);
    }

    /* État illuminé : hover sur la fenêtre OU focus sur le champ */
    html:hover::before, html:hover::after,
    html:hover body::before, html:hover body::after,
    html:focus-within::before, html:focus-within::after,
    body:focus-within::before, body:focus-within::after {
        border-color: #d0d4da;
        filter: drop-shadow(0 0 6px rgba(208, 212, 218, 0.75));
    }

    /* ── Scrollbar ───────────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #000000; }
    ::-webkit-scrollbar-thumb { background: rgba(208, 212, 218, 0.25); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(208, 212, 218, 0.45); }
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

if "active_sheet" not in st.session_state:
    st.session_state.active_sheet = None

# ─── Helpers ──────────────────────────────────────────────────────────────────
def build_history_str(exclude_last=True, max_messages=8):
    msgs = st.session_state.messages
    if exclude_last:
        msgs = msgs[:-1]
    recent = msgs[-max_messages:] if len(msgs) > max_messages else msgs
    lines = []
    for m in recent:
        role = "Utilisateur" if m["role"] == "user" else "Assistant"
        lines.append(f"[{role}] {m['content'][:600]}")
    return "\n".join(lines)


def build_sheet_schema(name, df):
    cols = " | ".join(f"{c} ({df[c].dtype})" for c in df.columns)
    dims = ["Pays", "Marque", "Véhicule", "Source_Traffic"]
    dim_lines = "\n".join(
        f"  {c} : {', '.join(str(v) for v in sorted(df[c].dropna().unique()))}"
        for c in dims if c in df.columns
    )
    date_col = next((c for c in ["Date", "Timestamp"] if c in df.columns), None)
    date_info = (
        f"  {date_col} : {df[date_col].min()} → {df[date_col].max()}"
        if date_col else "  (aucune colonne temporelle)"
    )
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
1. Si un contexte actif est établi (indiqué entre crochets ci-dessus) : utilise cette feuille sans redemander, SAUF si l'utilisateur mentionne explicitement l'autre.
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
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        text = m.group(1).strip()
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

# Marker minimal — le JS injecte l'animation directement dans le slot avatar PIL
THK_MARKER = '<span id="thk-marker" style="display:none"></span>'

# ─── Interface chat ───────────────────────────────────────────────────────────
for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown('<span class="msg-user"></span>', unsafe_allow_html=True)
            st.write(message["content"])
    else:
        with st.chat_message("assistant", avatar=AVATAR_IMG):
            st.write(message["content"])

if user_input := st.chat_input("Posez votre question..."):
    with st.chat_message("user"):
        st.markdown('<span class="msg-user"></span>', unsafe_allow_html=True)
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant", avatar=AVATAR_IMG):
        # Le marker déclenche l'injection JS de l'animation dans ce slot avatar
        thinking_slot = st.empty()
        thinking_slot.markdown(THK_MARKER, unsafe_allow_html=True)
        reply = process(user_input)
        thinking_slot.empty()   # supprime le marker → JS retire l'animation et restaure PIL
        st.write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

# ─── JS : fond noir + injection animation dans le slot avatar ─────────────────
# Le MutationObserver surveille le DOM entier de stApp pour deux responsabilités :
#   1. Forcer le fond noir (React le réécrit parfois via style inline)
#   2. Détecter l'apparition/disparition du #thk-marker pour injecter/retirer
#      l'animation LED directement dans le slot avatar PIL du même stChatMessage
components.html("""
<script>
(function () {
    const doc  = window.parent.document;
    const win  = window.parent;

    if (win._bgObserver) win._bgObserver.disconnect();

    // ── 1. Fond noir ─────────────────────────────────────────────────────────
    const BG_SELS = [
        'html','body','[data-testid="stApp"]','[data-testid="stAppViewContainer"]',
        '[data-testid="stMain"]','[data-testid="stBottom"]','.block-container','.main'
    ];
    function forceBg() {
        BG_SELS.forEach(s => {
            const el = doc.querySelector(s);
            if (el) {
                el.style.setProperty('background','#000000','important');
                el.style.setProperty('background-color','#000000','important');
            }
        });
    }

    // ── 2. Animation dans le slot avatar ────────────────────────────────────
    function injectThkCss() {
        if (doc.getElementById('thk-style')) return;
        const s = doc.createElement('style');
        s.id = 'thk-style';
        s.textContent = `
            @keyframes thk-fspin{
                0%{transform:rotate(0deg)}40%{transform:rotate(405deg)}
                50%{transform:rotate(405deg)}90%{transform:rotate(810deg)}
                100%{transform:rotate(810deg)}
            }
            @keyframes thk-ispin{
                0%{transform:rotate(0deg)}40%{transform:rotate(-405deg)}
                50%{transform:rotate(-405deg)}90%{transform:rotate(-810deg)}
                100%{transform:rotate(-810deg)}
            }
            #thk-anim{display:flex!important;align-items:center!important;justify-content:center!important;}
            #thk-frame{
                position:relative!important;width:100%!important;height:100%!important;
                display:flex!important;align-items:center!important;justify-content:center!important;
                animation:thk-fspin 2.8s ease-in-out infinite!important;
            }
            .thk-c{position:absolute!important;width:30%!important;height:30%!important;}
            .thk-c::before{content:''!important;position:absolute!important;
                width:100%!important;height:2px!important;
                background:#d0d4da!important;box-shadow:0 0 5px rgba(208,212,218,.7)!important;}
            .thk-c::after{content:''!important;position:absolute!important;
                width:2px!important;height:100%!important;
                background:#d0d4da!important;box-shadow:0 0 5px rgba(208,212,218,.7)!important;}
            .thk-tl{top:0;left:0} .thk-tl::before,.thk-tl::after{top:0;left:0}
            .thk-tr{top:0;right:0} .thk-tr::before,.thk-tr::after{top:0;right:0}
            .thk-bl{bottom:0;left:0} .thk-bl::before,.thk-bl::after{bottom:0;left:0}
            .thk-br{bottom:0;right:0} .thk-br::before,.thk-br::after{bottom:0;right:0}
            #thk-star{
                color:#d0d4da!important;font-size:15px!important;line-height:1!important;
                text-shadow:0 0 8px rgba(208,212,218,.8)!important;
                animation:thk-ispin 2.8s ease-in-out infinite!important;
            }
        `;
        doc.head.appendChild(s);
    }

    function applyThinkingAvatar() {
        const marker = doc.getElementById('thk-marker');
        const existing = doc.getElementById('thk-anim');

        if (marker && !existing) {
            // Remonter jusqu'au stChatMessage parent du marker
            let node = marker.parentElement;
            while (node && node !== doc.body) {
                if (node.getAttribute && node.getAttribute('data-testid') === 'stChatMessage') break;
                node = node.parentElement;
            }
            if (!node || node === doc.body) return;

            const img = node.querySelector('img');
            if (!img) return;

            injectThkCss();

            const sz = img.offsetWidth || 36;
            const anim = doc.createElement('div');
            anim.id = 'thk-anim';
            anim.style.cssText = 'width:'+sz+'px;height:'+sz+'px;';
            anim.innerHTML =
                '<div id="thk-frame">' +
                  '<div class="thk-c thk-tl"></div><div class="thk-c thk-tr"></div>' +
                  '<div class="thk-c thk-bl"></div><div class="thk-c thk-br"></div>' +
                  '<span id="thk-star">✦</span>' +
                '</div>';

            img.style.setProperty('display','none','important');
            win._thkImg = img;
            img.parentElement.appendChild(anim);

        } else if (!marker && existing) {
            existing.remove();
            if (win._thkImg) {
                win._thkImg.style.removeProperty('display');
                win._thkImg = null;
            }
        }
    }

    // ── Bootstrap + observer ─────────────────────────────────────────────────
    forceBg();
    applyThinkingAvatar();

    const appEl = doc.querySelector('[data-testid="stApp"]');
    if (appEl) {
        let raf = null;
        const obs = new MutationObserver(() => {
            forceBg();
            cancelAnimationFrame(raf);
            raf = requestAnimationFrame(applyThinkingAvatar);
        });
        obs.observe(appEl, {
            attributes: true, attributeFilter: ['style'],
            childList: true,  subtree: true
        });
        win._bgObserver = obs;
    }
})();
</script>
""", height=0, scrolling=False)
