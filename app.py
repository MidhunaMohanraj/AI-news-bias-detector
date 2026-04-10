"""
app.py — AI News Aggregator + Bias Detector Dashboard
"""

import sys
import json
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).parent / "src"))
from news_engine import (
    NEWS_SOURCES, ALLSIDES_ORDER, BIAS_COLORS, TONE_COLORS,
    fetch_multiple_sources, analyse_batch, cluster_stories,
    bias_spectrum_summary, NewsArticle, BiasAnalysis,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI News Bias Detector",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@1,700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .main { background: #070810; }

  .hero {
    background: linear-gradient(135deg, #07080f 0%, #0a0c1a 60%, #07080f 100%);
    border: 1px solid #1a2030;
    border-radius: 16px;
    padding: 34px 40px;
    text-align: center;
    margin-bottom: 24px;
  }
  .hero h1 { font-size: 38px; font-weight: 700; color: #fff; margin: 0 0 6px; }
  .hero p  { color: #64748b; font-size: 14px; margin: 0; }

  .article-card {
    background: #0b0d18;
    border: 1px solid #1e2040;
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
  }
  .article-title { font-size: 14px; font-weight: 600; color: #e2e8f0; line-height: 1.5; margin-bottom: 6px; }
  .article-neutral { font-size: 12px; color: #64748b; font-style: italic; margin-bottom: 8px; }
  .article-meta { font-size: 11px; color: #475569; display: flex; gap: 12px; flex-wrap: wrap; }

  .bias-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  .flag-chip {
    display: inline-block;
    background: #1a1a2e;
    border: 1px solid #2a2a50;
    color: #f87171;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    margin: 2px;
  }
  .loaded-word {
    display: inline-block;
    background: #1a0f00;
    border: 1px solid #78350f;
    color: #fcd34d;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    margin: 2px;
  }
  .stat-card {
    background: #0b0d18;
    border: 1px solid #1e2040;
    border-radius: 10px;
    padding: 14px;
    text-align: center;
  }
  .stat-val   { font-size: 24px; font-weight: 700; }
  .stat-label { font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 3px; }

  .cluster-card {
    background: #080a14;
    border: 1px solid #1e2040;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 14px;
  }
  .cluster-topic { font-size: 16px; font-weight: 700; color: #e2e8f0; margin-bottom: 8px; }

  .spectrum-bar {
    height: 14px;
    border-radius: 7px;
    margin: 4px 0;
  }

  div.stButton > button {
    background: linear-gradient(135deg, #1e3a8a, #3b82f6);
    color: white;
    font-weight: 700;
    border: none;
    border-radius: 10px;
    padding: 12px 28px;
    font-size: 15px;
    width: 100%;
  }
  div.stButton > button:hover { opacity: 0.85; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📰 News Bias Detector")
    st.markdown("---")

    st.markdown("### 🔑 Gemini API Key")
    api_key = st.text_input("Free Gemini API Key", type="password", placeholder="AIza...")
    if not api_key:
        st.info("🆓 Free at [aistudio.google.com](https://aistudio.google.com)")

    st.markdown("---")
    st.markdown("### 📡 News Sources")
    st.caption("Select sources to fetch from:")

    # Group by bias
    left_sources    = {k: v for k, v in NEWS_SOURCES.items() if v["allsides"] in ("left", "center-left")}
    center_sources  = {k: v for k, v in NEWS_SOURCES.items() if v["allsides"] == "center"}
    right_sources   = {k: v for k, v in NEWS_SOURCES.items() if v["allsides"] in ("right", "center-right")}
    other_sources   = {k: v for k, v in NEWS_SOURCES.items() if k in ("techcrunch", "ars", "aljazeera")}

    selected_sources = []

    st.markdown("🔵 **Left / Center-Left**")
    for k, v in left_sources.items():
        if st.checkbox(f"{v['emoji']} {v['name']}", value=k in ("npr", "guardian"), key=f"src_{k}"):
            selected_sources.append(k)

    st.markdown("🟢 **Center**")
    for k, v in center_sources.items():
        if st.checkbox(f"{v['emoji']} {v['name']}", value=k in ("reuters", "bbc", "ap"), key=f"src_{k}"):
            selected_sources.append(k)

    st.markdown("🔴 **Right / Center-Right**")
    for k, v in right_sources.items():
        if st.checkbox(f"{v['emoji']} {v['name']}", value=k in ("wsj", "foxnews"), key=f"src_{k}"):
            selected_sources.append(k)

    st.markdown("🌐 **International / Tech**")
    for k, v in other_sources.items():
        if st.checkbox(f"{v['emoji']} {v['name']}", value=k in ("aljazeera",), key=f"src_{k}"):
            selected_sources.append(k)

    st.markdown("---")
    max_articles = st.slider("Articles per source", 3, 10, 5)
    max_analyse  = st.slider("Max articles to analyse", 5, 30, 15,
                              help="Each analysis uses one Gemini API call")
    show_clusters = st.checkbox("Show story clusters", value=True)
    fetch_clicked = st.button("🔍 Fetch & Analyse News")

# ── Main UI ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>📰 AI News Aggregator + Bias Detector</h1>
  <p>Fetch live news from 15 sources across the political spectrum · Detect bias, tone, loaded language & credibility with Gemini AI</p>
</div>
""", unsafe_allow_html=True)

# ── Bias spectrum legend ───────────────────────────────────────────────────────
legend_cols = st.columns(5)
for col, bias in zip(legend_cols, ALLSIDES_ORDER):
    color = BIAS_COLORS[bias]
    with col:
        st.markdown(
            f'<div style="text-align:center;background:{color}22;border:1px solid {color}44;'
            f'border-radius:8px;padding:6px 4px;">'
            f'<div style="font-size:11px;font-weight:700;color:{color};letter-spacing:1px;">'
            f'{bias.upper()}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Fetch & Analyse ────────────────────────────────────────────────────────────
if fetch_clicked:
    if not selected_sources:
        st.warning("⚠️ Please select at least one news source in the sidebar.")
        st.stop()
    if not api_key:
        st.error("⚠️ Please add your free Gemini API key in the sidebar.")
        st.stop()

    # Fetch RSS
    progress_bar = st.progress(0, text="Fetching news...")
    articles: list[NewsArticle] = []

    def on_fetch(done, total, name, count):
        progress_bar.progress(done / total, text=f"Fetching {name}... ({count} articles)")

    with st.spinner("📡 Fetching news from selected sources..."):
        articles = fetch_multiple_sources(selected_sources, max_articles, on_fetch)

    progress_bar.empty()
    st.success(f"✅ Fetched {len(articles)} articles from {len(selected_sources)} sources")

    if not articles:
        st.error("No articles fetched. Check your internet connection or try different sources.")
        st.stop()

    # Analyse bias
    analyses: list[BiasAnalysis] = []
    analysis_progress = st.progress(0, text="Analysing bias...")

    def on_analyse(done, total, title):
        analysis_progress.progress(done / total, text=f"Analysing: {title}...")

    with st.spinner("🤖 Gemini AI analysing bias and tone..."):
        analyses = analyse_batch(articles, api_key, on_analyse, max_analyse)

    analysis_progress.empty()
    st.success(f"✅ Analysed {len(analyses)} articles")

    # Store in session
    st.session_state["articles"]  = articles
    st.session_state["analyses"]  = analyses
    st.session_state["api_key"]   = api_key
    st.session_state["show_clusters"] = show_clusters

# ── Display results ────────────────────────────────────────────────────────────
articles  = st.session_state.get("articles",  [])
analyses  = st.session_state.get("analyses",  [])
s_api_key = st.session_state.get("api_key",   api_key)
s_clusters = st.session_state.get("show_clusters", True)

if articles and analyses:
    summary = bias_spectrum_summary(analyses)
    art_map  = {a.id: a for a in articles}

    # ── KPI row ────────────────────────────────────────────────────────────────
    k1,k2,k3,k4,k5 = st.columns(5)
    kpis = [
        (len(articles),                 "Articles Fetched",   "#60a5fa"),
        (len(analyses),                 "Articles Analysed",  "#a78bfa"),
        (f"{summary['avg_credibility']}/100", "Avg Credibility", "#22c55e"),
        (f"{summary['avg_fact_ratio']}%",     "Avg Fact Ratio",  "#f59e0b"),
        (len(selected_sources),         "Sources Used",       "#94a3b8"),
    ]
    for col, (val, label, color) in zip([k1,k2,k3,k4,k5], kpis):
        with col:
            st.markdown(f'<div class="stat-card"><div class="stat-val" style="color:{color};">{val}</div><div class="stat-label">{label}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Bias Overview", "📰 Article Feed", "🔍 Story Clusters", "🌡️ Tone Analysis", "📋 Full Data"
    ])

    with tab1:
        st.markdown("### 📊 Bias Distribution Across All Articles")
        col_pie, col_bar = st.columns([1, 1])

        with col_pie:
            dist = summary["bias_distribution"]
            labels  = [b for b in ALLSIDES_ORDER if dist.get(b, 0) > 0]
            values  = [dist.get(b, 0) for b in labels]
            colors  = [BIAS_COLORS[b] for b in labels]
            fig_pie = go.Figure(go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors),
                hole=0.45,
                textinfo="label+percent",
            ))
            fig_pie.update_layout(
                paper_bgcolor="#07080f", plot_bgcolor="#07080f",
                font_color="#94a3b8", height=320,
                showlegend=False, margin=dict(t=20,b=10,l=10,r=10),
                title="Bias Distribution",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            # Bias by source
            source_bias = {}
            for a in analyses:
                art = next((x for x in articles if x.source_name == a.source), None)
                if art:
                    source_bias.setdefault(a.source, []).append(a.detected_bias)

            source_avg = []
            for source, biases in source_bias.items():
                avg_idx = sum(ALLSIDES_ORDER.index(b) for b in biases if b in ALLSIDES_ORDER) / max(len(biases), 1)
                source_avg.append({"source": source, "bias_score": avg_idx, "count": len(biases)})

            source_avg.sort(key=lambda x: x["bias_score"])
            sdf = pd.DataFrame(source_avg)
            fig_src = go.Figure(go.Bar(
                x=sdf["source"],
                y=sdf["bias_score"],
                marker_color=[BIAS_COLORS[ALLSIDES_ORDER[min(4, max(0, round(s)))]] for s in sdf["bias_score"]],
                text=sdf["count"].astype(str) + " articles",
                textposition="outside",
            ))
            fig_src.add_hline(y=2, line_dash="dot", line_color="#22c55e", opacity=0.5, annotation_text="Center")
            fig_src.update_layout(
                paper_bgcolor="#07080f", plot_bgcolor="#07080f",
                font_color="#94a3b8", height=320,
                yaxis=dict(title="← Left    Center    Right →", range=[-0.5, 4.5], gridcolor="#1e2040",
                           tickvals=[0,1,2,3,4], ticktext=ALLSIDES_ORDER),
                xaxis=dict(gridcolor="#1e2040"),
                margin=dict(t=20,b=20,l=10,r=10),
                title="Average Bias by Source",
            )
            st.plotly_chart(fig_src, use_container_width=True)

        # Top loaded words
        st.markdown("### ⚡ Most Common Loaded Language")
        if summary["top_loaded_words"]:
            word_df = pd.DataFrame(summary["top_loaded_words"], columns=["word", "count"])
            fig_words = go.Figure(go.Bar(
                x=word_df["word"], y=word_df["count"],
                marker_color="#f97316", opacity=0.8,
            ))
            fig_words.update_layout(
                paper_bgcolor="#07080f", plot_bgcolor="#07080f",
                font_color="#94a3b8", height=250,
                yaxis=dict(title="Frequency", gridcolor="#1e2040"),
                xaxis=dict(gridcolor="#1e2040"),
                margin=dict(t=10,b=20,l=10,r=10),
            )
            st.plotly_chart(fig_words, use_container_width=True)

        # Flag distribution
        st.markdown("### 🚩 Issue Flags Detected")
        flag_dist = summary.get("flag_distribution", {})
        if flag_dist:
            fl_cols = st.columns(len(flag_dist))
            for col, (flag, count) in zip(fl_cols, sorted(flag_dist.items(), key=lambda x: -x[1])):
                with col:
                    st.markdown(f'<div class="stat-card"><div class="stat-val" style="color:#f87171;font-size:20px;">{count}</div><div class="stat-label">{flag.replace("-"," ")}</div></div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("### 📰 Article Feed with Bias Analysis")

        # Filters
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            filter_bias = st.multiselect("Filter by bias", ALLSIDES_ORDER, default=ALLSIDES_ORDER)
        with fc2:
            filter_source = st.multiselect("Filter by source",
                                           sorted(set(a.source for a in analyses)),
                                           default=sorted(set(a.source for a in analyses)))
        with fc3:
            sort_by = st.selectbox("Sort by", ["Credibility ↑", "Credibility ↓", "Bias (left→right)", "Source"])

        # Sort
        sorted_analyses = list(analyses)
        if sort_by == "Credibility ↑":
            sorted_analyses.sort(key=lambda x: x.credibility_score)
        elif sort_by == "Credibility ↓":
            sorted_analyses.sort(key=lambda x: -x.credibility_score)
        elif sort_by == "Bias (left→right)":
            sorted_analyses.sort(key=lambda x: ALLSIDES_ORDER.index(x.detected_bias) if x.detected_bias in ALLSIDES_ORDER else 2)
        else:
            sorted_analyses.sort(key=lambda x: x.source)

        # Filter
        filtered = [a for a in sorted_analyses
                    if a.detected_bias in filter_bias and a.source in filter_source]

        for analysis in filtered:
            art = art_map.get(analysis.article_id)
            if not art:
                continue

            bias_color = BIAS_COLORS.get(analysis.detected_bias, "#94a3b8")
            tone_color = TONE_COLORS.get(analysis.tone, "#94a3b8")
            cred_color = "#22c55e" if analysis.credibility_score >= 70 else ("#f59e0b" if analysis.credibility_score >= 50 else "#ef4444")

            flags_html = "".join([f'<span class="flag-chip">{f}</span>' for f in analysis.flags])
            loaded_html = "".join([f'<span class="loaded-word">{w}</span>' for w in analysis.loaded_words[:5]])

            st.markdown(f"""
<div class="article-card" style="border-left:3px solid {bias_color};">
  <div class="article-title">📰 {analysis.title}</div>
  <div class="article-neutral">🔄 Neutral: {analysis.summary_neutral}</div>
  <div class="article-meta">
    <span><b>{analysis.source}</b></span>
    <span class="bias-pill" style="background:{bias_color}22;color:{bias_color};border:1px solid {bias_color}44;">{analysis.detected_bias.upper()}</span>
    <span style="color:{tone_color};">🌡️ {analysis.tone}</span>
    <span style="color:{cred_color};">⭐ {analysis.credibility_score}/100</span>
    <span style="color:#64748b;">📊 {analysis.fact_ratio}% factual</span>
    {'<a href="' + art.url + '" target="_blank" style="color:#60a5fa;font-size:11px;">🔗 Read</a>' if art.url else ''}
  </div>
  {('<div style="margin-top:8px;">' + flags_html + '</div>') if analysis.flags else ''}
  {('<div style="margin-top:6px;">' + loaded_html + '</div>') if analysis.loaded_words else ''}
  <div style="margin-top:8px;font-size:12px;color:#475569;line-height:1.5;">
    <b>Framing:</b> {analysis.framing}<br>
    <b>Missing context:</b> {analysis.missing_context}
  </div>
</div>
""", unsafe_allow_html=True)

    with tab3:
        st.markdown("### 🔍 Story Clusters — Same Story, Different Spins")
        st.caption("Groups of articles covering the same event from different political perspectives")

        if s_clusters and s_api_key:
            if "clusters" not in st.session_state:
                with st.spinner("🤖 Clustering stories across sources..."):
                    clusters = cluster_stories(articles, analyses, s_api_key)
                    st.session_state["clusters"] = clusters
            else:
                clusters = st.session_state["clusters"]

            if not clusters:
                st.info("Not enough articles from multiple sources on the same topic yet. Try selecting more sources.")
            else:
                for cluster in clusters:
                    bias_bar_html = ""
                    for art in cluster.articles:
                        color = BIAS_COLORS.get(art.allsides, "#94a3b8")
                        bias_bar_html += f'<span class="bias-pill" style="background:{color}22;color:{color};border:1px solid {color}44;margin:2px;">{art.source_name}</span>'

                    st.markdown(f"""
<div class="cluster-card">
  <div class="cluster-topic">📌 {cluster.topic}</div>
  <div style="margin-bottom:10px;">{bias_bar_html}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:10px;">
    <div style="background:#050a05;border:1px solid #14532d;border-radius:8px;padding:10px 12px;">
      <div style="font-size:10px;color:#16a34a;font-weight:700;letter-spacing:2px;margin-bottom:4px;">✅ CONSENSUS</div>
      <div style="font-size:12px;color:#86efac;line-height:1.5;">{cluster.consensus}</div>
    </div>
    <div style="background:#0f0500;border:1px solid #92400e;border-radius:8px;padding:10px 12px;">
      <div style="font-size:10px;color:#d97706;font-weight:700;letter-spacing:2px;margin-bottom:4px;">⚡ DIVERGENCE</div>
      <div style="font-size:12px;color:#fcd34d;line-height:1.5;">{cluster.divergence}</div>
    </div>
    <div style="background:#0a0510;border:1px solid #4c1d95;border-radius:8px;padding:10px 12px;">
      <div style="font-size:10px;color:#7c3aed;font-weight:700;letter-spacing:2px;margin-bottom:4px;">🔇 MISSING VOICE</div>
      <div style="font-size:12px;color:#c4b5fd;line-height:1.5;">{cluster.missing_voice}</div>
    </div>
  </div>
  <div style="margin-top:12px;">
""", unsafe_allow_html=True)
                    for art in cluster.articles:
                        analysis = next((a for a in cluster.analyses if a.article_id == art.id), None)
                        if analysis:
                            bc = BIAS_COLORS.get(analysis.detected_bias, "#94a3b8")
                            st.markdown(f"""
<div style="background:#080a14;border:1px solid #1e2040;border-radius:6px;padding:8px 12px;margin:4px 0;display:flex;justify-content:space-between;align-items:center;">
  <span style="font-size:12px;color:#cbd5e1;">{art.source_name}: {art.title[:70]}{'...' if len(art.title)>70 else ''}</span>
  <span class="bias-pill" style="background:{bc}22;color:{bc};border:1px solid {bc}44;white-space:nowrap;">{analysis.detected_bias}</span>
</div>""", unsafe_allow_html=True)
                    st.markdown("</div></div>", unsafe_allow_html=True)
        else:
            st.info("Story clustering requires a Gemini API key and the 'Show story clusters' option enabled.")

    with tab4:
        st.markdown("### 🌡️ Tone Analysis")
        tone_dist = summary.get("tone_distribution", {})

        if tone_dist:
            t_labels = list(tone_dist.keys())
            t_values = list(tone_dist.values())
            t_colors = [TONE_COLORS.get(t, "#94a3b8") for t in t_labels]

            fig_tone = go.Figure(go.Bar(
                x=t_labels, y=t_values,
                marker_color=t_colors,
                opacity=0.85,
                text=t_values,
                textposition="outside",
            ))
            fig_tone.update_layout(
                paper_bgcolor="#07080f", plot_bgcolor="#07080f",
                font_color="#94a3b8", height=300,
                yaxis=dict(title="Articles", gridcolor="#1e2040"),
                xaxis=dict(gridcolor="#1e2040"),
                margin=dict(t=20,b=20,l=10,r=10),
                title="Emotional Tone Distribution",
            )
            st.plotly_chart(fig_tone, use_container_width=True)

        # Tone vs bias heatmap
        st.markdown("### 🔥 Tone vs Bias Heatmap")
        heatmap_data = {}
        for a in analyses:
            key = (a.detected_bias, a.tone)
            heatmap_data[key] = heatmap_data.get(key, 0) + 1

        biases_present = [b for b in ALLSIDES_ORDER if any(b == k[0] for k in heatmap_data)]
        tones_present  = list(set(k[1] for k in heatmap_data))

        z = [[heatmap_data.get((b, t), 0) for b in biases_present] for t in tones_present]

        fig_heat = go.Figure(go.Heatmap(
            z=z, x=biases_present, y=tones_present,
            colorscale="Plasma",
            text=[[str(v) if v > 0 else "" for v in row] for row in z],
            texttemplate="%{text}",
        ))
        fig_heat.update_layout(
            paper_bgcolor="#07080f", plot_bgcolor="#07080f",
            font_color="#94a3b8", height=300,
            margin=dict(t=20,b=20,l=10,r=10),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with tab5:
        st.markdown("### 📋 Full Results")
        df = pd.DataFrame([
            {
                "Source": a.source,
                "Headline": a.title[:60] + "...",
                "Bias": a.detected_bias,
                "Confidence": f"{a.bias_confidence}%",
                "Tone": a.tone,
                "Credibility": a.credibility_score,
                "Fact%": f"{a.fact_ratio}%",
                "Flags": ", ".join(a.flags) if a.flags else "—",
                "Loaded Words": ", ".join(a.loaded_words[:3]) if a.loaded_words else "—",
            }
            for a in analyses
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

        export_data = {
            "fetched_at":  str(__import__("datetime").datetime.now()),
            "sources":     selected_sources,
            "summary":     summary,
            "articles":    [asdict(a) for a in articles],
            "analyses":    [asdict(a) for a in analyses],
        }
        st.download_button(
            "⬇️ Download Full Report (.json)",
            data=json.dumps(export_data, indent=2, default=str),
            file_name="news_bias_report.json",
            mime="application/json",
        )

else:
    st.markdown("""
<div style="text-align:center;padding:50px 20px;">
  <div style="font-size:72px;margin-bottom:16px;">📰</div>
  <h3 style="color:#475569;">Select sources in the sidebar and click Fetch & Analyse</h3>
  <p style="color:#334155;font-size:14px;max-width:540px;margin:0 auto;">
    Fetches live news from across the political spectrum, then uses Gemini AI
    to detect bias, tone, loaded language, and credibility — showing you how the
    same story looks from different political perspectives.
  </p>
</div>
""", unsafe_allow_html=True)
