"""
Automatic Feature Engineering Module
Handles missing values and creates new features automatically
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

class AutoFeatureEngineer:
    """Automatic feature engineering for missing values and data enhancement"""
    
    def __init__(self):
        self.transformations_applied = []
        self.original_columns = []
        self.engineered_columns = []
    
    def fit_transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Apply automatic feature engineering to the dataframe
        Returns: (transformed_df, transformation_report)
        """
        logger.info("Starting automatic feature engineering...")
        
        self.original_columns = df.columns.tolist()
        transformed_df = df.copy()
        
        # 1. Handle missing values
        transformed_df = self._handle_missing_values(transformed_df)
        
        # 2. Create derived features
        transformed_df = self._create_derived_features(transformed_df)
        
        # 3. Enhance categorical features
        transformed_df = self._enhance_categorical_features(transformed_df)
        
        # 4. Create time-based features
        transformed_df = self._create_time_features(transformed_df)
        
        # Generate report
        report = self._generate_transformation_report(df, transformed_df)
        
        logger.info(f"Feature engineering completed. Applied {len(self.transformations_applied)} transformations.")
        return transformed_df, report
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values with intelligent strategies"""
        
        for col in df.columns:
            missing_pct = df[col].isnull().mean() * 100
            
            if missing_pct == 0:
                continue
            
            if missing_pct > 90:
                # Drop columns with >90% missing values
                df = df.drop(columns=[col])
                self.transformations_applied.append({
                    "type": "drop_column",
                    "column": col,
                    "reason": f"Too many missing values ({missing_pct:.1f}%)"
                })
                continue
            
            # Handle based on data type
            if pd.api.types.is_numeric_dtype(df[col]):
                df = self._handle_numeric_missing(df, col, missing_pct)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                df = self._handle_datetime_missing(df, col, missing_pct)
            else:
                df = self._handle_categorical_missing(df, col, missing_pct)
        
        return df
    
    def _handle_numeric_missing(self, df: pd.DataFrame, col: str, missing_pct: float) -> pd.DataFrame:
        """Handle missing values in numeric columns"""
        
        series = df[col]
        
        # Create missing indicator if significant missing values
        if missing_pct > 10:
            indicator_col = f"{col}_was_missing"
            df[indicator_col] = series.isnull().astype(int)
            self.engineered_columns.append(indicator_col)
            self.transformations_applied.append({
                "type": "missing_indicator",
                "column": col,
                "new_column": indicator_col,
                "missing_pct": missing_pct
            })
        
        # Choose imputation strategy
        if missing_pct < 5:
            # Low missing: use mean/median
            if series.skew() > 1:  # Highly skewed
                fill_value = series.median()
                strategy = "median"
            else:
                fill_value = series.mean()
                strategy = "mean"
        elif missing_pct < 20:
            # Medium missing: use median (more robust)
            fill_value = series.median()
            strategy = "median"
        else:
            # High missing: use mode or create separate category
            fill_value = series.mode().iloc[0] if len(series.mode()) > 0 else series.median()
            strategy = "mode"
        
        df[col] = series.fillna(fill_value)
        
        self.transformations_applied.append({
            "type": "numeric_imputation",
            "column": col,
            "strategy": strategy,
            "fill_value": fill_value,
            "missing_pct": missing_pct
        })
        
        return df
    
    def _handle_categorical_missing(self, df: pd.DataFrame, col: str, missing_pct: float) -> pd.DataFrame:
        """Handle missing values in categorical columns"""
        
        series = df[col]
        
        if missing_pct > 10:
            # Create missing indicator
            indicator_col = f"{col}_was_missing"
            df[indicator_col] = series.isnull().astype(int)
            self.engineered_columns.append(indicator_col)
            self.transformations_applied.append({
                "type": "missing_indicator",
                "column": col,
                "new_column": indicator_col,
                "missing_pct": missing_pct
            })
        
        # Choose imputation strategy
        if missing_pct < 10:
            # Low missing: use mode
            fill_value = series.mode().iloc[0] if len(series.mode()) > 0 else "Unknown"
            strategy = "mode"
        else:
            # High missing: create explicit "Missing" category
            fill_value = "Missing"
            strategy = "explicit_missing"
        
        df[col] = series.fillna(fill_value)
        
        self.transformations_applied.append({
            "type": "categorical_imputation",
            "column": col,
            "strategy": strategy,
            "fill_value": fill_value,
            "missing_pct": missing_pct
        })
        
        return df
    
    def _handle_datetime_missing(self, df: pd.DataFrame, col: str, missing_pct: float) -> pd.DataFrame:
        """Handle missing values in datetime columns"""
        
        series = df[col]
        
        if missing_pct > 10:
            # Create missing indicator
            indicator_col = f"{col}_was_missing"
            df[indicator_col] = series.isnull().astype(int)
            self.engineered_columns.append(indicator_col)
            self.transformations_applied.append({
                "type": "missing_indicator",
                "column": col,
                "new_column": indicator_col,
                "missing_pct": missing_pct
            })
        
        # Use forward fill or median date
        if missing_pct < 20:
            df[col] = series.ffill().bfill()
            strategy = "forward_fill"
        else:
            # Use median date
            median_date = series.median()
            df[col] = series.fillna(median_date)
            strategy = "median_date"
        
        self.transformations_applied.append({
            "type": "datetime_imputation",
            "column": col,
            "strategy": strategy,
            "missing_pct": missing_pct
        })
        
        return df
    
    def _create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create derived features from existing columns - completely generic approach"""
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Create ratios for related numeric columns (only if we have multiple numeric columns)
        if len(numeric_cols) >= 2:
            ratio_count = 0
            for i, col1 in enumerate(numeric_cols):
                for col2 in numeric_cols[i+1:]:
                    # Skip if columns are too similar (correlation > 0.95)
                    try:
                        if abs(df[col1].corr(df[col2])) > 0.95:
                            continue
                    except:
                        continue
                    
                    # Create ratio if no zeros in denominator and values make sense
                    if (df[col2] != 0).all() and df[col2].min() > 0:
                        ratio_col = f"{col1}_to_{col2}_ratio"
                        df[ratio_col] = df[col1] / df[col2]
                        self.engineered_columns.append(ratio_col)
                        
                        self.transformations_applied.append({
                            "type": "ratio_feature",
                            "numerator": col1,
                            "denominator": col2,
                            "new_column": ratio_col
                        })
                        
                        ratio_count += 1
                        # Limit to avoid too many features (max 3 ratios)
                        if ratio_count >= 3:
                            break
                
                if ratio_count >= 3:
                    break
        
        # Create binned versions of continuous variables (for any numeric column with enough variation)
        binning_count = 0
        for col in numeric_cols:
            if (df[col].nunique() > 10 and  # Enough unique values
                df[col].std() > 0 and       # Has variation
                binning_count < 3):         # Limit number of binned features
                
                try:
                    binned_col = f"{col}_binned"
                    df[binned_col] = pd.qcut(df[col], q=5, labels=['Low', 'Low-Med', 'Medium', 'Med-High', 'High'], duplicates='drop')
                    self.engineered_columns.append(binned_col)
                    
                    self.transformations_applied.append({
                        "type": "binning",
                        "column": col,
                        "new_column": binned_col,
                        "bins": 5
                    })
                    binning_count += 1
                except:
                    # Skip if binning fails (e.g., too few unique values after removing duplicates)
                    continue
        
        return df
    
    def _enhance_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhance categorical features - works with any categorical data"""
        
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Only process categorical columns that have reasonable cardinality
        freq_encoding_count = 0
        for col in categorical_cols:
            unique_count = df[col].nunique()
            if (unique_count > 2 and           # More than binary
                unique_count <= 50 and        # Not too many categories
                freq_encoding_count < 3):     # Limit number of frequency encodings
                
                try:
                    # Create frequency encoding
                    freq_col = f"{col}_frequency"
                    value_counts = df[col].value_counts()
                    df[freq_col] = df[col].map(value_counts)
                    self.engineered_columns.append(freq_col)
                    
                    self.transformations_applied.append({
                        "type": "frequency_encoding",
                        "column": col,
                        "new_column": freq_col
                    })
                    freq_encoding_count += 1
                except:
                    # Skip if encoding fails
                    continue
        
        return df
    
    def _create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create time-based features from ANY datetime columns"""
        
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        for col in datetime_cols:
            try:
                # Use original column name for feature naming
                base_name = col.replace('_date', '').replace('_time', '').replace('date_', '').replace('time_', '')
                if not base_name:  # If column name becomes empty, use 'time'
                    base_name = 'time'
                
                # Extract common time features
                year_col = f"{base_name}_year"
                month_col = f"{base_name}_month"
                day_col = f"{base_name}_day"
                weekday_col = f"{base_name}_weekday"
                
                df[year_col] = df[col].dt.year
                df[month_col] = df[col].dt.month
                df[day_col] = df[col].dt.day
                df[weekday_col] = df[col].dt.dayofweek
                
                new_cols = [year_col, month_col, day_col, weekday_col]
                self.engineered_columns.extend(new_cols)
                
                self.transformations_applied.append({
                    "type": "datetime_features",
                    "column": col,
                    "new_columns": new_cols
                })
                
                # Create is_weekend feature
                weekend_col = f"{base_name}_is_weekend"
                df[weekend_col] = (df[col].dt.dayofweek >= 5).astype(int)
                self.engineered_columns.append(weekend_col)
                
                self.transformations_applied.append({
                    "type": "weekend_indicator",
                    "column": col,
                    "new_column": weekend_col
                })
            except:
                # Skip if datetime feature extraction fails
                continue
        
        return df
    
    def _generate_transformation_report(self, original_df: pd.DataFrame, transformed_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate a comprehensive transformation report"""
        
        original_missing = original_df.isnull().sum().sum()
        transformed_missing = transformed_df.isnull().sum().sum()
        
        report = {
            "summary": {
                "original_shape": original_df.shape,
                "transformed_shape": transformed_df.shape,
                "original_missing_values": original_missing,
                "transformed_missing_values": transformed_missing,
                "missing_reduction": original_missing - transformed_missing,
                "new_features_created": len(self.engineered_columns)
            },
            "transformations": self.transformations_applied,
            "new_columns": self.engineered_columns,
            "dropped_columns": [t["column"] for t in self.transformations_applied if t["type"] == "drop_column"]
        }
        
        return report

def apply_feature_engineering(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Convenience function to apply automatic feature engineering
    
    Args:
        df: Input dataframe
        
    Returns:
        Tuple of (transformed_dataframe, transformation_report)
    """
    engineer = AutoFeatureEngineer()
    return engineer.fit_transform(df)