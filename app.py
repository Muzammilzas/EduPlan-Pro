import streamlit as st
import json
import re
from openai import OpenAI
# This is the new magic tool that finds REAL videos
from youtubesearchpython import VideosSearch 

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EduPlan Pro", page_icon="🎓", layout="wide")

# --- CSS STYLING (Standard Web App Look) ---
st.markdown("""
    <style>
    .main-header {text-align: center; color: #333;}
    .topic-card {
        background-color: #ffffff; 
        padding: 25px; 
        border-radius: 10px; 
        border: 1px solid #e0e0e0; 
        margin-bottom: 30px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .topic-title {
        color: #2c3e50; 
        font-size: 24px; 
        font-weight: bold; 
        margin-bottom: 15px; 
        border-bottom: 2px solid #3498db; 
        padding-bottom: 10px;
    }
    .section-header {
        font-weight: bold; 
        color: #555; 
        margin-top: 20px; 
        margin-bottom: 10px; 
        text-transform: uppercase; 
        font-size: 14px; 
        letter-spacing: 1px;
    }
    .video-label {
        font-size: 12px;
        color: #777;
        margin-bottom: 5px;
    }
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

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.title("⚙️ EduPlan Settings")
    
    # API Key Input
    api_key_input = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    if api_key_input:
        api_key = api_key_input.strip()
    elif "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = None

    st.divider()
    if st.button("🔄 Start New Search"):
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

def get_real_video_url(search_term):
    """
    Searches YouTube for the search_term and returns the URL of the first result.
    This guarantees a working link.
    """
    try:
        videos_search = VideosSearch(search_term, limit=1)
        results = videos_search.result()
        if results and 'result' in results and len(results['result']) > 0:
            return results['result'][0]['link']
    except Exception as e:
        print(f"Video search error: {e}")
    return None

def get_table_of_contents(client, grade, subject):
    prompt = f"""
    Generate a numbered list of exactly 5 key topics for {subject}, Grade {grade}.
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

def generate_topic_data(client, grade, subject, mode, topic):
    # Context Logic
    if mode == "Physical (Classroom)":
        exp_context = "PHYSICAL LAB"
        exp_guide = "Experiment using school lab equipment."
    else:
        exp_context = "HOME/VIRTUAL"
        exp_guide = "Experiment using household items."

    # PROMPT: Ask for TEXT and SEARCH TERMS only. Do not ask for Links.
    MASTER_PROMPT = f"""
    You are EduPlan Pro.
    Subject: {subject} | Grade: {grade} | Topic: {topic} | Mode: {exp_context}

    OUTPUT JSON STRUCTURE ONLY:
    {{
        "title": "{topic}",
        "overview": "2 sentence summary.",
        "objectives": ["Goal 1", "Goal 2", "Goal 3"],
        "materials": ["Item 1", "Item 2"],
        "theory_search_term": "CrashCourse Physics {topic} explanation",
        "experiment_search_term": "Science experiment {topic} {mode}",
        "experiment_guide": {{
            "title": "Experiment Name",
            "steps": ["Step 1", "Step 2", "Step 3"]
        }}
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" }, 
        messages=[{"role": "user", "content": MASTER_PROMPT}],
        temperature=0.7
    )
    
    try:
        data = json.loads(response.choices[0].message.content)
        
        # --- THE FIX: FETCH REAL VIDEO LINKS HERE ---
        # We search YouTube immediately based on what GPT suggested
        data['theory_video_url'] = get_real_video_url(data['theory_search_term'])
        data['experiment_video_url'] = get_real_video_url(data['experiment_search_term'])
        
        return data
    except:
        return None

# --- MAIN APP UI ---

st.title("🎓 EduPlan Pro")
st.markdown("### AI Curriculum & Lesson Planner")
st.markdown("---")

# 1. LANDING INPUTS
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    subject = st.text_input("Subject", placeholder="e.g. Physics")
with c2:
    grade = st.text_input("Grade Level", placeholder="e.g. 8")
with c3:
    mode = st.radio("Mode", ["Physical (Classroom)", "Online (Virtual)"])

st.markdown("---")

# SECTION 1: Generate TOC
if not st.session_state.topics:
    # Center Button
    bc1, bc2, bc3 = st.columns([1, 2, 1])
    with bc2:
        if st.button("🚀 Generate Curriculum Plan", type="primary", use_container_width=True):
            if not subject or not grade:
                st.warning("Please fill in Subject and Grade.")
            else:
                client = get_client()
                with st.spinner("Analyzing curriculum standards..."):
                    toc = get_table_of_contents(client, grade, subject)
                    if toc:
                        st.session_state.toc_text = toc
                        st.session_state.topics = parse_topics(toc)
                        st.rerun()

# SECTION 2: Topic Selection
elif not st.session_state.generated_content:
    st.success(f"✅ Curriculum Found: **{subject} - {grade}**")
    
    with st.expander("📂 View Table of Contents", expanded=True):
        st.text(st.session_state.toc_text)
    
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

    if st.button(f"✨ Generate Lesson Plans & Find Videos", type="primary"):
        client = get_client()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, (seq, topic_name) in enumerate(selected_topics):
            status_text.text(f"Researching videos for: {topic_name}...")
            data = generate_topic_data(client, grade, subject, mode, topic_name)
            if data:
                st.session_state.generated_content.append(data)
            progress_bar.progress((i + 1) / len(selected_topics))
        
        status_text.empty()
        st.rerun()

# SECTION 3: RESULTS (The Landing Page Style)
else:
    st.success("✅ Curriculum Generated Successfully!")
    
    # Loop through content
    for idx, item in enumerate(st.session_state.generated_content):
        
        # CARD CONTAINER
        st.markdown(f"""
            <div class="topic-card">
                <div class="topic-title">📌 Topic {idx+1}: {item['title']}</div>
                <p><strong>Overview:</strong> {item['overview']}</p>
            </div>
        """, unsafe_allow_html=True)
        
        # 3-Column Layout: Objectives | Materials | Experiment
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown('<div class="section-header">🎯 Objectives</div>', unsafe_allow_html=True)
            for obj in item['objectives']:
                st.write(f"• {obj}")
                
            st.markdown('<div class="section-header">🧪 Materials</div>', unsafe_allow_html=True)
            for mat in item['materials']:
                st.write(f"• {mat}")

        with col_b:
            st.markdown(f'<div class="section-header">⚡ Experiment: {item["experiment_guide"]["title"]}</div>', unsafe_allow_html=True)
            with st.expander("📝 View Instructions", expanded=True):
                for step in item['experiment_guide']['steps']:
                    st.write(f"1. {step}")

        # VIDEOS SECTION (Now utilizing Real Links)
        st.markdown("---")
        st.markdown('<div class="section-header">🎥 Curated Video Resources</div>', unsafe_allow_html=True)
        
        v_col1, v_col2 = st.columns(2)
        
        with v_col1:
            st.markdown('<p class="video-label">🧠 THEORY & CONCEPTS</p>', unsafe_allow_html=True)
            if item.get('theory_video_url'):
                st.video(item['theory_video_url'])
            else:
                st.error("Video not found.")

        with v_col2:
            st.markdown(f'<p class="video-label">⚡ PRACTICAL DEMO ({mode})</p>', unsafe_allow_html=True)
            if item.get('experiment_video_url'):
                st.video(item['experiment_video_url'])
            else:
                st.error("Video not found.")
        
        st.markdown("<br><br>", unsafe_allow_html=True)