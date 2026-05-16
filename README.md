# AutoDash-LLM (Universal)

An open-source AI system that automatically generates dashboards from **ANY** CSV/Excel file structure.
Uses **Mistral-7B via OpenRouter API** for reliable LLM inference with enhanced error handling and automatic feature engineering.

## 🌟 Universal Data Support

**AutoDash works with ANY data structure - no assumptions about column names or business context!**

✅ **Scientific data** (temperature, pressure, pH levels)  
✅ **E-commerce data** (transactions, customers, orders)  
✅ **IoT sensor data** (battery, signals, device readings)  
✅ **Financial data** (stocks, prices, portfolios)  
✅ **Academic data** (grades, attendance, performance)  
✅ **Any other data** (your unique dataset structure)

## 🚀 Key Features

- **Universal Data Analysis**: Works with any column names, any data types, any business domain
- **Smart Data Analysis**: Automatic data type detection, correlation analysis, and quality assessment
- **Robust AI Generation**: Multiple retry mechanisms and fallback strategies to prevent failures
- **Automatic Feature Engineering**: Intelligently handles missing values and creates new features
- **Enhanced Visualizations**: Support for bar, line, scatter, histogram, and box plots with trend lines
- **Intelligent KPIs**: Context-aware KPI generation based on your specific data characteristics
- **Error Recovery**: Multiple fallback mechanisms ensure dashboard generation never fails completely
- **Performance Optimized**: Handles large datasets with sampling and data preprocessing

## 🛠️ Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variable:**
   ```bash
   # Get your API key from https://openrouter.ai/
   export OPENROUTER_API_KEY=your_api_key_here
   ```
   Or create a `.env` file:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

## 🧠 How It Works

1. **Universal Data Profiling**: Analyzes ANY dataset structure, types, and relationships
2. **AI Planning**: Uses LangGraph workflow to generate KPIs and chart recommendations
3. **Automatic Feature Engineering**: Fixes missing values and creates new features
4. **Validation**: Multiple validation layers ensure generated content works with your data
5. **Fallback Systems**: Smart fallbacks activate if AI generation fails
6. **Rendering**: Creates interactive Plotly dashboards with enhanced error handling

## 📊 Works With Any Data Types

- **Numerical columns** → KPIs, trends, correlations, distributions
- **Categorical columns** → Breakdowns, frequency analysis, comparisons  
- **DateTime columns** → Time series, seasonal patterns, temporal analysis
- **Text columns** → Frequency analysis, categorization
- **ID columns** → Automatically detected and handled appropriately
- **Mixed data types** → Comprehensive multi-dimensional analysis

## 🔧 Automatic Feature Engineering

### Missing Value Handling:
- **Numeric columns**: Smart imputation (mean/median) based on data distribution
- **Categorical columns**: Mode imputation or explicit "Missing" category
- **DateTime columns**: Forward-fill or median date imputation
- **Missing indicators**: Binary flags for columns with >10% missing data
- **Auto-cleanup**: Removes columns with >90% missing values

### Feature Creation:
- **Ratio features**: Creates meaningful ratios between numeric columns
- **Binned features**: Converts continuous variables into categorical bins
- **Frequency encoding**: Encodes categorical variables by their frequency
- **Time features**: Extracts year, month, day, weekday from datetime columns
- **Weekend indicators**: Binary flags for weekend dates

## 📈 Example Use Cases

**Any domain, any structure:**
- **Research Data**: Experiment results, measurements, observations
- **Business Data**: Sales, customers, operations, performance
- **Sensor Data**: IoT readings, monitoring, telemetry
- **Financial Data**: Transactions, portfolios, market data
- **Academic Data**: Grades, attendance, assessments
- **Survey Data**: Responses, demographics, feedback
- **Log Data**: System logs, user activity, events
- **Your Data**: Whatever structure you have!

## 🎯 No Configuration Required

Just upload your file - AutoDash automatically:
- Detects your data types and structure
- Handles missing values intelligently  
- Creates appropriate visualizations
- Generates meaningful KPIs
- Adapts to your specific domain

**No matter what your data looks like, AutoDash will create a beautiful, insightful dashboard!**