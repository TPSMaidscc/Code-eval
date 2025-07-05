# 🤖 Bot Repetitions Analysis API

A FastAPI-based REST API for analyzing chatbot message repetitions across different departments. This system fetches conversation data from Tableau, analyzes bot message repetitions, and uploads results to Google Sheets.

**🚀 Ready for Production Deployment** - See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for free hosting options.

## 📋 Overview

This API provides endpoints to:
- 🔍 Fetch conversation data from Tableau for the previous day
- 📊 Analyze bot message repetitions by department
- 📤 Upload results to Google Sheets automatically
- 🔄 Return structured JSON responses for integration

## 🏗️ Project Structure

```
bot-repetitions-api/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── config.py                 # Configuration settings
│   ├── models.py                 # Pydantic models
│   ├── api/                      # API routes
│   │   ├── __init__.py
│   │   └── routes.py             # API endpoint definitions
│   └── services/                 # Business logic services
│       ├── __init__.py
│       ├── tableau_service.py    # Tableau data fetching
│       ├── sheets_service.py     # Google Sheets integration
│       └── analysis_service.py   # Repetitions analysis logic
├── config/                       # Configuration files
│   ├── cred.json                 # Google OAuth credentials
│   └── service-account-key.json  # Service account key (optional)
├── data/                         # Data storage
│   ├── temp/                     # Temporary processing files
│   ├── output/                   # Analysis results
│   └── archive/                  # Historical data
├── logs/                         # Application logs
├── scripts/                      # Utility scripts
│   ├── start_server.py           # Server startup script
│   └── test_api.py               # API testing script
├── utils/                        # Utility modules
│   └── setup.py                  # Project setup utilities
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd bot-repetitions-api

# Install dependencies
pip install -r requirements.txt

# Run setup (creates directories and sample configs)
python utils/setup.py
```

### 2. Configuration

#### Option A: Google OAuth (Recommended for development)
1. Get Google OAuth credentials from [Google Cloud Console](https://console.cloud.google.com/)
2. Save as `config/cred.json`
3. Enable Google Sheets API and Google Drive API

#### Option B: Service Account (Recommended for production)
1. Create a Service Account in Google Cloud Console
2. Download the JSON key as `config/service-account-key.json`
3. Share your Google Sheets with the service account email

### 3. Start the Server

```bash
# Using the startup script (recommended)
python scripts/start_server.py

# Or directly with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the API

```bash
# Run the test suite
python scripts/test_api.py

# Or test manually
curl http://localhost:8000/health
```

## 🔗 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information and available endpoints |
| GET | `/health` | Health check |
| GET | `/departments` | List available departments |
| POST | `/analyze/{department}` | Analyze specific department |
| POST | `/analyze/all` | Analyze all departments |

### Department-Specific Endpoints

| Method | Endpoint | Department | Description |
|--------|----------|------------|-------------|
| POST | `/analyze/applicants` | Applicants | Analyze applicant conversations |
| POST | `/analyze/doctors` | Doctors | Analyze doctor consultation conversations |
| POST | `/analyze/mv_resolvers` | MV Resolvers | Analyze MV resolver conversations |
| POST | `/analyze/cc_sales` | CC Sales | Analyze CC sales conversations |

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📊 Usage Examples

### Python Client

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Analyze single department
response = requests.post("http://localhost:8000/analyze/applicants")
result = response.json()
print(f"Repetition rate: {result['repetition_percentage']}%")

# Analyze all departments
response = requests.post("http://localhost:8000/analyze/all")
results = response.json()
for dept_result in results['results']:
    print(f"{dept_result['department']}: {dept_result['repetition_percentage']}%")
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Analyze applicants (without Google Sheets upload)
curl -X POST "http://localhost:8000/analyze/applicants?upload_to_sheets=false"

# Analyze all departments
curl -X POST "http://localhost:8000/analyze/all"

# Get departments list
curl http://localhost:8000/departments
```

### JavaScript/Node.js

```javascript
// Analyze single department
const response = await fetch('http://localhost:8000/analyze/doctors', {
  method: 'POST'
});
const result = await response.json();
console.log(`Repetition rate: ${result.repetition_percentage}%`);
```

## 📈 Response Format

### Analysis Result

```json
{
  "department": "applicants",
  "analysis_date": "2025-07-03",
  "total_conversations": 399,
  "conversations_with_repetitions": 25,
  "repetition_percentage": 6.27,
  "repetitions": [
    {
      "conversation_id": "conv_123",
      "message_id": "msg_456",
      "message": "Hello! How can I help you today?",
      "repetition_count": 3,
      "skill": null
    }
  ],
  "summary": {
    "conversation_id": "SUMMARY",
    "message_id": "",
    "message": "TOTAL REPETITIONS",
    "repetition_count": "",
    "percentage_with_repetitions": "6.27%",
    "total_chats": 399,
    "chats_with_repetitions": 25
  }
}
```

## 🏢 Department Configuration

| Department | Tableau View | Skill Filter | Google Sheet ID |
|------------|--------------|--------------|-----------------|
| Applicants | Applicants | FILIPINA_OUTSIDE | 1VLDf6u2JhGqlWO4mYu02ZgJa8Zyc43tmoSj7-7syk2Y |
| Doctors | Doctors | GPT_Doctors | 1EJe_H3p47pcZ06Admn2OlI2pBZ0OhHhSTMsGx95mfm4 |
| MV Resolvers | Applicants | gpt_mv_resolvers | 15uMZ4YG7YXxFWPHia8ZnDmIk1WFFzl4xWoyaK3rONts |
| CC Sales | Sales CC | None (all bot messages) | 16qKSg_Imvgyh3Mk0f4god73hPsj6ORELSUNaMEgFSGU |

## 🔧 Configuration

### Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development

# Google Credentials
GOOGLE_CREDENTIALS_FILE=config/cred.json
GOOGLE_SERVICE_ACCOUNT_FILE=config/service-account-key.json

# Debugging
DEBUG=true
```

### Tableau Configuration

Update `app/config.py` with your Tableau server details:

```python
TABLEAU_CONFIG = {
    "server_url": "https://your-tableau-server.com",
    "api_version": "3.16",
    "token_name": "your-token-name",
    "token_value": "your-token-value",
    "site_content_url": "your-site",
    "workbook_name": "Your Workbook Name"
}
```

## 🚨 Troubleshooting

### Common Issues

**❌ "Cannot connect to API"**
- Ensure the server is running: `python scripts/start_server.py`
- Check if port 8000 is available

**❌ "Permission denied" for Google Sheets**
- Verify Google Sheets are shared with your account/service account
- Check OAuth scopes include Sheets and Drive permissions

**❌ "Failed to fetch data from Tableau"**
- Verify Tableau credentials in `app/config.py`
- Check network connectivity to Tableau server
- Ensure Personal Access Token is valid

**❌ "Module not found" errors**
- Install dependencies: `pip install -r requirements.txt`
- Ensure you're in the project root directory

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export DEBUG=true
python scripts/start_server.py
```

## 📊 Performance

- **Single Department Analysis**: ~30-60 seconds
- **All Departments (Batch)**: ~3-5 minutes
- **Concurrent Requests**: Supported (each request is independent)
- **Data Volume**: Handles 1000+ conversations per department

## 🐳 Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔄 Scheduling

For automated daily analysis:

```bash
# Cron job (daily at 9 AM)
0 9 * * * curl -X POST "http://localhost:8000/analyze/all"

# Or use a scheduler service to call the API
```

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure all endpoints work with the test script

## 📝 License

This project is for internal use by the Bot Analysis Team.

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Run the test script: `python scripts/test_api.py`
3. Check logs in the `logs/` directory
4. Contact the development team

---

**🎉 Happy Analyzing!** The API provides a robust, scalable solution for analyzing bot repetitions across multiple departments with easy integration into existing systems.
