import pandas as pd
import numpy as np
from preprocessing.feature_engineer import apply_feature_engineering

def infer_column_type(series):
    """Enhanced column type inference with better detection"""
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        # Check if it's actually an ID column (high cardinality, sequential, integer)
        if (series.nunique() / len(series) > 0.95 and 
            series.nunique() > 10 and 
            series.dtype in ['int64', 'int32'] and
            series.is_monotonic_increasing):
            return "id"
        return "numerical"
    
    # Check if categorical has too many unique values (might be text)
    unique_ratio = series.nunique() / len(series)
    if unique_ratio > 0.5 and series.nunique() > 20:
        return "text"
    
    return "categorical"

def get_column_insights(series, ctype):
    """Get deeper insights about each column"""
    insights = {}
    
    try:
        if ctype == "numerical":
            insights.update({
                "mean": round(float(series.mean()), 2) if not pd.isna(series.mean()) else 0,
                "median": round(float(series.median()), 2) if not pd.isna(series.median()) else 0,
                "std": round(float(series.std()), 2) if not pd.isna(series.std()) else 0,
                "min": round(float(series.min()), 2) if not pd.isna(series.min()) else 0,
                "max": round(float(series.max()), 2) if not pd.isna(series.max()) else 0,
                "q25": round(float(series.quantile(0.25)), 2) if not pd.isna(series.quantile(0.25)) else 0,
                "q75": round(float(series.quantile(0.75)), 2) if not pd.isna(series.quantile(0.75)) else 0,
                "is_integer": series.dtype in ['int64', 'int32'],
                "has_negatives": bool((series < 0).any()),
                "zero_count": int((series == 0).sum())
            })
        
        elif ctype == "categorical":
            value_counts = series.value_counts()
            insights.update({
                "unique_values": int(series.nunique()),
                "most_common": {str(k): int(v) for k, v in value_counts.head(5).to_dict().items()},
                "is_binary": bool(series.nunique() == 2),
                "top_category": str(value_counts.index[0]) if len(value_counts) > 0 else "None"
            })
        
        elif ctype == "datetime":
            insights.update({
                "min_date": str(series.min()),
                "max_date": str(series.max()),
                "date_range_days": int((series.max() - series.min()).days) if not pd.isna(series.min()) and not pd.isna(series.max()) else 0
            })
    
    except Exception as e:
        # If any insight calculation fails, just skip it
        insights["error"] = f"Could not calculate insights: {str(e)}"
    
    return insights

def suggest_chart_types(metadata):
    """Suggest appropriate chart types based on data characteristics - completely generic"""
    suggestions = []
    columns = metadata["columns"]
    
    numerical_cols = [c for c in columns if c["type"] == "numerical"]
    categorical_cols = [c for c in columns if c["type"] == "categorical"]
    datetime_cols = [c for c in columns if c["type"] == "datetime"]
    
    # Time series charts (any datetime + any numerical)
    if datetime_cols and numerical_cols:
        for datetime_col in datetime_cols[:2]:  # Max 2 datetime columns
            for num_col in numerical_cols[:3]:  # Max 3 numerical per datetime
                suggestions.append({
                    "type": "line",
                    "x": datetime_col["name"],
                    "y": num_col["name"],
                    "title": f"{num_col['name']} Over Time",
                    "priority": "high"
                })
    
    # Category vs numerical (any categorical with reasonable cardinality + any numerical)
    if categorical_cols and numerical_cols:
        for cat_col in categorical_cols:
            unique_count = cat_col.get("unique_values", 0)
            if unique_count > 1 and unique_count <= 20:  # Reasonable number of categories
                for num_col in numerical_cols[:2]:  # Max 2 numerical per categorical
                    suggestions.append({
                        "type": "bar",
                        "x": cat_col["name"],
                        "y": num_col["name"],
                        "title": f"{num_col['name']} by {cat_col['name']}",
                        "priority": "high"
                    })
    
    # Scatter plots for numerical correlations (any two numerical columns)
    if len(numerical_cols) >= 2:
        correlations = metadata.get("correlations", {})
        scatter_count = 0
        for i, col1 in enumerate(numerical_cols):
            for col2 in numerical_cols[i+1:]:
                # Check correlation if available
                corr = 0
                try:
                    corr = abs(correlations.get(col1["name"], {}).get(col2["name"], 0))
                except:
                    pass
                
                # Suggest scatter plot if there's some correlation or if we don't have correlation data
                if corr > 0.3 or corr == 0:  # Include if correlation unknown
                    suggestions.append({
                        "type": "scatter",
                        "x": col1["name"],
                        "y": col2["name"],
                        "title": f"{col1['name']} vs {col2['name']}",
                        "priority": "medium" if corr > 0.5 else "low"
                    })
                    scatter_count += 1
                    
                    # Limit scatter plots to avoid too many suggestions
                    if scatter_count >= 3:
                        break
            
            if scatter_count >= 3:
                break
    
    # Histogram for any numerical column with good distribution
    for num_col in numerical_cols[:2]:  # Max 2 histograms
        if num_col.get("std", 0) > 0:  # Has variation
            suggestions.append({
                "type": "histogram",
                "x": num_col["name"],
                "y": None,
                "title": f"Distribution of {num_col['name']}",
                "priority": "low"
            })
    
    return suggestions

def profile_dataframe(df, apply_feature_eng=True):
    """Enhanced dataframe profiling with automatic feature engineering"""
    
    # Store original info
    original_shape = df.shape
    original_missing = df.isnull().sum().sum()
    
    # Apply feature engineering if requested
    feature_report = None
    if apply_feature_eng and original_missing > 0:
        try:
            df, feature_report = apply_feature_engineering(df)
        except Exception as e:
            print(f"Feature engineering failed: {e}")
            # Continue with original dataframe
    
    metadata = {
        "n_rows": len(df),
        "n_columns": len(df.columns),
        "original_shape": original_shape,
        "columns": [],
        "data_quality": {
            "total_missing": df.isnull().sum().sum(),
            "missing_percentage": round((df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100, 2),
            "original_missing": original_missing
        }
    }
    
    # Add feature engineering report if available
    if feature_report:
        metadata["feature_engineering"] = feature_report

    for col in df.columns:
        s = df[col].dropna()  # Remove NaN for better analysis
        if len(s) == 0:  # Skip completely empty columns
            continue
            
        ctype = infer_column_type(s)
        insights = get_column_insights(s, ctype)

        info = {
            "name": col,
            "type": ctype,
            "missing_pct": round(df[col].isna().mean() * 100, 2),
            "sample_values": [str(x) for x in s.head(3).tolist()],  # Convert to strings to avoid type issues
            **insights
        }

        metadata["columns"].append(info)

    # Enhanced correlations
    num_df = df.select_dtypes(include=np.number)
    if num_df.shape[1] > 1:
        corr_matrix = num_df.corr()
        metadata["correlations"] = corr_matrix.round(3).to_dict()
        
        # Find strong correlations
        strong_correlations = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.5:
                    strong_correlations.append({
                        "col1": corr_matrix.columns[i],
                        "col2": corr_matrix.columns[j],
                        "correlation": round(corr_val, 3)
                    })
        metadata["strong_correlations"] = strong_correlations
    else:
        metadata["correlations"] = {}
        metadata["strong_correlations"] = []
    
    # Add chart suggestions
    metadata["suggested_charts"] = suggest_chart_types(metadata)
    
    return df, metadata