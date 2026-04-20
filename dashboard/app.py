import streamlit as st
import json
import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="SML - Mepolizumab Social Listening",
    page_icon="💊",
    layout="wide",
)

DATA_PATH = "data/analyzed_posts.json"

@st.cache_resource(show_spinner="Building vector store...")
def init_vector_store():
    """Build ChromaDB on first load — needed for Streamlit Cloud."""
    chroma_path = "data/chroma_db"
    already_built = os.path.exists(chroma_path) and len(os.listdir(chroma_path)) > 0
    if not already_built:
        from rag.vector_store import build_vector_store
        build_vector_store()
    return True

@st.cache_data
def load_data():
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_df(posts):
    rows = []
    for p in posts:
        rows.append({
            "id": p.get("id"),
            "subreddit": p.get("subreddit", ""),
            "stakeholder": p.get("stakeholder", "Patients"),
            "sentiment": p.get("sentiment", "Neutral"),
            "sentiment_score": p.get("sentiment_score", 0.0),
            "emotion": p.get("emotion", "Neutral"),
            "themes": p.get("themes", []),
            "drugs_mentioned": p.get("drugs_mentioned", []),
            "key_entities": p.get("key_entities", []),
            "summary": p.get("summary", ""),
            "quote": p.get("quote", ""),
            "url": p.get("url", ""),
            "created_utc": p.get("created_utc", ""),
            "score": p.get("score", 0),
        })
    return pd.DataFrame(rows)

# ── RAG Chat Dialog ──────────────────────────────────────────────────────────
@st.dialog("💬 Ask the Social Listening Assistant", width="large")
def rag_chat_dialog():
    from rag.retriever import rag_query

    st.markdown("Ask anything about patient/HCP discussions on Mepolizumab and asthma biologics.")

    stakeholder_filter = st.selectbox(
        "Filter by stakeholder (optional)",
        ["All", "Patients", "Physicians", "Pharmacists", "Caregivers", "Payers", "Patient Advocacy Groups"],
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    query = st.chat_input("Type your question...")
    if query:
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Searching and reasoning..."):
                try:
                    filters = None
                    if stakeholder_filter != "All":
                        filters = {"stakeholder": stakeholder_filter}
                    answer = rag_query(query, filters=filters)
                except Exception as e:
                    answer = f"Error: {str(e)}"
            st.markdown(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

# ── Main App ─────────────────────────────────────────────────────────────────
def main():
    # Init vector store on first load (handles Streamlit Cloud cold start)
    init_vector_store()

    # Top bar with chat button
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.title("💊 Mepolizumab Social Media Listening")
        st.caption("Hybrid RAG · Reddit · NER + Sentiment · Stakeholder Analysis")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💬 Open Chat", use_container_width=True, type="primary"):
            rag_chat_dialog()

    posts = load_data()

    if not posts:
        st.warning("No analyzed data found. Run the pipeline first:")
        st.code(
            "python scraper/reddit_scraper.py\n"
            "python preprocessing/preprocessor.py\n"
            "python analysis/analyzer.py\n"
            "python rag/vector_store.py",
            language="bash"
        )
        return

    df = get_df(posts)

    # ── Sidebar Filters ───────────────────────────────────────────────────────
    st.sidebar.header("Filters")
    stakeholders = ["All"] + sorted(df["stakeholder"].unique().tolist())
    selected_stakeholder = st.sidebar.selectbox("Stakeholder", stakeholders)
    sentiments = ["All"] + sorted(df["sentiment"].unique().tolist())
    selected_sentiment = st.sidebar.selectbox("Sentiment", sentiments)
    subreddits = ["All"] + sorted(df["subreddit"].unique().tolist())
    selected_subreddit = st.sidebar.selectbox("Subreddit", subreddits)

    filtered = df.copy()
    if selected_stakeholder != "All":
        filtered = filtered[filtered["stakeholder"] == selected_stakeholder]
    if selected_sentiment != "All":
        filtered = filtered[filtered["sentiment"] == selected_sentiment]
    if selected_subreddit != "All":
        filtered = filtered[filtered["subreddit"] == selected_subreddit]

    # ── KPI Row ───────────────────────────────────────────────────────────────
    st.markdown("---")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Posts", len(filtered))
    k2.metric("Subreddits", filtered["subreddit"].nunique())
    k3.metric("Avg Sentiment Score", f"{filtered['sentiment_score'].mean():.2f}")
    pos_pct = (filtered["sentiment"] == "Positive").sum() / max(len(filtered), 1) * 100
    k4.metric("Positive %", f"{pos_pct:.1f}%")
    neg_pct = (filtered["sentiment"] == "Negative").sum() / max(len(filtered), 1) * 100
    k5.metric("Negative %", f"{neg_pct:.1f}%")
    st.markdown("---")

    # ── Sentiment Analysis Section ────────────────────────────────────────────
    st.subheader("Sentiment Analysis")
    s_col1, s_col2, s_col3 = st.columns(3)

    with s_col1:
        sent_counts = filtered["sentiment"].value_counts().reset_index()
        sent_counts.columns = ["Sentiment", "Count"]
        color_map = {"Positive": "#2ecc71", "Negative": "#e74c3c", "Neutral": "#95a5a6"}
        fig_sent = px.pie(
            sent_counts, names="Sentiment", values="Count",
            color="Sentiment", color_discrete_map=color_map,
            title="Overall Sentiment Distribution",
        )
        st.plotly_chart(fig_sent, use_container_width=True)

    with s_col2:
        sent_by_stake = filtered.groupby(["stakeholder", "sentiment"]).size().reset_index(name="count")
        fig_bar = px.bar(
            sent_by_stake, x="stakeholder", y="count", color="sentiment",
            color_discrete_map=color_map, barmode="stack",
            title="Sentiment by Stakeholder",
            labels={"stakeholder": "Stakeholder", "count": "Posts"},
        )
        fig_bar.update_xaxes(tickangle=30)
        st.plotly_chart(fig_bar, use_container_width=True)

    with s_col3:
        emotion_counts = filtered["emotion"].value_counts().reset_index()
        emotion_counts.columns = ["Emotion", "Count"]
        fig_emo = px.bar(
            emotion_counts, x="Emotion", y="Count",
            color="Emotion", title="Emotion Distribution",
        )
        st.plotly_chart(fig_emo, use_container_width=True)

    # Sentiment score over time
    if "created_utc" in filtered.columns and filtered["created_utc"].notna().any():
        time_df = filtered[filtered["created_utc"] != ""].copy()
        time_df["date"] = pd.to_datetime(time_df["created_utc"], errors="coerce").dt.date
        time_df = time_df.dropna(subset=["date"])
        if not time_df.empty:
            trend = time_df.groupby("date")["sentiment_score"].mean().reset_index()
            fig_trend = px.line(
                trend, x="date", y="sentiment_score",
                title="Sentiment Score Trend Over Time",
                labels={"sentiment_score": "Avg Sentiment Score"},
            )
            fig_trend.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # ── NER / Stakeholder Analysis Section ───────────────────────────────────
    st.subheader("NER & Stakeholder Analysis")

    stakeholder_tabs = st.tabs([
        "Patients", "Physicians", "Pharmacists",
        "Caregivers", "Payers", "Patient Advocacy Groups", "All"
    ])

    all_stakeholders = [
        "Patients", "Physicians", "Pharmacists",
        "Caregivers", "Payers", "Patient Advocacy Groups", "All"
    ]

    for tab, stakeholder in zip(stakeholder_tabs, all_stakeholders):
        with tab:
            if stakeholder == "All":
                tab_df = filtered
            else:
                tab_df = filtered[filtered["stakeholder"] == stakeholder]

            if tab_df.empty:
                st.info(f"No posts found for {stakeholder} with current filters.")
                continue

            tc1, tc2 = st.columns(2)

            with tc1:
                # Sentiment for this stakeholder
                s_counts = tab_df["sentiment"].value_counts().reset_index()
                s_counts.columns = ["Sentiment", "Count"]
                fig_s = px.pie(
                    s_counts, names="Sentiment", values="Count",
                    color="Sentiment", color_discrete_map=color_map,
                    title=f"Sentiment — {stakeholder}",
                )
                st.plotly_chart(fig_s, use_container_width=True)

            with tc2:
                # Top themes for this stakeholder
                all_themes = []
                for themes in tab_df["themes"]:
                    if isinstance(themes, list):
                        all_themes.extend(themes)
                theme_counts = Counter(all_themes).most_common(10)
                if theme_counts:
                    theme_df = pd.DataFrame(theme_counts, columns=["Theme", "Count"])
                    fig_t = px.bar(
                        theme_df, x="Count", y="Theme", orientation="h",
                        title=f"Top Themes — {stakeholder}",
                        color="Count", color_continuous_scale="Blues",
                    )
                    fig_t.update_layout(yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig_t, use_container_width=True)

            # Top NER entities
            all_entities = []
            for ents in tab_df["key_entities"]:
                if isinstance(ents, list):
                    all_entities.extend(ents)
            if all_entities:
                ent_counts = Counter(all_entities).most_common(15)
                ent_df = pd.DataFrame(ent_counts, columns=["Entity", "Count"])
                fig_ner = px.bar(
                    ent_df, x="Entity", y="Count",
                    title=f"Key Entities (NER) — {stakeholder}",
                    color="Count", color_continuous_scale="Oranges",
                )
                st.plotly_chart(fig_ner, use_container_width=True)

            # Drugs mentioned
            all_drugs = []
            for drugs in tab_df["drugs_mentioned"]:
                if isinstance(drugs, list):
                    all_drugs.extend(drugs)
            if all_drugs:
                drug_counts = Counter(all_drugs).most_common(10)
                drug_df = pd.DataFrame(drug_counts, columns=["Drug", "Count"])
                fig_drug = px.bar(
                    drug_df, x="Drug", y="Count",
                    title=f"Drugs Mentioned — {stakeholder}",
                    color="Count", color_continuous_scale="Greens",
                )
                st.plotly_chart(fig_drug, use_container_width=True)

            # Representative quotes
            st.markdown(f"**Representative Quotes — {stakeholder}**")
            quotes = tab_df[tab_df["quote"].str.len() > 10]["quote"].head(5).tolist()
            for q in quotes:
                st.markdown(f"> _{q}_")

    st.markdown("---")

    # ── Raw Data Table ────────────────────────────────────────────────────────
    with st.expander("View Raw Analyzed Posts"):
        display_cols = ["subreddit", "stakeholder", "sentiment", "emotion", "summary", "url"]
        st.dataframe(
            filtered[display_cols].reset_index(drop=True),
            use_container_width=True,
            height=400,
        )

if __name__ == "__main__":
    main()
