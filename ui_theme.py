import math

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    --bg-0: #050914;
    --bg-1: #0A1124;
    --bg-2: #0F1B35;
    --bg-3: #182848;
    --border-0: rgba(255, 255, 255, 0.06);
    --border-1: rgba(255, 255, 255, 0.12);
    --border-2: rgba(255, 255, 255, 0.20);
    --border-accent: rgba(0, 210, 255, 0.35);

    --text-0: #F8FAFC;
    --text-1: #94A3B8;
    --text-2: #64748B;
    --text-3: #334155;

    --accent: #00D2FF;
    --accent-glow: rgba(0, 210, 255, 0.15);
    --accent-dim: rgba(0, 210, 255, 0.08);

    --fact: #10B981;
    --fact-dim: rgba(16, 185, 129, 0.12);
    --fact-border: rgba(16, 185, 129, 0.35);

    --hoax: #EF4444;
    --hoax-dim: rgba(239, 68, 68, 0.12);
    --hoax-border: rgba(239, 68, 68, 0.35);

    --warn: #F59E0B;
    --warn-dim: rgba(245, 158, 11, 0.12);
    --warn-border: rgba(245, 158, 11, 0.35);

    --radius-sm: 8px;
    --radius-md: 14px;
    --radius-lg: 20px;
}

*, *::before, *::after {
    box-sizing: border-box;
}

html, body, [class*="css"], [class*="st-"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

#MainMenu, header[data-testid="stHeader"], footer, .stDeployButton, [data-testid="stToolbar"] {
    display: none !important;
    visibility: hidden !important;
}

.main .block-container {
    max-width: 1260px !important;
    padding: 72px 2rem 4rem 2rem !important;
    margin: 0 auto !important;
}

.stApp {
    background-color: var(--bg-0) !important;
    background-image:
        radial-gradient(ellipse 65% 40% at 50% 0%, rgba(0, 210, 255, 0.07) 0%, transparent 70%),
        linear-gradient(rgba(255, 255, 255, 0.015) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.015) 1px, transparent 1px);
    background-size: auto, 50px 50px, 50px 50px;
    min-height: 100vh;
    color: var(--text-0);
}

[data-testid="stSidebar"] {
    background: #070D1E !important;
    border-right: 1px solid var(--border-0) !important;
}
[data-testid="stSidebar"] * {
    color: var(--text-1) !important;
}
[data-testid="stSidebarNav"] {
    display: none !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border-0) !important;
    gap: 8px !important;
    padding: 0 !important;
    margin-bottom: 1.5rem !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-2) !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    padding: 12px 22px !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    transition: all 0.2s ease !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-0) !important;
    background: rgba(255, 255, 255, 0.02) !important;
}

.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
    font-weight: 600 !important;
    background: transparent !important;
}

.stTabs [data-baseweb="tab-panel"] {
    padding: 1rem 0 0 0 !important;
}

.stTextInput > div > div,
.stTextArea > div > div,
.stSelectbox > div > div {
    background: var(--bg-1) !important;
    border: 1px solid var(--border-1) !important;
    border-radius: var(--radius-sm) !important;
    transition: all 0.2s ease !important;
}

.stTextInput > div > div:focus-within,
.stTextArea > div > div:focus-within,
.stSelectbox > div > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(0, 210, 255, 0.12) !important;
}

.stTextInput input, .stTextArea textarea {
    color: var(--text-0) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
}

.stTextInput label, .stTextArea label, .stSelectbox label, .stSlider label {
    color: var(--text-1) !important;
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    margin-bottom: 6px !important;
}

.stButton > button {
    background: linear-gradient(135deg, #0090B0 0%, #00D2FF 100%) !important;
    color: #030814 !important;
    font-weight: 700 !important;
    font-size: 0.86rem !important;
    letter-spacing: 0.02em !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    padding: 12px 24px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 18px rgba(0, 210, 255, 0.25) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 26px rgba(0, 210, 255, 0.4) !important;
}

.stDataFrame > div {
    background: var(--bg-1) !important;
    border: 1px solid var(--border-0) !important;
    border-radius: var(--radius-md) !important;
}

/* Navbar */
.ihnd-navbar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 62px;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2rem;
    background: rgba(5, 9, 20, 0.90);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid var(--border-0);
}

.ihnd-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.ihnd-logo {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 0.85rem;
    color: var(--accent);
    background: rgba(0, 210, 255, 0.1);
    border: 1px solid rgba(0, 210, 255, 0.3);
    padding: 4px 10px;
    border-radius: 6px;
    letter-spacing: 0.05em;
}

.ihnd-brand-title {
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--text-0);
    letter-spacing: -0.01em;
}

.ihnd-nav-tag {
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent);
    background: rgba(0, 210, 255, 0.08);
    border: 1px solid rgba(0, 210, 255, 0.2);
    padding: 4px 12px;
    border-radius: 99px;
}

/* Hero */
.hero-wrapper {
    display: grid;
    grid-template-columns: 1.25fr 0.75fr;
    gap: 3rem;
    align-items: center;
    padding: 2.5rem 0 3.5rem 0;
    min-height: 50vh;
}

@media (max-width: 992px) {
    .hero-wrapper {
        grid-template-columns: 1fr;
        padding: 1.5rem 0 2.5rem 0;
    }
    .hero-visual-card {
        display: none;
    }
}

.hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(0, 210, 255, 0.08);
    border: 1px solid rgba(0, 210, 255, 0.22);
    border-radius: 99px;
    padding: 5px 14px 5px 9px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 1.2rem;
}

.pill-pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 10px rgba(0, 210, 255, 0.8);
    animation: pulse 2.2s infinite ease-in-out;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.35; transform: scale(0.85); }
}

.hero-heading {
    font-size: clamp(2.2rem, 4vw, 3.4rem);
    font-weight: 900;
    line-height: 1.1;
    letter-spacing: -0.03em;
    color: var(--text-0);
    margin-bottom: 1.25rem;
}

.hero-heading span.gradient-text {
    background: linear-gradient(135deg, #00D2FF 0%, #3B82F6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-description {
    font-size: 1.05rem;
    color: var(--text-1);
    line-height: 1.7;
    max-width: 560px;
    margin-bottom: 1.75rem;
}

.hero-tags-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.hero-tech-tag {
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    color: var(--text-1);
    padding: 5px 11px;
    border-radius: 6px;
}

.hero-visual-card {
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-lg);
    padding: 2rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
}

.hvc-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-0);
}

.hvc-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-1);
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.hvc-live {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    color: var(--fact);
    font-weight: 600;
}

.hvc-node-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.hvc-layer-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-0);
    border-radius: var(--radius-sm);
}

.hvc-layer-info {
    display: flex;
    align-items: center;
    gap: 10px;
}

.hvc-icon {
    font-size: 1.1rem;
}

.hvc-name {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-0);
}

.hvc-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.76rem;
    font-weight: 600;
    color: var(--accent);
}

/* Stats */
.stats-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-md);
    margin-bottom: 3rem;
    overflow: hidden;
}

@media (max-width: 768px) {
    .stats-strip {
        grid-template-columns: repeat(2, 1fr);
    }
}

.stat-cell {
    padding: 1.5rem 1.25rem;
    text-align: center;
    border-right: 1px solid var(--border-0);
    transition: background 0.2s ease;
}

.stat-cell:last-child {
    border-right: none;
}

.stat-cell:hover {
    background: var(--bg-2);
}

.stat-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.8rem;
    font-weight: 700;
    line-height: 1.1;
    margin-bottom: 4px;
    color: var(--text-0);
}

.stat-num.fact { color: var(--fact); }
.stat-num.hoax { color: var(--hoax); }
.stat-num.accent { color: var(--accent); }

.stat-label {
    font-size: 0.72rem;
    color: var(--text-1);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
}

/* Section Head */
.section-head {
    margin-bottom: 1.5rem;
}

.section-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 4px;
}

.section-title {
    font-size: clamp(1.4rem, 2.5vw, 1.85rem);
    font-weight: 800;
    color: var(--text-0);
    letter-spacing: -0.02em;
    line-height: 1.2;
}

.section-sub {
    font-size: 0.9rem;
    color: var(--text-1);
    margin-top: 6px;
    line-height: 1.6;
}

/* Verdict Card */
.verdict-card {
    border-radius: var(--radius-lg);
    padding: 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
    border: 1px solid;
    position: relative;
    overflow: hidden;
}

@media (max-width: 768px) {
    .verdict-card {
        flex-direction: column;
        align-items: flex-start;
        gap: 1.5rem;
    }
}

.verdict-card.fact {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(5, 9, 20, 0.8) 100%);
    border-color: var(--fact-border);
    box-shadow: 0 10px 30px rgba(16, 185, 129, 0.08);
}

.verdict-card.hoax {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(5, 9, 20, 0.8) 100%);
    border-color: var(--hoax-border);
    box-shadow: 0 10px 30px rgba(239, 68, 68, 0.08);
}

.verdict-card.warn {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(5, 9, 20, 0.8) 100%);
    border-color: var(--warn-border);
    box-shadow: 0 10px 30px rgba(245, 158, 11, 0.08);
}

.verdict-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-2);
    margin-bottom: 6px;
}

.verdict-badge {
    font-size: clamp(2.2rem, 5vw, 3.2rem);
    font-weight: 900;
    line-height: 1;
    letter-spacing: -0.02em;
}

.verdict-badge.fact { color: var(--fact); }
.verdict-badge.hoax { color: var(--hoax); }
.verdict-badge.warn { color: var(--warn); }

.verdict-summary {
    font-size: 0.95rem;
    color: var(--text-1);
    margin-top: 10px;
    max-width: 600px;
    line-height: 1.6;
}

/* Pipeline */
.pipeline-container {
    display: flex;
    flex-direction: column;
    gap: 0;
}

.pipeline-node {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 14px 16px;
    border-radius: var(--radius-sm);
    background: var(--bg-1);
    border: 1px solid var(--border-0);
    transition: all 0.2s ease;
}

.pipeline-node:hover {
    border-color: var(--border-1);
    background: var(--bg-2);
}

.node-icon-box {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.05rem;
    flex-shrink: 0;
    background: var(--bg-2);
    border: 1px solid var(--border-1);
}

.node-icon-box.fact { background: var(--fact-dim); border-color: var(--fact-border); }
.node-icon-box.hoax { background: var(--hoax-dim); border-color: var(--hoax-border); }
.node-icon-box.accent { background: rgba(0, 210, 255, 0.08); border-color: var(--border-accent); }

.node-content {
    flex: 1;
}

.node-name {
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text-0);
    margin-bottom: 2px;
}

.node-desc {
    font-size: 0.78rem;
    color: var(--text-1);
    line-height: 1.5;
}

.node-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 99px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 6px;
}

.node-badge.fact { background: var(--fact-dim); color: var(--fact); }
.node-badge.hoax { background: var(--hoax-dim); color: var(--hoax); }
.node-badge.accent { background: rgba(0, 210, 255, 0.1); color: var(--accent); }
.node-badge.neutral { background: rgba(255, 255, 255, 0.06); color: var(--text-1); }

.node-connector {
    width: 2px;
    height: 16px;
    background: var(--border-0);
    margin-left: 32px;
}

/* Forensic */
.forensic-box {
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-md);
    overflow: hidden;
}

.forensic-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 18px;
    background: var(--bg-2);
    border-bottom: 1px solid var(--border-0);
}

.forensic-body {
    padding: 18px;
    font-size: 0.88rem;
    line-height: 1.8;
    color: var(--text-1);
    white-space: pre-wrap;
    max-height: 380px;
    overflow-y: auto;
}

/* Score bar */
.sbar-wrapper {
    margin: 10px 0;
}

.sbar-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
}

.sbar-title {
    font-size: 0.82rem;
    color: var(--text-1);
    font-weight: 500;
}

.sbar-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-0);
}

.sbar-track {
    height: 6px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 99px;
    overflow: hidden;
}

.sbar-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.6s ease;
}

.sbar-fill.fact { background: linear-gradient(90deg, #059669, #10B981); }
.sbar-fill.hoax { background: linear-gradient(90deg, #DC2626, #EF4444); }
.sbar-fill.accent { background: linear-gradient(90deg, #0284C7, #00D2FF); }
.sbar-fill.warn { background: linear-gradient(90deg, #D97706, #F59E0B); }

/* Domain Card */
.domain-card {
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    margin-bottom: 10px;
}

.domain-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.84rem;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 10px;
}

/* How It Works Grid */
.hiw-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.25rem;
    margin-top: 1.5rem;
}

@media (max-width: 992px) {
    .hiw-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 576px) {
    .hiw-grid { grid-template-columns: 1fr; }
}

.hiw-step {
    background: var(--bg-1);
    border: 1px solid var(--border-0);
    border-radius: var(--radius-md);
    padding: 1.75rem 1.5rem;
    transition: all 0.2s ease;
}

.hiw-step:hover {
    border-color: var(--border-1);
    background: var(--bg-2);
    transform: translateY(-2px);
}

.hiw-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: 0.1em;
    margin-bottom: 12px;
}

.hiw-icon {
    font-size: 1.6rem;
    margin-bottom: 12px;
}

.hiw-title {
    font-size: 0.98rem;
    font-weight: 700;
    color: var(--text-0);
    margin-bottom: 8px;
}

.hiw-text {
    font-size: 0.82rem;
    color: var(--text-1);
    line-height: 1.6;
}

/* Footer */
.ihnd-footer {
    border-top: 1px solid var(--border-0);
    padding: 3.5rem 0 2rem;
    margin-top: 5rem;
}

.footer-grid {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
    gap: 3rem;
    margin-bottom: 2.5rem;
}

@media (max-width: 768px) {
    .footer-grid {
        grid-template-columns: 1fr;
        gap: 2rem;
    }
}

.footer-brand {
    font-weight: 800;
    font-size: 1rem;
    color: var(--text-0);
    margin-bottom: 8px;
}

.footer-desc {
    font-size: 0.84rem;
    color: var(--text-1);
    line-height: 1.65;
    max-width: 400px;
    margin-bottom: 1.25rem;
}

.footer-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.fbadge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    padding: 3px 8px;
    background: var(--bg-1);
    border: 1px solid var(--border-0);
    border-radius: 4px;
    color: var(--text-1);
}

.footer-col-title {
    font-size: 0.76rem;
    font-weight: 700;
    color: var(--text-0);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 1rem;
}

.footer-item {
    font-size: 0.82rem;
    color: var(--text-1);
    margin-bottom: 8px;
    display: block;
}

.footer-bottom {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border-0);
    font-size: 0.78rem;
    color: var(--text-2);
}
</style>
"""

def render_confidence_ring(conf: float, color: str = "#10B981") -> str:
    radius = 42
    circumference = 2 * math.pi * radius
    dash_offset = circumference * (1.0 - conf)
    percentage = f"{conf * 100:.1f}%"

    return (
        '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;">'
        '<div style="position:relative;width:114px;height:114px;">'
        f'<svg width="114" height="114" viewBox="0 0 114 114" style="transform:rotate(-90deg);">'
        f'<circle cx="57" cy="57" r="{radius}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="9"/>'
        f'<circle cx="57" cy="57" r="{radius}" fill="none" stroke="{color}" stroke-width="9" stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{dash_offset:.2f}" stroke-linecap="round"/>'
        '</svg>'
        '<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;">'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:1.25rem;font-weight:700;color:{color};line-height:1;">{percentage}</span>'
        '<span style="font-size:0.58rem;color:var(--text-2);text-transform:uppercase;letter-spacing:0.1em;margin-top:4px;">Confidence</span>'
        '</div></div></div>'
    )

def render_score_bar(label: str, percent: float, style_class: str, display_value: str) -> str:
    safe_pct = max(0.0, min(100.0, percent))
    return (
        '<div class="sbar-wrapper">'
        '<div class="sbar-header">'
        f'<span class="sbar-title">{label}</span>'
        f'<span class="sbar-value">{display_value}</span>'
        '</div>'
        '<div class="sbar-track">'
        f'<div class="sbar-fill {style_class}" style="width:{safe_pct:.1f}%;"></div>'
        '</div></div>'
    )

def render_step_progress(active_index: int, completed_count: int) -> str:
    steps = [
        ("01", "Preprocessing", "🔧"),
        ("02", "IndoBERT", "🧠"),
        ("03", "Classifiers", "📊"),
        ("04", "GPT-3.5", "🤖"),
        ("05", "Domain Cred", "🌐"),
        ("06", "Consensus", "⚖️"),
    ]

    items_html = ""
    for i, (num, name, icon) in enumerate(steps):
        is_done = i < completed_count
        is_active = i == active_index

        if is_done:
            dot_content = "✓"
            dot_style = "background: rgba(0, 210, 255, 0.15); border-color: #00D2FF; color: #00D2FF;"
            text_color = "color: #F8FAFC;"
        elif is_active:
            dot_content = icon
            dot_style = "background: rgba(0, 210, 255, 0.25); border-color: #00D2FF; color: #FFFFFF; box-shadow: 0 0 15px rgba(0, 210, 255, 0.5);"
            text_color = "color: #00D2FF; font-weight: 700;"
        else:
            dot_content = icon
            dot_style = "background: rgba(255, 255, 255, 0.04); border-color: rgba(255, 255, 255, 0.1); color: #64748B;"
            text_color = "color: #64748B;"

        items_html += (
            '<div style="flex:1;display:flex;flex-direction:column;align-items:center;text-align:center;">'
            f'<div style="width:36px;height:36px;border-radius:50%;border:1px solid;display:flex;align-items:center;justify-content:center;font-size:0.85rem;margin-bottom:6px;{dot_style}">'
            f'{dot_content}</div>'
            f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.04em;{text_color}">'
            f'{name}</div></div>'
        )

    html = (
        '<div style="background:var(--bg-1);border:1px solid var(--border-0);border-radius:12px;padding:1.25rem 1.5rem;margin:1.5rem 0;">'
        '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:var(--text-2);margin-bottom:1rem;">'
        'Analysis Pipeline Execution</div>'
        '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">'
        f'{items_html}'
        '</div></div>'
    )
    return html
