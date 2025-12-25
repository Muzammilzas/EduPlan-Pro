import streamlit as st
import os
import re
import json
from openai import OpenAI

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EduPlan Pro", page_icon="🎓", layout="wide")

# --- CSS STYLING ---
st.markdown("""
    <style>
    .main-header {text-align: center; color: #333;}
    .topic-header {color: #2e86c1; border-bottom: 2px solid #2e86c1; padding-bottom: 10px; margin-top: 30px;}
    .sub-header {font-weight: bold; color: #555; margin-top: 15px;}
    .video-card {background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 10px;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'topics' not in st.session_state:
    st.session_state.topics = []
if 'generated_content' not in st.session_state:
    st.session_state.generated_content = [] 
if 'toc_text' not in st.session_state:
    st.session_state.toc_text = ""

# --- SIDEBAR: API KEY ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key_input = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    
    if api_key_input:
        api_key = api_key_input.strip()
    elif "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = None

    if st.button("🗑️ Clear / Reset App"):
        st.session_state.topics = []
        st.session_state.generated_content = []
        st.session_state.toc_text = ""
        st.rerun()

# --- HELPER FUNCTIONS ---
def get_client():
    if not api_key:
        st.error("⚠️ Please enter your OpenAI API Key in the sidebar.")
        st.stop()
    return OpenAI(api_key=api_key)

def get_table_of_contents(client, grade, subject):
    prompt = f"""
    Generate a numbered Table of Contents (exactly 5 key topics) for {subject}, Grade {grade}.
    Output format STRICTLY:
    1. Topic Name
    2. Topic Name
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def parse_topics(toc_text):
    lines = toc_text.split('\n')
    topics = []
    for line in lines:
        clean_line = re.sub(r'^\d+\.\s*', '', line).strip()
        if clean_line:
            topics.append(clean_line)
    return topics

def generate_topic_json(client, grade, subject, mode, topic, sequence_num):
    # Context Logic
    if mode == "Physical (Classroom)":
        exp_context = "PHYSICAL LAB DEMO"
        exp_guide = "Search for videos showing formal school equipment usage (microscopes, circuits, titration)."
    else:
        exp_context = "HOME/DIY EXPERIMENT"
        exp_guide = "Search for videos showing 'at-home' science using household items."

    # --- ADVANCED PROMPT ---
    MASTER_PROMPT = f"""
    You are EduPlan Pro, a curriculum expert.
    Subject: {subject} | Grade: {grade} | Topic: {topic} | Mode: {exp_context}

    YOUR GOAL: Provide a structured lesson plan with VALID video resources.

    VIDEO RULES:
    1. Sources: Khan Academy, CrashCourse, TED-Ed, SciShow, National Geographic, Steve Mould, Veritasium.
    2. SEPARATION: 'Theory Videos' must explain concepts. 'Experiment Videos' must show the practical demo.
    3. LINKS: Provide exact YouTube URLs (https://www.youtube.com/watch?v=...) ONLY if you are 100% sure they exist. 
       If unsure, provide a high-quality "search_term" instead.

    OUTPUT JSON STRUCTURE:
    {{
        "title": "{topic}",
        "overview": "2 sentence summary.",
        "theory_videos": [
            {{"title": "Concept Explanation", "url": "...", "search_term": "{topic} explanation crashcourse"}}
        ],
        "experiment_videos": [
            {{"title": "{exp_context} Demo", "url": "...", "search_term": "{topic} {mode} experiment"}}
        ],
        "experiment_guide": {{
            "materials": ["Item 1", "Item 2"],
            "steps": ["Step 1", "Step 2", "Step 3"]
        }}
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" }, 
        messages=[
            {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
            {"role": "user", "content": MASTER_PROMPT}
        ],
        temperature=0.5
    )
    
    try:
        data = json.loads(response.choices[0].message.content)
        return data, response.usage.total_tokens
    except:
        return None, 0

# --- MAIN APP UI ---

st.title("🎓 EduPlan Pro")
st.caption("AI Curriculum & Video Resource Generator")

# 1. TOP BAR INPUTS (Restored)
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    subject = st.text_input("Subject", placeholder="e.g. Physics")
with col2:
    grade = st.text_input("Grade", placeholder="e.g. 8")
with col3:
    mode = st.selectbox("Mode", ["Physical (Classroom)", "Online (Home)"])

st.markdown("---")

# SECTION 1: Generate Topics
if not st.session_state.topics:
    col_c = st.columns([1, 2, 1])
    with col_c[1]:
        if st.button("🚀 Generate Table of Contents", type="primary", use_container_width=True):
            if not subject or not grade:
                st.warning("Please fill in Subject and Grade.")
            else:
                client = get_client()
                with st.spinner("Brainstorming topics..."):
                    toc = get_table_of_contents(client, grade, subject)
                    if toc:
                        st.session_state.toc_text = toc
                        st.session_state.topics = parse_topics(toc)
                        st.rerun()

# SECTION 2: Topic Selection
elif not st.session_state.generated_content:
    st.info(f"Topics found for **{subject}**")
    
    # Show TOC
    with st.expander("📂 View Topic List", expanded=True):
        st.text(st.session_state.toc_text)
    
    # Selection Controls
    col_sel1, col_sel2 = st.columns([1, 2])
    with col_sel1:
        selection_mode = st.radio("Selection:", ["Generate ALL Topics", "Select Single Topic"])
    
    selected_topics = []
    if selection_mode == "Select Single Topic":
        with col_sel2:
            chosen = st.selectbox("Choose Topic:", st.session_state.topics)
            idx = st.session_state.topics.index(chosen) + 1
            selected_topics = [(idx, chosen)]
    else:
        selected_topics = [(i+1, t) for i, t in enumerate(st.session_state.topics)]

    if st.button(f"✨ Generate Content ({len(selected_topics)} Topics)", type="primary"):
        client = get_client()
        progress_bar = st.progress(0)
        
        for i, (seq, topic_name) in enumerate(selected_topics):
            data, tokens = generate_topic_json(client, grade, subject, mode, topic_name, seq)
            if data:
                st.session_state.generated_content.append(data)
            progress_bar.progress((i + 1) / len(selected_topics))
        
        st.rerun()

# SECTION 3: RESULTS DISPLAY (Restored Card Layout)
else:
    st.success("✅ Content Generated Successfully!")
    
    # Loop through results
    for idx, item in enumerate(st.session_state.generated_content):
        with st.container():
            st.markdown(f"<h2 class='topic-header'>📌 Topic {idx+1}: {item.get('title')}</h2>", unsafe_allow_html=True)
            
            # Overview
            st.info(f"**Overview:** {item.get('overview')}")
            
            # --- VIDEO SECTION (Split Columns) ---
            v_col1, v_col2 = st.columns(2)
            
            # Left: Theory
            with v_col1:
                st.markdown("### 🧠 Theory Videos")
                for vid in item.get('theory_videos', []):
                    with st.container():
                        st.caption(f"**{vid.get('title')}**")
                        url = vid.get('url', '')
                        # Try to Embed
                        if "youtube.com" in url or "youtu.be" in url:
                            st.video(url)
                        # Fallback to Search Button
                        else:
                            clean_search = vid.get('search_term', item['title'] + ' theory').replace(" ", "+")
                            st.markdown(f"""
                                <a href="https://www.youtube.com/results?search_query={clean_search}" target="_blank">
                                    <button style="width:100%; padding:8px; border-radius:5px; background-color:#ff4b4b; color:white; border:none; cursor:pointer;">
                                        ▶️ Search: {vid.get('title')}
                                    </button>
                                </a>
                            """, unsafe_allow_html=True)

            # Right: Experiment
            with v_col2:
                st.markdown(f"### 🧪 Experiment Videos ({mode})")
                for vid in item.get('experiment_videos', []):
                    with st.container():
                        st.caption(f"**{vid.get('title')}**")
                        url = vid.get('url', '')
                        if "youtube.com" in url or "youtu.be" in url:
                            st.video(url)
                        else:
                            clean_search = vid.get('search_term', item['title'] + ' experiment').replace(" ", "+")
                            st.markdown(f"""
                                <a href="https://www.youtube.com/results?search_query={clean_search}" target="_blank">
                                    <button style="width:100%; padding:8px; border-radius:5px; background-color:#2e86c1; color:white; border:none; cursor:pointer;">
                                        🔍 Search: {vid.get('title')}
                                    </button>
                                </a>
                            """, unsafe_allow_html=True)

            # --- INSTRUCTIONS SECTION ---
            st.markdown("---")
            with st.expander(f"📝 View Experiment Instructions ({mode})", expanded=False):
                st.markdown("**Materials:**")
                for mat in item.get('experiment_guide', {}).get('materials', []):
                    st.markdown(f"- {mat}")
                
                st.markdown("**Procedure:**")
                for step in item.get('experiment_guide', {}).get('steps', []):
                    st.markdown(f"- {step}")
            
            st.markdown("<br>", unsafe_allow_html=True)
