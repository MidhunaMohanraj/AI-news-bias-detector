# 📰 AI News Aggregator + Bias Detector

<div align="center">

![Banner](https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=2,8,16&height=200&section=header&text=AI%20News%20Bias%20Detector&fontSize=46&fontColor=fff&animation=twinkling&fontAlignY=35&desc=15%20Sources%20%E2%80%A2%20Live%20RSS%20%E2%80%A2%20Gemini%20Bias%20Analysis%20%E2%80%A2%20Story%20Clusters%20%E2%80%A2%20Free%20API&descAlignY=55&descSize=14)

<p>
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Streamlit-1.35-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
  <img src="https://img.shields.io/badge/Gemini%201.5%20Flash-Free%20API-4285F4?style=for-the-badge&logo=google&logoColor=white"/>
  <img src="https://img.shields.io/badge/15%20News%20Sources-Live%20RSS-22C55E?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/AllSides-Rated-f59e0b?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge"/>
</p>

<p>
  <b>Fetch live news from 15 sources across the political spectrum → Gemini AI detects bias, tone, loaded language, and credibility → Compare how the same story is covered differently across sources.</b>
</p>

</div>

---

## 🌟 Why This Project?

Most people read news from one or two sources and don't realise how much framing shapes their understanding. This tool makes the invisible visible:

```
Story: "Senate passes new AI regulation bill"

📻 NPR (Center-Left):
  Detected bias: center-left | Tone: analytical
  Framing: "Consumer protection milestone"
  Loaded words: ["crucial", "long-overdue"]

🦊 Fox News (Right):
  Detected bias: right | Tone: concern
  Framing: "Government overreach threatens innovation"
  Loaded words: ["radical", "bureaucrats", "stifles"]

🌐 Reuters (Center):
  Detected bias: center | Tone: neutral
  Framing: "Legislative development with mixed industry reaction"
  Loaded words: []  ← clean
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 📡 **15 Live RSS Sources** | NPR, Guardian, BBC, Reuters, AP, Fox News, WSJ, Al Jazeera, and more |
| 🎯 **Political Bias Detection** | Left / Center-Left / Center / Center-Right / Right with confidence % |
| 🌡️ **Tone Analysis** | Neutral / Sensational / Fear / Anger / Hope / Concern |
| ⚡ **Loaded Language** | Identifies emotionally charged words used to frame stories |
| 📊 **Fact vs Opinion Ratio** | % of factual claims vs editorial opinion |
| ⭐ **Credibility Score** | 0-100 credibility rating per article |
| 🔄 **Neutral Rewrite** | AI rewrites each headline in neutral language |
| 🚩 **Issue Flags** | Detects: clickbait, opinion-as-fact, missing sources, false balance |
| 📌 **Story Clusters** | Groups same story across sources — shows consensus vs divergence |
| 🔥 **Tone×Bias Heatmap** | Which political sides use which emotional tones |
| 📥 **JSON Export** | Download full analysis report |

---

## 🖥️ Demo

```
📰 AI News Bias Detector
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Fetched 47 articles from 8 sources
✅ Analysed 20 articles with Gemini AI

📊 Bias Distribution:
  Left: ██████ 6      Center-Left: ████████ 8
  Center: ████████████ 12     Center-Right: ████ 4
  Right: ██████ 6

📌 Story Cluster: "Federal AI Regulation"
  Sources: NPR | BBC | Fox News | WSJ | Al Jazeera
  ✅ Consensus: Bill passed 68-32 with bipartisan support
  ⚡ Divergence: NPR emphasises consumer protections;
                Fox News leads with "innovation concerns"
  🔇 Missing: Progressive / tech-worker perspective
```

---

## 📦 Installation

```bash
git clone https://github.com/YOUR_USERNAME/ai-news-bias-detector.git
cd ai-news-bias-detector
pip install -r requirements.txt
streamlit run app.py
```

---

## 📡 News Sources (15 total)

| Source | AllSides Rating | Category |
|---|---|---|
| HuffPost | Left | US News |
| Vox | Left | US News |
| NPR | Center-Left | US News |
| The Guardian | Center-Left | International |
| TechCrunch | Center-Left | Technology |
| Al Jazeera | Center-Left | International |
| AP News | Center | Wire Service |
| Reuters | Center | Wire Service |
| BBC News | Center | International |
| CS Monitor | Center | US News |
| Wall Street Journal | Center-Right | Business |
| NY Post | Right | US News |
| Fox News | Right | US News |
| Daily Wire | Right | US News |
| Ars Technica | Center | Technology |

---

## 🧠 How It Works

```
┌────────────────────────────────────────────────────┐
│  feedparser fetches RSS from 15 sources            │
└──────────────────────────┬─────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────┐
│  Article cleaning: strip HTML, truncate, dedup     │
└──────────────────────────┬─────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────┐
│  Gemini 1.5 Flash — per article (temp=0.1)         │
│  → detected_bias + bias_confidence                 │
│  → tone + tone_confidence                          │
│  → fact_ratio (% factual vs opinion)               │
│  → loaded_words (emotionally charged language)     │
│  → framing (how story is being presented)          │
│  → missing_context (what's notably absent)         │
│  → headline_bias (specific headline analysis)      │
│  → credibility_score (0-100)                       │
│  → summary_neutral (neutral headline rewrite)      │
│  → flags (clickbait / opinion-as-fact / etc.)      │
└──────────────────────────┬─────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────┐
│  Story Clustering — Gemini groups articles         │
│  by topic, identifies consensus vs divergence      │
└──────────────────────────┬─────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────┐
│  Streamlit Dashboard — 5 analysis tabs             │
└────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ai-news-bias-detector/
├── app.py                    # 🖥️ Streamlit dashboard
├── src/
│   └── news_engine.py        # 🧠 RSS fetcher + Gemini bias engine
├── requirements.txt          # 📦 6 dependencies
├── README.md
└── LICENSE
```

---

## 🗺️ Roadmap

- [ ] URL input — paste any article URL for instant analysis
- [ ] Historical tracking — track bias trends over time
- [ ] Browser extension version
- [ ] Email digest of balanced daily news
- [ ] Search across all fetched articles
- [ ] Side-by-side article comparison view

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

**⭐ Star this repo if you find it useful!**

*Read more. Read widely. Question framing.*

![Footer](https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=2,8,16&height=100&section=footer)

</div>
