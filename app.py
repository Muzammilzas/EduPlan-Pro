import streamlit as st
import os
import re
import json
from openai import OpenAI
import requests

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EduPlan Pro", page_icon="🎓", layout="wide")

# --- MODERN CSS STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 40px;
        border-radius: 15px;
        margin-bottom: 30px;
    }
    
    .topic-card {
        background: white;
        border-radius: 15px;
        padding: 30px;
        margin: 25px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        border-left: 5px solid #667eea;
    }
    
    .topic-header {
        font-size: 28px;
        font-weight: 700;
        color: #2d3748;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
    }
    
    .topic-number {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        width: 45px;
        height: 45px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 15px;
        font-weight: 700;
        font-size: 20px;
    }
    
    .section-header {
        font-size: 18px;
        font-weight: 600;
        color: #4a5568;
        margin-top: 25px;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }
    
    .overview-box {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-left: 4px solid #667eea;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        font-size: 16px;
        line-height: 1.6;
    }
    
    .objectives-list, .materials-list {
        background: #f7fafc;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    .list-item {
        padding: 10px 0;
        border-bottom: 1px solid #e2e8f0;
        font-size: 15px;
    }
    
    .list-item:last-child {
        border-bottom: none;
    }
    
    .video-section {
        margin: 25px 0;
    }
    
    .video-type-header {
        font-size: 16px;
        font-weight: 600;
        color: #667eea;
        margin-bottom: 15px;
        padding: 10px;
        background: #f7fafc;
        border-radius: 8px;
    }
    
    .video-container {
        margin-bottom: 20px;
    }
    
    .video-info-box {
        background: white;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 8px;
        border: 1px solid #e2e8f0;
    }
    
    .video-title {
        font-weight: 600;
        font-size: 14px;
        color: #2d3748;
        margin-bottom: 5px;
    }
    
    .video-channel {
        font-size: 12px;
        color: #718096;
    }
    
    .experiment-box {
        background: #fffbeb;
        border: 2px solid #fbbf24;
        border-radius: 12px;
        padding: 25px;
        margin: 20px 0;
    }
    
    .experiment-title {
        font-size: 20px;
        font-weight: 600;
        color: #92400e;
        margin-bottom: 15px;
    }
    
    .step-item {
        background: white;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border-left: 3px solid #fbbf24;
        font-size: 15px;
    }
    
    .step-number {
        display: inline-block;
        background: #fbbf24;
        color: white;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        text-align: center;
        line-height: 28px;
        margin-right: 10px;
        font-weight: 600;
        font-size: 14px;
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

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔐 Settings")
    
    api_key_input = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    if api_key_input:
        openai_api_key = api_key_input.strip()
    elif "OPENAI_API_KEY" in st.secrets:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
    else:
        openai_api_key = None
    
    st.divider()
    
    st.markdown("### 📚 About")
    st.caption("🇺🇸 US School Curriculum")
    st.caption("📖 K-12 Grade Levels")
    st.caption("🎬 Embedded YouTube Videos")
    
    st.divider()
    
    if st.button("🔄 Reset / New Search", use_container_width=True):
        st.session_state.topics = []
        st.session_state.generated_content = []
        st.session_state.toc_text = ""
        st.rerun()

# --- HELPER FUNCTIONS ---
def get_openai_client():
    if not openai_api_key:
        st.error("⚠️ Please enter your OpenAI API Key in the sidebar.")
        st.stop()
    return OpenAI(api_key=openai_api_key)

def extract_video_id(url):
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_table_of_contents(client, grade, subject):
    """Generate curriculum topics aligned with US standards."""
    prompt = f"""
You are a US curriculum expert. Generate a Table of Contents for {subject}, Grade {grade}, following US education standards (NGSS for Science, Common Core for Math, etc.).

Generate EXACTLY 8 core topics that are:
- Age-appropriate for Grade {grade} US students
- Aligned with national/state standards
- Sequenced logically (foundational concepts first)
- Cover key concepts for the academic year

Output format STRICTLY (no introduction, no explanation):
1. Topic Name
2. Topic Name
3. Topic Name
4. Topic Name
5. Topic Name
6. Topic Name
7. Topic Name
8. Topic Name

IMPORTANT: Output ONLY the numbered list. No extra text before or after.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def parse_topics(toc_text):
    """Extract clean topic names from numbered list."""
    lines = toc_text.split('\n')
    topics = []
    for line in lines:
        clean_line = re.sub(r'^\d+\.\s*', '', line).strip()
        if clean_line and len(clean_line) > 3:
            topics.append(clean_line)
    return topics

def generate_topic_content(client, grade, subject, mode, topic, sequence_num):
    """Generate comprehensive lesson content with actual YouTube video URLs."""
    
    if mode == "Physical (Classroom)":
        exp_context = "PHYSICAL CLASSROOM LAB"
        exp_guide = "Use standard school science lab equipment (microscopes, beakers, graduated cylinders, safety goggles, etc.)."
        video_guide = "Focus on formal lab demonstrations and proper equipment usage."
    else:
        exp_context = "HOME/VIRTUAL LEARNING"
        exp_guide = "Use ONLY safe, common household items (no chemicals, no sharp objects for young students)."
        video_guide = "Focus on DIY, at-home safe experiments suitable for remote learning."

    MASTER_PROMPT = f"""
You are an expert US curriculum designer creating content for Grade {grade} {subject}.

Topic: {topic}
Mode: {exp_context}
Standards: US Education Standards (NGSS/Common Core aligned)

Create a comprehensive lesson plan following this EXACT structure:

1. TOPIC OVERVIEW
Write 3-4 sentences explaining:
- What this topic is about
- Why it's important for Grade {grade} students
- How it connects to real-world applications

2. LEARNING OBJECTIVES
List exactly 3 specific, measurable objectives using action verbs (Students will be able to...):
- Objective 1
- Objective 2  
- Objective 3

3. REQUIRED MATERIALS
List 5-8 specific materials needed for the experiment.
{exp_guide}

4. HANDS-ON EXPERIMENT
Create an engaging experiment with:
- Experiment Title (creative and descriptive)
- 6-8 detailed, numbered steps that are clear and safe for Grade {grade}

5. RECOMMENDED YOUTUBE VIDEOS WITH REAL URLs
Provide 4 REAL, EXISTING YouTube videos with ACTUAL working URLs.

IMPORTANT INSTRUCTIONS FOR VIDEOS:
- You must provide REAL YouTube video URLs (https://www.youtube.com/watch?v=...)
- These should be actual popular educational videos that exist
- Choose well-known videos from these trusted channels:
  * Khan Academy
  * CrashCourse  
  * TED-Ed
  * SciShow
  * Veritasium
  * National Geographic
  * Amoeba Sisters
  * Bozeman Science
  * The Organic Chemistry Tutor

Video Requirements:
- 2 videos explaining theory/concepts (Type: "Theory")
- 2 videos showing experiments/demonstrations (Type: "Experiment Demo")
{video_guide}

For each video provide:
- title: Exact video title
- channel: Channel name
- url: Full YouTube URL (https://www.youtube.com/watch?v=VIDEO_ID)
- description: What the video covers (1 sentence)
- type: Either "Theory" or "Experiment Demo"

OUTPUT AS VALID JSON:
{{
    "title": "{topic}",
    "overview": "comprehensive overview text...",
    "objectives": [
        "Students will be able to...",
        "Students will be able to...",
        "Students will be able to..."
    ],
    "materials": [
        "Material 1",
        "Material 2",
        "Material 3",
        "Material 4",
        "Material 5"
    ],
    "experiment": {{
        "title": "Experiment Title",
        "steps": [
            "Step 1 description",
            "Step 2 description",
            "Step 3 description",
            "Step 4 description",
            "Step 5 description",
            "Step 6 description"
        ]
    }},
    "videos": [
        {{
            "title": "Real Video Title",
            "channel": "Channel Name",
            "url": "https://www.youtube.com/watch?v=ACTUAL_VIDEO_ID",
            "description": "What this video covers",
            "type": "Theory"
        }},
        {{
            "title": "Real Video Title",
            "channel": "Channel Name",
            "url": "https://www.youtube.com/watch?v=ACTUAL_VIDEO_ID",
            "description": "What this video covers",
            "type": "Theory"
        }},
        {{
            "title": "Real Video Title",
            "channel": "Channel Name",
            "url": "https://www.youtube.com/watch?v=ACTUAL_VIDEO_ID",
            "description": "What this video covers",
            "type": "Experiment Demo"
        }},
        {{
            "title": "Real Video Title",
            "channel": "Channel Name",
            "url": "https://www.youtube.com/watch?v=ACTUAL_VIDEO_ID",
            "description": "What this video covers",
            "type": "Experiment Demo"
        }}
    ]
}}

CRITICAL: 
- Output ONLY valid JSON
- All video URLs must be real working YouTube links
- Use popular educational videos that actually exist
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a US curriculum expert who outputs structured JSON lesson plans with real YouTube video URLs."},
                {"role": "user", "content": MASTER_PROMPT}
            ],
            temperature=0.7
        )
        
        data = json.loads(response.choices[0].message.content)
        return data, response.usage.total_tokens
    
    except Exception as e:
        st.error(f"Error generating content: {e}")
        return None, 0

def render_embedded_video(video):
    """Render an embedded YouTube video player."""
    video_url = video.get('url', '')
    video_id = extract_video_id(video_url)
    
    if video_id:
        # Display video info
        st.markdown(f"""
            <div class="video-info-box">
                <div class="video-title">📺 {video.get('title', 'Educational Video')}</div>
                <div class="video-channel">by {video.get('channel', 'YouTube')}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Embed the video using st.video or iframe
        try:
            # Method 1: Using Streamlit's built-in video player
            st.video(f"https://www.youtube.com/watch?v={video_id}")
        except:
            # Method 2: Fallback to iframe
            st.markdown(f"""
                <iframe width="100%" height="315" 
                src="https://www.youtube.com/embed/{video_id}" 
                frameborder="0" 
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
                </iframe>
            """, unsafe_allow_html=True)
        
        st.caption(f"📝 {video.get('description', '')}")
        st.markdown("---")
    else:
        st.warning(f"⚠️ Could not load video: {video.get('title', 'Unknown')}")

# --- MAIN APP ---
st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; font-size: 42px;">🎓 EduPlan Pro</h1>
        <p style="margin:10px 0 0 0; font-size: 18px; opacity: 0.9;">AI-Powered US Curriculum Designer</p>
    </div>
""", unsafe_allow_html=True)

# STEP 1: Input Form
if not st.session_state.topics:
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        subject = st.text_input("📚 Enter Subject", placeholder="Physics, Biology, Chemistry, etc.")
    
    with col2:
        grade = st.text_input("🎯 Grade Level", placeholder="e.g. 8")
    
    with col3:
        mode = st.radio("🏫 Learning Mode", ["Physical (Classroom)", "Online (Virtual)"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button("🚀 Generate Curriculum", type="primary", use_container_width=True):
            if not subject or not grade:
                st.warning("⚠️ Please enter both Subject and Grade Level")
            else:
                client = get_openai_client()
                with st.spinner("🧠 Creating your curriculum based on US education standards..."):
                    toc = get_table_of_contents(client, grade, subject)
                    if toc:
                        st.session_state.toc_text = toc
                        st.session_state.topics = parse_topics(toc)
                        if st.session_state.topics:
                            st.rerun()
                        else:
                            st.error("Failed to parse topics. Please try again.")

# STEP 2: Topic Selection
elif not st.session_state.generated_content:
    st.success(f"✅ Curriculum Generated Successfully for **{subject} - Grade {grade}**")
    
    # Display TOC nicely
    with st.expander("📖 View Complete Table of Contents", expanded=True):
        for i, topic in enumerate(st.session_state.topics, 1):
            st.markdown(f"**{i}.** {topic}")
    
    st.markdown("---")
    st.markdown("### 📝 Step 2: Generate Detailed Lesson Plans")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selection_type = st.radio(
            "Choose what to generate:",
            ["All Topics (Recommended)", "Select Specific Topics"]
        )
    
    selected_topics = []
    
    if selection_type == "Select Specific Topics":
        with col2:
            chosen = st.multiselect(
                "Select topics:", 
                st.session_state.topics
            )
            selected_topics = [(st.session_state.topics.index(t)+1, t) for t in chosen]
    else:
        selected_topics = [(i+1, t) for i, t in enumerate(st.session_state.topics)]
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button(f"✨ Generate {len(selected_topics)} Lesson Plan(s)", type="primary", use_container_width=True):
        if not selected_topics:
            st.warning("⚠️ Please select at least one topic")
        else:
            client = get_openai_client()
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i, (seq, topic_name) in enumerate(selected_topics):
                status.info(f"⏳ Generating: **{topic_name}** ({i+1}/{len(selected_topics)})")
                
                data, tokens = generate_topic_content(client, grade, subject, mode, topic_name, seq)
                
                if data:
                    st.session_state.generated_content.append(data)
                
                progress_bar.progress((i + 1) / len(selected_topics))
            
            status.success("✅ All lesson plans generated!")
            st.balloons()
            st.rerun()

# STEP 3: Display Generated Content
else:
    st.success(f"🎉 Complete Curriculum Ready for **{subject} - Grade {grade}**")
    
    # Display each topic
    for idx, item in enumerate(st.session_state.generated_content):
        
        st.markdown(f"""
            <div class="topic-card">
                <div class="topic-header">
                    <span class="topic-number">{idx+1}</span>
                    <span>{item.get('title', 'Untitled Topic')}</span>
                </div>
        """, unsafe_allow_html=True)
        
        # Overview
        st.markdown(f"""
            <div class="overview-box">
                <strong style="color: #667eea;">📖 Overview</strong><br><br>
                {item.get('overview', 'No overview available')}
            </div>
        """, unsafe_allow_html=True)
        
        # Two columns: Objectives & Materials
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="section-header">🎯 Learning Objectives</div>', unsafe_allow_html=True)
            st.markdown('<div class="objectives-list">', unsafe_allow_html=True)
            for obj in item.get('objectives', []):
                st.markdown(f'<div class="list-item">✓ {obj}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="section-header">🧪 Required Materials</div>', unsafe_allow_html=True)
            st.markdown('<div class="materials-list">', unsafe_allow_html=True)
            for mat in item.get('materials', []):
                st.markdown(f'<div class="list-item">• {mat}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Videos Section - EMBEDDED PLAYERS
        st.markdown('<div class="section-header">🎬 Educational Videos</div>', unsafe_allow_html=True)
        
        videos = item.get('videos', [])
        if videos:
            # Separate by type
            theory_videos = [v for v in videos if v.get('type') == 'Theory']
            experiment_videos = [v for v in videos if v.get('type') == 'Experiment Demo']
            
            if theory_videos:
                st.markdown('<div class="video-type-header">🧠 Conceptual Learning Videos</div>', unsafe_allow_html=True)
                for video in theory_videos:
                    render_embedded_video(video)
            
            if experiment_videos:
                st.markdown('<div class="video-type-header">🔬 Experiment & Demonstration Videos</div>', unsafe_allow_html=True)
                for video in experiment_videos:
                    render_embedded_video(video)
        
        # Experiment Section
        exp = item.get('experiment', {})
        if exp:
            st.markdown(f"""
                <div class="experiment-box">
                    <div class="experiment-title">⚗️ Hands-On Activity: {exp.get('title', 'Experiment')}</div>
            """, unsafe_allow_html=True)
            
            for i, step in enumerate(exp.get('steps', []), 1):
                st.markdown(f"""
                    <div class="step-item">
                        <span class="step-number">{i}</span>
                        {step}
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br><br>", unsafe_allow_html=True)
