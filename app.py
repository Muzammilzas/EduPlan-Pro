import streamlit as st
import os
import re
import json
from openai import OpenAI

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EduPlan Video Tool", page_icon="🎬", layout="wide")

# --- CSS STYLING (Minimal & Clean) ---
st.markdown("""
    <style>
    .main-header {text-align: center; color: #333;}
    .video-label {font-weight: bold; color: #444; margin-bottom: 5px;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    footer {visibility: hidden;}
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px; color: #555; }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b; color: white; }
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

    if st.button("🗑️ Clear / Reset"):
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
    # Reduced to 5 topics for the demo to ensure higher quality per topic
    prompt = f"""
    Generate a list of 5 key topics for {subject}, Grade {grade}.
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

    # --- ADVANCED PROMPT FOR VIDEOS ---
    MASTER_PROMPT = f"""
    You are a Video Recommendation Engine for Teachers.
    Subject: {subject} | Grade: {grade} | Topic: {topic} | Mode: {exp_context}

    YOUR GOAL: Provide valid YouTube links for this topic.
    
    RULES:
    1. **Sources:** Khan Academy, CrashCourse, TED-Ed, SciShow, Veritasium, National Geographic, SpanglerScience, Steve Mould.
    2. **No Duplicates:** The Theory video and Experiment video MUST be different.
    3. **Accuracy:** If you are not 100% sure a specific URL exists, provide a generic search query instead.
    
    OUTPUT JSON STRUCTURE:
    {{
        "title": "{topic}",
        "summary": "1 sentence summary.",
        "theory_videos": [
            {{"title": "Detailed Theory Lesson", "url": "https://www.youtube.com/watch?v=..."}},
            {{"title": "Visual Explanation", "url": "https://www.youtube.com/watch?v=..."}}
        ],
        "experiment_videos": [
            {{"title": "{exp_context} Demonstration 1", "url": "https://www.youtube.com/watch?v=..."}},
            {{"title": "{exp_context} Demonstration 2", "url": "https://www.youtube.com/watch?v=..."}}
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

st.title("🎬 EduPlan: Video Recommender")
st.caption("AI-Powered Curriculum & Video Finder")

# 1. TOP BAR INPUTS (Minimal)
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
with col1:
    subject = st.text_input("Subject", placeholder="e.g. Physics")
with col2:
    grade = st.text_input("Grade", placeholder="e.g. 8")
with col3:
    mode = st.selectbox("Mode", ["Physical (Classroom)", "Online (Home)"])
with col4:
    st.write("") # Spacer
    if st.button("🚀 Find Topics", type="primary"):
        if not subject or not grade:
            st.warning("Enter Subject & Grade")
        else:
            client = get_client()
            with st.spinner("Searching..."):
                toc = get_table_of_contents(client, grade, subject)
                if toc:
                    st.session_state.toc_text = toc
                    st.session_state.topics = parse_topics(toc)
                    st.session_state.generated_content = [] # Clear old content
                    st.rerun()

st.divider()

# 2. SELECTION & GENERATION
if st.session_state.topics and not st.session_state.generated_content:
    st.subheader(f"Select Topics for {subject}")
    
    # Selection UI
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        selected_topics_list = st.multiselect("Choose topics to generate:", st.session_state.topics, default=st.session_state.topics)
    
    with col_s2:
        if st.button(f"✨ Get Videos ({len(selected_topics_list)})", type="primary", use_container_width=True):
            client = get_client()
            progress_bar = st.progress(0)
            
            # Map selection back to index
            selected_indices = [(i+1, t) for i, t in enumerate(st.session_state.topics) if t in selected_topics_list]
            
            for i, (seq, topic_name) in enumerate(selected_indices):
                data, tokens = generate_topic_json(client, grade, subject, mode, topic_name, seq)
                if data:
                    st.session_state.generated_content.append(data)
                progress_bar.progress((i + 1) / len(selected_indices))
            
            st.rerun()

# 3. RESULTS DISPLAY (Minimal & Video-Focused)
if st.session_state.generated_content:
    
    # Tabs for each topic
    topic_names = [item['title'] for item in st.session_state.generated_content]
    tabs = st.tabs(topic_names)

    for i, tab in enumerate(tabs):
        item = st.session_state.generated_content[i]
        
        with tab:
            st.info(f"**Topic Summary:** {item.get('summary')}")
            
            # --- SECTION 1: THEORY VIDEOS ---
            st.markdown("### 🧠 Theory & Concepts")
            t_cols = st.columns(2)
            for idx, vid in enumerate(item.get('theory_videos', [])):
                with t_cols[idx % 2]:
                    st.markdown(f"**{vid.get('title')}**")
                    # Smart Embed
                    if "youtube" in vid.get('url'):
                        st.video(vid.get('url'))
                    else:
                        st.write(f"🔗 [Watch Video]({vid.get('url')})")

            # --- SECTION 2: EXPERIMENT VIDEOS ---
            st.markdown("---")
            st.markdown(f"### 🧪 Practical Experiments ({mode})")
            e_cols = st.columns(2)
            for idx, vid in enumerate(item.get('experiment_videos', [])):
                with e_cols[idx % 2]:
                    st.markdown(f"**{vid.get('title')}**")
                    if "youtube" in vid.get('url'):
                        st.video(vid.get('url'))
                    else:
                        st.write(f"🔗 [Watch Video]({vid.get('url')})")

            # --- SECTION 3: INSTRUCTIONS (Collapsed) ---
            st.markdown("---")
            with st.expander("📝 View Experiment Instructions & Materials"):
                st.markdown("**Materials Needed:**")
                for mat in item.get('experiment_guide', {}).get('materials', []):
                    st.markdown(f"- {
