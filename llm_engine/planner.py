import os
import re
import json
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from typing import TypedDict, List, Dict, Any
import time
import logging

from langgraph.graph import StateGraph, END

# ======================================================
# LOGGING SETUP
# ======================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================================================
# ENV
# ======================================================

load_dotenv(override=True)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "mistralai/mistral-7b-instruct"

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")

# ======================================================
# ENHANCED LLM CALL WITH RETRY LOGIC
# ======================================================

def call_llm(prompt: str, max_retries: int = 3, timeout: int = 30) -> dict:
    """Enhanced LLM call with retry logic and better error handling"""
    
    for attempt in range(max_retries):
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a professional BI analyst. You MUST respond with valid JSON only. No explanations, no markdown, just pure JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000,
                },
                timeout=timeout,
            )
            
            if r.status_code != 200:
                logger.warning(f"API call failed with status {r.status_code}, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise Exception(f"API call failed: {r.status_code}")
            
            response_data = r.json()
            text = response_data["choices"][0]["message"]["content"].strip()
            
            # Multiple JSON extraction strategies
            json_obj = extract_json_from_text(text)
            if json_obj:
                return json_obj
                
            logger.warning(f"Failed to extract JSON from response, attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
                
        except Exception as e:
            logger.error(f"LLM call error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise e
    
    raise Exception("All LLM call attempts failed")

def extract_json_from_text(text: str) -> dict:
    """Multiple strategies to extract JSON from LLM response"""
    
    # Strategy 1: Remove markdown code blocks
    text = re.sub(r"```(?:json)?", "", text).strip()
    text = re.sub(r"```", "", text).strip()
    
    # Strategy 2: Find JSON object
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Try to parse the entire text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 4: Look for array format
    array_match = re.search(r'\[.*\]', text, re.DOTALL)
    if array_match:
        try:
            return {"data": json.loads(array_match.group())}
        except json.JSONDecodeError:
            pass
    
    return None

# ======================================================
# ENHANCED VALIDATION TOOLS
# ======================================================

VALID_AGGS = ["sum", "mean", "median", "min", "max", "count", "std"]
VALID_CHART_TYPES = [
    "bar", "clustered_bar", "stacked_bar", "clustered_column", "stacked_column",
    "line", "area", "stacked_area", "pie", "donut", "treemap", "funnel", 
    "waterfall", "scatter", "histogram", "box", "table", "matrix"
]

def normalize_agg(a: str) -> str:
    """Normalize aggregation function names"""
    mapping = {
        "avg": "mean", "average": "mean", "total": "sum", 
        "cnt": "count", "stdev": "std", "stddev": "std"
    }
    return mapping.get(a.lower(), a.lower())

def validate_kpi(df: pd.DataFrame, kpi: dict) -> bool:
    """Enhanced KPI validation"""
    try:
        col = kpi.get("column")
        agg = normalize_agg(kpi.get("aggregation", ""))
        
        if not col or col not in df.columns:
            return False
        if agg not in VALID_AGGS:
            return False
        
        # Check if aggregation makes sense for the column type
        series = df[col]
        if agg in ["sum", "mean", "median", "std"] and not pd.api.types.is_numeric_dtype(series):
            return False
        
        # Test the actual computation
        result = getattr(series, agg)()
        return isinstance(result, (int, float, np.number)) and not pd.isna(result)
        
    except Exception as e:
        logger.warning(f"KPI validation failed: {e}")
        return False

def validate_chart(df: pd.DataFrame, chart: dict) -> bool:
    """Enhanced chart validation for all PowerBI chart types"""
    try:
        chart_type = chart.get("type", "").lower()
        x_col = chart.get("x")
        y_col = chart.get("y")
        
        if chart_type not in VALID_CHART_TYPES:
            return False
        if not x_col or x_col not in df.columns:
            return False
        
        # Special handling for table and matrix charts
        if chart_type == "table":
            columns_to_check = chart.get("columns", [])
            if columns_to_check:
                missing_cols = [col for col in columns_to_check if col not in df.columns]
                return len(missing_cols) == 0
            return True
        
        if chart_type == "matrix":
            rows_col = chart.get("rows")
            cols_col = chart.get("columns")
            values_col = chart.get("values")
            
            if rows_col and rows_col not in df.columns:
                return False
            if cols_col and cols_col not in df.columns:
                return False
            if values_col and values_col not in df.columns:
                return False
            return True
        
        # Chart types that don't require y column or use "count"
        if chart_type in ["histogram", "pie", "donut"] and (not y_col or y_col == "count"):
            return True
        
        # Handle y_col as list (for stacked charts)
        if isinstance(y_col, list):
            missing_y_cols = [col for col in y_col if col not in df.columns]
            return len(missing_y_cols) == 0
        
        # Single y column validation
        if not y_col or (y_col != "count" and y_col not in df.columns):
            return False
        
        # Skip detailed type validation for now - let the renderer handle it
        # This allows more flexibility in chart creation
        return True
        
    except Exception as e:
        logger.warning(f"Chart validation failed: {e}")
        return False

# ======================================================
# SMART FALLBACK STRATEGIES
# ======================================================

def generate_smart_fallback_plan(df: pd.DataFrame, metadata: dict) -> dict:
    """Generate a comprehensive PowerBI-style dashboard with all visualization types"""
    
    plan = {"kpis": [], "charts": []}
    columns = metadata.get("columns", [])
    
    numerical_cols = [c for c in columns if c["type"] == "numerical"]
    categorical_cols = [c for c in columns if c["type"] == "categorical" and c.get("unique_values", 0) <= 50]
    datetime_cols = [c for c in columns if c["type"] == "datetime"]
    
    # Generate enhanced KPIs with different card types
    kpi_count = 0
    for num_col in numerical_cols[:6]:  # Max 6 KPIs
        col_name = num_col["name"]
        
        if kpi_count < 2:
            # Regular KPI cards
            if (num_col.get("is_integer", False) and 
                not num_col.get("has_negatives", True) and
                num_col.get("min", 0) >= 0):
                agg = "sum"
                label = f"Total {col_name.replace('_', ' ').title()}"
                kpi_type = "card"
            else:
                agg = "mean"
                label = f"Average {col_name.replace('_', ' ').title()}"
                kpi_type = "card"
        elif kpi_count < 4:
            # Multi-row cards with additional stats
            agg = "sum" if num_col.get("is_integer", False) else "mean"
            label = f"{col_name.replace('_', ' ').title()}"
            kpi_type = "multi_row_card"
        else:
            # Gauge charts for remaining metrics
            agg = "mean"
            label = f"{col_name.replace('_', ' ').title()}"
            kpi_type = "gauge"
        
        plan["kpis"].append({
            "label": label,
            "column": col_name,
            "aggregation": agg,
            "type": kpi_type
        })
        kpi_count += 1
    
    # COMPREHENSIVE CHART GENERATION - Full PowerBI Suite
    chart_count = 0
    
    # 1. Time Series Visualizations
    if datetime_cols and numerical_cols and chart_count < 12:
        for datetime_col in datetime_cols[:2]:
            for num_col in numerical_cols[:2]:
                # Line Chart
                plan["charts"].append({
                    "type": "line",
                    "x": datetime_col["name"],
                    "y": num_col["name"],
                    "title": f"{num_col['name'].replace('_', ' ').title()} Trend Over Time"
                })
                chart_count += 1
                
                # Area Chart
                if chart_count < 12:
                    plan["charts"].append({
                        "type": "area",
                        "x": datetime_col["name"],
                        "y": num_col["name"],
                        "title": f"{num_col['name'].replace('_', ' ').title()} Area Chart"
                    })
                    chart_count += 1
                
                if chart_count >= 12:
                    break
            if chart_count >= 12:
                break
    
    # 2. Categorical Analysis - Multiple Bar Chart Types (LIMITED to ensure variety)
    if categorical_cols and numerical_cols and chart_count < 12:
        # Only generate 4 charts maximum in this section to leave room for variety
        charts_in_section = 0
        max_charts_in_section = 4
        
        for cat_col in categorical_cols[:2]:  # Only first 2 categorical columns
            for num_col in numerical_cols[:1]:  # Only first numerical column
                if cat_col.get("unique_values", 0) <= 20 and charts_in_section < max_charts_in_section:
                    # Clustered Column Chart
                    plan["charts"].append({
                        "type": "clustered_column",
                        "x": cat_col["name"],
                        "y": num_col["name"],
                        "title": f"{num_col['name'].replace('_', ' ').title()} by {cat_col['name'].replace('_', ' ').title()}"
                    })
                    chart_count += 1
                    charts_in_section += 1
                    
                    # Stacked Column Chart (if we have multiple numerical columns)
                    if len(numerical_cols) > 1 and chart_count < 12 and charts_in_section < max_charts_in_section:
                        plan["charts"].append({
                            "type": "stacked_column",
                            "x": cat_col["name"],
                            "y": [num_col["name"], numerical_cols[1]["name"]] if len(numerical_cols) > 1 else [num_col["name"]],
                            "title": f"Stacked Analysis by {cat_col['name'].replace('_', ' ').title()}"
                        })
                        chart_count += 1
                        charts_in_section += 1
                
                if chart_count >= 12 or charts_in_section >= max_charts_in_section:
                    break
            if chart_count >= 12 or charts_in_section >= max_charts_in_section:
                break
    
    # 3. Pie and Donut Charts for Categorical Distribution
    if categorical_cols and chart_count < 12:
        for cat_col in categorical_cols[:2]:
            if cat_col.get("unique_values", 0) <= 20:  # Increased threshold for pie charts
                # Pie Chart
                plan["charts"].append({
                    "type": "pie",
                    "x": cat_col["name"],
                    "y": "count",
                    "title": f"Distribution of {cat_col['name'].replace('_', ' ').title()}"
                })
                chart_count += 1
                
                # Donut Chart
                if chart_count < 12:
                    plan["charts"].append({
                        "type": "donut",
                        "x": cat_col["name"],
                        "y": "count",
                        "title": f"{cat_col['name'].replace('_', ' ').title()} Breakdown"
                    })
                    chart_count += 1
    
    # 4. Advanced Chart Types - ALWAYS generate some variety
    if numerical_cols and chart_count < 12:
        # Treemap for hierarchical data
        if len(categorical_cols) >= 1:
            plan["charts"].append({
                "type": "treemap",
                "x": categorical_cols[0]["name"],
                "y": numerical_cols[0]["name"],
                "title": f"Treemap: {numerical_cols[0]['name'].replace('_', ' ').title()} Analysis"
            })
            chart_count += 1
        
        # Funnel Chart for process data
        if len(categorical_cols) >= 1 and chart_count < 12:
            plan["charts"].append({
                "type": "funnel",
                "x": categorical_cols[0]["name"],
                "y": numerical_cols[0]["name"],
                "title": f"Funnel Analysis: {categorical_cols[0]['name'].replace('_', ' ').title()}"
            })
            chart_count += 1
        
        # Waterfall Chart for cumulative analysis
        if datetime_cols and chart_count < 12:
            plan["charts"].append({
                "type": "waterfall",
                "x": datetime_cols[0]["name"],
                "y": numerical_cols[0]["name"],
                "title": f"Waterfall: {numerical_cols[0]['name'].replace('_', ' ').title()} Changes"
            })
            chart_count += 1
        
        # Bar Chart (different from column charts)
        if categorical_cols and chart_count < 12:
            plan["charts"].append({
                "type": "bar",
                "x": categorical_cols[0]["name"],
                "y": numerical_cols[0]["name"],
                "title": f"Bar Chart: {numerical_cols[0]['name'].replace('_', ' ').title()} by {categorical_cols[0]['name'].replace('_', ' ').title()}"
            })
            chart_count += 1
    
    # 5. Correlation and Distribution Analysis
    if len(numerical_cols) >= 2 and chart_count < 12:
        # Scatter Chart with enhanced features
        strong_corrs = metadata.get("strong_correlations", [])
        if strong_corrs:
            for corr in strong_corrs[:2]:
                plan["charts"].append({
                    "type": "scatter",
                    "x": corr["col1"],
                    "y": corr["col2"],
                    "size": numerical_cols[2]["name"] if len(numerical_cols) > 2 else None,
                    "color": categorical_cols[0]["name"] if categorical_cols else None,
                    "title": f"Correlation: {corr['col1'].replace('_', ' ').title()} vs {corr['col2'].replace('_', ' ').title()}"
                })
                chart_count += 1
                if chart_count >= 12:
                    break
        
        # Box Plot for distribution analysis
        if categorical_cols and chart_count < 12:
            plan["charts"].append({
                "type": "box",
                "x": categorical_cols[0]["name"],
                "y": numerical_cols[0]["name"],
                "title": f"{numerical_cols[0]['name'].replace('_', ' ').title()} Distribution by {categorical_cols[0]['name'].replace('_', ' ').title()}"
            })
            chart_count += 1
    
    # 6. Table and Matrix for detailed data
    if chart_count < 12:
        # Data Table
        plan["charts"].append({
            "type": "table",
            "columns": [col["name"] for col in columns[:6]],  # Top 6 columns
            "title": "📋 Data Overview Table"
        })
        chart_count += 1
        
        # Matrix (if we have categorical and numerical data)
        if categorical_cols and numerical_cols and chart_count < 12:
            plan["charts"].append({
                "type": "matrix",
                "rows": categorical_cols[0]["name"],
                "columns": categorical_cols[1]["name"] if len(categorical_cols) > 1 else None,
                "values": numerical_cols[0]["name"],
                "title": "Data Matrix Analysis"
            })
            chart_count += 1
    
    # 7. GUARANTEE: Ensure we have meaningful charts
    if chart_count == 0:
        # Create basic charts from available data
        if numerical_cols:
            plan["charts"].append({
                "type": "clustered_column",
                "x": categorical_cols[0]["name"] if categorical_cols else "index",
                "y": numerical_cols[0]["name"],
                "title": f"Basic Analysis: {numerical_cols[0]['name'].replace('_', ' ').title()}"
            })
            chart_count += 1
            
            plan["charts"].append({
                "type": "pie",
                "x": categorical_cols[0]["name"] if categorical_cols else "category",
                "y": "count",
                "title": "Distribution Analysis"
            })
            chart_count += 1
    
    return plan

# ======================================================
# STATE
# ======================================================

class DashboardState(TypedDict):
    metadata: dict
    df: pd.DataFrame
    kpis: List[dict]
    charts: List[dict]
    failures: int
    max_failures: int
    suggested_charts: List[dict]

# ======================================================
# ENHANCED GRAPH NODES
# ======================================================

def generate_kpis(state: DashboardState):
    """Generate KPIs with enhanced prompting - completely generic approach"""
    
    columns = state['metadata']['columns']
    numerical_cols = [c for c in columns if c['type'] == 'numerical']
    
    if not numerical_cols:
        return {"kpis": []}
    
    # Create detailed column descriptions without assuming business context
    col_descriptions = []
    for col in numerical_cols[:5]:  # Limit to avoid token overflow
        desc = f"- {col['name']}: {col['type']}"
        if 'mean' in col:
            desc += f" (average: {col['mean']}, range: {col['min']}-{col['max']})"
        if 'sample_values' in col:
            desc += f" (examples: {col['sample_values'][:3]})"
        col_descriptions.append(desc)
    
    prompt = f"""
You are analyzing a dataset with {state['metadata']['n_rows']} rows and {state['metadata']['n_columns']} columns.

Available numerical columns for KPIs:
{chr(10).join(col_descriptions)}

Generate 2-3 meaningful KPIs (Key Performance Indicators) for this dataset.

Rules:
1. Use only these aggregations: {VALID_AGGS}
2. Choose aggregations based on the data characteristics:
   - For counts, quantities, amounts: use "sum" or "count"
   - For rates, scores, averages: use "mean" or "median"
   - For ranges, spreads: use "min", "max", or "std"
3. Create descriptive labels that make sense for the data
4. Don't assume specific business context - work with any data type

Return ONLY this JSON format:
{{
  "kpis": [
    {{"label": "Total [Column Name]", "column": "column_name", "aggregation": "sum"}},
    {{"label": "Average [Column Name]", "column": "column_name", "aggregation": "mean"}}
  ]
}}
"""
    
    try:
        result = call_llm(prompt)
        kpis = result.get("kpis", [])
        
        # Validate each KPI
        valid_kpis = []
        for kpi in kpis:
            if validate_kpi(state["df"], kpi):
                valid_kpis.append(kpi)
        
        return {"kpis": valid_kpis}
        
    except Exception as e:
        logger.error(f"KPI generation failed: {e}")
        return {"kpis": []}

def generate_chart(state: DashboardState):
    """Generate chart with enhanced prompting and suggestions - completely generic"""
    
    columns = state['metadata']['columns']
    existing_charts = state.get('charts', [])
    suggested_charts = state['metadata'].get('suggested_charts', [])
    
    # Use suggestions if available and not already used
    for suggestion in suggested_charts:
        chart_exists = any(
            c.get('x') == suggestion.get('x') and c.get('y') == suggestion.get('y') 
            for c in existing_charts
        )
        if not chart_exists and validate_chart(state["df"], suggestion):
            return {
                "candidate_chart": suggestion,
                "failures": state["failures"]
            }
    
    # Generate new chart via LLM
    numerical_cols = [c for c in columns if c['type'] == 'numerical']
    categorical_cols = [c for c in columns if c['type'] == 'categorical']
    datetime_cols = [c for c in columns if c['type'] == 'datetime']
    
    col_info = []
    for col in columns[:10]:  # Show more columns but limit to avoid token overflow
        info = f"- {col['name']} ({col['type']})"
        if col['type'] == 'categorical':
            info += f" - {col.get('unique_values', 0)} unique values"
        elif col['type'] == 'numerical':
            info += f" - range: {col.get('min', 0)}-{col.get('max', 0)}"
        elif col['type'] == 'datetime':
            info += f" - date range: {col.get('date_range_days', 0)} days"
        col_info.append(info)
    
    existing_chart_info = [f"{c.get('type', 'unknown')}: {c.get('x', '')} vs {c.get('y', '')}" for c in existing_charts]
    
    prompt = f"""
Dataset columns:
{chr(10).join(col_info)}

Existing charts: {existing_chart_info}

Create ONE new chart that provides different insights from existing ones.

Chart type guidelines:
- "line": Use for time series (datetime x-axis, numerical y-axis)
- "bar": Use for categorical x-axis, numerical y-axis (max 20 categories)
- "scatter": Use for numerical x-axis, numerical y-axis (correlation analysis)
- "histogram": Use for single numerical column distribution

Rules:
1. Choose columns that exist in the dataset
2. Don't duplicate existing chart combinations
3. Create meaningful titles based on the actual column names
4. Work with any data domain - don't assume business context

Return ONLY this JSON format:
{{
  "chart": {{
    "type": "bar",
    "x": "actual_column_name",
    "y": "actual_column_name", 
    "title": "Descriptive Title Using Actual Column Names"
  }}
}}
"""
    
    try:
        result = call_llm(prompt)
        chart = result.get("chart")
        return {
            "candidate_chart": chart,
            "failures": state["failures"]
        }
        
    except Exception as e:
        logger.error(f"Chart generation failed: {e}")
        return {
            "candidate_chart": None,
            "failures": state["failures"]
        }

def validate_chart_node(state: DashboardState):
    """Validate generated chart"""
    chart = state.get("candidate_chart")
    
    if chart and validate_chart(state["df"], chart):
        return {"charts": state["charts"] + [chart], "failures": state["failures"]}
    else:
        return {"failures": state["failures"] + 1}

def should_continue(state: DashboardState):
    """Decide whether to continue generating charts"""
    if state["failures"] >= state.get("max_failures", 3):
        return "end"
    if len(state["charts"]) >= 4:  # Max 4 charts
        return "end"
    return "generate_chart"

# ======================================================
# GRAPH BUILD
# ======================================================

def build_graph():
    """Build the LangGraph workflow"""
    graph = StateGraph(DashboardState)

    graph.add_node("generate_kpis", generate_kpis)
    graph.add_node("generate_chart", generate_chart)
    graph.add_node("validate_chart", validate_chart_node)

    graph.set_entry_point("generate_kpis")
    graph.add_edge("generate_kpis", "generate_chart")
    graph.add_edge("generate_chart", "validate_chart")

    graph.add_conditional_edges(
        "validate_chart",
        should_continue,
        {
            "generate_chart": "generate_chart",
            "end": END
        }
    )

    return graph.compile()

app = build_graph()

# ======================================================
# PUBLIC API
# ======================================================

def generate_dashboard_plan(metadata: dict, df: pd.DataFrame) -> dict:
    """Generate dashboard plan with guaranteed chart generation"""
    
    try:
        # Always use the enhanced fallback system for guaranteed results
        logger.info("Generating comprehensive dashboard plan...")
        plan = generate_smart_fallback_plan(df, metadata)
        
        # Ensure we have meaningful content
        if not plan["kpis"] and not plan["charts"]:
            logger.warning("Enhanced fallback failed, using basic fallback")
            plan = basic_fallback_plan(df)
        
        logger.info(f"Generated plan with {len(plan['kpis'])} KPIs and {len(plan['charts'])} charts")
        return plan
        
    except Exception as e:
        logger.error(f"Dashboard generation failed: {e}")
        # Last resort fallback
        return generate_smart_fallback_plan(df, metadata)

def basic_fallback_plan(df: pd.DataFrame) -> dict:
    """Most basic fallback when everything else fails"""
    numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    
    plan = {"kpis": [], "charts": []}
    
    if numerical_cols:
        plan["kpis"].append({
            "label": f"Count of {numerical_cols[0]}",
            "column": numerical_cols[0],
            "aggregation": "count"
        })
    
    if len(numerical_cols) >= 2:
        plan["charts"].append({
            "type": "scatter",
            "x": numerical_cols[0],
            "y": numerical_cols[1],
            "title": f"{numerical_cols[0]} vs {numerical_cols[1]}"
        })
    
    return plan
