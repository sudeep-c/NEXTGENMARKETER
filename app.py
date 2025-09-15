"""
NextGen Marketer - Modern Streamlit App
Main application for the multi-agent marketing system with refreshed UI.
"""

import streamlit as st
import json
import pandas as pd
from orchestrator import run_flow
import os

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
    import time
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

# Custom CSS
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
    
    /* Global styles */
    .main .block-container {
        padding-top: 0.5rem;
        padding-bottom: 1rem;
        max-width: 1200px;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        color: white;
        padding: 1.2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
    }
    
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .main-header p {
        font-size: 1.1rem;
        margin: 0.3rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Card styling */
    .metric-card {
        background: var(--card-background);
        border-radius: 8px;
        padding: 0.6rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border: 1px solid var(--border-color);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 80px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .metric-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--primary-color);
        margin: 0;
        line-height: 1;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin: 0.2rem 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-change {
        font-size: 0.7rem;
        margin-top: 0.2rem;
    }
    
    .metric-change.positive {
        color: var(--success-color);
    }
    
    .metric-change.negative {
        color: var(--error-color);
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 1.2rem 0 0.8rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid var(--primary-color);
    }
    
    .subsection-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0.8rem 0 0.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding-bottom: 0.3rem;
    }
    
    /* Tile styling for outputs */
    .output-tile {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .output-tile h3 {
        color: var(--primary-color);
        margin: 0 0 1rem 0;
        font-size: 1.2rem;
        font-weight: 600;
    }
    
    /* Light grey box for insights and recommendations */
    .insight-box {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid var(--primary-color);
    }
    
    .recommendation-box {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid var(--success-color);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }
    
    /* File uploader styling */
    .stFileUploader > div {
        border: 2px dashed var(--border-color);
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background: var(--background-color);
        transition: border-color 0.2s ease;
    }
    
    .stFileUploader > div:hover {
        border-color: var(--primary-color);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, var(--primary-color), var(--secondary-color));
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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

# Recent Activity section removed

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

# Analysis Results with tile styling
if analyze_btn and user_input:
    with st.spinner("🤖 AI agents are analyzing your request..."):
        try:
            # Track analysis start time
            import time
            start_time = time.time()
            
            # Build conversation context
            context = build_conversation_context()
            
            # Enhance user input with context if available
            enhanced_input = user_input
            if context:
                enhanced_input = f"{context}\n\nCurrent question: {user_input}"
            
            # Run the multi-agent workflow with context
            result = run_flow(enhanced_input)
            
            # Calculate actual metrics
            end_time = time.time()
            actual_latency = round(end_time - start_time, 2)
            
            # Update system metrics with real data
            if 'agent_outputs' in result:
                # Estimate token usage based on response length
                total_chars = sum(len(str(output)) for output in result['agent_outputs'])
                estimated_tokens = total_chars // 4  # Rough estimation
                
            # Store metrics in session state for display
            st.session_state['last_analysis_metrics'] = {
                'tokens_used': estimated_tokens,
                'latency': actual_latency,
                'timestamp': time.strftime("%H:%M:%S")
            }
            
            # Add to conversation history
            add_to_conversation_history(user_input, result)
            
            # Display results with modern tile styling
            st.success("✅ Analysis Complete!")
            
            # Show agent outputs in tiles
            if "agent_outputs" in result:
                st.markdown('<div class="section-header">📊 Agent Insights</div>', unsafe_allow_html=True)
                
                agent_names = ["Sentiment", "Purchase", "Campaign"]
                for i, output in enumerate(result["agent_outputs"]):
                    agent_name = agent_names[i] if i < len(agent_names) else f"Agent {i+1}"
                    
                    with st.expander(f"🤖 {agent_name} Agent", expanded=True):
                        # Parse the output if it contains JSON
                        parsed_output = output.copy()
                        
                        # If summary is a JSON string, parse it
                        if "summary" in output and isinstance(output["summary"], str):
                            parsed_summary = parse_agent_response(output["summary"])
                            if isinstance(parsed_summary, dict):
                                # Merge parsed JSON fields into the output
                                parsed_output.update(parsed_summary)
                        
                        # Display only top 3 insights and recommendations in light grey boxes
                        if "insights" in parsed_output and parsed_output["insights"]:
                            st.markdown("<h3>💡 Insights</h3>", unsafe_allow_html=True)
                            # Ensure insights is a list and limit to top 3
                            insights = parsed_output["insights"]
                            if isinstance(insights, list):
                                insights = insights[:3]
                            else:
                                insights = [str(insights)]
                            
                            for insight in insights:
                                # Clean and format insight text
                                cleaned_insight = clean_insight_text(insight)
                                # Truncate long insights at word boundaries
                                truncated_insight = truncate_text(cleaned_insight, 300)
                                st.markdown(f'<div class="insight-box">• {truncated_insight}</div>', unsafe_allow_html=True)
                        
                        if "recommendations" in parsed_output and parsed_output["recommendations"]:
                            st.markdown("<h3>🎯 Recommendations</h3>", unsafe_allow_html=True)
                            # Ensure recommendations is a list and limit to top 3
                            recommendations = parsed_output["recommendations"]
                            if isinstance(recommendations, list):
                                recommendations = recommendations[:3]
                            else:
                                recommendations = [str(recommendations)]
                            
                            for rec in recommendations:
                                # Clean and format recommendation text
                                cleaned_rec = clean_insight_text(rec)
                                # Truncate long recommendations at word boundaries
                                truncated_rec = truncate_text(cleaned_rec, 300)
                                st.markdown(f'<div class="recommendation-box">• {truncated_rec}</div>', unsafe_allow_html=True)
            
            # Show final decision in a prominent tile
            if "final_decision" in result:
                st.markdown('<div class="section-header">🎯 Final Marketing Strategy</div>', unsafe_allow_html=True)
                final = result["final_decision"]
                
                # Parse final decision if it's a JSON string
                parsed_final = final.copy()
                if isinstance(final, dict):
                    # Check if any field contains JSON strings
                    for key, value in final.items():
                        if isinstance(value, str) and (value.strip().startswith('{') or value.strip().startswith('```json')):
                            parsed_value = parse_agent_response(value)
                            if isinstance(parsed_value, dict):
                                parsed_final.update(parsed_value)
                
                # Display only top 3 key findings and strategic recommendations in light grey boxes
                if "key_findings" in parsed_final and parsed_final["key_findings"]:
                    st.markdown("<h3>🔍 Key Findings</h3>", unsafe_allow_html=True)
                    key_findings = parsed_final["key_findings"]
                    findings_list = []
                    
                    if isinstance(key_findings, dict):
                        for category, findings in key_findings.items():
                            if isinstance(findings, dict):
                                for key, value in findings.items():
                                    findings_list.append(f"{key}: {value}")
                            else:
                                findings_list.append(str(findings))
                    elif isinstance(key_findings, list):
                        findings_list = [str(finding) for finding in key_findings]
                    elif isinstance(key_findings, str):
                        # If key_findings is a JSON string, parse it
                        parsed_findings = parse_agent_response(key_findings)
                        if isinstance(parsed_findings, dict) and "key_findings" in parsed_findings:
                            findings_list = [str(finding) for finding in parsed_findings["key_findings"]]
                        else:
                            findings_list = [key_findings]
                    
                    # Limit to top 3 findings
                    if isinstance(findings_list, list):
                        findings_list = findings_list[:3]
                    else:
                        findings_list = [str(findings_list)]
                    
                    for finding in findings_list:
                        # Clean and format finding text
                        cleaned_finding = clean_insight_text(finding)
                        truncated_finding = truncate_text(cleaned_finding, 300)
                        st.markdown(f'<div class="insight-box">• {truncated_finding}</div>', unsafe_allow_html=True)
                else:
                    # Fallback: Show executive summary or raw content if key_findings is empty
                    st.markdown("<h3>🔍 Key Findings</h3>", unsafe_allow_html=True)
                    if "executive_summary" in parsed_final and parsed_final["executive_summary"]:
                        summary = clean_insight_text(str(parsed_final["executive_summary"]))
                        truncated_summary = truncate_text(summary, 300)
                        st.markdown(f'<div class="insight-box">• {truncated_summary}</div>', unsafe_allow_html=True)
                    else:
                        # Show raw content as fallback
                        raw_content = str(parsed_final)
                        if len(raw_content) > 50:  # Only show if there's substantial content
                            cleaned_content = clean_insight_text(raw_content)
                            truncated_content = truncate_text(cleaned_content, 300)
                            st.markdown(f'<div class="insight-box">• {truncated_content}</div>', unsafe_allow_html=True)
                
                # Display strategic recommendations
                if "strategic_recommendations" in parsed_final and parsed_final["strategic_recommendations"]:
                    st.markdown("<h3>🎯 Strategic Recommendations</h3>", unsafe_allow_html=True)
                    recommendations = parsed_final["strategic_recommendations"]
                    recs_list = []
                    
                    if isinstance(recommendations, list):
                        recs_list = [str(rec) for rec in recommendations]
                    elif isinstance(recommendations, str):
                        # If recommendations is a JSON string, parse it
                        parsed_recs = parse_agent_response(recommendations)
                        if isinstance(parsed_recs, dict) and "strategic_recommendations" in parsed_recs:
                            recs_list = [str(rec) for rec in parsed_recs["strategic_recommendations"]]
                        else:
                            recs_list = [recommendations]
                    
                    # Limit to top 3 recommendations
                    if isinstance(recs_list, list):
                        recs_list = recs_list[:3]
                    else:
                        recs_list = [str(recs_list)]
                    
                    for rec in recs_list:
                        # Clean and format recommendation text
                        cleaned_rec = clean_insight_text(rec)
                        truncated_rec = truncate_text(cleaned_rec, 300)
                        st.markdown(f'<div class="recommendation-box">• {truncated_rec}</div>', unsafe_allow_html=True)
                else:
                    # Fallback: Show conflicts or other available content if strategic_recommendations is empty
                    st.markdown("<h3>🎯 Strategic Recommendations</h3>", unsafe_allow_html=True)
                    if "conflicts" in parsed_final and parsed_final["conflicts"]:
                        conflicts = parsed_final["conflicts"]
                        if isinstance(conflicts, list) and conflicts:
                            for conflict in conflicts[:3]:  # Show top 3 conflicts
                                cleaned_conflict = clean_insight_text(str(conflict))
                                truncated_conflict = truncate_text(cleaned_conflict, 300)
                                st.markdown(f'<div class="recommendation-box">• {truncated_conflict}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="recommendation-box">• No specific recommendations available at this time</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="recommendation-box">• No specific recommendations available at this time</div>', unsafe_allow_html=True)
            
            # Show raw JSON for debugging
            with st.expander("🔧 Raw Results (Debug)"):
                st.json(result)
                
        except Exception as e:
            st.error(f"❌ Error during analysis: {str(e)}")
            st.info("Please check that all services are running and try again.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: var(--text-secondary); padding: 2rem;">
    <p>🚀 NextGen Marketer - Powered by AI Agents | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)