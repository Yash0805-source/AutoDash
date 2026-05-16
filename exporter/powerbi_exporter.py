#!/usr/bin/env python3
"""
PowerBI Export Module - Generate downloadable PowerBI-compatible files
"""

import json
import zipfile
import io
import pandas as pd
from datetime import datetime
import base64
import logging

logger = logging.getLogger(__name__)

class PowerBIExporter:
    """Export dashboard data and configuration to PowerBI-compatible formats"""
    
    def __init__(self):
        self.version = "1.0.0"
        self.created_date = datetime.now().isoformat()
    
    def export_to_pbix_file(self, df: pd.DataFrame, plan: dict, metadata: dict) -> bytes:
        """
        Export dashboard to PowerBI file format (.pbix)
        This creates a complete PowerBI file with data included
        """
        try:
            # Create PowerBI file structure with embedded data
            pbix_data = self._create_powerbi_file(df, plan, metadata)
            
            # Create in-memory zip file (PBIX files are zip files with data)
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add data model with embedded data
                zip_file.writestr('DataModelSchema', json.dumps(pbix_data['data_model'], indent=2))
                
                # Add actual data as CSV
                csv_data = df.to_csv(index=False)
                zip_file.writestr('Data/data.csv', csv_data)
                
                # Add report layout
                zip_file.writestr('Report/Layout', json.dumps(pbix_data['layout'], indent=2))
                
                # Add data source info
                zip_file.writestr('DataSources', json.dumps(pbix_data['data_sources'], indent=2))
                
                # Add metadata
                zip_file.writestr('Metadata', json.dumps(pbix_data['metadata'], indent=2))
                
                # Add version info
                zip_file.writestr('Version', self.version)
                
                # Add PowerBI specific files
                zip_file.writestr('SecurityBindings', json.dumps(pbix_data['security'], indent=2))
                zip_file.writestr('Settings', json.dumps(pbix_data['settings'], indent=2))
                
                # Add data relationships
                zip_file.writestr('Relationships', json.dumps(pbix_data['relationships'], indent=2))
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"PowerBI PBIX export failed: {e}")
            raise e
    
    def _create_powerbi_file(self, df: pd.DataFrame, plan: dict, metadata: dict) -> dict:
        """Create complete PowerBI file structure with embedded data"""
        
        # Convert DataFrame to PowerBI data model
        data_model = self._create_data_model(df, metadata)
        
        # Convert charts to PowerBI visuals
        layout = self._create_report_layout(plan, metadata)
        
        # Create data source configuration for embedded data
        data_sources = self._create_embedded_data_sources(metadata)
        
        # Create security bindings
        security = self._create_security_bindings()
        
        # Create settings
        settings = self._create_pbix_settings()
        
        # Create relationships
        relationships = self._create_data_relationships(metadata)
        
        # Create metadata
        pbix_metadata = {
            "version": self.version,
            "created": self.created_date,
            "generator": "AutoDash-LLM",
            "description": "AI-Generated PowerBI Dashboard with Embedded Data",
            "charts_count": len(plan.get('charts', [])),
            "kpis_count": len(plan.get('kpis', [])),
            "data_rows": len(df),
            "data_columns": len(df.columns),
            "file_type": "pbix"
        }
        
        return {
            "data_model": data_model,
            "layout": layout,
            "data_sources": data_sources,
            "metadata": pbix_metadata,
            "security": security,
            "settings": settings,
            "relationships": relationships
        }
    
    def _create_embedded_data_sources(self, metadata: dict) -> dict:
        """Create PowerBI data source configuration for embedded data"""
        return {
            "dataSources": [{
                "name": "EmbeddedData",
                "connectionDetails": {
                    "protocol": "embedded",
                    "address": {
                        "path": "Data/data.csv"
                    }
                },
                "options": {
                    "commandTimeout": "00:20:00",
                    "sqlQueryTimeout": "00:20:00"
                },
                "credential": {
                    "AuthenticationKind": "Embedded",
                    "kind": "Embedded",
                    "path": "Data/data.csv"
                }
            }],
            "mashup": json.dumps({
                "Version": "2.0",
                "Queries": [{
                    "Name": "MainTable",
                    "Source": "Data/data.csv",
                    "Type": "CSV"
                }]
            })
        }
    
    def _create_security_bindings(self) -> dict:
        """Create PowerBI security bindings"""
        return {
            "version": "1.0",
            "bindings": [],
            "permissions": {
                "read": True,
                "write": False,
                "admin": False
            }
        }
    
    def _create_pbix_settings(self) -> dict:
        """Create PowerBI file settings"""
        return {
            "version": "1.0",
            "settings": {
                "locale": "en-US",
                "theme": "default",
                "autoRefresh": False,
                "dataRefreshSettings": {
                    "enabled": False,
                    "frequency": "daily"
                }
            }
        }
    
    def _create_data_relationships(self, metadata: dict) -> dict:
        """Create data relationships for PowerBI"""
        return {
            "version": "1.0",
            "relationships": [],
            "hierarchies": []
        }
    
    def _create_data_model(self, df: pd.DataFrame, metadata: dict) -> dict:
        """Create PowerBI data model from DataFrame"""
        
        # Convert DataFrame schema to PowerBI format
        columns = []
        for col_info in metadata.get('columns', []):
            col_name = col_info['name']
            col_type = col_info['type']
            
            # Map our types to PowerBI types
            powerbi_type = {
                'numerical': 'Double',
                'categorical': 'Text',
                'datetime': 'DateTime',
                'boolean': 'Boolean'
            }.get(col_type, 'Text')
            
            columns.append({
                "name": col_name,
                "dataType": powerbi_type,
                "isHidden": False,
                "summarizeBy": "Sum" if col_type == 'numerical' else "None",
                "formatString": self._get_format_string(col_type, col_info)
            })
        
        return {
            "name": "AutoDashData",
            "tables": [{
                "name": "MainTable",
                "columns": columns,
                "measures": self._create_measures(metadata),
                "relationships": []
            }],
            "culture": "en-US"
        }
    
    def _create_measures(self, metadata: dict) -> list:
        """Create PowerBI measures (calculated fields)"""
        measures = []
        
        # Create measures for numerical columns
        for col_info in metadata.get('columns', []):
            if col_info['type'] == 'numerical':
                col_name = col_info['name']
                
                # Total measure
                measures.append({
                    "name": f"Total {col_name}",
                    "expression": f"SUM(MainTable[{col_name}])",
                    "formatString": "#,##0.00"
                })
                
                # Average measure
                measures.append({
                    "name": f"Average {col_name}",
                    "expression": f"AVERAGE(MainTable[{col_name}])",
                    "formatString": "#,##0.00"
                })
        
        return measures
    
    def _create_report_layout(self, plan: dict, metadata: dict) -> dict:
        """Create PowerBI report layout from dashboard plan"""
        
        visuals = []
        
        # Convert KPIs to PowerBI cards
        for i, kpi in enumerate(plan.get('kpis', [])):
            visual = self._create_kpi_visual(kpi, i)
            visuals.append(visual)
        
        # Convert charts to PowerBI visuals
        for i, chart in enumerate(plan.get('charts', [])):
            visual = self._create_chart_visual(chart, i + len(plan.get('kpis', [])))
            visuals.append(visual)
        
        return {
            "id": 1,
            "displayName": "AI Generated Dashboard",
            "visualContainers": visuals,
            "config": json.dumps({
                "layouts": [{
                    "id": 0,
                    "position": {
                        "x": 0,
                        "y": 0,
                        "z": 0,
                        "width": 1280,
                        "height": 720
                    }
                }]
            })
        }
    
    def _create_kpi_visual(self, kpi: dict, index: int) -> dict:
        """Convert KPI to PowerBI card visual"""
        
        # Calculate position in grid
        col = index % 4
        row = index // 4
        
        return {
            "id": f"kpi_{index}",
            "visualType": "card",
            "position": {
                "x": col * 300,
                "y": row * 150,
                "width": 280,
                "height": 140
            },
            "config": json.dumps({
                "singleVisual": {
                    "visualType": "card",
                    "projections": {
                        "Values": [{
                            "queryRef": f"MainTable.{kpi.get('column')}",
                            "aggregation": kpi.get('aggregation', 'Sum').title()
                        }]
                    },
                    "prototypeQuery": {
                        "Version": 2,
                        "From": [{"Name": "MainTable", "Entity": "MainTable"}]
                    }
                }
            }),
            "title": kpi.get('label', 'KPI'),
            "subtitle": ""
        }
    
    def _create_chart_visual(self, chart: dict, index: int) -> dict:
        """Convert chart to PowerBI visual"""
        
        # Map our chart types to PowerBI visual types
        chart_type_mapping = {
            'clustered_column': 'clusteredColumnChart',
            'stacked_column': 'stackedColumnChart',
            'bar': 'clusteredBarChart',
            'clustered_bar': 'clusteredBarChart',
            'stacked_bar': 'stackedBarChart',
            'line': 'lineChart',
            'area': 'areaChart',
            'pie': 'pieChart',
            'donut': 'donutChart',
            'scatter': 'scatterChart',
            'treemap': 'treemap',
            'funnel': 'funnelChart',
            'waterfall': 'waterfallChart',
            'table': 'table',
            'matrix': 'matrix'
        }
        
        powerbi_type = chart_type_mapping.get(chart.get('type'), 'clusteredColumnChart')
        
        # Calculate position in grid (after KPIs)
        charts_per_row = 3
        col = index % charts_per_row
        row = (index // charts_per_row) + 2  # Start after KPI rows
        
        return {
            "id": f"chart_{index}",
            "visualType": powerbi_type,
            "position": {
                "x": col * 400,
                "y": row * 300,
                "width": 380,
                "height": 280
            },
            "config": json.dumps({
                "singleVisual": {
                    "visualType": powerbi_type,
                    "projections": self._create_projections(chart),
                    "prototypeQuery": {
                        "Version": 2,
                        "From": [{"Name": "MainTable", "Entity": "MainTable"}]
                    }
                }
            }),
            "title": chart.get('title', 'Chart'),
            "subtitle": ""
        }
    
    def _create_projections(self, chart: dict) -> dict:
        """Create PowerBI projections from chart configuration"""
        projections = {}
        
        chart_type = chart.get('type')
        x_col = chart.get('x')
        y_col = chart.get('y')
        
        if chart_type in ['table', 'matrix']:
            # Table/Matrix projections
            if chart_type == 'table':
                columns = chart.get('columns', [])
                projections["Values"] = [{"queryRef": f"MainTable.{col}"} for col in columns]
            else:  # matrix
                if chart.get('rows'):
                    projections["Rows"] = [{"queryRef": f"MainTable.{chart['rows']}"}]
                if chart.get('columns'):
                    projections["Columns"] = [{"queryRef": f"MainTable.{chart['columns']}"}]
                if chart.get('values'):
                    projections["Values"] = [{"queryRef": f"MainTable.{chart['values']}", "aggregation": "Sum"}]
        else:
            # Standard chart projections
            if x_col:
                projections["Category"] = [{"queryRef": f"MainTable.{x_col}"}]
            
            if y_col:
                if isinstance(y_col, list):
                    projections["Y"] = [{"queryRef": f"MainTable.{col}", "aggregation": "Sum"} for col in y_col]
                elif y_col != "count":
                    projections["Y"] = [{"queryRef": f"MainTable.{y_col}", "aggregation": "Sum"}]
                else:
                    projections["Y"] = [{"queryRef": f"MainTable.{x_col}", "aggregation": "Count"}]
        
        return projections
    
    def _create_data_sources(self, metadata: dict) -> dict:
        """Create PowerBI data source configuration"""
        return {
            "dataSources": [{
                "name": "AutoDashData",
                "connectionDetails": {
                    "protocol": "file",
                    "address": {
                        "path": "data.csv"
                    }
                },
                "options": {
                    "commandTimeout": "00:20:00",
                    "sqlQueryTimeout": "00:20:00"
                },
                "credential": {
                    "AuthenticationKind": "Anonymous",
                    "kind": "Anonymous",
                    "path": "data.csv"
                }
            }],
            "mashup": ""
        }
    
    def _get_format_string(self, col_type: str, col_info: dict) -> str:
        """Get PowerBI format string for column type"""
        if col_type == 'numerical':
            if col_info.get('is_integer', False):
                return "#,##0"
            else:
                return "#,##0.00"
        elif col_type == 'datetime':
            return "mm/dd/yyyy"
        else:
            return ""
    
    def export_to_json(self, df: pd.DataFrame, plan: dict, metadata: dict) -> str:
        """Export dashboard configuration as JSON for PowerBI import"""
        
        export_data = {
            "version": self.version,
            "created": self.created_date,
            "generator": "AutoDash-LLM",
            "file_type": "pbix",
            "data": {
                "columns": df.columns.tolist(),
                "dtypes": df.dtypes.astype(str).to_dict(),
                "sample_data": df.head(5).to_dict('records'),
                "embedded": True
            },
            "dashboard": {
                "kpis": plan.get('kpis', []),
                "charts": plan.get('charts', [])
            },
            "metadata": metadata,
            "powerbi_instructions": {
                "steps": [
                    "1. Download the .pbix file",
                    "2. Open the .pbix file in PowerBI Desktop",
                    "3. The dashboard will load with embedded data",
                    "4. Customize further if needed"
                ],
                "advantages": [
                    "✅ Complete file with embedded data",
                    "✅ No need to connect external data sources",
                    "✅ Ready to use immediately",
                    "✅ Can be shared easily"
                ],
                "chart_mappings": {
                    "clustered_column": "Clustered Column Chart",
                    "stacked_column": "Stacked Column Chart",
                    "bar": "Clustered Bar Chart",
                    "pie": "Pie Chart",
                    "donut": "Donut Chart",
                    "line": "Line Chart",
                    "area": "Area Chart",
                    "scatter": "Scatter Chart",
                    "treemap": "Treemap",
                    "funnel": "Funnel Chart",
                    "waterfall": "Waterfall Chart",
                    "table": "Table",
                    "matrix": "Matrix"
                }
            }
        }
        
        return json.dumps(export_data, indent=2, default=str)

def create_powerbi_export(df: pd.DataFrame, plan: dict, metadata: dict) -> tuple:
    """
    Create PowerBI export files (.pbix with embedded data)
    Returns: (pbix_bytes, json_config)
    """
    exporter = PowerBIExporter()
    
    try:
        # Create PowerBI file with embedded data
        pbix_bytes = exporter.export_to_pbix_file(df, plan, metadata)
        
        # Create JSON configuration
        json_config = exporter.export_to_json(df, plan, metadata)
        
        return pbix_bytes, json_config
        
    except Exception as e:
        logger.error(f"PowerBI export creation failed: {e}")
        raise e