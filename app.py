import streamlit as st
import os
import re
import json
from openai import OpenAI

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
    
    .video-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;
        margin: 20px 0;
    }
    
    .video-card {
        background: white;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s, box-shadow 0.2s;
        border: 1px solid #e2e8f0;
    }
    
    .video-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .video-thumbnail {
        position: relative;
        background: #000;
        height: 180px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .video-info {
        padding: 15px;
    }
    
    .video-title {
        font-weight: 600;
        font-size: 14px;
        color: #2d3748;
        margin-bottom: 8px;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .video-channel {
        font-size: 12px;
        color: #718096;
        margin-bottom: 12px;
    }
    
    .watch-button {
        display: inline-block;
        background: #FF0000;
        color: white;
        padding: 10px 20px;
        border-radius: 6px;
        text-decoration: none;
        font-weight: 600;
        font-size: 13px;
        text-align: center;
        width: 100%;
        transition: background 0.2s;
    }
    
    .watch-button:hover {
        background: #CC0000;
        color: white;
        text-decoration: none;
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
    st.header("🔐 API Configuration")
    
    api_key_input = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    if api_key_input:
        openai_api_key = api_key_input.strip()
    elif "OPENAI_API_KEY" in st.secrets:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
    else:
        openai_api_key = None
    
    st.divider()
    
    st.markdown("### 📚 About EduPlan Pro")
    st.caption("Designed for US school curriculum standards (K-12)")
    
    st.divider()
    
    if st.button("🔄 Start New Curriculum", use_container_width=True):
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
        # Remove number and dot
        clean_line = re.sub(r'^\d+\.\s*', '', line).strip()
        if clean_line and len(clean_line) > 3:  # Ignore very short lines
            topics.append(clean_line)
    return topics

def generate_topic_content(client, grade, subject, mode, topic, sequence_num):
    """Generate comprehensive lesson content with curated video recommendations."""
    
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

5. RECOMMENDED EDUCATIONAL VIDEOS
Find 4 HIGH-QUALITY videos from these trusted sources ONLY:
- Khan Academy
- CrashCourse
- TED-Ed
- SciShow
- Veritasium
- National Geographic
- Amoeba Sisters (for Biology)
- The Organic Chemistry Tutor (for Chemistry/Physics)

For each video, provide:
- Exact video title (real videos only)
- Channel name
- Brief description of what the video covers (1 sentence)
- Video type: "Theory" or "Experiment Demo"

Video distribution:
- 2 videos explaining theory/concepts
- 2 videos showing experiments/demonstrations
{video_guide}

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
            "title": "Exact Video Title",
            "channel": "Channel Name",
            "description": "What this video covers",
            "type": "Theory",
            "search_query": "channel name + video title keywords"
        }},
        {{
            "title": "Exact Video Title",
            "channel": "Channel Name", 
            "description": "What this video covers",
            "type": "Theory",
            "search_query": "channel name + video title keywords"
        }},
        {{
            "title": "Exact Video Title",
            "channel": "Channel Name",
            "description": "What this video covers", 
            "type": "Experiment Demo",
            "search_query": "channel name + video title keywords"
        }},
        {{
            "title": "Exact Video Title",
            "channel": "Channel Name",
            "description": "What this video covers",
            "type": "Experiment Demo", 
            "search_query": "channel name + video title keywords"
        }}
    ]
}}

CRITICAL: Output ONLY valid JSON. No markdown, no explanation, just the JSON object.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a US curriculum expert who outputs structured JSON lesson plans."},
                {"role": "user", "content": MASTER_PROMPT}
            ],
            temperature=0.7
        )
        
        data = json.loads(response.choices[0].message.content)
        return data, response.usage.total_tokens
    
    except Exception as e:
        st.error(f"Error generating content: {e}")
        return None, 0

def render_video_card(video, index):
    """Render a modern video card with YouTube search link."""
    search_query = video.get('search_query', f"{video.get('channel', '')} {video.get('title', '')}").replace(' ', '+')
    youtube_search_url = f"https://www.youtube.com/results?search_query={search_query}"
    
    video_type_emoji = "🧠" if video.get('type') == 'Theory' else "🔬"
    
    st.markdown(f"""
        <div class="video-card">
            <div class="video-thumbnail">
                <div style="font-size: 48px;">{video_type_emoji}</div>
            </div>
            <div class="video-info">
                <div class="video-title">{video.get('title', 'Educational Video')}</div>
                <div class="video-channel">📺 {video.get('channel', 'YouTube')}</div>
                <p style="font-size: 12px; color: #4a5568; margin-bottom: 12px;">{video.get('description', '')}</p>
                <a href="{youtube_search_url}" target="_blank" class="watch-button">
                    ▶ Watch on YouTube
                </a>
            </div>
        </div>
    """, unsafe_allow_html=True)

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
        subject = st.text_input("📚 Subject", placeholder="Physics, Biology, Chemistry, etc.", key="subject_input")
    
    with col2:
        grade = st.text_input("🎯 Grade Level", placeholder="e.g., 8", key="grade_input")
    
    with col3:
        mode = st.selectbox("🏫 Learning Mode", ["Physical (Classroom)", "Online (Virtual)"])
    
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
    st.success(f"✅ Curriculum Generated: **{subject} - Grade {grade}**")
    
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
            ["All Topics (Recommended)", "Select Specific Topics"],
            key="selection_type"
        )
    
    selected_topics = []
    
    if selection_type == "Select Specific Topics":
        with col2:
            chosen = st.multiselect(
                "Select topics:", 
                st.session_state.topics,
                key="topic_selector"
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
    st.success(f"🎉 Complete Curriculum Ready!")
    
    # Display each topic as a beautiful card
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
        
        # Videos Section
        st.markdown('<div class="section-header">🎬 Recommended Educational Videos</div>', unsafe_allow_html=True)
        
        videos = item.get('videos', [])
        if videos:
            # Separate by type
            theory_videos = [v for v in videos if v.get('type') == 'Theory']
            experiment_videos = [v for v in videos if v.get('type') == 'Experiment Demo']
            
            if theory_videos:
                st.markdown("**🧠 Conceptual Learning Videos**")
                cols = st.columns(len(theory_videos))
                for i, video in enumerate(theory_videos):
                    with cols[i]:
                        render_video_card(video, i)
            
            if experiment_videos:
                st.markdown("**🔬 Experiment & Demonstration Videos**")
                cols = st.columns(len(experiment_videos))
                for i, video in enumerate(experiment_videos):
                    with cols[i]:
                        render_video_card(video, i)
        
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
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close topic-card
        st.markdown("<br>", unsafe_allow_html=True)
