# 🚀 Bot Analysis API - Clean Deployment Guide

## 📁 Essential Files for Deployment

### Core Application Files
```
app/
├── __init__.py
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration with summary spreadsheet IDs
├── models.py              # Pydantic models
├── api/
│   ├── __init__.py
│   ├── routes.py          # Main API routes with combined analysis
│   └── delays_routes.py   # Delays analysis routes
└── services/
    ├── __init__.py
    ├── analysis_service.py    # Repetitions analysis
    ├── delays_service.py      # Delays analysis
    ├── sheets_service.py      # Google Sheets with summary functionality
    └── tableau_service.py     # Tableau data fetching

data/
├── temp/                  # Temporary processing files
├── output/               # Analysis results
└── archive/              # Archived data

requirements.txt          # Python dependencies
Dockerfile               # Container configuration
start.py                # Application startup script
```

### Documentation Files
```
README.md               # Main documentation
API_DOCUMENTATION.md    # API endpoints documentation
DEPLOYMENT.md          # Deployment instructions
DEPLOYMENT_SUMMARY.md  # Environment variables and configuration
```

## 🔧 New Features Added

### Summary Sheet Functionality
- **Combined Analysis**: `/analyze/combined/{department}` now creates summary sheets
- **Sheet Format**: Date-based sheet names (YYYY-MM-DD format)
- **Metrics Tracked**:
  - Total Number of Chats
  - Repetition % (formatted as "count (percentage%)")
  - Avg Delay - Initial msg
  - Avg Delay - non-initial msg

### Summary Spreadsheet IDs
```python
SUMMARY_SPREADSHEET_IDS = {
    "applicants": "1E5wHZKSDXQZlHIb3sV4ZWqIxvboLduzUEU0eupK7tys",
    "doctors": "1STHimb0IJ077iuBtTOwsa-GD8jStjU3SiBW7yBWom-E", 
    "cc_sales": "1te1fbAXhURIUO0EzQ2Mrorv3a6GDtEVM_5np9TO775o",
    "mv_resolvers": "1XkVcHlkh8fEp7mmBD1Zkavdp2blBLwSABT1dE_sOf74"
}
```

## 🚀 Quick Deployment Steps

1. **Upload Essential Files**: Copy all files listed above to your deployment environment
2. **Set Environment Variables**: Use the configuration from DEPLOYMENT_SUMMARY.md
3. **Install Dependencies**: `pip install -r requirements.txt`
4. **Run Application**: `python start.py` or use Docker

## 🔑 Key Environment Variables

```bash
# Google Service Account (JSON format)
GOOGLE_CREDENTIALS={"type":"service_account",...}

# Tableau Configuration
TABLEAU_TOKEN_NAME=your_token_name
TABLEAU_TOKEN_VALUE=your_token_value
TABLEAU_SITE_CONTENT_URL=your_site_url

# Spreadsheet IDs for repetitions analysis
APPLICANTS_SPREADSHEET_ID=your_applicants_id
DOCTORS_SPREADSHEET_ID=your_doctors_id
MV_RESOLVERS_SPREADSHEET_ID=your_mv_id
CC_SALES_SPREADSHEET_ID=your_cc_sales_id
```

## 📊 API Usage

### Combined Analysis with Summary Sheet
```bash
curl -X POST "http://localhost:8000/analyze/combined/applicants?upload_to_sheets=true"
```

This will:
1. Run both repetitions and delays analysis
2. Create a summary sheet with date-based name (e.g., "2025-07-06")
3. Populate metrics in the specified format

## 🗂️ Files Removed for Clean Deployment

- Test files (`test_*.py`)
- Cache directories (`__pycache__`)
- Temporary data files
- Development logs
- Unused configuration directories
- Extra documentation files

## ✅ Deployment Checklist

- [ ] All essential files copied
- [ ] Environment variables configured
- [ ] Dependencies installed
- [ ] Google Service Account credentials set
- [ ] Tableau credentials configured
- [ ] Summary spreadsheet IDs verified
- [ ] Application starts successfully
- [ ] Combined analysis endpoint tested
