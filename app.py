#!/usr/bin/env python3
"""
NextGen Marketer - Streamlit App
Main application for the multi-agent marketing system.
"""

import streamlit as st
import json
from orchestrator import run_flow

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

# try:
#     from utils.llm_utils import ask_ollama
#     _ = ask_ollama("ping", model="gpt-oss:20b", json_mode=False)
#     _ = ask_ollama("ping", model="gemma2:9b", json_mode=False)
# except Exception:
#     pass

# ---------- Page config ----------
st.set_page_config(
    page_title="NextGen Marketer",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- CSS ----------
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .agent-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
st.markdown('<h1 class="main-header">🚀 NextGen Marketer</h1>', unsafe_allow_html=True)
st.markdown("### AI-Powered Multi-Agent Marketing Intelligence System")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("📊 System Status")
    
    # Check if data is available
    try:
        import os
        if os.path.exists("./chroma_db"):
            st.success("✅ ChromaDB: Connected")
        else:
            st.error("❌ ChromaDB: Not found")
    except:
        st.error("❌ ChromaDB: Error")
    
    st.header("🤖 Available Agents")
    st.markdown("""
    - **Campaign Agent**: Analyzes campaign performance
    - **Purchase Agent**: Studies buying patterns  
    - **Sentiment Agent**: Monitors customer feedback
    - **Marketer Agent**: Synthesizes insights
    """)
    
    st.header("📈 Quick Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Campaigns", "2,000")
    with col2:
        st.metric("Purchases", "2,000")
    
    col3, col4 = st.columns(2)
    with col3:
        st.metric("Sentiments", "2,000")
    with col4:
        st.metric("PDF Docs", "10")

# ---------- Main Content ----------
st.header("💬 Ask Your Marketing Questions")

# Input area
user_input = st.text_area(
    "Enter your marketing question or request:",
    placeholder="e.g., 'Analyze our campaign performance and suggest improvements for Q4'",
    height=100
)

# Action buttons
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    analyze_btn = st.button("🔍 Analyze", type="primary")
with col2:
    clear_btn = st.button("🗑️ Clear")
with col3:
    st.markdown("*Powered by AI Agents*")

if clear_btn:
    st.rerun()

# ---------- Analysis Results ----------
if analyze_btn and user_input:
    with st.spinner("🤖 AI agents are analyzing your request..."):
        try:
            # Run the multi-agent workflow
            result = run_flow(user_input)
            
            # Display results
            st.success("✅ Analysis Complete!")
            
            # Show agent outputs
            if "agent_outputs" in result:
                st.header("📊 Agent Insights")
                
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
                        
                        # Display summary
                        if "summary" in parsed_output:
                            summary_text = parsed_output["summary"]
                            if isinstance(summary_text, str) and not (summary_text.strip().startswith('```json') or summary_text.strip().startswith('{')):
                                st.write("**Summary:**")
                                st.write(summary_text)
                        
                        # Display key metrics
                        if "key_metrics" in parsed_output and parsed_output["key_metrics"]:
                            st.write("**Key Metrics:**")
                            if isinstance(parsed_output["key_metrics"], dict):
                                for key, value in parsed_output["key_metrics"].items():
                                    st.write(f"• **{key.replace('_', ' ').title()}:** {value}")
                            else:
                                st.json(parsed_output["key_metrics"])
                        
                        # Display insights
                        if "insights" in parsed_output and parsed_output["insights"]:
                            st.write("**Insights:**")
                            for insight in parsed_output["insights"]:
                                st.write(f"• {insight}")
                        
                        # Display recommendations
                        if "recommendations" in parsed_output and parsed_output["recommendations"]:
                            st.write("**Recommendations:**")
                            for rec in parsed_output["recommendations"]:
                                st.write(f"• {rec}")
            
            # Show final decision
            if "final_decision" in result:
                st.header("🎯 Final Marketing Strategy")
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
                
                # Display executive summary
                if "executive_summary" in parsed_final:
                    st.subheader("📋 Executive Summary")
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
                    st.subheader("🔍 Key Findings")
                    key_findings = parsed_final["key_findings"]
                    
                    if isinstance(key_findings, dict):
                        for category, findings in key_findings.items():
                            st.write(f"**{category.title()}:**")
                            if isinstance(findings, dict):
                                for key, value in findings.items():
                                    st.write(f"• {key}: {value}")
                            else:
                                st.write(f"• {findings}")
                    elif isinstance(key_findings, list):
                        for finding in key_findings:
                            st.write(f"• {finding}")
                    elif isinstance(key_findings, str):
                        # If key_findings is a JSON string, parse it
                        parsed_findings = parse_agent_response(key_findings)
                        if isinstance(parsed_findings, dict) and "key_findings" in parsed_findings:
                            findings_list = parsed_findings["key_findings"]
                            if isinstance(findings_list, list):
                                for finding in findings_list:
                                    st.write(f"• {finding}")
                        else:
                            st.write(key_findings)
                
                # Display conflicts
                if "conflicts" in parsed_final and parsed_final["conflicts"]:
                    st.subheader("⚠️ Conflicts & Issues")
                    conflicts = parsed_final["conflicts"]
                    
                    if isinstance(conflicts, list):
                        for conflict in conflicts:
                            st.write(f"• {conflict}")
                    elif isinstance(conflicts, str):
                        # If conflicts is a JSON string, parse it
                        parsed_conflicts = parse_agent_response(conflicts)
                        if isinstance(parsed_conflicts, dict) and "conflicts" in parsed_conflicts:
                            conflicts_list = parsed_conflicts["conflicts"]
                            if isinstance(conflicts_list, list):
                                for conflict in conflicts_list:
                                    st.write(f"• {conflict}")
                        else:
                            st.write(conflicts)
                
                # Display strategic recommendations
                if "strategic_recommendations" in parsed_final and parsed_final["strategic_recommendations"]:
                    st.subheader("🎯 Strategic Recommendations")
                    recommendations = parsed_final["strategic_recommendations"]
                    
                    if isinstance(recommendations, list):
                        for rec in recommendations:
                            st.write(f"• {rec}")
                    elif isinstance(recommendations, str):
                        # If recommendations is a JSON string, parse it
                        parsed_recs = parse_agent_response(recommendations)
                        if isinstance(parsed_recs, dict) and "strategic_recommendations" in parsed_recs:
                            recs_list = parsed_recs["strategic_recommendations"]
                            if isinstance(recs_list, list):
                                for rec in recs_list:
                                    st.write(f"• {rec}")
                        else:
                            st.write(recommendations)
            
            # Show raw JSON for debugging
            with st.expander("🔧 Raw Results (Debug)"):
                st.json(result)
                
        except Exception as e:
            st.error(f"❌ Error during analysis: {str(e)}")
            st.exception(e)

# ---------- Footer ----------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🚀 NextGen Marketer - AI-Powered Marketing Intelligence</p>
    <p>Built with Streamlit, LangGraph, and Ollama</p>
</div>
""", unsafe_allow_html=True)
