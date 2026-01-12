import requests
import sys
import json
from datetime import datetime
import pandas as pd
import os

class WorkoutStreakAPITester:
    def __init__(self, base_url="https://streakfit.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    Details: {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, cookies=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, cookies=cookies)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers, cookies=cookies)
            
            success = response.status_code == expected_status
            details = f"Status: {response.status_code}, Expected: {expected_status}"
            
            if not success:
                try:
                    error_detail = response.json().get('detail', 'No error detail')
                    details += f", Error: {error_detail}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test(name, success, details)
            return success, response

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, None

    def test_user_registration(self):
        """Test user registration with valid data"""
        test_user = f"TestUser_{datetime.now().strftime('%H%M%S')}"
        test_pin = "1234"
        
        success, response = self.run_test(
            "User Registration - Valid Data",
            "POST",
            "register",
            200,
            data={"name": test_user, "pin": test_pin}
        )
        
        if success:
            # Store user for later tests
            self.test_user = test_user
            self.test_pin = test_pin
            return True
        return False

    def test_duplicate_user_registration(self):
        """Test registration with duplicate user"""
        if not hasattr(self, 'test_user'):
            self.log_test("Duplicate User Registration", False, "No test user available")
            return False
            
        success, response = self.run_test(
            "User Registration - Duplicate User",
            "POST", 
            "register",
            400,
            data={"name": self.test_user, "pin": self.test_pin}
        )
        return success

    def test_invalid_pin_registration(self):
        """Test registration with invalid PIN"""
        test_cases = [
            ("123", "3 digits"),
            ("12345", "5 digits"), 
            ("abcd", "non-numeric"),
            ("", "empty PIN")
        ]
        
        all_passed = True
        for pin, description in test_cases:
            success, response = self.run_test(
                f"User Registration - Invalid PIN ({description})",
                "POST",
                "register", 
                400,
                data={"name": f"TestInvalid_{description.replace(' ', '_')}", "pin": pin}
            )
            if not success:
                all_passed = False
        
        return all_passed

    def test_user_login(self):
        """Test user login with valid credentials"""
        if not hasattr(self, 'test_user'):
            self.log_test("User Login - Valid Credentials", False, "No test user available")
            return False
            
        success, response = self.run_test(
            "User Login - Valid Credentials",
            "POST",
            "login",
            200,
            data={"name": self.test_user, "pin": self.test_pin}
        )
        
        if success:
            # Store cookies for authenticated requests
            self.auth_cookies = response.cookies
            return True
        return False

    def test_invalid_login(self):
        """Test login with invalid credentials"""
        test_cases = [
            ({"name": "NonExistentUser", "pin": "1234"}, "Non-existent user"),
            ({"name": self.test_user if hasattr(self, 'test_user') else "TestUser", "pin": "9999"}, "Wrong PIN")
        ]
        
        all_passed = True
        for credentials, description in test_cases:
            success, response = self.run_test(
                f"User Login - Invalid ({description})",
                "POST",
                "login",
                401,
                data=credentials
            )
            if not success:
                all_passed = False
        
        return all_passed

    def test_dashboard_access(self):
        """Test dashboard access with authentication"""
        if not hasattr(self, 'auth_cookies'):
            self.log_test("Dashboard Access - Authenticated", False, "No auth cookies available")
            return False
            
        success, response = self.run_test(
            "Dashboard Access - Authenticated",
            "GET",
            "dashboard",
            200,
            cookies=self.auth_cookies
        )
        
        if success:
            try:
                data = response.json()
                # Verify dashboard data structure
                required_fields = ['name', 'today_date', 'current_streak', 'total_workout_days', 'today_marked', 'workout_history']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Dashboard Data Structure", False, f"Missing fields: {missing_fields}")
                    return False
                else:
                    self.log_test("Dashboard Data Structure", True, "All required fields present")
                    self.dashboard_data = data
                    return True
            except Exception as e:
                self.log_test("Dashboard Data Parsing", False, f"JSON parsing error: {str(e)}")
                return False
        return False

    def test_dashboard_unauthenticated(self):
        """Test dashboard access without authentication"""
        success, response = self.run_test(
            "Dashboard Access - Unauthenticated",
            "GET",
            "dashboard",
            401
        )
        return success

    def test_mark_workout(self):
        """Test marking workout for today"""
        if not hasattr(self, 'auth_cookies'):
            self.log_test("Mark Workout - First Time", False, "No auth cookies available")
            return False
            
        success, response = self.run_test(
            "Mark Workout - First Time",
            "POST",
            "mark-workout",
            200,
            cookies=self.auth_cookies
        )
        
        if success:
            try:
                data = response.json()
                if data.get('success'):
                    self.log_test("Mark Workout Response", True, f"Streak: {data.get('streak')}, Total: {data.get('total_days')}")
                    return True
                else:
                    self.log_test("Mark Workout Response", False, f"Success=False: {data.get('message')}")
                    return False
            except Exception as e:
                self.log_test("Mark Workout Response Parsing", False, f"JSON parsing error: {str(e)}")
                return False
        return False

    def test_mark_workout_duplicate(self):
        """Test marking workout twice in same day"""
        if not hasattr(self, 'auth_cookies'):
            self.log_test("Mark Workout - Duplicate", False, "No auth cookies available")
            return False
            
        success, response = self.run_test(
            "Mark Workout - Duplicate (Same Day)",
            "POST",
            "mark-workout",
            200,
            cookies=self.auth_cookies
        )
        
        if success:
            try:
                data = response.json()
                # Should return success=False with "already marked" message
                if not data.get('success') and 'already marked' in data.get('message', '').lower():
                    self.log_test("Duplicate Workout Prevention", True, "Correctly prevented duplicate marking")
                    return True
                else:
                    self.log_test("Duplicate Workout Prevention", False, f"Unexpected response: {data}")
                    return False
            except Exception as e:
                self.log_test("Duplicate Workout Response Parsing", False, f"JSON parsing error: {str(e)}")
                return False
        return False

    def test_logout(self):
        """Test logout functionality"""
        if not hasattr(self, 'auth_cookies'):
            self.log_test("Logout", False, "No auth cookies available")
            return False
            
        success, response = self.run_test(
            "Logout",
            "POST",
            "logout",
            200,
            cookies=self.auth_cookies
        )
        
        if success:
            # Test that dashboard is no longer accessible
            success2, response2 = self.run_test(
                "Dashboard After Logout",
                "GET",
                "dashboard",
                401,
                cookies=self.auth_cookies
            )
            return success2
        return False

    def verify_excel_file(self):
        """Verify Excel file exists and has correct structure"""
        excel_path = "/app/backend/workout_app_data.xlsx"
        
        try:
            if not os.path.exists(excel_path):
                self.log_test("Excel File Exists", False, f"File not found at {excel_path}")
                return False
            
            self.log_test("Excel File Exists", True, f"Found at {excel_path}")
            
            # Check sheets
            try:
                users_df = pd.read_excel(excel_path, sheet_name='users')
                workouts_df = pd.read_excel(excel_path, sheet_name='workouts')
                
                # Check users sheet structure
                expected_user_cols = ['user_id', 'name', 'pin', 'created_at']
                missing_user_cols = [col for col in expected_user_cols if col not in users_df.columns]
                
                if missing_user_cols:
                    self.log_test("Excel Users Sheet Structure", False, f"Missing columns: {missing_user_cols}")
                else:
                    self.log_test("Excel Users Sheet Structure", True, "All required columns present")
                
                # Check workouts sheet structure  
                expected_workout_cols = ['user_id', 'date', 'workout_done']
                missing_workout_cols = [col for col in expected_workout_cols if col not in workouts_df.columns]
                
                if missing_workout_cols:
                    self.log_test("Excel Workouts Sheet Structure", False, f"Missing columns: {missing_workout_cols}")
                else:
                    self.log_test("Excel Workouts Sheet Structure", True, "All required columns present")
                
                # Check if test user data exists
                if hasattr(self, 'test_user'):
                    user_exists = self.test_user in users_df['name'].values
                    self.log_test("Test User in Excel", user_exists, f"User '{self.test_user}' {'found' if user_exists else 'not found'}")
                
                return True
                
            except Exception as e:
                self.log_test("Excel File Reading", False, f"Error reading Excel: {str(e)}")
                return False
                
        except Exception as e:
            self.log_test("Excel File Verification", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Workout Streak Tracker Backend Tests")
        print(f"Testing API at: {self.api_url}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            self.test_user_registration,
            self.test_duplicate_user_registration, 
            self.test_invalid_pin_registration,
            self.test_user_login,
            self.test_invalid_login,
            self.test_dashboard_unauthenticated,
            self.test_dashboard_access,
            self.test_mark_workout,
            self.test_mark_workout_duplicate,
            self.test_logout,
            self.verify_excel_file
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_test(test.__name__, False, f"Test execution error: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    tester = WorkoutStreakAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'summary': {
                'total_tests': tester.tests_run,
                'passed_tests': tester.tests_passed,
                'success_rate': f"{(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%",
                'timestamp': datetime.now().isoformat()
            },
            'detailed_results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())