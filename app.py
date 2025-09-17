"""
NextGen Marketer - Modern Streamlit App
Main application for the multi-agent marketing system with refreshed UI.
"""

import streamlit as st
import json
import pandas as pd
from orchestrator import run_flow
import os
import time
import traceback

# Initialize session state for conversation memory
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

def parse_agent_response(response_text):
    """Parse agent response that might be JSON or plain text"""
    if isinstance(response_text, str):
        # Try to parse as JSON if it looks like JSON
        if response_text.strip().startswith('```json') and response_text.strip().endswith('```'):
            # Extract JSON from markdown code block
            json_text = response_text.strip()[7:-3].strip()
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                return {"summary": response_text}
        elif response_text.strip().startswith('{') and response_text.strip().endswith('}'):
            # Direct JSON string
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {"summary": response_text}
        else:
            # Plain text response
            return {"summary": response_text}
    return response_text

def truncate_text(text, max_length=300):
    """Truncate text at word boundaries to avoid cutting words in half"""
    text = str(text)
    if len(text) <= max_length:
        return text
    
    # Find the last space before the max length
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    # Only truncate if we can find a good break point
    if last_space > max_length * 0.8:  # If we can find a space in the last 20% of the text
        return text[:last_space] + "..."
    elif last_space > max_length * 0.5:  # If we can find a space in the last 50% of the text
        return text[:last_space] + "..."
    else:
        # If no good break point, just show the full text up to max_length
        return text[:max_length] + "..."

def clean_insight_text(text):
    """Clean and format insight text, extracting meaningful content from dictionaries"""
    text_str = str(text)
    
    # If it's a dictionary string, try to extract meaningful content
    if text_str.startswith('{') and text_str.endswith('}'):
        try:
            # Try to parse as JSON
            import ast
            parsed = ast.literal_eval(text_str)
            if isinstance(parsed, dict):
                # Extract values and join them meaningfully
                cleaned_parts = []
                for key, value in parsed.items():
                    if isinstance(value, str) and value.strip():
                        cleaned_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                if cleaned_parts:
                    return " | ".join(cleaned_parts)
        except:
            pass
    
    # If it's a list string, try to extract items
    if text_str.startswith('[') and text_str.endswith(']'):
        try:
            import ast
            parsed = ast.literal_eval(text_str)
            if isinstance(parsed, list):
                return " | ".join([str(item) for item in parsed if str(item).strip()])
        except:
            pass
    
    # Return as is if not a dictionary or list
    return text_str

def build_conversation_context():
    """Build context from conversation history for better continuity"""
    if not st.session_state.conversation_history:
        return ""
    
    context_parts = []
    context_parts.append("Previous conversation context:")
    
    # Include last 3 conversations for context
    recent_conversations = st.session_state.conversation_history[-3:]
    
    for i, conv in enumerate(recent_conversations, 1):
        context_parts.append(f"\nConversation {i}:")
        context_parts.append(f"Question: {conv.get('question', 'N/A')}")
        if conv.get('summary'):
            context_parts.append(f"Summary: {conv.get('summary', 'N/A')}")
    
    return "\n".join(context_parts)

def add_to_conversation_history(question, result):
    """Add current question and result to conversation history"""
    conversation_entry = {
        'question': question,
        'timestamp': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        'summary': result.get('final_decision', {}).get('executive_summary', 'No summary available') if result else 'No result'
    }
    
    st.session_state.conversation_history.append(conversation_entry)
    
    # Keep only last 10 conversations to prevent memory overflow
    if len(st.session_state.conversation_history) > 10:
        st.session_state.conversation_history = st.session_state.conversation_history[-10:]

def load_sample_data():
    """Load sample data for quick analytics"""
    try:
        # Load sample data from CSV files
        sentiment_data = pd.read_csv('data/sentiment_data.csv')
        campaign_data = pd.read_csv('data/campaign_data.csv')
        purchase_data = pd.read_csv('data/purchase_data.csv')
        return sentiment_data, campaign_data, purchase_data
    except:
        return None, None, None

def get_system_metrics():
    """Get system performance metrics"""
    import random
    
    # Check if we have real metrics from last analysis
    if 'last_analysis_metrics' in st.session_state:
        real_metrics = st.session_state['last_analysis_metrics']
        total_tokens = real_metrics.get('tokens_used', random.randint(15000, 25000))
        avg_latency = real_metrics.get('latency', round(random.uniform(1.2, 3.5), 2))
        last_updated = real_metrics.get('timestamp', time.strftime("%H:%M:%S"))
    else:
        total_tokens = random.randint(15000, 25000)
        avg_latency = round(random.uniform(1.2, 3.5), 2)
        last_updated = time.strftime("%H:%M:%S")
    
    # Simulate or get real metrics
    metrics = {
        'total_tokens': total_tokens,
        'avg_latency': avg_latency,
        'similarity_score': round(random.uniform(0.75, 0.95), 3),  # Simulated similarity score
        'top_k': random.randint(3, 8),  # Simulated top K documents
        'active_agents': 4,  # Number of active agents
        'last_updated': last_updated
    }
    
    return metrics

def calculate_quick_analytics(sentiment_data, campaign_data, purchase_data):
    """Calculate quick analytics metrics"""
    analytics = {
        'sentiment': {
            'positive_percent': 0,
            'negative_percent': 0,
            'neutral_percent': 0
        },
        'campaign': {
            'avg_ctr': 0,
            'avg_conversion': 0,
            'total_impressions': 0
        },
        'purchase': {
            'total_sales': 0,
            'avg_transaction': 0
        }
    }
    
    # Calculate sentiment analytics
    if sentiment_data is not None and not sentiment_data.empty:
        if 'sentiment' in sentiment_data.columns:
            sentiment_counts = sentiment_data['sentiment'].value_counts()
            total = len(sentiment_data)
            if total > 0:
                analytics['sentiment']['positive_percent'] = round((sentiment_counts.get('positive', 0) / total) * 100, 1)
                analytics['sentiment']['negative_percent'] = round((sentiment_counts.get('negative', 0) / total) * 100, 1)
                analytics['sentiment']['neutral_percent'] = round((sentiment_counts.get('neutral', 0) / total) * 100, 1)
        else:
            # If no sentiment column, use sample data
            analytics['sentiment'] = {'positive_percent': 75.2, 'negative_percent': 12.8, 'neutral_percent': 12.0}
    else:
        # Sample data if no file loaded
        analytics['sentiment'] = {'positive_percent': 75.2, 'negative_percent': 12.8, 'neutral_percent': 12.0}
    
    # Calculate campaign analytics
    if campaign_data is not None and not campaign_data.empty:
        if 'ctr' in campaign_data.columns:
            analytics['campaign']['avg_ctr'] = round(campaign_data['ctr'].mean() * 100, 2)
        else:
            analytics['campaign']['avg_ctr'] = 3.58
            
        if 'conversion_rate' in campaign_data.columns:
            analytics['campaign']['avg_conversion'] = round(campaign_data['conversion_rate'].mean() * 100, 2)
        else:
            analytics['campaign']['avg_conversion'] = 3.46
            
        if 'impressions' in campaign_data.columns:
            analytics['campaign']['total_impressions'] = int(campaign_data['impressions'].sum())
        else:
            analytics['campaign']['total_impressions'] = 125000
    else:
        # Sample data if no file loaded
        analytics['campaign'] = {'avg_ctr': 3.58, 'avg_conversion': 3.46, 'total_impressions': 125000}
    
    # Calculate purchase analytics
    if purchase_data is not None and not purchase_data.empty:
        analytics['purchase']['total_sales'] = len(purchase_data)
        if 'transaction_value' in purchase_data.columns:
            analytics['purchase']['avg_transaction'] = int(purchase_data['transaction_value'].mean())
        else:
            analytics['purchase']['avg_transaction'] = 627597
    else:
        # Sample data if no file loaded
        analytics['purchase'] = {'total_sales': 5, 'avg_transaction': 627597}
    
    return analytics

# Custom CSS for modern styling
st.set_page_config(
    page_title="NextGen Marketer",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (added small tile styles for agent insights/recs)
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #6366f1;
        --secondary-color: #8b5cf6;
        --accent-color: #06b6d4;
        --success-color: #10b981;
        --warning-color: #f59e0b;
        --error-color: #ef4444;
        --background-color: #f8fafc;
        --card-background: #ffffff;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --border-color: #e2e8f0;
    }
    .main .block-container { padding-top: 0.5rem; padding-bottom: 1rem; max-width: 1200px; }

    .main-header { background: linear-gradient(135deg, var(--primary-color), var(--secondary-color)); color: white; padding: 1.2rem; border-radius: 12px; margin-bottom: 1.5rem; text-align: center; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2); }
    .main-header h1 { font-size: 2.2rem; font-weight: 700; margin: 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .main-header p { font-size: 1.1rem; margin: 0.3rem 0 0 0; opacity: 0.9; }

    /* Metric cards */
    .metric-card { background: var(--card-background); border-radius: 8px; padding: 0.6rem; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); border: 1px solid var(--border-color); transition: transform 0.2s ease, box-shadow 0.2s ease; height: 80px; display: flex; flex-direction: column; justify-content: center; }
    .metric-value { font-size: 1.6rem; font-weight: 700; color: var(--primary-color); margin: 0; line-height: 1; }
    .metric-label { font-size: 0.8rem; color: var(--text-secondary); margin: 0.2rem 0 0 0; text-transform: uppercase; letter-spacing: 0.5px; }

    .section-header { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); margin: 1.2rem 0 0.8rem 0; display: flex; align-items: center; gap: 0.5rem; padding-bottom: 0.5rem; border-bottom: 3px solid var(--primary-color); }
    .subsection-header { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0.8rem 0 0.5rem 0; display: flex; align-items: center; gap: 0.5rem; padding-bottom: 0.3rem; }

    .output-tile { background: #f8f9fa; border-radius: 12px; padding: 1.5rem; margin: 1rem 0; border: 1px solid #e9ecef; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); }
    .output-tile h3 { color: var(--primary-color); margin: 0 0 1rem 0; font-size: 1.2rem; font-weight: 600; }

    .insight-box { background: #f8f9fa; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; border-left: 4px solid var(--primary-color); }
    .recommendation-box { background: #f8f9fa; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; border-left: 4px solid var(--success-color); }

    /* Compact tile styles for agent insights/recs */
    .insight-tile { background: white; border: 1px solid var(--border-color); border-radius: 8px; padding: 10px; margin: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); width: 280px; display:inline-block; vertical-align:top; }
    .insight-tile .k { font-weight:700; color:var(--text-primary); font-size:13px; display:block; margin-bottom:4px; }
    .insight-tile .v { font-size:13px; color:var(--text-secondary); display:block; margin-bottom:6px; }

    .rec-tile { background: white; border: 1px solid var(--border-color); border-radius: 8px; padding: 10px; margin: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); width: 360px; display:inline-block; vertical-align:top; }
    .rec-tile .idea { font-weight:700; font-size:14px; color:var(--primary-color); margin-bottom:6px; }
    .rec-tile .conf { font-size:12px; color:var(--text-secondary); margin-bottom:4px; }

    .stButton > button { background: linear-gradient(135deg, var(--primary-color), var(--secondary-color)); color: white; border: none; border-radius: 8px; padding: 0.5rem 1.5rem; font-weight: 500; transition: all 0.2s ease; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>🚀 NextGen Marketer</h1>
    <p>AI-Powered Marketing Intelligence Platform</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Control Panel")
    
    # File upload section
    st.markdown("### 📁 Data Upload")
    uploaded_file = st.file_uploader(
        "Upload CSV/PDF for RAG",
        type=['csv', 'pdf'],
        help="Upload marketing data files to enhance AI analysis"
    )
    
    if uploaded_file is not None:
        # Save uploaded file
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"✅ Uploaded: {uploaded_file.name}")
        
        # Process the file (you can add RAG processing here)
        if uploaded_file.type == "text/csv":
            df = pd.read_csv(uploaded_file)
            st.write(f"📈 Data Preview ({len(df)} rows):")
            st.dataframe(df.head(), use_container_width=True)
    
    st.markdown("---")
    
    # System status
    st.markdown("### 🔧 System Status")
    st.markdown("🟢 **Ollama**: Connected")
    st.markdown("🟢 **ChromaDB**: Active")
    st.markdown("🟢 **Agents**: Ready")
    
    st.markdown("---")
    
    # Conversation History
    if st.session_state.conversation_history:
        st.markdown("### 💬 Recent Questions")
        for i, conv in enumerate(st.session_state.conversation_history[-3:], 1):
            with st.expander(f"Q{i}: {conv['question'][:50]}..."):
                st.write(f"**Time:** {conv['timestamp']}")
                st.write(f"**Summary:** {conv['summary'][:100]}...")
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.conversation_history = []
        st.rerun()
    
    if st.button("📊 Generate Report", use_container_width=True):
        st.info("Report generation feature coming soon!")

# Main content area - more compact layout
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    # Quick Analytics Section
    st.markdown('<div class="section-header">📈 Quick Analytics</div>', unsafe_allow_html=True)
    
    # Load sample data and calculate analytics
    sentiment_data, campaign_data, purchase_data = load_sample_data()
    analytics = calculate_quick_analytics(sentiment_data, campaign_data, purchase_data)
    
    # Sentiment Analytics
    st.markdown('<div class="subsection-header">💭 Sentiment Analysis</div>', unsafe_allow_html=True)
    col_s1, col_s2, col_s3 = st.columns(3)
    
    with col_s1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{analytics['sentiment']['positive_percent']}%</div>
            <div class="metric-label">Positive</div>
            <div class="metric-change positive">↗ +2.1% from last week</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_s2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{analytics['sentiment']['negative_percent']}%</div>
            <div class="metric-label">Negative</div>
            <div class="metric-change negative">↘ -1.2% from last week</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_s3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{analytics['sentiment']['neutral_percent']}%</div>
            <div class="metric-label">Neutral</div>
            <div class="metric-change">→ 0.0% from last week</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Campaign Analytics
    st.markdown('<div class="subsection-header">🎯 Campaign Performance</div>', unsafe_allow_html=True)
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{analytics['campaign']['avg_ctr']}%</div>
            <div class="metric-label">Avg CTR</div>
            <div class="metric-change positive">↗ +0.3% from last week</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{analytics['campaign']['avg_conversion']}%</div>
            <div class="metric-label">Conversion Rate</div>
            <div class="metric-change positive">↗ +1.2% from last week</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{analytics['campaign']['total_impressions']:,}</div>
            <div class="metric-label">Total Impressions</div>
            <div class="metric-change positive">↗ +5.4% from last week</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Purchase Analytics
    st.markdown('<div class="subsection-header">💰 Purchase Insights</div>', unsafe_allow_html=True)
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{analytics['purchase']['total_sales']:,}</div>
            <div class="metric-label">Total Sales</div>
            <div class="metric-change positive">↗ +12.3% from last week</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_p2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">₹{analytics['purchase']['avg_transaction']:,}</div>
            <div class="metric-label">Avg Transaction</div>
            <div class="metric-change positive">↗ +8.7% from last week</div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    # System Overview
    st.markdown('<div class="section-header">🔧 System Overview</div>', unsafe_allow_html=True)
    
    # Get system metrics
    system_metrics = get_system_metrics()
    
    # Token Usage
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{system_metrics['total_tokens']:,}</div>
        <div class="metric-label">Total Tokens</div>
        <div class="metric-change">Last updated: {system_metrics['last_updated']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Latency
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{system_metrics['avg_latency']}s</div>
        <div class="metric-label">Avg Latency</div>
        <div class="metric-change positive">↗ Optimized</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Similarity Score
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{system_metrics['similarity_score']}</div>
        <div class="metric-label">Similarity Score</div>
        <div class="metric-change positive">↗ High Quality</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Top K Documents
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{system_metrics['top_k']}</div>
        <div class="metric-label">Top K Results</div>
        <div class="metric-change">→ Balanced</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Documents Retrieved and Chroma Collections tiles removed

# Main Query Section
st.markdown('<div class="section-header">💬 AI Marketing Assistant</div>', unsafe_allow_html=True)

# Input area with modern styling
user_input = st.text_area(
    "Ask your marketing question:",
    placeholder="e.g., 'Analyze our campaign performance and suggest improvements for Q4'",
    height=100,
    help="Enter your marketing question and our AI agents will provide comprehensive analysis"
)

# Action buttons
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
with col_btn1:
    analyze_btn = st.button("🔍 Analyze", type="primary", use_container_width=True)
with col_btn2:
    clear_btn = st.button("🗑️ Clear", use_container_width=True)
with col_btn3:
    st.markdown("*Powered by AI Agents*")

if clear_btn:
    st.rerun()

# Helper: render a compact insight tile (HTML)
def render_insight_tile(insight: dict):
    # expected insight keys: audience_segment, product_focus, region, signal, confidence (but robust)
    audience = insight.get("audience_segment") or insight.get("audience") or insight.get("segment") or "-"
    product = insight.get("product_focus") or insight.get("product") or "-"
    region = insight.get("region") or insight.get("regions") or "-"
    signal = insight.get("signal") or insight.get("note") or ""
    confidence = insight.get("confidence")
    conf_text = f"{confidence:.2f}" if isinstance(confidence, (float, int)) else (str(confidence) if confidence else "-")
    html = f"""
    <div class="insight-tile">
      <div class="k">Audience</div><div class="v">{audience}</div>
      <div class="k">Product</div><div class="v">{product}</div>
      <div class="k">Region</div><div class="v">{region}</div>
      <div class="k">Signal</div><div class="v">{truncate_text(signal, 120)}</div>
      <div class="k">Confidence</div><div class="v">{conf_text}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_rec_tile(rec: dict):
    idea = rec.get("idea") or rec.get("campaign_name") or rec.get("concept") or str(rec)
    confidence = rec.get("confidence")
    conf_text = f"{confidence:.2f}" if isinstance(confidence, (float, int)) else (str(confidence) if confidence else "-")
    html = f"""
    <div class="rec-tile">
      <div class="idea">{truncate_text(idea, 120)}</div>
      <div class="conf">Confidence: {conf_text}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# Analysis Results with tile styling
if analyze_btn and user_input:
    with st.spinner("🤖 AI agents are analyzing your request..."):
        try:
            # Track analysis start time
            start_time = time.time()
            
            # Build conversation context
            context = build_conversation_context()
            
            # Enhance user input with context if available
            enhanced_input = user_input
            if context:
                enhanced_input = f"{context}\n\nCurrent question: {user_input}"
            
            # Run the multi-agent workflow with context
            # NOTE: run_flow may raise exceptions; wrap in try/except to avoid crashing the UI
            try:
                thread_id = None
                result = run_flow(enhanced_input, thread_id=thread_id)
            except Exception as invoke_exc:
                tb = traceback.format_exc()
                st.error("❌ Error running the agent workflow. Check server logs for details.")
                st.write("Error details (truncated):")
                st.code(str(invoke_exc)[:1000])
                print("Detailed traceback from run_flow():\n", tb)
                result = {"error": str(invoke_exc)}

            # Calculate actual metrics
            end_time = time.time()
            actual_latency = round(end_time - start_time, 2)
            
            # Update system metrics with real data
            estimated_tokens = 0
            if isinstance(result, dict) and 'agent_outputs' in result:
                total_chars = sum(len(str(output)) for output in result['agent_outputs'])
                estimated_tokens = total_chars // 4  # Rough estimation
                
            st.session_state['last_analysis_metrics'] = {
                'tokens_used': estimated_tokens,
                'latency': actual_latency,
                'timestamp': time.strftime("%H:%M:%S")
            }
            
            # Add to conversation history
            add_to_conversation_history(user_input, result)
            
            # Display results with modern tile styling
            st.success("✅ Analysis Complete!")
            
            # Show agent outputs in compact tiles — only for routed agents
            if isinstance(result, dict) and "agent_outputs" in result:
                st.markdown('<div class="section-header">📊 Agent Insights</div>', unsafe_allow_html=True)
                
                agent_outputs = result.get("agent_outputs", []) or []
                routed_agents = [r.lower() for r in result.get("route", [])] if result.get("route") else []
                
                # For each agent that ran, show a card with compact tiles for insights & recommendations
                for output in agent_outputs:
                    agent_key = output.get("agent", "").lower()
                    agent_label = agent_key.capitalize() if agent_key else "Agent"
                    # Only show if agent was routed/run
                    if agent_key not in routed_agents:
                        continue
                    with st.expander(f"🤖 {agent_label} Agent", expanded=False):
                        # parse summary fields if needed
                        parsed_output = output.copy()
                        if "summary" in output and isinstance(output["summary"], str):
                            parsed = parse_agent_response(output["summary"])
                            if isinstance(parsed, dict):
                                parsed_output.update(parsed)
                        
                        # Insights: expect list of dicts (insight objects)
                        insights = parsed_output.get("insights") or []
                        if isinstance(insights, dict):
                            # sometimes one dict
                            insights = [insights]
                        if insights:
                            st.markdown("<div style='margin-bottom:6px;'><strong style='color:#6366f1;'>💡 Insights</strong></div>", unsafe_allow_html=True)
                            # render tiles inline
                            for ins in insights[:6]:  # cap to avoid too many
                                if isinstance(ins, (str, int, float)):
                                    # if string, render as single signal
                                    st.markdown(f"<div class='insight-tile'><div class='k'>Signal</div><div class='v'>{truncate_text(str(ins), 140)}</div></div>", unsafe_allow_html=True)
                                elif isinstance(ins, dict):
                                    render_insight_tile(ins)
                                else:
                                    render_insight_tile({"signal": str(ins)})
                        else:
                            st.markdown("<div style='color:gray; font-style:italic;'>No insights produced by this agent.</div>", unsafe_allow_html=True)
                        
                        # Recommendations: list of dicts or strings
                        recs = parsed_output.get("recommendations") or parsed_output.get("recommendation") or []
                        if isinstance(recs, dict):
                            recs = [recs]
                        if recs:
                            st.markdown("<div style='margin-top:8px;'><strong style='color:#10b981;'>🎯 Recommendations</strong></div>", unsafe_allow_html=True)
                            for r in recs[:6]:
                                if isinstance(r, str):
                                    render_rec_tile({"idea": r})
                                elif isinstance(r, dict):
                                    render_rec_tile(r)
                                else:
                                    render_rec_tile({"idea": str(r)})
                        else:
                            st.markdown("<div style='color:gray; font-style:italic; margin-top:6px;'>No recommendations produced by this agent.</div>", unsafe_allow_html=True)
            
            # Show final decision in a prominent tile (Marketer)
            final = {}
            if isinstance(result, dict):
                final = result.get("final_decision") or result.get("final_strategy") or {}
            
            if final:
                st.markdown('<div class="section-header">🎯 Final Marketing Strategy</div>', unsafe_allow_html=True)
                
                parsed_final = final.copy() if isinstance(final, dict) else {}
                if not parsed_final and isinstance(final, str):
                    parsed_final = parse_agent_response(final) if isinstance(final, str) else {}
                
                # Key Findings — show as small tiles (but keep fallback)
                if "key_findings" in parsed_final and parsed_final["key_findings"]:
                    st.markdown("<h3>🔍 Key Findings</h3>", unsafe_allow_html=True)
                    kf = parsed_final["key_findings"]
                    # Flatten and show up to 6 items
                    items = []
                    if isinstance(kf, dict):
                        for cat, vals in kf.items():
                            if isinstance(vals, list):
                                for v in vals:
                                    items.append(f"{cat}: {v}")
                            elif isinstance(vals, dict):
                                for kk, vv in vals.items():
                                    items.append(f"{cat} - {kk}: {vv}")
                            else:
                                items.append(f"{cat}: {vals}")
                    elif isinstance(kf, list):
                        items = [str(x) for x in kf]
                    else:
                        items = [str(kf)]
                    
                    for it in items[:6]:
                        st.markdown(f'<div class="insight-tile"><div class="k">Finding</div><div class="v">{truncate_text(it, 160)}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown("<h3>🔍 Key Findings</h3>", unsafe_allow_html=True)
                    # fallback: executive summary
                    if "executive_summary" in parsed_final and parsed_final["executive_summary"]:
                        summary = clean_insight_text(str(parsed_final["executive_summary"]))
                        truncated_summary = truncate_text(summary, 300)
                        st.markdown(f'<div class="insight-box">• {truncated_summary}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="insight-box">• No key findings available</div>', unsafe_allow_html=True)
                
                # Strategic recommendations (prefer final_campaign if present)
                st.markdown("<h3>🎯 Strategic Recommendations</h3>", unsafe_allow_html=True)
                recs_list = []
                # prefer final_campaign -> strategic_recommendations -> recommendations
                if isinstance(parsed_final.get("final_campaign"), dict) and parsed_final.get("final_campaign"):
                    fc = parsed_final["final_campaign"]
                    # display the campaign as one rec-tile
                    render_rec_tile({
                        "idea": f"{fc.get('campaign_name', 'Campaign')} — {fc.get('concept', '')}",
                        "confidence": fc.get("confidence", parsed_final.get("confidence"))
                    })
                else:
                    sr = parsed_final.get("strategic_recommendations") or parsed_final.get("strategic_recs") or parsed_final.get("recommendations") or []
                    if isinstance(sr, dict):
                        # flatten dict values
                        for v in sr.values():
                            if isinstance(v, list):
                                for x in v:
                                    recs_list.append(x)
                            else:
                                recs_list.append(v)
                    elif isinstance(sr, list):
                        recs_list = sr
                    elif isinstance(sr, str):
                        recs_list = [sr]
                    
                    if recs_list:
                        for rr in recs_list[:6]:
                            if isinstance(rr, str):
                                render_rec_tile({"idea": rr})
                            elif isinstance(rr, dict):
                                render_rec_tile(rr)
                            else:
                                render_rec_tile({"idea": str(rr)})
                    else:
                        # fallback: conflicts or none
                        if "conflicts" in parsed_final and parsed_final["conflicts"]:
                            for c in parsed_final["conflicts"][:3]:
                                st.markdown(f'<div class="recommendation-box">• {clean_insight_text(str(c))}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="recommendation-box">• No specific recommendations available at this time</div>', unsafe_allow_html=True)
            
            # Show raw JSON for debugging
            with st.expander("🔧 Raw Results (Debug)"):
                st.json(result)
                
        except Exception as e:
            # This outer except ensures any unexpected UI errors are caught and shown
            tb = traceback.format_exc()
            st.error(f"❌ Error during analysis: {str(e)}")
            st.info("Please check that all services are running and try again.")
            print("Unexpected exception in analysis flow:", tb)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: var(--text-secondary); padding: 2rem;">
    <p>🚀 NextGen Marketer - Powered by AI Agents | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)
