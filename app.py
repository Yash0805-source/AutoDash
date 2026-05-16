import streamlit as st
import pandas as pd
import logging
import traceback

from profiler.data_profiler import profile_dataframe
from llm_engine.planner import generate_dashboard_plan
from renderer.dashboard import render_dashboard

# --------------------------------
# Logging setup
# --------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------
# Streamlit page config
# --------------------------------
st.set_page_config(
    page_title="AutoDash – AI Dashboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 AutoDash")
st.caption("LLM-powered automatic dashboard generation from CSV / Excel data")

# Add sidebar with information
with st.sidebar:
    st.header("ℹ️ How it works")
    st.markdown("""
    1. **Upload** your CSV or Excel file
    2. **AI analyzes** your data structure
    3. **Generates** meaningful KPIs and charts
    4. **Renders** an interactive dashboard
    
    **Supported formats:** CSV, XLSX
    **Max file size:** 200MB
    """)
    
    st.header("🔧 Features")
    st.markdown("""
    - Automatic data type detection
    - **Smart missing value handling**
    - **Automatic feature engineering**
    - Smart KPI generation
    - Multiple chart types
    - Correlation analysis
    - Fallback mechanisms
    """)

# --------------------------------
# File upload
# --------------------------------
uploaded_file = st.file_uploader(
    "Upload a CSV or Excel file",
    type=["csv", "xlsx"],
    help="Upload your data file to generate an AI-powered dashboard"
)

if uploaded_file is not None:
    try:
        # Show file info
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.1f} KB"
        }
        
        with st.expander("📁 File Information"):
            for key, value in file_details.items():
                st.write(f"**{key}:** {value}")

        # Read data with progress
        with st.spinner("Reading file..."):
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

        st.success(f"✅ File uploaded successfully! Dataset contains {len(df)} rows and {len(df.columns)} columns.")

        # Data validation
        if len(df) == 0:
            st.error("The uploaded file is empty. Please upload a file with data.")
            st.stop()
        
        if len(df.columns) == 0:
            st.error("No columns found in the file. Please check your file format.")
            st.stop()
        
        if len(df) > 50000:
            st.warning(f"Large dataset detected ({len(df)} rows). Processing might take longer.")
            # Sample for preview but use full dataset for analysis
            preview_df = df.sample(n=1000, random_state=42)
            st.info("Showing sample of 1000 rows in preview")
        else:
            preview_df = df

        # Show preview
        with st.expander("🔍 Data Preview", expanded=True):
            st.dataframe(preview_df.head(10), use_container_width=True)
            
            # Basic stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Rows", len(df))
            with col2:
                st.metric("Total Columns", len(df.columns))
            with col3:
                missing_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
                st.metric("Missing Data %", f"{missing_pct:.1f}%")

        # Generate metadata with progress
        with st.spinner("Analyzing data structure and applying feature engineering..."):
            try:
                df, metadata = profile_dataframe(df, apply_feature_eng=True)
                st.success("✅ Data analysis and feature engineering completed!")
                
                # Show feature engineering results if applied
                if metadata.get("feature_engineering"):
                    fe_report = metadata["feature_engineering"]
                    if fe_report["summary"]["missing_reduction"] > 0:
                        st.info(f"🔧 Feature engineering applied: Fixed {fe_report['summary']['missing_reduction']} missing values and created {fe_report['summary']['new_features_created']} new features")
                
            except Exception as e:
                st.error(f"Failed to analyze data: {str(e)}")
                logger.error(f"Data profiling error: {e}")
                st.stop()

        with st.expander("🧠 Dataset Analysis (Auto-EDA)"):
            
            # Show feature engineering results first if available
            if metadata.get("feature_engineering"):
                st.subheader("🔧 Feature Engineering Applied")
                fe_report = metadata["feature_engineering"]
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Missing Values Fixed", fe_report["summary"]["missing_reduction"])
                with col2:
                    st.metric("New Features Created", fe_report["summary"]["new_features_created"])
                with col3:
                    st.metric("Original Shape", f"{fe_report['summary']['original_shape'][0]}×{fe_report['summary']['original_shape'][1]}")
                with col4:
                    st.metric("Final Shape", f"{fe_report['summary']['transformed_shape'][0]}×{fe_report['summary']['transformed_shape'][1]}")
                
                # Show transformations applied
                if fe_report["transformations"]:
                    st.subheader("🔍 Transformations Applied")
                    if st.checkbox("Show detailed transformations", key="show_transformations"):
                        for i, transform in enumerate(fe_report["transformations"]):
                            if transform["type"] == "numeric_imputation":
                                st.write(f"**{i+1}.** Fixed missing values in `{transform['column']}` using {transform['strategy']} ({transform['missing_pct']:.1f}% missing)")
                            elif transform["type"] == "categorical_imputation":
                                st.write(f"**{i+1}.** Fixed missing values in `{transform['column']}` using {transform['strategy']} ({transform['missing_pct']:.1f}% missing)")
                            elif transform["type"] == "missing_indicator":
                                st.write(f"**{i+1}.** Created missing indicator `{transform['new_column']}` for `{transform['column']}`")
                            elif transform["type"] == "ratio_feature":
                                st.write(f"**{i+1}.** Created ratio feature `{transform['new_column']}` from `{transform['numerator']}` / `{transform['denominator']}`")
                            elif transform["type"] == "binning":
                                st.write(f"**{i+1}.** Created binned feature `{transform['new_column']}` from `{transform['column']}`")
                            elif transform["type"] == "datetime_features":
                                st.write(f"**{i+1}.** Extracted time features from `{transform['column']}`: {', '.join(transform['new_columns'])}")
                            elif transform["type"] == "drop_column":
                                st.write(f"**{i+1}.** Dropped column `{transform['column']}` - {transform['reason']}")
                            elif transform["type"] == "frequency_encoding":
                                st.write(f"**{i+1}.** Created frequency encoding `{transform['new_column']}` for `{transform['column']}`")
                            elif transform["type"] == "weekend_indicator":
                                st.write(f"**{i+1}.** Created weekend indicator `{transform['new_column']}` for `{transform['column']}`")
            
            # Show column analysis
            st.subheader("Column Analysis")
            try:
                col_df = pd.DataFrame(metadata["columns"])
                if not col_df.empty:
                    # Convert any problematic columns to strings for display
                    for col in col_df.columns:
                        if col_df[col].dtype == 'object':
                            col_df[col] = col_df[col].astype(str)
                    st.dataframe(col_df, use_container_width=True)
                else:
                    st.info("No column analysis data available")
            except Exception as e:
                st.warning(f"Could not display column analysis table: {str(e)}")
                # Show basic column info as text instead
                st.write("**Columns detected:**")
                for col_info in metadata.get("columns", []):
                    st.write(f"- **{col_info['name']}** ({col_info['type']}) - {col_info.get('missing_pct', 0):.1f}% missing")
            
            # Show correlations if available
            if metadata.get("strong_correlations"):
                st.subheader("Strong Correlations")
                try:
                    corr_df = pd.DataFrame(metadata["strong_correlations"])
                    st.dataframe(corr_df, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not display correlations table: {str(e)}")
                    # Show correlations as text instead
                    for corr in metadata["strong_correlations"]:
                        st.write(f"- **{corr['col1']}** ↔ **{corr['col2']}**: {corr['correlation']:.3f}")
            
            # Show suggested charts
            if metadata.get("suggested_charts"):
                st.subheader("AI Chart Suggestions")
                try:
                    suggestions_df = pd.DataFrame(metadata["suggested_charts"])
                    display_cols = ["type", "x", "y", "title"]
                    available_cols = [col for col in display_cols if col in suggestions_df.columns]
                    st.dataframe(suggestions_df[available_cols], use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not display suggestions table: {str(e)}")
                    # Show suggestions as text instead
                    for i, chart in enumerate(metadata["suggested_charts"], 1):
                        st.write(f"**{i}.** {chart.get('type', 'unknown')} chart: {chart.get('title', 'Untitled')}")
            
            # Raw metadata
            st.subheader("Raw Metadata")
            if st.checkbox("Show detailed metadata (JSON)", key="show_metadata"):
                st.json(metadata)

        # --------------------------------
        # Generate dashboard
        # --------------------------------
        
        # Add generation options
        st.subheader("🚀 Dashboard Generation")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            generate_button = st.button("🚀 Generate AI Dashboard", type="primary", use_container_width=True)
        with col2:
            max_retries = st.selectbox("Retry attempts", [1, 2, 3], index=2, help="Number of retry attempts if AI generation fails")
        with col3:
            if metadata.get("data_quality", {}).get("missing_percentage", 0) > 0:
                st.info(f"✨ Feature engineering was applied to handle {metadata['data_quality']['missing_percentage']:.1f}% missing data")
            else:
                st.success("✅ No missing data detected")
        
        if generate_button:
            try:
                with st.spinner("🤖 AI is designing your dashboard..."):
                    plan = generate_dashboard_plan(metadata, df)

                if plan and (plan.get("kpis") or plan.get("charts")):
                    st.success(f"✅ Generated {len(plan.get('kpis', []))} KPIs and {len(plan.get('charts', []))} interactive charts!")
                    
                    with st.expander("📐 AI Dashboard Plan (JSON)"):
                        st.json(plan)

                    # Render dashboard
                    with st.spinner("🎨 Rendering dashboard..."):
                        render_dashboard(df, plan)
                        
                else:
                    st.warning("⚠️ AI couldn't generate a meaningful dashboard. This might be due to:")
                    st.markdown("""
                    - Insufficient numeric data for KPIs
                    - Complex data structure
                    - API limitations
                    
                    Try uploading a different dataset or check the data preview above.
                    """)

            except Exception as e:
                st.error("❌ Dashboard generation failed!")
                
                error_msg = str(e)
                if "API" in error_msg or "timeout" in error_msg.lower():
                    st.error("🌐 API connection issue. Please check your internet connection and try again.")
                elif "JSON" in error_msg:
                    st.error("🔧 AI response parsing failed. The AI might be having trouble understanding your data.")
                else:
                    st.error(f"🐛 Unexpected error: {error_msg}")
                
                # Show detailed error in expander for debugging
                with st.expander("🔍 Technical Details (for debugging)"):
                    st.code(traceback.format_exc())
                
                logger.error(f"Dashboard generation error: {e}")
                logger.error(traceback.format_exc())

    except Exception as e:
        st.error("❌ Something went wrong while processing the file!")
        
        error_msg = str(e)
        if "codec" in error_msg.lower() or "encoding" in error_msg.lower():
            st.error("📝 File encoding issue. Try saving your file with UTF-8 encoding.")
        elif "excel" in error_msg.lower() or "xlsx" in error_msg.lower():
            st.error("📊 Excel file issue. Make sure the file is not corrupted and contains data.")
        else:
            st.error(f"� Fil e processing error: {error_msg}")
        
        with st.expander("🔍 Technical Details"):
            st.exception(e)
        
        logger.error(f"File processing error: {e}")

else:
    # Landing page content
    st.info("👆 Please upload a CSV or Excel file to begin generating your AI-powered dashboard.")
    
    # Show capabilities without specific examples
    st.subheader("🎯 What AutoDash Can Do")
    st.markdown("""
    **AutoDash works with ANY data structure:**
    
    🔍 **Automatic Analysis**
    - Detects data types automatically (numbers, text, dates, categories)
    - Identifies relationships and patterns in your data
    - Handles missing values intelligently
    
    📊 **Smart Visualizations**
    - Creates appropriate charts based on your data characteristics
    - Generates meaningful KPIs from numerical columns
    - Suggests correlations and trends
    
    🛠️ **Data Enhancement**
    - Automatically fixes missing values
    - Creates new features to enhance insights
    - Optimizes data for better visualizations
    
    **Just upload your file - no matter what columns or structure it has!**
    """)
    
    # Generic capabilities
    with st.expander("💡 Supported Data Types"):
        st.markdown("""
        - **Any numerical data** → KPIs, trends, correlations
        - **Any categorical data** → Breakdowns, distributions
        - **Any date/time data** → Time series, seasonal patterns
        - **Any text data** → Frequency analysis, categorization
        - **Mixed data types** → Comprehensive multi-dimensional analysis
        
        The AI adapts to YOUR data structure automatically!
        """)