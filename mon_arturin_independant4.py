import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Gold Santé Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path("gold_sante_studio.db")


def inject_css() -> None:
    css = """
    <style>
        .stApp {
            background: linear-gradient(135deg, #07111f 0%, #0f172a 45%, #111827 100%);
            color: #e5eefc;
        }
        section[data-testid="stSidebar"] {
            background: #0b1220;
        }
        .hero {
            padding: 1.4rem 1.6rem;
            border-radius: 20px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            margin-bottom: 1rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 2.4rem;
        }
        .muted {
            color: #aebed1;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


@contextmanager
def db_cursor():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL,
                author_name TEXT,
                rating INTEGER NOT NULL,
                review_text TEXT NOT NULL,
                reply_text TEXT,
                reply_status TEXT NOT NULL DEFAULT 'À traiter',
                review_date TEXT,
                google_review_id TEXT,
                synced_from_google INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                content TEXT NOT NULL,
                networks TEXT NOT NULL,
                tone TEXT,
                scheduled_date TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Programmée'
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS newsletters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                audience TEXT,
                scheduled_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Programmée'
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS integrations (
                name TEXT PRIMARY KEY,
                connected INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        for name in ["google_business", "brevo", "xai_grok"]:
            cur.execute(
                "INSERT OR IGNORE INTO integrations(name, connected) VALUES (?, 0)",
                (name,),
            )

        review_count = cur.execute("SELECT COUNT(*) AS c FROM reviews").fetchone()["c"]
        if review_count == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            demo_reviews = [
                (
                    now,
                    "Google My Business",
                    "Sophie M.",
                    5,
                    "Très bon accueil et équipe à l'écoute.",
                    None,
                    "À traiter",
                    "2026-04-05",
                    "g-demo-001",
                    1,
                ),
                (
                    now,
                    "Google My Business",
                    "Marc D.",
                    3,
                    "Service correct mais attente un peu longue.",
                    "Bonjour Marc D.,\n\nMerci pour votre retour.\n\nBien cordialement,\nL'équipe Gold Santé",
                    "Répondu",
                    "2026-04-04",
                    "g-demo-002",
                    1,
                ),
                (
                    now,
                    "Facebook",
                    "Nina R.",
                    5,
                    "Professionnalisme et gentillesse, merci !",
                    None,
                    "À traiter",
                    "2026-04-03",
                    None,
                    0,
                ),
            ]
            cur.executemany(
                """
                INSERT INTO reviews(
                    created_at, source, author_name, rating, review_text,
                    reply_text, reply_status, review_date, google_review_id, synced_from_google
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                demo_reviews,
            )

        post_count = cur.execute("SELECT COUNT(*) AS c FROM posts").fetchone()["c"]
        if post_count == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            demo_posts = [
                (
                    now,
                    "Astuce bien-être de la semaine",
                    "Instagram, Facebook",
                    "Pédagogique",
                    "2026-04-08",
                    "09:00",
                    "Programmée",
                ),
                (
                    now,
                    "Conseil santé et expertise",
                    "LinkedIn",
                    "Professionnel",
                    "2026-04-10",
                    "14:30",
                    "Brouillon",
                ),
            ]
            cur.executemany(
                """
                INSERT INTO posts(
                    created_at, content, networks, tone, scheduled_date, scheduled_time, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                demo_posts,
            )

        newsletter_count = cur.execute("SELECT COUNT(*) AS c FROM newsletters").fetchone()["c"]
        if newsletter_count == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            demo_news = [
                (
                    now,
                    "Vos nouveautés santé d'avril",
                    "Bonjour,\n\nDécouvrez nos nouveautés santé du mois.\n\nL'équipe Gold Santé",
                    "Clients fidèles",
                    "2026-04-12",
                    "Programmée",
                )
            ]
            cur.executemany(
                """
                INSERT INTO newsletters(created_at, subject, content, audience, scheduled_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                demo_news,
            )


def fetch_df(query: str, params: tuple = ()) -> pd.DataFrame:
    with db_cursor() as cur:
        rows = cur.execute(query, params).fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(row) for row in rows])


def save_review(
    source: str,
    author: str,
    rating: int,
    review_text: str,
    review_date: str,
    google_review_id: str | None = None,
    synced_from_google: int = 0,
) -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO reviews(
                created_at, source, author_name, rating, review_text,
                reply_text, reply_status, review_date, google_review_id, synced_from_google
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source,
                author,
                rating,
                review_text,
                None,
                "À traiter",
                review_date,
                google_review_id,
                synced_from_google,
            ),
        )


def update_review_reply(review_id: int, reply_text: str, status: str = "Répondu") -> None:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE reviews SET reply_text = ?, reply_status = ? WHERE id = ?",
            (reply_text, status, review_id),
        )


def save_post(
    content: str,
    networks: list[str],
    tone: str,
    scheduled_date: str,
    scheduled_time: str,
    status: str = "Programmée",
) -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO posts(created_at, content, networks, tone, scheduled_date, scheduled_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                content,
                ", ".join(networks),
                tone,
                scheduled_date,
                scheduled_time,
                status,
            ),
        )


def save_newsletter(
    subject: str,
    content: str,
    audience: str,
    scheduled_date: str,
    status: str = "Programmée",
) -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO newsletters(created_at, subject, content, audience, scheduled_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                subject,
                content,
                audience,
                scheduled_date,
                status,
            ),
        )


def set_integration_connected(name: str, connected: bool) -> None:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE integrations SET connected = ? WHERE name = ?",
            (1 if connected else 0, name),
        )


def get_integration_status(name: str) -> bool:
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT connected FROM integrations WHERE name = ?",
            (name,),
        ).fetchone()
    return bool(row["connected"]) if row else False


def generate_reply(author: str, review_text: str, rating: int, tone: str = "Premium") -> str:
    author_display = author.strip() if author else "cher client"

    if tone == "Chaleureux":
        opening_positive = "Un grand merci pour votre message, il nous fait vraiment plaisir."
        opening_neutral = "Merci beaucoup d'avoir pris le temps de nous écrire."
        opening_negative = "Merci d'avoir partagé votre ressenti avec nous."
        signature_intro = "Merci encore pour votre confiance,"
    elif tone == "Professionnel":
        opening_positive = "Nous vous remercions sincèrement pour votre retour."
        opening_neutral = "Nous vous remercions pour votre commentaire."
        opening_negative = "Nous vous remercions d'avoir pris le temps de nous faire part de votre retour."
        signature_intro = "Bien cordialement,"
    else:
        opening_positive = "Merci infiniment pour votre message et pour votre confiance."
        opening_neutral = "Merci beaucoup pour votre retour positif."
        opening_negative = "Merci d'avoir pris le temps de partager votre retour."
        signature_intro = "Au plaisir de vous accueillir à nouveau,"

    if rating >= 5:
        opening = opening_positive
        body = (
            "Nous sommes très heureux de savoir que votre expérience chez Gold Santé a été à la hauteur de vos attentes.\n\n"
            "Votre retour nous encourage à poursuivre avec le même niveau d'exigence, d'écoute et d'attention."
        )
    elif rating == 4:
        opening = opening_neutral
        body = (
            "Nous sommes ravis de lire que votre expérience a été globalement satisfaisante.\n\n"
            "Nous restons attentifs à chaque détail pour rendre votre prochaine visite encore plus agréable."
        )
    else:
        opening = opening_negative
        body = (
            "Nous sommes sincèrement désolés que votre expérience n'ait pas pleinement répondu à vos attentes.\n\n"
            "Votre avis est précieux pour nous, car il nous aide à progresser et à mieux vous accompagner. "
            "Si vous le souhaitez, nous restons à votre écoute pour échanger plus en détail."
        )

    lines = [
        f"Bonjour {author_display},",
        "",
        opening,
        body,
        "",
        signature_intro,
        "L'équipe Gold Santé",
    ]
    return "\n".join(lines)


def generate_post_idea(theme: str, tone: str) -> str:
    theme = theme.strip() if theme else "le bien-être au quotidien"
    ideas = {
        "Professionnel": f"Aujourd'hui, nous partageons un conseil utile autour de {theme}. Notre priorité : vous accompagner avec clarté, confiance et expertise.",
        "Chaleureux": f"Prendre soin de soi commence souvent par de petits gestes. Aujourd'hui, parlons de {theme} avec simplicité et bienveillance.",
        "Premium": f"Chez Gold Santé, nous croyons à une approche exigeante et élégante du soin. Focus du jour : {theme}.",
        "Pédagogique": f"Comprendre {theme}, c'est déjà mieux agir. Voici un repère simple et concret à retenir aujourd'hui.",
        "Dynamique": f"Un bon réflexe santé peut tout changer. Aujourd'hui, on vous parle de {theme} en version claire, rapide et utile.",
    }
    return ideas.get(tone, ideas["Professionnel"])


def generate_newsletter_draft(topic: str) -> str:
    topic = topic.strip() if topic else "vos actualités santé"
    lines = [
        "Bonjour,",
        "",
        f"Nous avons le plaisir de vous partager nos actualités autour de : {topic}.",
        "",
        "Au programme :",
        "- un conseil pratique pour mieux prendre soin de vous,",
        "- un éclairage simple sur un sujet utile,",
        "- et nos nouveautés du moment.",
        "",
        "Merci pour votre confiance,",
        "L'équipe Gold Santé",
    ]
    return "\n".join(lines)


def simulate_google_sync() -> int:
    demo_reviews = [
        {
            "source": "Google My Business",
            "author_name": "Claire T.",
            "rating": 5,
            "review_text": "Très satisfaite, équipe chaleureuse et très professionnelle.",
            "review_date": datetime.now().strftime("%Y-%m-%d"),
            "google_review_id": "g-sim-1001",
        },
        {
            "source": "Google My Business",
            "author_name": "Paul R.",
            "rating": 4,
            "review_text": "Très bon accompagnement, merci pour votre disponibilité.",
            "review_date": datetime.now().strftime("%Y-%m-%d"),
            "google_review_id": "g-sim-1002",
        },
    ]

    existing = fetch_df("SELECT google_review_id FROM reviews WHERE google_review_id IS NOT NULL")
    existing_ids = set(existing["google_review_id"].tolist()) if not existing.empty else set()

    inserted = 0
    for review in demo_reviews:
        if review["google_review_id"] not in existing_ids:
            save_review(
                review["source"],
                review["author_name"],
                review["rating"],
                review["review_text"],
                review["review_date"],
                review["google_review_id"],
                1,
            )
            inserted += 1
    return inserted


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>Gold Santé Studio</h1>
            <p class="muted">Le cockpit premium de votre réputation locale, de vos contenus et de vos campagnes.</p>
            <p class="muted">Dashboard, avis, publications, newsletters et préparation Google Business.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(google_connected: bool) -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-box">
                <div class="sidebar-brand">Gold Santé</div>
                <div class="sidebar-text">Studio digital pour piloter réputation, contenus et relation client.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 🔐 Configuration API")
        st.text_input("Clé API xAI Grok", type="password", placeholder="Entrez votre clé")
        st.text_input("Clé API Brevo", type="password", placeholder="Entrez votre clé")

        st.markdown("### 🌍 Google Business")
        st.text_input("Client ID Google", placeholder="OAuth Client ID")
        st.text_input("Client Secret Google", type="password", placeholder="OAuth Client Secret")
        st.text_input("Redirect URI", placeholder="http://localhost:8501")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Connecter", use_container_width=True):
                set_integration_connected("google_business", True)
                st.rerun()
        with c2:
            if st.button("Déconnecter", use_container_width=True):
                set_integration_connected("google_business", False)
                st.rerun()

        st.caption(f"Statut : {'🟢 Connecté' if google_connected else '🟠 À configurer'}")

        st.markdown("---")
        return st.radio(
            "Navigation",
            [
                "🏠 Dashboard",
                "📥 Avis & Réponses IA",
                "📅 Publications Réseaux",
                "✉️ Bulletins d'information",
                "⚙️ Intégrations",
            ],
            label_visibility="collapsed",
        )


def main() -> None:
    inject_css()
    init_db()

    reviews_df = fetch_df("SELECT * FROM reviews ORDER BY created_at DESC")
    posts_df = fetch_df("SELECT * FROM posts ORDER BY scheduled_date ASC, scheduled_time ASC")
    news_df = fetch_df("SELECT * FROM newsletters ORDER BY scheduled_date ASC")
    google_connected = get_integration_status("google_business")

    reviews_total = len(reviews_df)
    reviews_pending = len(reviews_df[reviews_df["reply_status"] == "À traiter"]) if not reviews_df.empty else 0
    reviews_answered = len(reviews_df[reviews_df["reply_status"] == "Répondu"]) if not reviews_df.empty else 0
    avg_rating = round(reviews_df["rating"].astype(float).mean(), 1) if not reviews_df.empty else 0.0
    posts_total = len(posts_df)
    posts_scheduled = len(posts_df[posts_df["status"] == "Programmée"]) if not posts_df.empty else 0
    news_total = len(news_df)
    reputation_score = max(0, min(100, int((avg_rating * 20) - (reviews_pending * 2)))) if reviews_total else 0
    low_rating_reviews = len(reviews_df[reviews_df["rating"].astype(int) <= 3]) if not reviews_df.empty else 0
    high_rating_reviews = len(reviews_df[reviews_df["rating"].astype(int) >= 4]) if not reviews_df.empty else 0

    render_header()
    page = render_sidebar(google_connected)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Avis totaux", reviews_total)
    k2.metric("À traiter", reviews_pending)
    k3.metric("Répondus", reviews_answered)
    k4.metric("Note moyenne", avg_rating)

    st.markdown("")

    if page == "🏠 Dashboard":
        st.subheader("🏠 Dashboard")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Publications prévues", posts_total)
        d2.metric("Programmées", posts_scheduled)
        d3.metric("Newsletters planifiées", news_total)
        d4.metric("Score réputation", f"{reputation_score}/100")

        if not reviews_df.empty:
            chart_reviews = reviews_df.copy()
            chart_reviews["review_date"] = pd.to_datetime(chart_reviews["review_date"], errors="coerce")
            chart_reviews = chart_reviews.dropna(subset=["review_date"])
            if not chart_reviews.empty:
                daily_ratings = chart_reviews.groupby(chart_reviews["review_date"].dt.date)["rating"].mean().reset_index()
                daily_ratings.columns = ["Date", "Note moyenne"]

                left, right = st.columns([1, 1.6])
                with left:
                    st.metric("Avis positifs", high_rating_reviews)
                    st.metric("Avis sensibles", low_rating_reviews)
                with right:
                    st.markdown("#### Évolution de la note moyenne")
                    st.line_chart(daily_ratings.set_index("Date"))

        a_left, a_right = st.columns([1.2, 1])
        with a_left:
            st.markdown("#### Activité récente")
            activity = []

            for _, row in reviews_df.head(4).iterrows():
                activity.append(
                    {
                        "Type": "Avis",
                        "Détail": f"{row.get('author_name') or 'Client'} a laissé un avis {int(row['rating'])}★",
                        "Statut": row["reply_status"],
                        "Date": row.get("review_date") or str(row.get("created_at", ""))[:10],
                    }
                )
            for _, row in posts_df.head(2).iterrows():
                activity.append(
                    {
                        "Type": "Publication",
                        "Détail": row["content"][:70],
                        "Statut": row["status"],
                        "Date": row["scheduled_date"],
                    }
                )
            for _, row in news_df.head(2).iterrows():
                activity.append(
                    {
                        "Type": "Newsletter",
                        "Détail": row["subject"],
                        "Statut": row["status"],
                        "Date": row["scheduled_date"],
                    }
                )

            activity_df = pd.DataFrame(activity)
            if not activity_df.empty:
                st.dataframe(activity_df, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune activité enregistrée pour le moment.")

        with a_right:
            st.markdown("#### Priorités du jour")
            if reviews_pending > 0:
                st.warning(f"{reviews_pending} avis attendent encore une réponse.")
            else:
                st.success("Tous les avis ont reçu une réponse.")

            if reputation_score >= 85:
                st.success("La réputation locale est solide et inspire confiance.")
            elif reputation_score >= 65:
                st.info("La réputation est saine, avec encore une marge d'amélioration sur la réactivité.")
            else:
                st.warning("Il est temps de prioriser les réponses et de lisser l'expérience client.")

            if posts_total > 0:
                st.info("Passez en revue les publications à venir pour garder une tonalité cohérente.")
            if news_total > 0:
                st.success("Une campagne newsletter est déjà en attente de validation ou d'envoi.")
            if google_connected:
                st.success("Google Business est connecté : le terrain est prêt pour la synchronisation réelle.")
            else:
                st.info("Branchez Google Business pour recevoir les avis Google dans le tableau de bord.")

    elif page == "📥 Avis & Réponses IA":
        st.subheader("📥 Avis & Réponses IA")

        m1, m2, m3 = st.columns(3)
        m1.metric("Avis en attente", reviews_pending)
        m2.metric("Note moyenne", avg_rating)
        m3.metric("Google connecté", "Oui" if google_connected else "Non")

        with st.expander("➕ Ajouter un avis manuellement", expanded=False):
            r1, r2 = st.columns([2, 1])
            with r1:
                review_text = st.text_area("Texte de l'avis", height=140, placeholder="Collez ici l'avis reçu...")
                rating = st.slider("Note", 1, 5, 5)
            with r2:
                author = st.text_input("Auteur / pseudo", placeholder="Jean Dupont")
                source = st.selectbox("Source", ["Google My Business", "Facebook", "Instagram", "Site web", "Autre"])
                review_date = st.date_input("Date de l'avis", value=date.today())

            if st.button("Enregistrer l'avis", use_container_width=True):
                if review_text.strip():
                    save_review(source, author, rating, review_text.strip(), review_date.strftime("%Y-%m-%d"))
                    st.success("Avis enregistré.")
                    st.rerun()
                else:
                    st.error("Le texte de l'avis est requis.")

        if google_connected:
            if st.button("🔄 Synchroniser les avis Google", use_container_width=True):
                inserted = simulate_google_sync()
                if inserted:
                    st.success(f"{inserted} nouvel(s) avis Google importé(s).")
                else:
                    st.info("Aucun nouvel avis Google à importer.")
                st.rerun()
        else:
            st.info("Connectez Google Business depuis la barre latérale pour activer la synchronisation des avis.")

        st.markdown("#### Répondre à un avis")

        if not reviews_df.empty:
            options = {
                f"#{int(row['id'])} • {row.get('author_name') or 'Client'} • {int(row['rating'])}★ • {row['source']}": int(row["id"])
                for _, row in reviews_df.iterrows()
            }
            selected_label = st.selectbox("Choisissez un avis", list(options.keys()))
            selected_id = options[selected_label]
            selected_review = reviews_df[reviews_df["id"] == selected_id].iloc[0]

            st.write(f"**Auteur :** {selected_review.get('author_name') or 'Client'}")
            st.write(f"**Source :** {selected_review['source']}")
            st.write(f"**Note :** {int(selected_review['rating'])} / 5")
            st.write(f"**Texte :** {selected_review['review_text']}")

            reply_tone = st.selectbox("Ton de réponse IA", ["Premium", "Chaleureux", "Professionnel"], index=0)
            auto_ready = int(selected_review["rating"]) >= 4 and selected_review["source"] == "Google My Business"
            if auto_ready:
                st.caption("Cet avis est éligible à une future réponse semi-automatique après validation.")
            else:
                st.caption("Cet avis restera en validation manuelle, même avec l'automatisation future.")

            existing_reply = selected_review["reply_text"] if pd.notna(selected_review["reply_text"]) and selected_review["reply_text"] else ""
            default_reply = existing_reply or generate_reply(
                selected_review.get("author_name") or "",
                selected_review["review_text"],
                int(selected_review["rating"]),
                reply_tone,
            )

            if st.button("🤖 Proposer une réponse IA", use_container_width=True):
                st.session_state["draft_reply"] = generate_reply(
                    selected_review.get("author_name") or "",
                    selected_review["review_text"],
                    int(selected_review["rating"]),
                    reply_tone,
                )

            reply_value = st.session_state.get("draft_reply", default_reply)
            reply = st.text_area("Réponse à envoyer", value=reply_value, height=220, key=f"reply_{selected_id}")

            if st.button("✅ Enregistrer la réponse", type="primary", use_container_width=True):
                update_review_reply(selected_id, reply, "Répondu")
                st.success("Réponse enregistrée.")
                st.rerun()

            display_reviews = reviews_df[["id", "review_date", "source", "author_name", "rating", "reply_status", "review_text"]].copy()
            display_reviews.columns = ["ID", "Date", "Source", "Auteur", "Note", "Statut", "Avis"]
            st.dataframe(display_reviews, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun avis disponible.")

    elif page == "📅 Publications Réseaux":
        st.subheader("📅 Publications Réseaux")

        with st.expander("✨ Créer une publication", expanded=True):
            theme = st.text_input("Thème ou angle", placeholder="Ex. prévention, bien-être, routine du matin")
            tone = st.selectbox("Ton souhaité", ["Professionnel", "Chaleureux", "Premium", "Pédagogique", "Dynamique"])

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                post_date = st.date_input("Date de publication", value=date.today() + timedelta(days=1), key="post_date")
            with col_p2:
                post_time = st.time_input("Heure de publication", value=time(9, 0), key="post_time")

            networks = st.multiselect("Réseaux", ["Instagram", "Facebook", "LinkedIn", "Google Posts"], default=["Instagram", "Facebook"])

            b1, b2 = st.columns(2)
            with b1:
                if st.button("🤖 Générer une idée de publication", use_container_width=True):
                    st.session_state["post_draft"] = generate_post_idea(theme, tone)
            with b2:
                if st.button("🧹 Réinitialiser le brouillon", use_container_width=True):
                    st.session_state["post_draft"] = ""

            content = st.text_area(
                "Contenu",
                value=st.session_state.get("post_draft", ""),
                height=180,
                placeholder="Rédigez votre publication ici...",
            )

            if st.button("📅 Programmer la publication", type="primary", use_container_width=True):
                if content.strip() and networks:
                    save_post(content.strip(), networks, tone, post_date.strftime("%Y-%m-%d"), post_time.strftime("%H:%M"), "Programmée")
                    st.success("Publication programmée.")
                    st.rerun()
                else:
                    st.error("Le contenu et au moins un réseau sont requis.")

        st.markdown("#### Calendrier éditorial")
        if not posts_df.empty:
            calendar_df = posts_df.copy()
            calendar_df["datetime"] = pd.to_datetime(
                calendar_df["scheduled_date"] + " " + calendar_df["scheduled_time"],
                errors="coerce",
            )
            calendar_df = calendar_df.sort_values("datetime")

            display_calendar = calendar_df[["scheduled_date", "scheduled_time", "status", "networks", "tone", "content"]].copy()
            display_calendar.columns = ["Date", "Heure", "Statut", "Réseaux", "Ton", "Contenu"]
            st.dataframe(display_calendar, use_container_width=True, hide_index=True)

            upcoming_only = calendar_df[["datetime", "content", "networks", "status"]].dropna().copy()
            if not upcoming_only.empty:
                st.markdown("#### Vue agenda")
                upcoming_only["Moment"] = upcoming_only["datetime"].dt.strftime("%d/%m/%Y • %H:%M")
                for _, row in upcoming_only.head(8).iterrows():
                    st.markdown(f"**{row['Moment']}** — {row['content']}")
                    st.caption(f"{row['networks']} • {row['status']}")
        else:
            st.info("Aucune publication planifiée.")

    elif page == "✉️ Bulletins d'information":
        st.subheader("✉️ Bulletins d'information")

        with st.expander("💌 Créer un bulletin", expanded=True):
            topic = st.text_input("Sujet / thème", placeholder="Ex. nouveautés du mois, conseils saisonniers")
            audience = st.selectbox("Audience cible", ["Tous les contacts", "Clients fidèles", "Prospects", "Patients récents", "Liste personnalisée"])
            send_date = st.date_input("Date d'envoi", value=date.today() + timedelta(days=3), key="newsletter_date")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("🤖 Générer un brouillon", use_container_width=True):
                    st.session_state["newsletter_draft"] = generate_newsletter_draft(topic)
            with b2:
                if st.button("🧽 Effacer le brouillon", use_container_width=True):
                    st.session_state["newsletter_draft"] = ""

            newsletter_content = st.text_area(
                "Contenu du bulletin",
                value=st.session_state.get("newsletter_draft", ""),
                height=260,
                placeholder="Rédigez ici le contenu de votre bulletin...",
            )
            subject = st.text_input("Objet du mail", placeholder="Ex. Vos nouveautés santé du mois")

            if st.button("✉️ Programmer l'envoi", type="primary", use_container_width=True):
                if subject.strip() and newsletter_content.strip():
                    save_newsletter(subject.strip(), newsletter_content.strip(), audience, send_date.strftime("%Y-%m-%d"), "Programmée")
                    st.success("Bulletin programmé.")
                    st.rerun()
                else:
                    st.error("L'objet et le contenu sont requis.")

        st.markdown("#### Campagnes prévues")
        if not news_df.empty:
            display_news = news_df[["id", "scheduled_date", "audience", "status", "subject"]].copy()
            display_news.columns = ["ID", "Date", "Audience", "Statut", "Sujet"]
            st.dataframe(display_news, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune newsletter planifiée.")

    elif page == "⚙️ Intégrations":
        st.subheader("⚙️ Intégrations")

        left, right = st.columns(2)

        with left:
            st.markdown("### Google Business Profile")
            st.write(f"**Statut actuel :** {'Connecté' if google_connected else 'Non connecté'}")
            st.write("Cette version prépare l'arrivée des vrais avis Google directement dans l'application.")
            st.write("Le bouton de synchronisation actuel simule l'import pour valider l'expérience produit.")

            if st.button("🔄 Lancer une synchro test", use_container_width=True):
                if google_connected:
                    inserted = simulate_google_sync()
                    if inserted:
                        st.success(f"{inserted} avis test importé(s).")
                    else:
                        st.info("Aucun nouvel avis test à importer.")
                    st.rerun()
                else:
                    st.error("Commencez par activer Google Business depuis la barre latérale.")

        with right:
            st.markdown("### Architecture recommandée")
            st.write("- Streamlit pour l'interface")
            st.write("- OAuth Google pour connecter le compte Business")
            st.write("- Appels API pour lister les avis et publier les réponses")
            st.write("- Notifications pour recevoir les nouveaux avis plus vite")
            st.write("- Base SQLite aujourd'hui")
            st.write("- Préparation à une réponse semi-automatique pour les avis positifs")

        with st.expander("🛠️ Notes techniques pour la production", expanded=False):
            st.code(
                "pip install streamlit pandas google-auth google-auth-oauthlib google-api-python-client",
                language="bash",
            )

    st.markdown("---")
    st.caption("Gold Santé Studio — V2.2 clean • Base locale SQLite • Expérience premium • Prêt à accueillir Google Business réel")


if __name__ == "__main__":
    main()