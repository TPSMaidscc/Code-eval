#!/usr/bin/env python3
"""
API testing script for the Bot Repetitions Analysis API
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# API Configuration
API_BASE_URL = "http://localhost:8000"

class APITester:
    """Test client for the Repetitions Analysis API."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def test_connection(self) -> bool:
        """Test if API is accessible."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def test_health(self) -> Dict[str, Any]:
        """Test health endpoint."""
        print("🏥 Testing health endpoint...")
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        result = response.json()
        print(f"   Status: {result['status']}")
        return result
    
    def test_root(self) -> Dict[str, Any]:
        """Test root endpoint."""
        print("🏠 Testing root endpoint...")
        response = self.session.get(f"{self.base_url}/")
        response.raise_for_status()
        result = response.json()
        print(f"   API: {result['message']}")
        print(f"   Version: {result['version']}")
        print(f"   Departments: {result['departments']}")
        return result
    
    def test_departments(self) -> Dict[str, Any]:
        """Test departments endpoint."""
        print("📋 Testing departments endpoint...")
        response = self.session.get(f"{self.base_url}/departments")
        response.raise_for_status()
        result = response.json()
        print(f"   Available departments: {len(result['departments'])}")
        for dept in result['departments']:
            print(f"   • {dept}")
        return result
    
    def test_single_analysis(self, department: str, upload_to_sheets: bool = False) -> Dict[str, Any]:
        """Test single department analysis."""
        print(f"🔬 Testing analysis for {department}...")
        
        url = f"{self.base_url}/analyze/{department}"
        params = {"upload_to_sheets": upload_to_sheets}
        
        start_time = time.time()
        response = self.session.post(url, params=params, timeout=300)  # 5 minute timeout
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Analysis completed in {duration:.2f} seconds")
            print(f"   Total conversations: {result['total_conversations']}")
            print(f"   Conversations with repetitions: {result['conversations_with_repetitions']}")
            print(f"   Repetition percentage: {result['repetition_percentage']}%")
            print(f"   Repetitions found: {len(result['repetitions'])}")
            return result
        else:
            print(f"   ❌ Analysis failed: {response.status_code}")
            print(f"   Error: {response.text}")
            response.raise_for_status()
    
    def test_batch_analysis(self, upload_to_sheets: bool = False) -> Dict[str, Any]:
        """Test batch analysis for all departments."""
        print("🔬 Testing batch analysis for all departments...")
        
        url = f"{self.base_url}/analyze/all"
        params = {"upload_to_sheets": upload_to_sheets}
        
        start_time = time.time()
        response = self.session.post(url, params=params, timeout=600)  # 10 minute timeout
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Batch analysis completed in {duration:.2f} seconds")
            print(f"   Total departments: {result['total_departments']}")
            print(f"   Successful analyses: {result['successful_analyses']}")
            print(f"   Failed analyses: {result['failed_analyses']}")
            
            if result['results']:
                print(f"   Summary statistics:")
                stats = result['summary_statistics']
                print(f"   • Total conversations: {stats['total_conversations']}")
                print(f"   • Overall repetition rate: {stats['overall_percentage']}%")
            
            return result
        else:
            print(f"   ❌ Batch analysis failed: {response.status_code}")
            print(f"   Error: {response.text}")
            response.raise_for_status()

def main():
    """Main testing function."""
    print("🧪 Bot Repetitions Analysis API - Test Suite")
    print("=" * 60)
    
    tester = APITester()
    
    # Test connection
    print("🔌 Testing API connection...")
    if not tester.test_connection():
        print("❌ Cannot connect to API. Make sure the server is running:")
        print("   python scripts/start_server.py")
        sys.exit(1)
    print("✅ API connection successful")
    
    try:
        # Basic endpoint tests
        print("\n" + "="*40)
        print("BASIC ENDPOINT TESTS")
        print("="*40)
        
        tester.test_health()
        tester.test_root()
        tester.test_departments()
        
        # Single department analysis test
        print("\n" + "="*40)
        print("SINGLE DEPARTMENT ANALYSIS TEST")
        print("="*40)
        
        # Test with a single department (no sheets upload for testing)
        test_department = "applicants"
        tester.test_single_analysis(test_department, upload_to_sheets=False)
        
        # Batch analysis test (optional - takes longer)
        print("\n" + "="*40)
        print("BATCH ANALYSIS TEST (Optional)")
        print("="*40)
        
        user_input = input("Run batch analysis test? This may take several minutes. (y/N): ")
        if user_input.lower() in ['y', 'yes']:
            tester.test_batch_analysis(upload_to_sheets=False)
        else:
            print("⏭️  Skipping batch analysis test")
        
        print("\n🎉 All tests completed successfully!")
        print("\n📊 API Performance Summary:")
        print("   • Basic endpoints: Fast (< 1 second)")
        print("   • Single department analysis: ~30-60 seconds")
        print("   • Batch analysis: ~3-5 minutes")
        
        print("\n🔗 API Endpoints Available:")
        print(f"   • Interactive Docs: {API_BASE_URL}/docs")
        print(f"   • ReDoc: {API_BASE_URL}/redoc")
        print(f"   • Health Check: {API_BASE_URL}/health")
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ API Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
