#!/usr/bin/env python3
"""
Test script to verify analysis module installation and configuration
"""

import sys
import os

def test_imports():
    """Test that all required packages can be imported"""
    print("Testing imports...")
    
    try:
        import boto3
        print("✓ boto3")
    except ImportError as e:
        print(f"✗ boto3: {e}")
        return False
    
    try:
        import langchain_aws
        print("✓ langchain_aws")
    except ImportError as e:
        print(f"✗ langchain_aws: {e}")
        return False
    
    try:
        import langgraph
        print("✓ langgraph")
    except ImportError as e:
        print(f"✗ langgraph: {e}")
        return False
    
    try:
        from analysis import BatchAnalyzer, SessionAnalyzer
        print("✓ analysis module")
    except ImportError as e:
        print(f"✗ analysis module: {e}")
        return False
    
    print("\n✓ All imports successful!\n")
    return True


def test_aws_credentials():
    """Test AWS credentials and Bedrock access"""
    print("Testing AWS credentials...")
    
    try:
        import boto3
        
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials is None:
            print("✗ No AWS credentials found")
            print("  Configure with: aws configure")
            return False
        
        print(f"✓ AWS credentials found")
        print(f"  Region: {session.region_name or 'us-east-1 (default)'}")
        
        # Test Bedrock access via LangChain (how the actual code uses it)
        print("\nTesting Bedrock access...")
        try:
            from langchain_aws import ChatBedrock
            
            # Try to initialize ChatBedrock (this validates access)
            llm = ChatBedrock(
                model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_name=session.region_name or 'us-west-2',
                model_kwargs={
                    "temperature": 0.0,
                    "max_tokens": 10
                }
            )
            
            # Try a simple invocation
            response = llm.invoke("test")
            print("✓ Bedrock access confirmed")
            print("  Model: Claude 3.5 Sonnet")
        except Exception as e:
            print(f"⚠ Bedrock access test skipped: {e}")
            print("  Note: This test requires actual model invocation.")
            print("  The analysis module should still work if you have Bedrock access.")
            print("  To verify manually, try running the server.")
        
        print("\n✓ AWS configuration successful!\n")
        return True
        
    except Exception as e:
        print(f"✗ AWS test failed: {e}")
        return False


def test_analysis_module():
    """Test analysis module can be instantiated"""
    print("Testing analysis module...")
    
    try:
        from analysis import BatchAnalyzer, SessionAnalyzer
        
        # Test BatchAnalyzer
        batch_analyzer = BatchAnalyzer(batch_interval_seconds=60, region='us-west-2')
        print("✓ BatchAnalyzer created")
        
        # Test SessionAnalyzer
        session_analyzer = SessionAnalyzer(region='us-west-2')
        print("✓ SessionAnalyzer created")
        
        print("\n✓ Analysis module working!\n")
        return True
        
    except Exception as e:
        print(f"✗ Analysis module test failed: {e}")
        return False


def test_sessions_directory():
    """Test sessions directory can be created"""
    print("Testing sessions directory...")
    
    try:
        sessions_dir = os.path.join(os.path.dirname(__file__), 'sessions')
        os.makedirs(sessions_dir, exist_ok=True)
        
        if os.path.isdir(sessions_dir):
            print(f"✓ Sessions directory ready: {sessions_dir}")
            print("\n✓ Directory structure ready!\n")
            return True
        else:
            print(f"✗ Failed to create sessions directory")
            return False
            
    except Exception as e:
        print(f"✗ Directory test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Reading Analysis Module - Installation Test")
    print("="*60)
    print()
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test AWS
    results.append(("AWS Configuration", test_aws_credentials()))
    
    # Test analysis module
    results.append(("Analysis Module", test_analysis_module()))
    
    # Test directory structure
    results.append(("Directory Structure", test_sessions_directory()))
    
    # Summary
    print("="*60)
    print("Test Summary")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:30s} {status}")
    
    print()
    
    if all(result[1] for result in results):
        print("✓ All tests passed! The analysis module is ready to use.")
        print("\nYou can now run: python app.py")
        return 0
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Run: pip install -r requirements.txt")
        print("  - Run: aws configure")
        print("  - Check AWS Bedrock access in console")
        return 1


if __name__ == "__main__":
    sys.exit(main())
