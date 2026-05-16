import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import streamlit as st
import logging
from .chart_scaler import chart_scaler

logger = logging.getLogger(__name__)

def validate_chart(chart, df_columns):
    """Enhanced chart validation for all PowerBI chart types"""
    if not isinstance(chart, dict):
        raise ValueError("Chart must be a dictionary")
    
    chart_type = chart.get("type", "").lower()
    x_col = chart.get("x")
    y_col = chart.get("y")
    
    if not chart_type:
        raise ValueError("Chart type is required")
    
    # Complete list of supported PowerBI chart types
    supported_types = [
        "bar", "clustered_bar", "stacked_bar", "clustered_column", "stacked_column",
        "line", "area", "stacked_area", "pie", "donut", "treemap", "funnel", 
        "waterfall", "scatter", "histogram", "box", "table", "matrix"
    ]
    
    if chart_type not in supported_types:
        raise ValueError(f"Unsupported chart type '{chart_type}'. Supported types: {', '.join(supported_types)}")
    
    # Special handling for table and matrix charts (don't require x column)
    if chart_type == "table":
        columns_to_check = chart.get("columns", [])
        if columns_to_check:
            missing_cols = [col for col in columns_to_check if col not in df_columns]
            if missing_cols:
                raise ValueError(f"Table columns not found: {missing_cols}")
        return True
    
    if chart_type == "matrix":
        rows_col = chart.get("rows")
        cols_col = chart.get("columns")
        values_col = chart.get("values")
        
        if rows_col and rows_col not in df_columns:
            raise ValueError(f"Matrix rows column '{rows_col}' not found")
        if cols_col and cols_col not in df_columns:
            raise ValueError(f"Matrix columns column '{cols_col}' not found")
        if values_col and values_col not in df_columns:
            raise ValueError(f"Matrix values column '{values_col}' not found")
        return True
    
    # For all other chart types, x column is required
    if not x_col:
        raise ValueError("X column is required")
    
    # Check x column exists
    if x_col not in df_columns:
        raise ValueError(f"X column '{x_col}' does not exist in dataset. Available columns: {list(df_columns)}")
    
    # Chart types that don't require y column
    if chart_type in ["histogram", "pie", "donut"] and (not y_col or y_col == "count"):
        return True
    
    # Handle y_col as list (for stacked charts)
    if isinstance(y_col, list):
        missing_y_cols = [col for col in y_col if col not in df_columns]
        if missing_y_cols:
            raise ValueError(f"Y columns not found: {missing_y_cols}")
        return True
    
    # Single y column validation
    if not y_col:
        raise ValueError(f"Y column is required for {chart_type} chart")
    
    if y_col != "count" and y_col not in df_columns:
        raise ValueError(f"Y column '{y_col}' does not exist in dataset. Available columns: {list(df_columns)}")
    
    return True

def create_safe_chart(df, chart):
    """Create comprehensive PowerBI-style charts with all visualization types"""
    try:
        chart_type = chart["type"].lower()
        title = chart.get("title", f"{chart_type.title()} Chart")
        
        # Special handling for table and matrix charts (don't use x/y structure)
        if chart_type == "table":
            columns_to_show = chart.get("columns", df.columns.tolist()[:6])
            table_df = df[columns_to_show].head(100)  # Show top 100 rows
            
            fig = go.Figure(data=[go.Table(
                header=dict(values=list(table_df.columns),
                           fill_color='#2E86AB',  # Modern blue header
                           font=dict(color='white', size=12),
                           align='left'),
                cells=dict(values=[table_df[col] for col in table_df.columns],
                          fill_color=['#F8F9FA', '#E9ECEF'],  # Alternating light gray rows
                          font=dict(color='#212529', size=11),
                          align='left'))
            ])
            fig.update_layout(
                title=title,
                font=dict(family="Arial, sans-serif"),
                margin=dict(l=0, r=0, t=40, b=0),
                height=400
            )
            return fig
        
        elif chart_type == "matrix":
            rows_col = chart.get("rows")
            cols_col = chart.get("columns")
            values_col = chart.get("values")
            
            if rows_col and values_col:
                if cols_col:
                    # Pivot table
                    pivot_df = df.pivot_table(values=values_col, index=rows_col, 
                                            columns=cols_col, aggfunc='sum', fill_value=0)
                    fig = px.imshow(pivot_df, title=title, aspect="auto")
                else:
                    # Simple aggregation
                    agg_df = df.groupby(rows_col)[values_col].sum().reset_index()
                    fig = px.bar(agg_df, x=rows_col, y=values_col, title=title)
            else:
                # Fallback to correlation matrix if available
                numeric_df = df.select_dtypes(include=[np.number])
                if len(numeric_df.columns) > 1:
                    corr_matrix = numeric_df.corr()
                    fig = px.imshow(corr_matrix, title="Correlation Matrix", aspect="auto")
                else:
                    return None
            return fig
        
        # For all other chart types, use standard x/y structure
        x_col = chart["x"]
        y_col = chart.get("y")
        
        # Data preprocessing
        plot_df = df.copy()
        
        # Handle missing values
        if y_col and y_col != "count" and isinstance(y_col, str):
            plot_df = plot_df.dropna(subset=[x_col, y_col])
        elif isinstance(y_col, list):
            plot_df = plot_df.dropna(subset=[x_col] + y_col)
        else:
            plot_df = plot_df.dropna(subset=[x_col])
        
        if len(plot_df) == 0:
            st.warning(f"No data available for chart: {title}")
            return None
        
        # Limit data points for performance
        if len(plot_df) > 2000:
            plot_df = plot_df.sample(n=2000, random_state=42)
            st.info(f"Chart shows sample of 2000 points from {len(df)} total rows")
        
        # CREATE COMPREHENSIVE POWERBI-STYLE CHARTS
        
        # 1. BAR AND COLUMN CHARTS
        if chart_type in ["bar", "clustered_column", "clustered_bar"]:
            if y_col == "count":
                count_df = plot_df[x_col].value_counts().reset_index()
                count_df.columns = [x_col, 'count']
                fig = px.bar(count_df, x=x_col, y='count', title=title,
                           color='count', color_continuous_scale='viridis')
            else:
                if not pd.api.types.is_numeric_dtype(plot_df[x_col]):
                    if plot_df[x_col].nunique() > 20:
                        top_categories = plot_df[x_col].value_counts().head(20).index
                        plot_df = plot_df[plot_df[x_col].isin(top_categories)]
                        st.info(f"Showing top 20 categories for {x_col}")
                    
                    agg_df = plot_df.groupby(x_col)[y_col].sum().reset_index()
                    fig = px.bar(agg_df, x=x_col, y=y_col, title=title,
                               color=y_col, color_continuous_scale='blues')
                else:
                    fig = px.bar(plot_df, x=x_col, y=y_col, title=title,
                               color=y_col, color_continuous_scale='blues')
        
        elif chart_type in ["stacked_column", "stacked_bar"]:
            if isinstance(y_col, list) and len(y_col) > 1:
                # Create stacked chart with multiple y columns
                melted_df = plot_df.melt(id_vars=[x_col], value_vars=y_col, 
                                       var_name='Metric', value_name='Value')
                fig = px.bar(melted_df, x=x_col, y='Value', color='Metric', title=title)
            else:
                # Regular bar chart if only one y column
                y_actual = y_col[0] if isinstance(y_col, list) else y_col
                agg_df = plot_df.groupby(x_col)[y_actual].sum().reset_index()
                fig = px.bar(agg_df, x=x_col, y=y_actual, title=title)
        
        # 2. LINE AND AREA CHARTS
        elif chart_type == "line":
            plot_df = plot_df.sort_values(x_col)
            fig = px.line(plot_df, x=x_col, y=y_col, title=title,
                         markers=True, line_shape='spline')
            fig.update_traces(mode='lines+markers', hovertemplate='<b>%{x}</b><br>%{y}<extra></extra>')
        
        elif chart_type == "area":
            plot_df = plot_df.sort_values(x_col)
            fig = px.area(plot_df, x=x_col, y=y_col, title=title)
        
        elif chart_type == "stacked_area":
            if isinstance(y_col, list) and len(y_col) > 1:
                fig = px.area(plot_df, x=x_col, y=y_col, title=title)
            else:
                fig = px.area(plot_df, x=x_col, y=y_col, title=title)
        
        # 3. PIE AND DONUT CHARTS
        elif chart_type == "pie":
            if y_col == "count":
                value_counts = plot_df[x_col].value_counts()
                fig = px.pie(values=value_counts.values, names=value_counts.index, title=title)
            else:
                agg_df = plot_df.groupby(x_col)[y_col].sum().reset_index()
                fig = px.pie(agg_df, values=y_col, names=x_col, title=title)
        
        elif chart_type == "donut":
            if y_col == "count":
                value_counts = plot_df[x_col].value_counts()
                fig = px.pie(values=value_counts.values, names=value_counts.index, title=title, hole=0.4)
            else:
                agg_df = plot_df.groupby(x_col)[y_col].sum().reset_index()
                fig = px.pie(agg_df, values=y_col, names=x_col, title=title, hole=0.4)
        
        # 4. ADVANCED CHART TYPES
        elif chart_type == "treemap":
            color_col = chart.get("color")
            if y_col == "count":
                value_counts = plot_df[x_col].value_counts()
                fig = px.treemap(names=value_counts.index, values=value_counts.values, title=title)
            else:
                agg_df = plot_df.groupby(x_col)[y_col].sum().reset_index()
                if color_col and color_col in plot_df.columns:
                    fig = px.treemap(agg_df, path=[x_col], values=y_col, color=color_col, title=title)
                else:
                    fig = px.treemap(agg_df, path=[x_col], values=y_col, title=title)
        
        elif chart_type == "funnel":
            agg_df = plot_df.groupby(x_col)[y_col].sum().reset_index().sort_values(y_col, ascending=False)
            fig = px.funnel(agg_df, x=y_col, y=x_col, title=title)
        
        elif chart_type == "waterfall":
            # Create waterfall chart using bar chart with custom styling
            plot_df_sorted = plot_df.sort_values(x_col)
            fig = px.bar(plot_df_sorted, x=x_col, y=y_col, title=title)
            fig.update_traces(marker_color=['green' if val > 0 else 'red' for val in plot_df_sorted[y_col]])
        
        # 5. SCATTER CHARTS
        elif chart_type == "scatter":
            size_col = chart.get("size")
            color_col = chart.get("color")
            
            if size_col and color_col:
                fig = px.scatter(plot_df, x=x_col, y=y_col, size=size_col, color=color_col, 
                               title=title, opacity=0.7)
            elif size_col:
                fig = px.scatter(plot_df, x=x_col, y=y_col, size=size_col, title=title, opacity=0.7)
            elif color_col:
                fig = px.scatter(plot_df, x=x_col, y=y_col, color=color_col, title=title, opacity=0.7)
            else:
                fig = px.scatter(plot_df, x=x_col, y=y_col, title=title, opacity=0.7)
            
            # Add trend line if both columns are numeric
            if pd.api.types.is_numeric_dtype(plot_df[x_col]) and pd.api.types.is_numeric_dtype(plot_df[y_col]):
                fig = px.scatter(plot_df, x=x_col, y=y_col, title=title, trendline="ols", opacity=0.7)
        
        # 6. DISTRIBUTION CHARTS
        elif chart_type == "histogram":
            fig = px.histogram(plot_df, x=x_col, title=title, nbins=30,
                             color_discrete_sequence=['#636EFA'])
            mean_val = plot_df[x_col].mean()
            fig.add_vline(x=mean_val, line_dash="dash", line_color="red",
                         annotation_text=f"Mean: {mean_val:.2f}")
        
        elif chart_type == "box":
            if y_col:
                fig = px.box(plot_df, x=x_col, y=y_col, title=title, color=x_col, notched=True)
            else:
                fig = px.box(plot_df, y=x_col, title=title, notched=True)
        
        else:
            raise ValueError(f"Chart type '{chart_type}' not implemented")
        
        # POWERBI-STYLE ENHANCEMENTS
        fig.update_layout(
            showlegend=True,
            hovermode='closest',
            template='plotly_white',
            font=dict(size=12),
            title=dict(font=dict(size=16, color='#2E2E2E')),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=40, r=40, t=60, b=40)
        )
        
        # Add interactivity
        if chart_type not in ["table", "matrix"]:
            fig.update_traces(hovertemplate='<b>%{x}</b><br>%{y}<br><extra></extra>')
        
        # Add grid for appropriate chart types
        if chart_type in ["bar", "line", "area", "scatter", "clustered_column", "stacked_column"]:
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        return fig
        
    except Exception as e:
        logger.error(f"Error creating chart: {e}")
        st.error(f"Failed to create chart: {str(e)}")
        return None

def render_kpi_safely(df, kpi):
    """Render enhanced KPI cards with different PowerBI-style formats"""
    try:
        col = kpi.get("column")
        agg = kpi.get("aggregation", "sum")
        label = kpi.get("label", f"{agg.title()} of {col}")
        kpi_type = kpi.get("type", "card")
        
        if col not in df.columns:
            st.error(f"KPI column '{col}' not found in dataset")
            return
        
        series = df[col]
        
        # Handle missing values
        if series.isna().all():
            st.warning(f"All values are missing for {col}")
            return
        
        series = series.dropna()
        
        if len(series) == 0:
            st.warning(f"No valid data for {col}")
            return
        
        # Normalize aggregation function
        agg_mapping = {
            "avg": "mean", "average": "mean", "total": "sum",
            "cnt": "count", "stdev": "std", "stddev": "std"
        }
        agg = agg_mapping.get(agg.lower(), agg.lower())
        
        # Calculate value
        if agg == "count":
            value = len(series)
        elif agg in ["sum", "mean", "median", "min", "max", "std"]:
            if not pd.api.types.is_numeric_dtype(series):
                st.error(f"Cannot calculate {agg} for non-numeric column {col}")
                return
            value = getattr(series, agg)()
        else:
            st.error(f"Unsupported aggregation: {agg}")
            return
        
        # Format value nicely
        if isinstance(value, (int, float, np.number)):
            if abs(value) >= 1000000:
                formatted_value = f"{value/1000000:.1f}M"
            elif abs(value) >= 1000:
                formatted_value = f"{value/1000:.1f}K"
            elif isinstance(value, float):
                formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(int(value))
        else:
            formatted_value = str(value)
        
        # Render different KPI types
        if kpi_type == "card":
            # Standard KPI card
            st.metric(label, formatted_value)
        
        elif kpi_type == "multi_row_card":
            # Multi-row card with additional statistics
            st.metric(label, formatted_value)
            
            # Add additional stats in smaller text
            if pd.api.types.is_numeric_dtype(series):
                min_val = series.min()
                max_val = series.max()
                st.caption(f"Range: {min_val:.1f} - {max_val:.1f}")
        
        elif kpi_type == "gauge":
            # Gauge chart using plotly
            if pd.api.types.is_numeric_dtype(series):
                max_range = series.max() * 1.2  # 20% above max for gauge range
                
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = value,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': label},
                    delta = {'reference': series.mean()},
                    gauge = {
                        'axis': {'range': [None, max_range]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, max_range*0.5], 'color': "lightgray"},
                            {'range': [max_range*0.5, max_range*0.8], 'color': "gray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': max_range*0.9
                        }
                    }
                ))
                
                fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                # Fallback to regular metric for non-numeric data
                st.metric(label, formatted_value)
        
        else:
            # Default to standard card
            st.metric(label, formatted_value)
        
    except Exception as e:
        logger.error(f"Error rendering KPI: {e}")
        st.error(f"Failed to render KPI: {str(e)}")

def render_dashboard(df, plan):
    """Enhanced PowerBI-style dashboard rendering with export options and simplified controls"""
    
    if df is None or len(df) == 0:
        st.error("No data available to render dashboard")
        return
    
    if not isinstance(plan, dict):
        st.error("Invalid dashboard plan format")
        return
    
    st.markdown("---")
    st.markdown("## 📊 AI-Generated Interactive Dashboard")
    st.markdown("*PowerBI-style visualizations with export capabilities*")
    
    # PowerBI Export Section
    st.markdown("### 📤 Export Options")
    col_export1, col_export2, col_export3 = st.columns(3)
    
    # Initialize session state for exports
    if 'powerbi_export_ready' not in st.session_state:
        st.session_state.powerbi_export_ready = False
    if 'csv_export_ready' not in st.session_state:
        st.session_state.csv_export_ready = False
    
    with col_export1:
        if st.button("📊 Generate PowerBI Export", help="Generate PowerBI file with embedded data"):
            try:
                with st.spinner("Generating PowerBI file with embedded data..."):
                    from exporter.powerbi_exporter import create_powerbi_export
                    pbix_bytes, json_config = create_powerbi_export(df, plan, {})
                    
                    # Store in session state
                    st.session_state.pbix_bytes = pbix_bytes
                    st.session_state.json_config = json_config
                    st.session_state.powerbi_export_ready = True
                    st.session_state.export_timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                
                st.success("✅ PowerBI file generated with embedded data!")
                
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
                st.session_state.powerbi_export_ready = False
        
        # Show download buttons if export is ready
        if st.session_state.powerbi_export_ready:
            st.download_button(
                label="📥 Download PowerBI File (.pbix)",
                data=st.session_state.pbix_bytes,
                file_name=f"autodash_dashboard_{st.session_state.export_timestamp}.pbix",
                mime="application/octet-stream",
                key="download_pbix",
                help="Complete PowerBI file with embedded data - open directly in PowerBI Desktop"
            )
            
            st.download_button(
                label="📄 Download Configuration (.json)",
                data=st.session_state.json_config,
                file_name=f"dashboard_config_{st.session_state.export_timestamp}.json",
                mime="application/json",
                key="download_json",
                help="Dashboard configuration for reference"
            )
    
    with col_export2:
        if st.button("📄 Generate CSV Export", help="Generate processed data export"):
            try:
                with st.spinner("Generating CSV export..."):
                    csv_data = df.to_csv(index=False)
                    st.session_state.csv_data = csv_data
                    st.session_state.csv_export_ready = True
                    st.session_state.csv_timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                
                st.success("✅ CSV export generated!")
                
            except Exception as e:
                st.error(f"CSV export failed: {str(e)}")
                st.session_state.csv_export_ready = False
        
        # Show download button if CSV export is ready
        if st.session_state.csv_export_ready:
            st.download_button(
                label="📥 Download CSV Data",
                data=st.session_state.csv_data,
                file_name=f"dashboard_data_{st.session_state.csv_timestamp}.csv",
                mime="text/csv",
                key="download_csv"
            )
    
    with col_export3:
        if st.button("🖼️ Export Screenshots", help="Export dashboard as images"):
            st.info("📸 Screenshot export functionality - would capture all charts as PNG/PDF")
            st.markdown("""
            **Coming Soon:**
            - Individual chart PNG exports
            - Full dashboard PDF export
            - High-resolution image downloads
            """)
    
    st.markdown("---")
    
    # Render KPIs in a nice layout
    kpis = plan.get("kpis", [])
    if kpis:
        st.markdown("### 📈 Key Performance Indicators")
        
        # Create responsive columns for KPIs
        num_kpis = len(kpis)
        if num_kpis <= 4:
            kpi_cols = st.columns(num_kpis)
        else:
            # Create multiple rows for more than 4 KPIs
            kpi_cols = st.columns(4)
        
        for i, kpi in enumerate(kpis):
            with kpi_cols[i % len(kpi_cols)]:
                render_kpi_safely(df, kpi)
        
        st.markdown("---")
    
    # Render Charts in a PowerBI-style grid with simplified controls
    charts = plan.get("charts", [])
    if charts:
        st.markdown("### 📊 Interactive Visualizations")
        
        # Global dashboard controls in sidebar
        with st.sidebar:
            st.markdown("## 🎛️ Dashboard Controls")
            
            global_height = st.slider(
                "Global Chart Height",
                min_value=250,
                max_value=600,
                value=400,
                step=50,
                key="global_height"
            )
            
            charts_per_row = st.selectbox(
                "Charts per Row",
                options=[1, 2, 3, 4],
                index=2,  # 3 charts per row
                key="charts_per_row"
            )
        
        # Create responsive grid layout
        num_charts = len(charts)
        
        # Render charts in responsive grid
        for i in range(0, num_charts, charts_per_row):
            cols = st.columns(min(charts_per_row, num_charts - i))
            
            for j, col in enumerate(cols):
                if i + j < num_charts:
                    chart = charts[i + j]
                    chart_id = f"chart_{i+j+1}"
                    
                    with col:
                        try:
                            validate_chart(chart, df.columns)
                            fig = create_safe_chart(df, chart)
                            if fig:
                                # Apply global height
                                fig.update_layout(height=global_height)
                                st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.error(f"Failed to render chart {i+j+1}: {str(e)}")
    
    # Dashboard summary and insights
    if kpis or charts:
        st.markdown("---")
        st.markdown("### 💡 Dashboard Insights")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Visualizations", len(charts))
        with col2:
            st.metric("📈 Key Metrics", len(kpis))
        with col3:
            st.metric("📋 Data Points", len(df))
        
        # Add data quality info
        missing_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
        if missing_pct > 0:
            st.info(f"ℹ️ Data Quality: {100-missing_pct:.1f}% complete ({missing_pct:.1f}% missing values were automatically handled)")
        else:
            st.success("✅ Data Quality: 100% complete - no missing values detected")
        
        st.success(f"🎉 Dashboard generated successfully with {len(kpis)} KPIs and {len(charts)} interactive charts!")
    
    else:
        st.warning("⚠️ No KPIs or charts were generated. This might indicate:")
        st.markdown("""
        - Dataset contains only text/categorical data
        - All numerical columns have the same values
        - Data structure is too complex for automatic analysis
        """)
        
        # Offer basic data exploration
        st.markdown("### 📋 Basic Data Summary")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Dataset Overview:**")
            st.write(f"- Rows: {df.shape[0]:,}")
            st.write(f"- Columns: {df.shape[1]}")
            st.write(f"- Data Types: {df.dtypes.nunique()}")
        
        with col2:
            st.write("**Column Types:**")
            type_counts = df.dtypes.value_counts()
            for dtype, count in type_counts.items():
                st.write(f"- {dtype}: {count} columns")
        
        if len(df.select_dtypes(include=[np.number]).columns) > 0:
            st.markdown("**Numerical Summary:**")
            st.dataframe(df.describe(), use_container_width=True)
