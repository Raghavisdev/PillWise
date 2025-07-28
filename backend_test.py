#!/usr/bin/env python3
"""
PillWise Backend API Testing Suite
Tests all backend endpoints and functionality
"""

import requests
import json
import base64
import uuid
import time
from datetime import datetime
import os
from pathlib import Path

# Get backend URL from frontend .env file
def get_backend_url():
    frontend_env_path = Path("/app/frontend/.env")
    if frontend_env_path.exists():
        with open(frontend_env_path, 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    return "http://localhost:8001"

BASE_URL = get_backend_url()
API_URL = f"{BASE_URL}/api"

print(f"Testing PillWise Backend API at: {API_URL}")
print("=" * 60)

# Test session ID for consistency
TEST_SESSION_ID = str(uuid.uuid4())

def create_test_image_base64():
    """Create a valid test image in base64 format"""
    # Create a simple but valid JPEG image (small white square with some text-like pattern)
    # This is a minimal valid JPEG that should be accepted by Gemini Vision API
    jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00 \x00 \x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
    return base64.b64encode(jpeg_data).decode('utf-8')

def test_health_check():
    """Test GET /api/ endpoint"""
    print("1. Testing Health Check Endpoint...")
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if "PillWise API" in data.get("message", ""):
                print("   ✅ Health check PASSED")
                return True
            else:
                print("   ❌ Health check FAILED - Unexpected message")
                return False
        else:
            print("   ❌ Health check FAILED - Wrong status code")
            return False
            
    except Exception as e:
        print(f"   ❌ Health check FAILED - Exception: {str(e)}")
        return False

def test_pill_analysis():
    """Test POST /api/analyze-pill endpoint"""
    print("\n2. Testing Pill Analysis Endpoint...")
    try:
        test_image = create_test_image_base64()
        payload = {
            "image_base64": test_image,
            "session_id": TEST_SESSION_ID
        }
        
        print("   Sending pill analysis request...")
        response = requests.post(f"{API_URL}/analyze-pill", 
                               json=payload, 
                               timeout=30)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response keys: {list(data.keys())}")
            
            # Check required fields
            required_fields = ["id", "session_id", "pill_name", "pill_description", 
                             "uses", "side_effects", "dosage", "ayurvedic_alternatives", 
                             "safety_info", "confidence"]
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
                return False
            
            # Verify session ID matches
            if data["session_id"] != TEST_SESSION_ID:
                print(f"   ❌ Session ID mismatch: expected {TEST_SESSION_ID}, got {data['session_id']}")
                return False
            
            print(f"   Pill Name: {data['pill_name']}")
            print(f"   Confidence: {data['confidence']}")
            print("   ✅ Pill analysis PASSED")
            return True
            
        else:
            print(f"   ❌ Pill analysis FAILED - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Pill analysis FAILED - Exception: {str(e)}")
        return False

def test_analysis_history():
    """Test GET /api/analysis-history/{session_id} endpoint"""
    print("\n3. Testing Analysis History Endpoint...")
    try:
        # Wait a moment for the previous analysis to be stored
        time.sleep(2)
        
        response = requests.get(f"{API_URL}/analysis-history/{TEST_SESSION_ID}", timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Number of analyses found: {len(data)}")
            
            if len(data) > 0:
                # Check the structure of the first analysis
                analysis = data[0]
                required_fields = ["id", "session_id", "image_base64", "pill_name", 
                                 "timestamp"]
                
                missing_fields = [field for field in required_fields if field not in analysis]
                if missing_fields:
                    print(f"   ❌ Missing fields in history: {missing_fields}")
                    return False
                
                if analysis["session_id"] != TEST_SESSION_ID:
                    print(f"   ❌ Session ID mismatch in history")
                    return False
                
                print("   ✅ Analysis history PASSED")
                return True
            else:
                print("   ❌ Analysis history FAILED - No analyses found")
                return False
                
        else:
            print(f"   ❌ Analysis history FAILED - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Analysis history FAILED - Exception: {str(e)}")
        return False

def test_error_handling():
    """Test error handling with invalid requests"""
    print("\n4. Testing Error Handling...")
    
    # Test 1: Invalid base64 image
    print("   4.1 Testing invalid base64 image...")
    try:
        payload = {
            "image_base64": "invalid_base64_data",
            "session_id": TEST_SESSION_ID
        }
        response = requests.post(f"{API_URL}/analyze-pill", json=payload, timeout=10)
        
        if response.status_code >= 400:
            print("   ✅ Invalid base64 handling PASSED")
            error_test_1 = True
        else:
            print("   ❌ Invalid base64 handling FAILED - Should return error")
            error_test_1 = False
    except Exception as e:
        print(f"   ❌ Invalid base64 test FAILED - Exception: {str(e)}")
        error_test_1 = False
    
    # Test 2: Missing required fields
    print("   4.2 Testing missing required fields...")
    try:
        payload = {"session_id": TEST_SESSION_ID}  # Missing image_base64
        response = requests.post(f"{API_URL}/analyze-pill", json=payload, timeout=10)
        
        if response.status_code >= 400:
            print("   ✅ Missing fields handling PASSED")
            error_test_2 = True
        else:
            print("   ❌ Missing fields handling FAILED - Should return error")
            error_test_2 = False
    except Exception as e:
        print(f"   ❌ Missing fields test FAILED - Exception: {str(e)}")
        error_test_2 = False
    
    # Test 3: Invalid session ID for history
    print("   4.3 Testing invalid session ID for history...")
    try:
        response = requests.get(f"{API_URL}/analysis-history/invalid-session-id", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if len(data) == 0:
                print("   ✅ Invalid session ID handling PASSED")
                error_test_3 = True
            else:
                print("   ❌ Invalid session ID handling FAILED - Should return empty list")
                error_test_3 = False
        else:
            print("   ❌ Invalid session ID test FAILED - Unexpected status code")
            error_test_3 = False
    except Exception as e:
        print(f"   ❌ Invalid session ID test FAILED - Exception: {str(e)}")
        error_test_3 = False
    
    return error_test_1 and error_test_2 and error_test_3

def test_database_functionality():
    """Test database storage and retrieval"""
    print("\n5. Testing Database Functionality...")
    
    # Create a unique session for this test
    db_test_session = str(uuid.uuid4())
    
    try:
        # Step 1: Perform multiple analyses
        print("   5.1 Storing multiple analyses...")
        test_image = create_test_image_base64()
        
        analyses_created = []
        for i in range(3):
            payload = {
                "image_base64": test_image,
                "session_id": db_test_session
            }
            response = requests.post(f"{API_URL}/analyze-pill", json=payload, timeout=30)
            
            if response.status_code == 200:
                analyses_created.append(response.json()["id"])
                time.sleep(1)  # Small delay between requests
            else:
                print(f"   ❌ Failed to create analysis {i+1}")
                return False
        
        print(f"   Created {len(analyses_created)} analyses")
        
        # Step 2: Retrieve and verify
        print("   5.2 Retrieving stored analyses...")
        time.sleep(2)  # Wait for database consistency
        
        response = requests.get(f"{API_URL}/analysis-history/{db_test_session}", timeout=10)
        
        if response.status_code == 200:
            stored_analyses = response.json()
            
            if len(stored_analyses) == len(analyses_created):
                print(f"   ✅ Database storage PASSED - {len(stored_analyses)} analyses stored and retrieved")
                
                # Verify UUIDs are properly formatted
                for analysis in stored_analyses:
                    try:
                        uuid.UUID(analysis["id"])
                    except ValueError:
                        print(f"   ❌ Invalid UUID format: {analysis['id']}")
                        return False
                
                return True
            else:
                print(f"   ❌ Database storage FAILED - Expected {len(analyses_created)}, got {len(stored_analyses)}")
                return False
        else:
            print(f"   ❌ Database retrieval FAILED - Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Database functionality FAILED - Exception: {str(e)}")
        return False

def run_all_tests():
    """Run all tests and provide summary"""
    print("Starting PillWise Backend API Tests")
    print("=" * 60)
    
    test_results = {
        "Health Check": test_health_check(),
        "Pill Analysis": test_pill_analysis(),
        "Analysis History": test_analysis_history(),
        "Error Handling": test_error_handling(),
        "Database Functionality": test_database_functionality()
    }
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED! Backend API is working correctly.")
        return True
    else:
        print("⚠️  Some tests FAILED. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)