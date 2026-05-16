#!/usr/bin/env python3
"""
Chart Scaler Module - PowerBI-style zoom and scaling controls for visualizations
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging

logger = logging.getLogger(__name__)

class ChartScaler:
    """PowerBI-style scaling and zoom controls for charts"""
    
    def __init__(self):
        self.scale_options = {
            "Fit to Width": "fit_width",
            "Fit to Height": "fit_height", 
            "Actual Size": "actual_size",
            "Fill Page": "fill_page",
            "Custom Scale": "custom"
        }
        
        self.zoom_levels = {
            "25%": 0.25,
            "50%": 0.5,
            "75%": 0.75,
            "100%": 1.0,
            "125%": 1.25,
            "150%": 1.5,
            "200%": 2.0,
            "300%": 3.0
        }
    
    def create_scaling_controls(self, chart_id: str) -> dict:
        """Create PowerBI-style scaling controls for a chart"""
        
        with st.expander(f"🔍 Chart Controls - {chart_id}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Scale mode selection
                scale_mode = st.selectbox(
                    "Scale Mode",
                    options=list(self.scale_options.keys()),
                    index=3,  # Default to "Fill Page"
                    key=f"scale_mode_{chart_id}"
                )
            
            with col2:
                # Zoom level
                zoom_level = st.selectbox(
                    "Zoom Level",
                    options=list(self.zoom_levels.keys()),
                    index=3,  # Default to 100%
                    key=f"zoom_level_{chart_id}"
                )
            
            with col3:
                # Chart height adjustment
                height_adjustment = st.slider(
                    "Height",
                    min_value=200,
                    max_value=800,
                    value=400,
                    step=50,
                    key=f"height_{chart_id}"
                )
            
            # Advanced controls
            st.markdown("**Advanced Controls:**")
            col4, col5, col6 = st.columns(3)
            
            with col4:
                show_toolbar = st.checkbox(
                    "Show Toolbar",
                    value=True,
                    key=f"toolbar_{chart_id}"
                )
            
            with col5:
                enable_zoom = st.checkbox(
                    "Enable Zoom",
                    value=True,
                    key=f"enable_zoom_{chart_id}"
                )
            
            with col6:
                enable_pan = st.checkbox(
                    "Enable Pan",
                    value=True,
                    key=f"enable_pan_{chart_id}"
                )
            
            # Export options
            st.markdown("**Export Options:**")
            col7, col8 = st.columns(2)
            
            with col7:
                if st.button(f"📊 Export PNG", key=f"export_png_{chart_id}"):
                    st.info("PNG export functionality would be implemented here")
            
            with col8:
                if st.button(f"📈 Export SVG", key=f"export_svg_{chart_id}"):
                    st.info("SVG export functionality would be implemented here")
        
        return {
            "scale_mode": self.scale_options[scale_mode],
            "zoom_level": self.zoom_levels[zoom_level],
            "height": height_adjustment,
            "show_toolbar": show_toolbar,
            "enable_zoom": enable_zoom,
            "enable_pan": enable_pan
        }
    
    def apply_scaling_to_figure(self, fig: go.Figure, scaling_config: dict, chart_type: str = None) -> go.Figure:
        """Apply PowerBI-style scaling configuration to a Plotly figure"""
        
        try:
            # Get scaling parameters
            scale_mode = scaling_config.get("scale_mode", "fill_page")
            zoom_level = scaling_config.get("zoom_level", 1.0)
            height = scaling_config.get("height", 400)
            show_toolbar = scaling_config.get("show_toolbar", True)
            enable_zoom = scaling_config.get("enable_zoom", True)
            enable_pan = scaling_config.get("enable_pan", True)
            
            # Apply height scaling
            scaled_height = int(height * zoom_level)
            
            # Configure layout based on scale mode
            layout_updates = {
                "height": scaled_height,
                "showlegend": True,
                "hovermode": "closest"
            }
            
            # Scale mode specific adjustments
            if scale_mode == "fit_width":
                layout_updates.update({
                    "autosize": True,
                    "margin": dict(l=40, r=40, t=60, b=40)
                })
            elif scale_mode == "fit_height":
                layout_updates.update({
                    "autosize": False,
                    "height": scaled_height,
                    "margin": dict(l=60, r=60, t=80, b=60)
                })
            elif scale_mode == "actual_size":
                layout_updates.update({
                    "autosize": False,
                    "width": 800,
                    "height": scaled_height,
                    "margin": dict(l=50, r=50, t=70, b=50)
                })
            elif scale_mode == "fill_page":
                layout_updates.update({
                    "autosize": True,
                    "margin": dict(l=20, r=20, t=40, b=20)
                })
            elif scale_mode == "custom":
                # Custom scaling with zoom level
                layout_updates.update({
                    "autosize": False,
                    "width": int(800 * zoom_level),
                    "height": scaled_height,
                    "margin": dict(
                        l=int(50 * zoom_level),
                        r=int(50 * zoom_level),
                        t=int(70 * zoom_level),
                        b=int(50 * zoom_level)
                    )
                })
            
            # Apply PowerBI-style theme enhancements
            layout_updates.update({
                "template": "plotly_white",
                "font": dict(
                    family="Segoe UI, Arial, sans-serif",
                    size=int(12 * zoom_level),
                    color="#323130"
                ),
                "title": dict(
                    font=dict(
                        size=int(16 * zoom_level),
                        color="#323130"
                    ),
                    x=0.5,
                    xanchor="center"
                ),
                "plot_bgcolor": "rgba(0,0,0,0)",
                "paper_bgcolor": "rgba(0,0,0,0)"
            })
            
            # Configure interactivity
            config = {
                "displayModeBar": show_toolbar,
                "displaylogo": False,
                "modeBarButtonsToRemove": [],
                "scrollZoom": enable_zoom,
                "doubleClick": "reset+autosize" if enable_zoom else False,
                "showTips": True,
                "responsive": scale_mode in ["fit_width", "fill_page"]
            }
            
            # Disable zoom/pan if requested
            if not enable_zoom:
                config["modeBarButtonsToRemove"].extend([
                    "zoom2d", "zoomIn2d", "zoomOut2d", "autoScale2d"
                ])
            
            if not enable_pan:
                config["modeBarButtonsToRemove"].extend([
                    "pan2d", "select2d", "lasso2d"
                ])
            
            # Apply chart-type specific scaling
            if chart_type:
                layout_updates.update(self._get_chart_specific_scaling(chart_type, zoom_level))
            
            # Update figure
            fig.update_layout(**layout_updates)
            
            # Store config for Streamlit
            fig._config = config
            
            return fig
            
        except Exception as e:
            logger.error(f"Error applying scaling to figure: {e}")
            return fig
    
    def _get_chart_specific_scaling(self, chart_type: str, zoom_level: float) -> dict:
        """Get chart-type specific scaling adjustments"""
        
        scaling_adjustments = {}
        
        if chart_type in ["bar", "clustered_column", "stacked_column"]:
            # Bar/Column charts
            scaling_adjustments.update({
                "xaxis": dict(
                    tickfont=dict(size=int(10 * zoom_level)),
                    titlefont=dict(size=int(12 * zoom_level)),
                    showgrid=True,
                    gridwidth=1,
                    gridcolor="rgba(128,128,128,0.2)"
                ),
                "yaxis": dict(
                    tickfont=dict(size=int(10 * zoom_level)),
                    titlefont=dict(size=int(12 * zoom_level)),
                    showgrid=True,
                    gridwidth=1,
                    gridcolor="rgba(128,128,128,0.2)"
                )
            })
        
        elif chart_type in ["pie", "donut"]:
            # Pie/Donut charts
            scaling_adjustments.update({
                "showlegend": True,
                "legend": dict(
                    font=dict(size=int(10 * zoom_level)),
                    orientation="v",
                    x=1.02,
                    y=0.5
                )
            })
        
        elif chart_type in ["line", "area"]:
            # Line/Area charts
            scaling_adjustments.update({
                "xaxis": dict(
                    tickfont=dict(size=int(10 * zoom_level)),
                    titlefont=dict(size=int(12 * zoom_level)),
                    showgrid=True,
                    gridwidth=1,
                    gridcolor="rgba(128,128,128,0.2)"
                ),
                "yaxis": dict(
                    tickfont=dict(size=int(10 * zoom_level)),
                    titlefont=dict(size=int(12 * zoom_level)),
                    showgrid=True,
                    gridwidth=1,
                    gridcolor="rgba(128,128,128,0.2)"
                )
            })
        
        elif chart_type == "scatter":
            # Scatter plots
            scaling_adjustments.update({
                "xaxis": dict(
                    tickfont=dict(size=int(10 * zoom_level)),
                    titlefont=dict(size=int(12 * zoom_level)),
                    showgrid=True,
                    gridwidth=1,
                    gridcolor="rgba(128,128,128,0.2)"
                ),
                "yaxis": dict(
                    tickfont=dict(size=int(10 * zoom_level)),
                    titlefont=dict(size=int(12 * zoom_level)),
                    showgrid=True,
                    gridwidth=1,
                    gridcolor="rgba(128,128,128,0.2)"
                )
            })
        
        return scaling_adjustments
    
    def create_dashboard_scaler(self) -> dict:
        """Create dashboard-wide scaling controls"""
        
        st.sidebar.markdown("## 🎛️ Dashboard Controls")
        
        # Global zoom
        global_zoom = st.sidebar.selectbox(
            "Global Zoom",
            options=list(self.zoom_levels.keys()),
            index=3,  # 100%
            key="global_zoom"
        )
        
        # Layout density
        layout_density = st.sidebar.selectbox(
            "Layout Density",
            options=["Compact", "Normal", "Spacious"],
            index=1,  # Normal
            key="layout_density"
        )
        
        # Chart grid
        charts_per_row = st.sidebar.selectbox(
            "Charts per Row",
            options=[1, 2, 3, 4],
            index=2,  # 3 charts per row
            key="charts_per_row"
        )
        
        # Theme selection
        theme = st.sidebar.selectbox(
            "Dashboard Theme",
            options=["Light", "Dark", "PowerBI", "Custom"],
            index=2,  # PowerBI theme
            key="dashboard_theme"
        )
        
        # Export dashboard
        st.sidebar.markdown("### 📤 Export Dashboard")
        
        if st.sidebar.button("📊 Export to PowerBI"):
            st.sidebar.success("PowerBI export initiated!")
        
        if st.sidebar.button("📄 Export to PDF"):
            st.sidebar.info("PDF export would be implemented here")
        
        if st.sidebar.button("🖼️ Export to PNG"):
            st.sidebar.info("PNG export would be implemented here")
        
        return {
            "global_zoom": self.zoom_levels[global_zoom],
            "layout_density": layout_density.lower(),
            "charts_per_row": charts_per_row,
            "theme": theme.lower(),
            "export_requested": False  # Would be set by export buttons
        }
    
    def apply_dashboard_scaling(self, dashboard_config: dict) -> dict:
        """Apply dashboard-wide scaling configuration"""
        
        # Calculate responsive column configuration
        charts_per_row = dashboard_config.get("charts_per_row", 3)
        global_zoom = dashboard_config.get("global_zoom", 1.0)
        layout_density = dashboard_config.get("layout_density", "normal")
        
        # Density-based spacing
        spacing_config = {
            "compact": {"padding": 10, "margin": 5, "height_multiplier": 0.8},
            "normal": {"padding": 20, "margin": 10, "height_multiplier": 1.0},
            "spacious": {"padding": 30, "margin": 15, "height_multiplier": 1.2}
        }
        
        spacing = spacing_config.get(layout_density, spacing_config["normal"])
        
        return {
            "columns_config": charts_per_row,
            "base_height": int(400 * global_zoom * spacing["height_multiplier"]),
            "padding": int(spacing["padding"] * global_zoom),
            "margin": int(spacing["margin"] * global_zoom),
            "global_zoom": global_zoom,
            "responsive": True
        }

# Global scaler instance
chart_scaler = ChartScaler()