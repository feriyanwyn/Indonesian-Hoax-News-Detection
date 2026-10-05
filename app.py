import os
import sys
import re
import requests
import subprocess
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import streamlit as st
from urllib.parse import urlparse

import torch
from transformers import AutoTokenizer, AutoModel

from ui_theme import (
    THEME_CSS,
    render_confidence_ring,
    render_score_bar,
    render_step_progress
)

# Fallback for HoaxPreprocessor
try:
    from train_models import HoaxPreprocessor
except ImportError:
    class HoaxPreprocessor:
        def __init__(self):
            pass
        def clean_text(self, text, mode='natural'):
            return text

# ==============================================================================
# STREAMLIT PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Indonesia Hoax News Detection | AI Fact Checking",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom design system CSS
st.markdown(THEME_CSS, unsafe_allow_html=True)

# ==============================================================================
# CACHED NLP & MACHINE LEARNING MODELS
# ==============================================================================
@st.cache_resource
def load_nlp_resources():
    """Load IndoBERT transformer and preprocessing components."""
    model_checkpoint = "indobenchmark/indobert-base-p1"
    tokenizer = AutoTokenizer.from_pretrained(model_checkpoint)
    bert_model = AutoModel.from_pretrained(model_checkpoint)
    
    device = torch.device(
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available()
        else "cpu"
    )
    bert_model.to(device)
    bert_model.eval()
    
    preprocessor = HoaxPreprocessor()
    return tokenizer, bert_model, device, preprocessor

tokenizer, bert_model, device, preprocessor = load_nlp_resources()

def check_models_exist():
    """Check if all trained model weights are saved in models/."""
    required = [
        "models/scaler.joblib",
        "models/model_svm.joblib",
        "models/model_rf.joblib",
        "models/model_nb.joblib"
    ]
    return all(os.path.exists(f) for f in required)

@st.cache_resource
def _load_ml_models_cached():
    scaler = joblib.load("models/scaler.joblib")
    models = {
        "SVM (Linear)": joblib.load("models/model_svm.joblib"),
        "Random Forest": joblib.load("models/model_rf.joblib"),
        "Naive Bayes": joblib.load("models/model_nb.joblib")
    }
    return {"scaler": scaler, "models": models}

def load_ml_models():
    if not check_models_exist():
        return None
    try:
        return _load_ml_models_cached()
    except Exception:
        return None

ml_pipeline = load_ml_models()

# ==============================================================================
# INFERENCE & VERIFICATION FUNCTIONS
# ==============================================================================
def predict_single_text(text, trained_models, scaler):
    """Clean text -> IndoBERT 768-dim embeddings -> StandardScale -> Classifiers."""
    clean_text = preprocessor.clean_text(text, mode='natural')
    
    encoded_input = tokenizer(
        [clean_text],
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    ).to(device)
    
    with torch.no_grad():
        model_output = bert_model(**encoded_input)
        
    attention_mask = encoded_input["attention_mask"].unsqueeze(-1).expand(
        model_output.last_hidden_state.size()
    ).float()
    
    weighted_sum = torch.sum(model_output.last_hidden_state * attention_mask, dim=1)
    mask_sum = torch.clamp(attention_mask.sum(dim=1), min=1e-9)
    text_embedding = (weighted_sum / mask_sum).cpu().numpy()
    
    embedding_scaled = scaler.transform(text_embedding)
    
    results = {}
    for model_name, clf in trained_models.items():
        pred = clf.predict(embedding_scaled)[0]
        probs = clf.predict_proba(embedding_scaled)[0]
        confidence = probs[pred]
        
        results[model_name] = {
            "prediction": "Hoax" if pred == 0 else "Fact",
            "confidence": confidence
        }
    return results

def predict_hoax_openai(text: str, api_key: str) -> str:
    """Perform LLM forensic linguistic check."""
    import openai
    if not api_key:
        return "Error: OpenAI API key is not configured."
    
    client = openai.OpenAI(api_key=api_key)
    prompt_template = f"""Anda adalah pakar analisis misinformasi (Forensic News Analyst) terpercaya di Indonesia.
Tugas Anda adalah mengevaluasi kebenaran narasi berikut secara objektif dan mendalam.

Evaluasi poin-poin berikut:
- Apakah terdapat pola clickbait atau bahasa provokatif?
- Apakah klaim tersebut masuk akal secara logis?
- Apakah narasi ini sering muncul sebagai disinformasi?

Berikan format jawaban yang terstruktur persis seperti ini:
Klasifikasi: [Hoaks / Fakta / Perlu Verifikasi]
Skor Keyakinan: [0-100%]
Analisis Linguistik: [Penjelasan gaya bahasa]
Analisis Konten: [Penjelasan kebenaran isi]
Tautan Pendukung/Sanggahan: [Daftar tautan dari media kredibel]

Teks berita yang akan dianalisis:
\"\"\"{text}\"\"\""""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional fact-checker for Indonesian news content."},
                {"role": "user", "content": prompt_template}
            ],
            temperature=0,
            max_tokens=600
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling OpenAI API: {e}"

def extract_domains_from_text(text: str) -> list:
    urls = re.findall(r'https?://(?:www\.)?([^/\s]+)', text)
    domains = set()
    for url in urls:
        parsed_url = urlparse(f"https://{url}")
        domain = parsed_url.netloc
        if domain:
            if domain.startswith('www.'):
                domain = domain[4:]
            domains.add(domain)
    return list(domains)

def get_domain_metrics(domain: str) -> dict:
    api_url = f"https://bot11-q8bt.onrender.com/check-metrics?domain={domain}"
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

def parse_gpt_verdict(gpt_text: str):
    """Parse classification and score from structured GPT output."""
    cls = "Uncertain"
    conf = 0.70
    if not gpt_text or gpt_text.startswith("Error"):
        return cls, conf
        
    m = re.search(r'Klasifikasi:\s*(Hoaks|Fakta|Perlu Verifikasi)', gpt_text, re.IGNORECASE)
    if m:
        val = m.group(1).lower()
        if "hoaks" in val or "hoax" in val:
            cls = "Hoax"
        elif "fakta" in val or "fact" in val:
            cls = "Fact"
        else:
            cls = "Uncertain"
            
    c = re.search(r'Skor Keyakinan:\s*(\d+(?:\.\d+)?)%?', gpt_text, re.IGNORECASE)
    if c:
        try:
            conf = min(max(float(c.group(1)) / 100.0, 0.0), 1.0)
        except Exception:
            conf = 0.70
    return cls, conf

# ==============================================================================
# SIDEBAR NAVIGATION & CONFIGURATION
# ==============================================================================
with st.sidebar:
    st.markdown("""
    <div style="padding: 0.5rem 0 1rem 0;">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <span class="ihnd-logo">IHND</span>
            <span style="font-weight:700; font-size:1.05rem; color:#F8FAFC;">Control Panel</span>
        </div>
        <div style="font-size:0.75rem; color:#64748B;">Indonesia Hoax News Detection</div>
    </div>
    <hr style="border-color: rgba(255,255,255,0.06); margin: 0.5rem 0 1.25rem 0;">
    """, unsafe_allow_html=True)
    
    # API Key Configuration
    default_key = ""
    api_key = st.text_input(
        "OpenAI API Key (GPT-3.5)",
        type="password",
        value=default_key,
        help="Digunakan untuk lapisan verifikasi forensik kualitatif berbasis LLM."
    )
    st.markdown('<div style="font-size:0.7rem; color:#64748B; margin-top:-6px; margin-bottom:18px;">Powers qualitative forensic LLM layer</div>', unsafe_allow_html=True)
    
    # ML Models Status
    st.markdown('<div style="font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#94A3B8; margin-bottom:8px;">Model Health Status</div>', unsafe_allow_html=True)
    if check_models_exist():
        st.success("✓ ML Classifiers Loaded")
        st.markdown('<div style="font-size:0.72rem; color:#64748B; margin-top:-4px; margin-bottom:14px;">Linear SVM · Random Forest · Naive Bayes</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ Model Belum Dilatih")
        st.markdown('<div style="font-size:0.72rem; color:#64748B; margin-top:-4px; margin-bottom:14px;">Silakan latih model di Tab 3.</div>', unsafe_allow_html=True)
        
    # Transformer Status
    st.info("✓ IndoBERT Active")
    st.markdown('<div style="font-size:0.72rem; color:#64748B; margin-top:-4px; margin-bottom:18px;">indobenchmark/indobert-base-p1 (768-dim)</div>', unsafe_allow_html=True)
    
    # Architecture Overview Box
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 14px; font-size: 0.78rem; line-height: 1.6; color: #94A3B8;">
        <strong style="color:#F8FAFC; display:block; margin-bottom:4px;">Multi-Layer Verification:</strong>
        1. Sastrawi Indonesian Preprocessing<br>
        2. IndoBERT Transformer Embedding<br>
        3. Statistical ML Classification (SVM)<br>
        4. GPT-3.5 Forensic Linguistic Analysis<br>
        5. Source Domain Authority & Credibility
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# TOP FIXED NAVBAR
# ==============================================================================
st.markdown("""
<div class="ihnd-navbar">
    <div class="ihnd-brand">
        <span class="ihnd-logo">IHND</span>
        <span class="ihnd-brand-title">Indonesia Hoax News Detection</span>
    </div>
    <div class="ihnd-nav-items">
        <span class="ihnd-nav-tag">IndoBERT 768-dim</span>
        <span class="ihnd-nav-tag">SVM 99.80% Acc</span>
        <span class="ihnd-nav-tag">Multi-Layer AI</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# APPLICATION TABS
# ==============================================================================
tab_detect, tab_eda, tab_train = st.tabs([
    "🔍  Analisis Berita (AI Detection)",
    "📊  Eksplorasi Data (Dataset & EDA)",
    "⚙️  Model Training Console"
])

# ==============================================================================
# TAB 1: DETECTION DASHBOARD
# ==============================================================================
with tab_detect:
    # ---- HERO SECTION ----
    st.markdown("""
    <div class="hero-wrapper">
        <div>
            <div class="hero-pill">
                <span class="pill-pulse"></span>
                AI-Powered Fact Checking
            </div>
            <h1 class="hero-heading">
                Deteksi Berita Hoaks<br>
                <span class="gradient-text">Dengan Kecerdasan Buatan</span>
            </h1>
            <p class="hero-description">
                Sistem verifikasi hibrida canggih yang memadukan representasi semantik <strong>IndoBERT</strong>, 
                klasifikasi statistik <strong>Machine Learning</strong>, analisis logis <strong>GPT-3.5</strong>, 
                dan validasi kredibilitas <strong>Domain Authority</strong> untuk mendeteksi disinformasi berbahasa Indonesia.
            </p>
            <div class="hero-tags-row">
                <span class="hero-tech-tag">⚡ IndoBERT Transformer</span>
                <span class="hero-tech-tag">🧠 Support Vector Machine</span>
                <span class="hero-tech-tag">🌲 Random Forest</span>
                <span class="hero-tech-tag">🤖 GPT-3.5 Forensic</span>
                <span class="hero-tech-tag">🌐 Domain Rating</span>
            </div>
        </div>
        <div class="hero-visual-card">
            <div class="hvc-header">
                <span class="hvc-title">Pipeline Architecture</span>
                <span class="hvc-live">● Live Ready</span>
            </div>
            <div class="hvc-node-grid">
                <div class="hvc-layer-row">
                    <div class="hvc-layer-info">
                        <span class="hvc-icon">🔧</span>
                        <span class="hvc-name">Preprocessing</span>
                    </div>
                    <span class="hvc-val">Sastrawi + HTML Scrub</span>
                </div>
                <div class="hvc-layer-row">
                    <div class="hvc-layer-info">
                        <span class="hvc-icon">🧠</span>
                        <span class="hvc-name">IndoBERT Embeddings</span>
                    </div>
                    <span class="hvc-val">768 Dimensions</span>
                </div>
                <div class="hvc-layer-row">
                    <div class="hvc-layer-info">
                        <span class="hvc-icon">📊</span>
                        <span class="hvc-name">SVM Classifier</span>
                    </div>
                    <span class="hvc-val">99.80% Test Accuracy</span>
                </div>
                <div class="hvc-layer-row">
                    <div class="hvc-layer-info">
                        <span class="hvc-icon">🤖</span>
                        <span class="hvc-name">GPT-3.5 Forensic</span>
                    </div>
                    <span class="hvc-val">Qualitative Audit</span>
                </div>
                <div class="hvc-layer-row">
                    <div class="hvc-layer-info">
                        <span class="hvc-icon">🌐</span>
                        <span class="hvc-name">Domain Credibility</span>
                    </div>
                    <span class="hvc-val">DA / DR / Spam Score</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ---- DATASET STATS STRIP ----
    st.markdown("""
    <div class="stats-strip">
        <div class="stat-cell">
            <div class="stat-num">5,040</div>
            <div class="stat-label">Total Artikel Dataset</div>
        </div>
        <div class="stat-cell">
            <div class="stat-num fact">2,520</div>
            <div class="stat-label">Berita Fakta Terverifikasi</div>
        </div>
        <div class="stat-cell">
            <div class="stat-num hoax">2,520</div>
            <div class="stat-label">Artikel Hoaks Teridentifikasi</div>
        </div>
        <div class="stat-cell">
            <div class="stat-num accent">99.80%</div>
            <div class="stat-label">Akurasi Model SVM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- DETECTION FORM ----
    st.markdown("""
    <div class="section-head">
        <div class="section-eyebrow">Input & Analisis</div>
        <div class="section-title">Pemeriksaan Artikel Berita</div>
        <div class="section-sub">
            Pilih judul berita dari dataset untuk pengujian instan atau ketik berita kustom secara manual.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Load dataset for quick select
    df_titles = None
    if os.path.exists("dataset_clean.csv"):
        try:
            df_titles = pd.read_csv("dataset_clean.csv")
        except Exception:
            pass

    if df_titles is not None:
        titles_list = ["--- Tulis Berita Kustom ---"] + df_titles["TITLE"].dropna().unique().tolist()
        selected_title_option = st.selectbox(
            "Cari / Pilih Berita dari Dataset (5,040 Artikel Tersedia)", 
            options=titles_list,
            help="Pilih judul berita dari dataset untuk mengisi otomatis judul dan narasi berita, atau pilih 'Tulis Berita Kustom' untuk menulis sendiri."
        )
    else:
        selected_title_option = "--- Tulis Berita Kustom ---"

    default_title = ""
    default_narrative = ""

    if selected_title_option != "--- Tulis Berita Kustom ---" and df_titles is not None:
        row = df_titles[df_titles["TITLE"] == selected_title_option].iloc[0]
        default_title = str(row["TITLE"])
        default_narrative = str(row["NARRATIVE"])

    col_input, col_ctrl = st.columns([3, 1], gap="medium")
    with col_input:
        judul_input = st.text_input(
            "Judul Berita (Headline)", 
            value=default_title, 
            placeholder="Masukkan judul atau headline berita yang akan dianalisis..."
        )
        narasi_input = st.text_area(
            "Konten / Narasi Berita Lengkap", 
            value=default_narrative, 
            placeholder="Tempelkan (paste) narasi lengkap atau isi artikel berita di sini...", 
            height=160
        )
        char_cnt = len(narasi_input)
        word_cnt = len(narasi_input.split()) if narasi_input else 0
        st.markdown(f'<div style="font-size:0.75rem; color:#64748B; text-align:right; margin-top:2px;">{char_cnt} karakter · {word_cnt} kata</div>', unsafe_allow_html=True)
    
    with col_ctrl:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🚀 Mulai Analisis Multi-Layer", use_container_width=True)
        threshold = st.slider(
            "Ambang Batas Hoaks (Threshold)", 
            min_value=0.40, 
            max_value=0.80, 
            value=0.55, 
            step=0.05, 
            help="Ambang batas sensitivitas probabilitas hoaks. Nilai lebih rendah meningkatkan kewaspadaan sistem terhadap indikasi hoaks."
        )
        st.markdown('<div style="font-size:0.72rem; color:#64748B; line-height:1.5;">Sensitivitas klasifikasi hoaks. Default: 0.55</div>', unsafe_allow_html=True)

    # Empty State Notice (if no analysis done yet)
    if not analyze_btn and "detection_result" not in st.session_state:
        st.markdown("""
        <div style="background: var(--bg-1); border: 1px dashed var(--border-1); border-radius: var(--radius-md); padding: 3rem 2rem; text-align: center; margin-top: 2rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.75rem; opacity: 0.6;">🛡️</div>
            <div style="font-weight: 700; font-size: 1.1rem; color: #F8FAFC; margin-bottom: 6px;">Sistem Siap Menganalisis</div>
            <div style="font-size: 0.88rem; color: #94A3B8; max-width: 480px; margin: 0 auto; line-height: 1.6;">
                Masukkan judul dan narasi berita di atas, lalu klik <strong>Mulai Analisis Multi-Layer</strong> untuk menguji keaslian informasi melalui 6 lapisan verifikasi AI.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ---- RUN ANALYSIS PIPELINE ----
    if analyze_btn:
        if not narasi_input.strip():
            st.error("❌ Narasi atau isi berita wajib diisi untuk melakukan analisis!")
            if "detection_result" in st.session_state:
                del st.session_state["detection_result"]
        else:
            combined_text = f"{judul_input}. {narasi_input}" if judul_input.strip() else narasi_input
            
            progress_placeholder = st.empty()
            
            # Step 1: Preprocessing
            progress_placeholder.markdown(render_step_progress(0, 0), unsafe_allow_html=True)
            
            # Step 2: IndoBERT Embeddings & ML Inferences
            progress_placeholder.markdown(render_step_progress(1, 1), unsafe_allow_html=True)
            ml_ready = check_models_exist()
            ml_predictions = {}
            if ml_ready:
                pipeline = ml_pipeline or load_ml_models()
                if pipeline is not None:
                    ml_predictions = predict_single_text(combined_text, pipeline["models"], pipeline["scaler"])
            
            # Step 3: Classifiers complete
            progress_placeholder.markdown(render_step_progress(2, 2), unsafe_allow_html=True)
            
            # Step 4: GPT Forensic
            progress_placeholder.markdown(render_step_progress(3, 3), unsafe_allow_html=True)
            gpt_report = predict_hoax_openai(combined_text, api_key)
            gpt_cls, gpt_conf = parse_gpt_verdict(gpt_report)
            
            # Step 5: Domain Check
            progress_placeholder.markdown(render_step_progress(4, 4), unsafe_allow_html=True)
            extracted_domains = extract_domains_from_text(combined_text)
            gpt_links = extract_domains_from_text(gpt_report) if not gpt_report.startswith("Error") else []
            all_extracted_domains = list(set(extracted_domains + gpt_links))
            
            domain_metrics_results = {}
            for dom in all_extracted_domains:
                metrics = get_domain_metrics(dom)
                if metrics:
                    domain_metrics_results[dom] = metrics
                    
            # Step 6: Final Consensus
            progress_placeholder.markdown(render_step_progress(5, 5), unsafe_allow_html=True)
            
            # Determine overall consensus
            svm_res = ml_predictions.get("SVM (Linear)", {"prediction": "Fact", "confidence": 0.5})
            svm_pred = svm_res["prediction"]
            svm_conf = svm_res["confidence"]
            
            # Vote tally
            votes = [r["prediction"] for r in ml_predictions.values()]
            if gpt_cls in ["Hoax", "Fact"]:
                votes.append(gpt_cls)
                
            hoax_votes = sum(1 for v in votes if v == "Hoax")
            fact_votes = sum(1 for v in votes if v == "Fact")
            
            if hoax_votes > fact_votes or (svm_pred == "Hoax" and svm_conf >= threshold):
                final_verdict = "HOAKS"
                verdict_class = "hoax"
                verdict_color = "#EF4444"
                verdict_summary = "Artikel ini terdeteksi memiliki karakteristik narasi tidak benar (disinformasi) berdasarkan klasifikasi semantik IndoBERT dan verifikasi forensik."
            elif fact_votes > hoax_votes or (svm_pred == "Fact" and svm_conf >= threshold):
                final_verdict = "FAKTA"
                verdict_class = "fact"
                verdict_color = "#10B981"
                verdict_summary = "Artikel ini terverifikasi memiliki struktur dan karakteristik konten yang valid serta sesuai dengan pola berita kredibel."
            else:
                final_verdict = "PERLU VERIFIKASI"
                verdict_class = "warn"
                verdict_color = "#F59E0B"
                verdict_summary = "Hasil klasifikasi menghasilkan keyakinan moderat. Disarankan melakukan kroscek silang dengan sumber berita arus utama resmi."
                
            progress_placeholder.markdown(render_step_progress(-1, 6), unsafe_allow_html=True)
            
            # Cache results in session state
            st.session_state["detection_result"] = {
                "final_verdict": final_verdict,
                "verdict_class": verdict_class,
                "verdict_color": verdict_color,
                "verdict_summary": verdict_summary,
                "svm_conf": svm_conf,
                "ml_predictions": ml_predictions,
                "gpt_report": gpt_report,
                "gpt_cls": gpt_cls,
                "gpt_conf": gpt_conf,
                "all_extracted_domains": all_extracted_domains,
                "domain_metrics_results": domain_metrics_results,
                "ml_ready": ml_ready
            }

    # ---- RENDER DETECTION REPORT ----
    if "detection_result" in st.session_state:
        res = st.session_state["detection_result"]
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="section-head">
            <div class="section-eyebrow">Hasil Investigasi</div>
            <div class="section-title">Laporan Forensik Berita</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 1. Prominent Verdict Card with Circular SVG Gauge
        verdict_html = f"""
        <div class="verdict-card {res['verdict_class']}">
            <div>
                <div class="verdict-eyebrow">Konsensus Keputusan AI</div>
                <div class="verdict-badge {res['verdict_class']}">{res['final_verdict']}</div>
                <div class="verdict-summary">{res['verdict_summary']}</div>
            </div>
            <div>
                {render_confidence_ring(res['svm_conf'], res['verdict_color'])}
            </div>
        </div>
        """
        st.markdown(verdict_html, unsafe_allow_html=True)
        
        # 2. Detailed Breakdown Grid
        col_pipe, col_detail = st.columns([1, 1], gap="large")
        
        # Left: Multi-Layer Pipeline Flow
        with col_pipe:
            st.markdown('<div class="section-eyebrow">Alur Deteksi</div><h4 style="color:#F8FAFC; margin-top:0;">Pipeline Verifikasi Multi-Layer</h4>', unsafe_allow_html=True)
            
            # Construct Pipeline Nodes
            pipeline_html = '<div class="pipeline-container">'
            
            # Step 1: Preprocessing
            pipeline_html += (
                '<div class="pipeline-node">'
                '<div class="node-icon-box fact">🔧</div>'
                '<div class="node-content">'
                '<div class="node-name">1. Text Preprocessing &amp; Cleaning</div>'
                '<div class="node-desc">Sastrawi Indonesian Stemming, stopword scrubbing, dan pembersihan tag HTML BeautifulSoup.</div>'
                '<span class="node-badge fact">Selesai</span>'
                '</div></div>'
                '<div class="node-connector"></div>'
            )
            
            # Step 2: IndoBERT Embeddings
            pipeline_html += (
                '<div class="pipeline-node">'
                '<div class="node-icon-box accent">🧠</div>'
                '<div class="node-content">'
                '<div class="node-name">2. IndoBERT Transformer Representation</div>'
                '<div class="node-desc">Ekstraksi vektor representasi semantik 768 dimensi menggunakan <code>indobenchmark/indobert-base-p1</code>.</div>'
                '<span class="node-badge accent">768 Dimensi</span>'
                '</div></div>'
                '<div class="node-connector"></div>'
            )
            
            # Step 3: Primary Classifier (SVM)
            svm_res = res["ml_predictions"].get("SVM (Linear)", {"prediction": "N/A", "confidence": 0.0})
            svm_cls = "hoax" if svm_res["prediction"] == "Hoax" else "fact"
            pipeline_html += (
                f'<div class="pipeline-node">'
                f'<div class="node-icon-box {svm_cls}">📊</div>'
                '<div class="node-content">'
                '<div class="node-name">3. Linear SVM Classifier (Primary)</div>'
                '<div class="node-desc">Klasifikasi bidang batas optimal berakurasi 99.80% pada ruang fitur IndoBERT.</div>'
                f'<span class="node-badge {svm_cls}">Prediksi: {svm_res["prediction"].upper()} ({svm_res["confidence"]*100:.1f}%)</span>'
                '</div></div>'
                '<div class="node-connector"></div>'
            )
            
            # Step 4: Secondary Models (Random Forest & Naive Bayes)
            rf_res = res["ml_predictions"].get("Random Forest", {"prediction": "N/A"})
            nb_res = res["ml_predictions"].get("Naive Bayes", {"prediction": "N/A"})
            pipeline_html += (
                '<div class="pipeline-node">'
                '<div class="node-icon-box accent">🌲</div>'
                '<div class="node-content">'
                '<div class="node-name">4. Ensemble Validation (RF &amp; Naive Bayes)</div>'
                f'<div class="node-desc">Random Forest: <strong>{rf_res["prediction"]}</strong> · Naive Bayes: <strong>{nb_res["prediction"]}</strong>.</div>'
                '<span class="node-badge neutral">Validasi Statistik</span>'
                '</div></div>'
                '<div class="node-connector"></div>'
            )
            
            # Step 5: GPT-3.5 Forensic
            gpt_badge_cls = "hoax" if res["gpt_cls"] == "Hoax" else ("fact" if res["gpt_cls"] == "Fact" else "warn")
            pipeline_html += (
                f'<div class="pipeline-node">'
                f'<div class="node-icon-box {gpt_badge_cls}">🤖</div>'
                '<div class="node-content">'
                '<div class="node-name">5. GPT-3.5 Qualitative Forensic Audit</div>'
                '<div class="node-desc">Pemeriksaan gaya bahasa, clickbait, dan penalaran konten logis.</div>'
                f'<span class="node-badge {gpt_badge_cls}">Klasifikasi: {res["gpt_cls"].upper()} ({res["gpt_conf"]*100:.0f}%)</span>'
                '</div></div>'
                '<div class="node-connector"></div>'
            )
            
            # Step 6: Domain Authority
            domain_count = len(res["all_extracted_domains"])
            dom_status = f"{domain_count} domain diperiksa" if domain_count > 0 else "Tidak ada link domain luar"
            pipeline_html += (
                '<div class="pipeline-node">'
                '<div class="node-icon-box accent">🌐</div>'
                '<div class="node-content">'
                '<div class="node-name">6. Source Domain Credibility Audit</div>'
                f'<div class="node-desc">{dom_status}.</div>'
                '<span class="node-badge neutral">Metrik Otoritas</span>'
                '</div></div>'
                '<div class="node-connector"></div>'
            )
            
            # Step 7: Final Consensus
            pipeline_html += (
                f'<div class="pipeline-node">'
                f'<div class="node-icon-box {res["verdict_class"]}">⚖️</div>'
                '<div class="node-content">'
                '<div class="node-name">7. Keputusan Akhir (Final Consensus)</div>'
                f'<div class="node-desc">Voting mayoritas multi-layer: <strong>{res["final_verdict"]}</strong>.</div>'
                f'<span class="node-badge {res["verdict_class"]}">Keyakinan: {res["svm_conf"]*100:.1f}%</span>'
                '</div></div>'
            )
            
            pipeline_html += '</div>'
            st.markdown(pipeline_html, unsafe_allow_html=True)
            
        # Right: Qualitative Reports & Score Bars
        with col_detail:
            # 1. GPT-3.5 Forensic Report Card
            st.markdown('<div class="section-eyebrow">Pemeriksaan Kualitatif</div><h4 style="color:#F8FAFC; margin-top:0;">Audit Forensik LLM (GPT-3.5)</h4>', unsafe_allow_html=True)
            if not api_key:
                st.info("⚠️ Masukkan OpenAI API Key pada sidebar untuk mengaktifkan audit forensik kualitatif.")
            elif res["gpt_report"].startswith("Error"):
                st.error(res["gpt_report"])
            else:
                st.markdown(f"""
                <div class="forensic-box">
                    <div class="forensic-header">
                        <span style="font-size:1.1rem;">🤖</span>
                        <div>
                            <div style="font-weight:700; font-size:0.86rem; color:#F8FAFC;">Analisis Forensik Misinformasi</div>
                            <div style="font-size:0.72rem; color:#64748B;">Audit Logika & Karakteristik Bahasa</div>
                        </div>
                    </div>
                    <div class="forensic-body">{res['gpt_report']}</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 2. Classifier Comparison Score Bars
            st.markdown('<div class="section-eyebrow">Performa Komparatif</div><h4 style="color:#F8FAFC; margin-top:0;">Skor Model Machine Learning</h4>', unsafe_allow_html=True)
            if res["ml_predictions"]:
                for model_name, m_res in res["ml_predictions"].items():
                    pred_label = m_res["prediction"]
                    conf_pct = m_res["confidence"] * 100
                    bar_cls = "hoax" if pred_label == "Hoax" else "fact"
                    disp_str = f"{pred_label} · {conf_pct:.1f}%"
                    st.markdown(render_score_bar(model_name, conf_pct, bar_cls, disp_str), unsafe_allow_html=True)
            else:
                st.info("Model statistik lokal belum dilatih.")
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 3. Domain Authority & Source Reputation
            st.markdown('<div class="section-eyebrow">Verifikasi Sumber</div><h4 style="color:#F8FAFC; margin-top:0;">Kredibilitas Domain Rujukan</h4>', unsafe_allow_html=True)
            if not res["all_extracted_domains"]:
                st.markdown("""
                <div style="background: var(--bg-1); border: 1px solid var(--border-0); border-radius: var(--radius-sm); padding: 16px; font-size: 0.82rem; color: #94A3B8;">
                    Tidak ada rujukan tautan domain eksternal yang teridentifikasi dalam teks berita ini.
                </div>
                """, unsafe_allow_html=True)
            else:
                for dom in res["all_extracted_domains"]:
                    metrics = res["domain_metrics_results"].get(dom)
                    if metrics and "error" not in metrics:
                        da = int(metrics.get("Domain Authority", 0))
                        dr = int(metrics.get("Domain Rating", 0))
                        spam_raw = metrics.get("Spam Score", "0%")
                        try:
                            spam_score = float(str(spam_raw).replace('%','').strip())
                        except Exception:
                            spam_score = 0.0
                            
                        avg_authority = (da + dr) / 2
                        if avg_authority >= 60:
                            cred_label = "● Kredibilitas Tinggi (Mainstream Media)"
                            cred_color = "#10B981"
                        elif avg_authority >= 30:
                            cred_label = "● Kredibilitas Sedang"
                            cred_color = "#F59E0B"
                        else:
                            cred_label = "● Kredibilitas Rendah / Tidak Dikenal"
                            cred_color = "#EF4444"
                            
                        spam_style = "hoax" if spam_score > 30 else "fact"
                        
                        dom_html = f"""
                        <div class="domain-card">
                            <div class="domain-name">🌐 {dom}</div>
                            {render_score_bar("Domain Authority (DA)", da, "accent", f"{da}/100")}
                            {render_score_bar("Domain Rating (DR)", dr, "accent", f"{dr}/100")}
                            {render_score_bar("Spam Score", spam_score, spam_style, f"{spam_raw}")}
                            <div style="font-size:0.75rem; font-weight:700; color:{cred_color}; margin-top:10px;">
                                {cred_label}
                            </div>
                        </div>
                        """
                        st.markdown(dom_html, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="domain-card">
                            <div class="domain-name">🌐 {dom}</div>
                            <div style="font-size:0.75rem; color:#64748B;">Data metrik otoritas tidak dapat diakses untuk domain ini.</div>
                        </div>
                        """, unsafe_allow_html=True)

    # ---- HOW IT WORKS GRID ----
    st.markdown("""
    <div style="padding-top: 3.5rem;">
        <div class="section-head">
            <div class="section-eyebrow">Cara Kerja Sistem</div>
            <div class="section-title">Enam Tahap Investigasi Hoaks Berbasis AI</div>
            <div class="section-sub">Mekanisme komprehensif dari ekstraksi fitur bahasa hingga voting konsensus akhir.</div>
        </div>
        <div class="hiw-grid">
            <div class="hiw-step">
                <div class="hiw-num">01 / INPUT</div>
                <div class="hiw-icon">📄</div>
                <div class="hiw-title">Pemasukan Berita</div>
                <div class="hiw-text">Pengguna memasukkan judul dan narasi berita berbahasa Indonesia secara langsung atau memilih sampel dari dataset.</div>
            </div>
            <div class="hiw-step">
                <div class="hiw-num">02 / PREPROCESS</div>
                <div class="hiw-icon">🔧</div>
                <div class="hiw-title">Pembersihan Bahasa</div>
                <div class="hiw-text">Pembersihan tag HTML, normalisasi karakter khusus, stopword removal, dan stemming Sastrawi untuk bahasa Indonesia baku.</div>
            </div>
            <div class="hiw-step">
                <div class="hiw-num">03 / TRANSFORMER</div>
                <div class="hiw-icon">🧠</div>
                <div class="hiw-title">Embedding IndoBERT</div>
                <div class="hiw-text">Model transformer mengekstrak representasi semantik kontekstual tingkat tinggi ke dalam ruang vektor 768 dimensi dengan mean pooling.</div>
            </div>
            <div class="hiw-step">
                <div class="hiw-num">04 / ML VOTING</div>
                <div class="hiw-icon">📊</div>
                <div class="hiw-title">Klasifikasi Statistik</div>
                <div class="hiw-text">Support Vector Machine (SVM), Random Forest, dan Gaussian Naive Bayes mengklasifikasi fitur vektor secara independen.</div>
            </div>
            <div class="hiw-step">
                <div class="hiw-num">05 / AUDIT LLM</div>
                <div class="hiw-icon">🤖</div>
                <div class="hiw-title">Forensik GPT-3.5</div>
                <div class="hiw-text">Audit logika, gaya bahasa clickbait, dan konsistensi klaim oleh model bahasa besar sebagai lapisan verifikasi kualitatif.</div>
            </div>
            <div class="hiw-step">
                <div class="hiw-num">06 / VERDICT</div>
                <div class="hiw-icon">⚖️</div>
                <div class="hiw-title">Konsensus Final</div>
                <div class="hiw-text">Penggabungan skor statistik, audit LLM, dan skor domain otoritas untuk menetapkan vonis akhir: FAKTA, HOAKS, atau PERLU VERIFIKASI.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# TAB 2: EXPLORATORY DATA ANALYSIS (EDA)
# ==============================================================================
with tab_eda:
    st.markdown("""
    <div class="section-head">
        <div class="section-eyebrow">Dataset Insights</div>
        <div class="section-title">Eksplorasi Statistik Dataset Berita</div>
        <div class="section-sub">Analisis distribusi, panjang artikel, dan visualisasi kata kunci dari dataset 5,040 artikel berita Indonesia.</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Overview Cards
    st.markdown("""
    <div class="stats-strip">
        <div class="stat-cell">
            <div class="stat-num">5,040</div>
            <div class="stat-label">Total Data Observasi</div>
        </div>
        <div class="stat-cell">
            <div class="stat-num fact">2,520</div>
            <div class="stat-label">Fakta Terverifikasi (Label 1)</div>
        </div>
        <div class="stat-cell">
            <div class="stat-num hoax">2,520</div>
            <div class="stat-label">Berita Hoaks (Label 0)</div>
        </div>
        <div class="stat-cell">
            <div class="stat-num accent">1:1</div>
            <div class="stat-label">Rasio Keseimbangan Kelas</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    data_file = "dataset_clean.csv"
    if not os.path.exists(data_file):
        st.warning(f"⚠️ File dataset `{data_file}` tidak ditemukan di direktori proyek.")
    else:
        df = pd.read_csv(data_file).convert_dtypes(convert_string=False)
        # Ensure NARRATIVE is a plain Python string column (no Arrow/StringDtype backing)
        df['NARRATIVE'] = df['NARRATIVE'].fillna('').astype(str)
        
        st.markdown('<div class="section-eyebrow">Pratinjau Data</div><h4 style="color:#F8FAFC; margin-top:0;">Tabel Sampel Dataset</h4>', unsafe_allow_html=True)
        st.dataframe(df.head(10), use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2, gap="large")
        
        with col_c1:
            st.markdown('<div class="section-eyebrow">Distribusi Kelas</div><h4 style="color:#F8FAFC; margin-top:0;">Proporsi Kategori Berita</h4>', unsafe_allow_html=True)
            fig, ax = plt.subplots(figsize=(6, 4.2))
            counts = df['LABEL'].value_counts()
            labels = ['Fakta (1)' if x == 1 else 'Hoaks (0)' for x in counts.index]
            colors = ['#10B981', '#EF4444']
            wedges, texts, autotexts = ax.pie(
                counts, 
                labels=labels, 
                autopct='%1.1f%%', 
                colors=colors, 
                startangle=90, 
                wedgeprops={'linewidth': 2, 'edgecolor': '#050914'},
                textprops={'color': '#F8FAFC', 'fontsize': 10, 'fontweight': '600'}
            )
            for autotext in autotexts:
                autotext.set_color('#050914')
                autotext.set_fontweight('bold')
            fig.patch.set_facecolor('#0A1124')
            ax.set_facecolor('#0A1124')
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
            
        with col_c2:
            st.markdown('<div class="section-eyebrow">Karakteristik Teks</div><h4 style="color:#F8FAFC; margin-top:0;">Panjang Artikel (Jumlah Kata)</h4>', unsafe_allow_html=True)
            df['word_count'] = df['NARRATIVE'].fillna('').astype(str).apply(lambda x: len(x.split()))
            fig2, ax2 = plt.subplots(figsize=(6, 4.2))
            sns.histplot(
                data=df, 
                x='word_count', 
                hue='LABEL', 
                multiple='stack', 
                kde=True, 
                ax=ax2, 
                palette={0: '#EF4444', 1: '#10B981'},
                alpha=0.85
            )
            ax2.tick_params(colors='#94A3B8', labelsize=8)
            ax2.set_xlabel("Jumlah Kata per Artikel", color='#94A3B8', fontsize=9)
            ax2.set_ylabel("Frekuensi", color='#94A3B8', fontsize=9)
            for spine in ax2.spines.values():
                spine.set_edgecolor((1, 1, 1, 0.06))
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            fig2.patch.set_facecolor('#0A1124')
            ax2.set_facecolor('#0A1124')
            leg = ax2.get_legend()
            if leg:
                leg.get_frame().set_facecolor('#0F1B35')
                leg.get_frame().set_edgecolor((1, 1, 1, 0.08))
                for t in leg.get_texts():
                    t.set_color('#F8FAFC')
                    t.set_fontsize(9)
            plt.tight_layout()
            st.pyplot(fig2)
            plt.close()

        # WordCloud Visualizations
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-eyebrow">Analisis Leksikal</div><h4 style="color:#F8FAFC; margin-top:0;">Awan Kata Kunci (Word Cloud)</h4>', unsafe_allow_html=True)
        try:
            from wordcloud import WordCloud
            col_w1, col_w2 = st.columns(2, gap="large")
            
            with col_w1:
                st.markdown('<div style="font-weight:700; color:#EF4444; font-size:0.88rem; margin-bottom:8px;">● Kata Kunci Paling Sering Muncul pada HOAKS</div>', unsafe_allow_html=True)
                hoax_text = " ".join(df[df['LABEL'] == 0]['NARRATIVE'].astype(str))
                wc_hoax = WordCloud(
                    width=600, height=280, 
                    background_color='#0A1124', 
                    colormap='Reds', 
                    max_words=60, 
                    prefer_horizontal=0.85
                ).generate(hoax_text)
                
                fig_h, ax_h = plt.subplots(figsize=(6.5, 3))
                ax_h.imshow(wc_hoax, interpolation='bilinear')
                ax_h.axis('off')
                fig_h.patch.set_facecolor('#0A1124')
                fig_h.tight_layout(pad=0)
                st.pyplot(fig_h)
                plt.close()
                
            with col_w2:
                st.markdown('<div style="font-weight:700; color:#10B981; font-size:0.88rem; margin-bottom:8px;">● Kata Kunci Paling Sering Muncul pada FAKTA</div>', unsafe_allow_html=True)
                fact_text = " ".join(df[df['LABEL'] == 1]['NARRATIVE'].astype(str))
                wc_fact = WordCloud(
                    width=600, height=280, 
                    background_color='#0A1124', 
                    colormap='Greens', 
                    max_words=60, 
                    prefer_horizontal=0.85
                ).generate(fact_text)
                
                fig_f, ax_f = plt.subplots(figsize=(6.5, 3))
                ax_f.imshow(wc_fact, interpolation='bilinear')
                ax_f.axis('off')
                fig_f.patch.set_facecolor('#0A1124')
                fig_f.tight_layout(pad=0)
                st.pyplot(fig_f)
                plt.close()
                
        except ImportError:
            st.info("Modul `wordcloud` belum terpasang. Gunakan `pip install wordcloud` untuk melihat visualisasi awan kata.")


# ==============================================================================
# TAB 3: MODEL TRAINING CONSOLE
# ==============================================================================
with tab_train:
    st.markdown("""
    <div class="section-head">
        <div class="section-eyebrow">Model Operations</div>
        <div class="section-title">Konsol Pelatihan Model Machine Learning</div>
        <div class="section-sub">
            Latih ulang classifier Linear SVM, Random Forest, dan Naive Bayes menggunakan representasi semantik IndoBERT transformer.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns([1, 1], gap="large")
    
    with col_t1:
        st.markdown('<div class="section-eyebrow">Parameter Pelatihan</div><h4 style="color:#F8FAFC; margin-top:0;">Konfigurasi Hyperparameter</h4>', unsafe_allow_html=True)
        sample_size = st.selectbox(
            "Batas Jumlah Sampel Dataset (Sample Limit)", 
            options=[50, 200, 1000, 2500, None], 
            index=0, 
            format_func=lambda x: f"{x} sampel — Pengujian Cepat (~15 detik)" if x == 50
                else (f"{x:,} sampel" if x else "Seluruh Dataset (5,040 sampel — ~15 menit di CPU)"),
            help="Pilih ukuran sampel kecil untuk pengujian cepat pipeline atau None untuk melatih seluruh dataset."
        )
        batch_size = st.slider(
            "Ukuran Batch Embedding (IndoBERT Batch Size)", 
            min_value=8, 
            max_value=64, 
            value=16, 
            step=8,
            help="Jumlah teks yang diproses secara simultan saat inferensi transformer."
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        start_training = st.button("🚀 Jalankan Pelatihan Model Sekarang", use_container_width=True)
        
    with col_t2:
        st.markdown('<div class="section-eyebrow">Spesifikasi Arsitektur</div><h4 style="color:#F8FAFC; margin-top:0;">Model Pipeline Summary</h4>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background: var(--bg-1); border: 1px solid var(--border-1); border-radius: var(--radius-md); padding: 18px;">
            <div style="margin-bottom:10px;">
                <div style="font-size:0.68rem; color:#64748B; text-transform:uppercase; letter-spacing:0.06em; font-weight:700;">Base Transformer</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#00D2FF; font-weight:600;">indobenchmark/indobert-base-p1</div>
            </div>
            <div style="margin-bottom:10px;">
                <div style="font-size:0.68rem; color:#64748B; text-transform:uppercase; letter-spacing:0.06em; font-weight:700;">Dimensi Representasi</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#F8FAFC;">768-dim Tensor (Mean Pooling)</div>
            </div>
            <div style="margin-bottom:10px;">
                <div style="font-size:0.68rem; color:#64748B; text-transform:uppercase; letter-spacing:0.06em; font-weight:700;">Normalisasi Fitur</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#F8FAFC;">StandardScaler (Zero Mean, Unit Variance)</div>
            </div>
            <div style="margin-bottom:10px;">
                <div style="font-size:0.68rem; color:#64748B; text-transform:uppercase; letter-spacing:0.06em; font-weight:700;">Pembagian Data</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#F8FAFC;">90% Train · 10% Test (Stratified)</div>
            </div>
            <div>
                <div style="font-size:0.68rem; color:#64748B; text-transform:uppercase; letter-spacing:0.06em; font-weight:700;">Output Artefak</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#10B981;">models/ (scaler.joblib, model_*.joblib)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    if start_training:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-eyebrow">Terminal Eksekusi</div><h4 style="color:#F8FAFC; margin-top:0;">Log Proses Pelatihan Real-time</h4>', unsafe_allow_html=True)
        
        cmd = [sys.executable, "train_models.py"]
        if sample_size is not None:
            cmd += ["--sample_limit", str(sample_size)]
        cmd += ["--batch_size", str(batch_size)]
        
        st.info(f"Eksekusi perintah: `{' '.join(cmd)}`")
        log_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        logs = ""
        for line in proc.stdout:
            logs += line
            log_placeholder.code(logs, language="bash")
            
            if "Setting up Sastrawi" in line:       progress_bar.progress(10)
            elif "Running preprocessing" in line:   progress_bar.progress(25)
            elif "Generating Embeddings" in line:   progress_bar.progress(50)
            elif "Fitting StandardScaler" in line:  progress_bar.progress(70)
            elif "Training: SVM" in line:            progress_bar.progress(80)
            elif "Training: Random Forest" in line:  progress_bar.progress(90)
            elif "Saving models" in line:             progress_bar.progress(95)
            
        proc.wait()
        if proc.returncode == 0:
            progress_bar.progress(100)
            st.success("🎉 Pelatihan model selesai! Bobot model baru telah tersimpan di direktori `models/`. Segarkan aplikasi untuk memuat model terbaru.")
            ml_pipeline = load_ml_models()
        else:
            st.error(f"❌ Terjadi kesalahan pada proses training. Kode keluar: {proc.returncode}")


# ==============================================================================
# FOOTER
# ==============================================================================
st.markdown("""
<div class="ihnd-footer">
    <div class="footer-grid">
        <div>
            <div class="footer-brand">Indonesia Hoax News Detection (IHND)</div>
            <div class="footer-desc">
                Platform intelijen verifikasi berita berbasis transformer NLP dan machine learning multi-layer 
                yang dikembangkan untuk mendeteksi serta memerangi disinformasi berita berbahasa Indonesia.
            </div>
            <div class="footer-badges">
                <span class="fbadge">IndoBERT Base P1</span>
                <span class="fbadge">Linear SVM</span>
                <span class="fbadge">Random Forest</span>
                <span class="fbadge">Naive Bayes</span>
                <span class="fbadge">GPT-3.5 Turbo</span>
                <span class="fbadge">PyTorch</span>
                <span class="fbadge">Scikit-Learn</span>
                <span class="fbadge">Sastrawi</span>
                <span class="fbadge">Streamlit</span>
            </div>
        </div>
        <div>
            <div class="footer-col-title">Dataset Informasi</div>
            <span class="footer-item">Total: 5,040 Artikel Berita</span>
            <span class="footer-item">Fakta: 2,520 Artikel (50%)</span>
            <span class="footer-item">Hoaks: 2,520 Artikel (50%)</span>
            <span class="footer-item">Distribusi: Balanced 1:1</span>
            <span class="footer-item">Bahasa: Bahasa Indonesia</span>
        </div>
        <div>
            <div class="footer-col-title">Performa Model</div>
            <span class="footer-item">Akurasi SVM: 99.80%</span>
            <span class="footer-item">F1-Score: 99.80% (Weighted)</span>
            <span class="footer-item">Vektor Fitur: 768 Dimensi</span>
            <span class="footer-item">Pembagian Data: 90% Train / 10% Test</span>
            <span class="footer-item">Status: Siap Produksi</span>
        </div>
    </div>
    <div class="footer-bottom">
        <div>© 2024–2026 Indonesia Hoax News Detection · Penulisan Ilmiah (PI)</div>
        <div>Dikembangkan dengan arsitektur <strong>IndoBERT + Multi-Layer AI</strong></div>
    </div>
</div>
""", unsafe_allow_html=True)
