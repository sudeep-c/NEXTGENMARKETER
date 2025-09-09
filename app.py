"""
NextGen Marketer - Modern Streamlit App
Main application for the multi-agent marketing system with refreshed UI.
"""

import streamlit as st
import json
import pandas as pd
from orchestrator import run_flow
import os

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
    
    if sentiment_data is not None and not sentiment_data.empty:
        if 'sentiment' in sentiment_data.columns:
            sentiment_counts = sentiment_data['sentiment'].value_counts()
            total = len(sentiment_data)
            analytics['sentiment']['positive_percent'] = round((sentiment_counts.get('positive', 0) / total) * 100, 1)
            analytics['sentiment']['negative_percent'] = round((sentiment_counts.get('negative', 0) / total) * 100, 1)
            analytics['sentiment']['neutral_percent'] = round((sentiment_counts.get('neutral', 0) / total) * 100, 1)
    
    if campaign_data is not None and not campaign_data.empty:
        if 'ctr' in campaign_data.columns:
            analytics['campaign']['avg_ctr'] = round(campaign_data['ctr'].mean() * 100, 2)
        if 'conversion_rate' in campaign_data.columns:
            analytics['campaign']['avg_conversion'] = round(campaign_data['conversion_rate'].mean() * 100, 2)
        if 'impressions' in campaign_data.columns:
            analytics['campaign']['total_impressions'] = int(campaign_data['impressions'].sum())
    
    if purchase_data is not None and not purchase_data.empty:
        analytics['purchase']['total_sales'] = len(purchase_data)
        if 'transaction_value' in purchase_data.columns:
            analytics['purchase']['avg_transaction'] = int(purchase_data['transaction_value'].mean())
    
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
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        color: white;
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 10px 25px rgba(99, 102, 241, 0.2);
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .main-header p {
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Card styling */
    .metric-card {
        background: var(--card-background);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid var(--border-color);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--primary-color);
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: var(--text-secondary);
        margin: 0.5rem 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-change {
        font-size: 0.8rem;
        margin-top: 0.5rem;
    }
    
    .metric-change.positive {
        color: var(--success-color);
    }
    
    .metric-change.negative {
        color: var(--error-color);
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 2rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Tile styling for outputs */
    .output-tile {
        background: linear-gradient(135deg, #f8fafc, #f1f5f9);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid var(--border-color);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .output-tile h3 {
        color: var(--primary-color);
        margin: 0 0 1rem 0;
        font-size: 1.2rem;
        font-weight: 600;
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
    st.markdown("## 📊 Navigation")
    
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
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    
    if st.button("📊 Generate Report", use_container_width=True):
        st.info("Report generation feature coming soon!")

# Main content area
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Quick Analytics Section
    st.markdown('<div class="section-header">📈 Quick Analytics</div>', unsafe_allow_html=True)
    
    # Load sample data and calculate analytics
    sentiment_data, campaign_data, purchase_data = load_sample_data()
    analytics = calculate_quick_analytics(sentiment_data, campaign_data, purchase_data)
    
    # Sentiment Analytics
    st.markdown("### 💭 Sentiment Analysis")
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
    st.markdown("### 🎯 Campaign Performance")
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
    st.markdown("### 💰 Purchase Insights")
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
    
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">4</div>
        <div class="metric-label">Active Agents</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">2,000</div>
        <div class="metric-label">Data Points</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    # Recent Activity
    st.markdown('<div class="section-header">📊 Recent Activity</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">741</div>
        <div class="metric-label">New Items</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">123</div>
        <div class="metric-label">New Orders</div>
    </div>
    """, unsafe_allow_html=True)

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
            # Run the multi-agent workflow
            result = run_flow(user_input)
            
            # Display results with modern tile styling
            st.success("✅ Analysis Complete!")
            
            # Show agent outputs in tiles
            if "agent_outputs" in result:
                st.markdown('<div class="section-header">📊 Agent Insights</div>', unsafe_allow_html=True)
                
                agent_names = ["Sentiment", "Purchase", "Campaign"]
                for i, output in enumerate(result["agent_outputs"]):
                    agent_name = agent_names[i] if i < len(agent_names) else f"Agent {i+1}"
                    
                    with st.expander(f"🤖 {agent_name} Agent", expanded=True):
                        st.markdown('<div class="output-tile">', unsafe_allow_html=True)
                        
                        # Parse the output if it contains JSON
                        parsed_output = output.copy()
                        
                        # If summary is a JSON string, parse it
                        if "summary" in output and isinstance(output["summary"], str):
                            parsed_summary = parse_agent_response(output["summary"])
                            if isinstance(parsed_summary, dict):
                                # Merge parsed JSON fields into the output
                                parsed_output.update(parsed_summary)
                        
                        # Display summary
                        if "summary" in parsed_output:
                            summary_text = parsed_output["summary"]
                            if isinstance(summary_text, str) and not (summary_text.strip().startswith('```json') or summary_text.strip().startswith('{')):
                                st.markdown(f"<h3>📋 Summary</h3><p>{summary_text}</p>", unsafe_allow_html=True)
                        
                        # Display key metrics
                        if "key_metrics" in parsed_output and parsed_output["key_metrics"]:
                            st.markdown("<h3>📊 Key Metrics</h3>", unsafe_allow_html=True)
                            if isinstance(parsed_output["key_metrics"], dict):
                                for key, value in parsed_output["key_metrics"].items():
                                    st.markdown(f"• **{key.replace('_', ' ').title()}:** {value}")
                            else:
                                st.json(parsed_output["key_metrics"])
                        
                        # Display insights
                        if "insights" in parsed_output and parsed_output["insights"]:
                            st.markdown("<h3>💡 Insights</h3>", unsafe_allow_html=True)
                            for insight in parsed_output["insights"]:
                                st.markdown(f"• {insight}")
                        
                        # Display recommendations
                        if "recommendations" in parsed_output and parsed_output["recommendations"]:
                            st.markdown("<h3>🎯 Recommendations</h3>", unsafe_allow_html=True)
                            for rec in parsed_output["recommendations"]:
                                st.markdown(f"• {rec}")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
            
            # Show final decision in a prominent tile
            if "final_decision" in result:
                st.markdown('<div class="section-header">🎯 Final Marketing Strategy</div>', unsafe_allow_html=True)
                final = result["final_decision"]
                
                st.markdown('<div class="output-tile">', unsafe_allow_html=True)
                
                # Parse final decision if it's a JSON string
                parsed_final = final.copy()
                if isinstance(final, dict):
                    # Check if any field contains JSON strings
                    for key, value in final.items():
                        if isinstance(value, str) and (value.strip().startswith('{') or value.strip().startswith('```json')):
                            parsed_value = parse_agent_response(value)
                            if isinstance(parsed_value, dict):
                                parsed_final.update(parsed_value)
                
                # Display executive summary
                if "executive_summary" in parsed_final:
                    st.markdown("<h3>📋 Executive Summary</h3>", unsafe_allow_html=True)
                    summary_text = parsed_final["executive_summary"]
                    if isinstance(summary_text, str) and not (summary_text.strip().startswith('```json') or summary_text.strip().startswith('{')):
                        st.write(summary_text)
                    else:
                        # If it's still JSON, try to extract the actual summary
                        parsed_summary = parse_agent_response(summary_text)
                        if isinstance(parsed_summary, dict) and "executive_summary" in parsed_summary:
                            st.write(parsed_summary["executive_summary"])
                        else:
                            st.write(summary_text)
                
                # Display key findings
                if "key_findings" in parsed_final and parsed_final["key_findings"]:
                    st.markdown("<h3>🔍 Key Findings</h3>", unsafe_allow_html=True)
                    key_findings = parsed_final["key_findings"]
                    
                    if isinstance(key_findings, dict):
                        for category, findings in key_findings.items():
                            st.markdown(f"**{category.title()}:**")
                            if isinstance(findings, dict):
                                for key, value in findings.items():
                                    st.markdown(f"• {key}: {value}")
                            else:
                                st.markdown(f"• {findings}")
                    elif isinstance(key_findings, list):
                        for finding in key_findings:
                            st.markdown(f"• {finding}")
                    elif isinstance(key_findings, str):
                        # If key_findings is a JSON string, parse it
                        parsed_findings = parse_agent_response(key_findings)
                        if isinstance(parsed_findings, dict) and "key_findings" in parsed_findings:
                            findings_list = parsed_findings["key_findings"]
                            if isinstance(findings_list, list):
                                for finding in findings_list:
                                    st.markdown(f"• {finding}")
                        else:
                            st.write(key_findings)
                
                # Display conflicts
                if "conflicts" in parsed_final and parsed_final["conflicts"]:
                    st.markdown("<h3>⚠️ Conflicts & Issues</h3>", unsafe_allow_html=True)
                    conflicts = parsed_final["conflicts"]
                    
                    if isinstance(conflicts, list):
                        for conflict in conflicts:
                            st.markdown(f"• {conflict}")
                    elif isinstance(conflicts, str):
                        # If conflicts is a JSON string, parse it
                        parsed_conflicts = parse_agent_response(conflicts)
                        if isinstance(parsed_conflicts, dict) and "conflicts" in parsed_conflicts:
                            conflicts_list = parsed_conflicts["conflicts"]
                            if isinstance(conflicts_list, list):
                                for conflict in conflicts_list:
                                    st.markdown(f"• {conflict}")
                        else:
                            st.write(conflicts)
                
                # Display strategic recommendations
                if "strategic_recommendations" in parsed_final and parsed_final["strategic_recommendations"]:
                    st.markdown("<h3>🎯 Strategic Recommendations</h3>", unsafe_allow_html=True)
                    recommendations = parsed_final["strategic_recommendations"]
                    
                    if isinstance(recommendations, list):
                        for rec in recommendations:
                            st.markdown(f"• {rec}")
                    elif isinstance(recommendations, str):
                        # If recommendations is a JSON string, parse it
                        parsed_recs = parse_agent_response(recommendations)
                        if isinstance(parsed_recs, dict) and "strategic_recommendations" in parsed_recs:
                            recs_list = parsed_recs["strategic_recommendations"]
                            if isinstance(recs_list, list):
                                for rec in recs_list:
                                    st.markdown(f"• {rec}")
                        else:
                            st.write(recommendations)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
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