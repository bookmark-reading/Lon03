#!/usr/bin/env python3
"""
Query existing DynamoDB data
Shows what data is already in the tables
"""
import boto3
import json
import os
from dotenv import load_dotenv
from decimal import Decimal

# Load environment variables
load_dotenv()


class DecimalEncoder(json.JSONEncoder):
    """Helper to convert Decimal to int/float for JSON"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


def get_dynamodb_resource():
    """Get DynamoDB resource with credentials"""
    session_kwargs = {'region_name': 'us-west-2'}
    
    if os.getenv('AWS_ACCESS_KEY_ID'):
        session_kwargs['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID')
    if os.getenv('AWS_SECRET_ACCESS_KEY'):
        session_kwargs['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY')
    if os.getenv('AWS_SESSION_TOKEN'):
        session_kwargs['aws_session_token'] = os.getenv('AWS_SESSION_TOKEN')
    
    return boto3.resource('dynamodb', **session_kwargs)


def query_books():
    """Query all books"""
    print("\n" + "="*60)
    print("BOOKS TABLE")
    print("="*60 + "\n")
    
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table('books')
    
    response = table.scan()
    items = response.get('Items', [])
    
    if not items:
        print("No books found")
        return
    
    print(f"Found {len(items)} books:\n")
    
    for item in sorted(items, key=lambda x: x.get('book_id', 0)):
        print(f"Book ID: {item.get('book_id')}")
        
        # Print all fields
        for key, value in sorted(item.items()):
            if key != 'book_id':
                print(f"  {key}: {value}")
        print()


def query_student_profiles():
    """Query all student profiles"""
    print("\n" + "="*60)
    print("STUDENT PROFILES TABLE")
    print("="*60 + "\n")
    
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table('student_profiles')
    
    response = table.scan()
    items = response.get('Items', [])
    
    if not items:
        print("No student profiles found")
        return
    
    print(f"Found {len(items)} student profiles:\n")
    
    for item in items:
        print(json.dumps(item, indent=2, cls=DecimalEncoder))
        print()


def query_student_sessions():
    """Query all student sessions"""
    print("\n" + "="*60)
    print("STUDENT SESSIONS TABLE")
    print("="*60 + "\n")
    
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table('student_sessions')
    
    response = table.scan()
    items = response.get('Items', [])
    
    if not items:
        print("No student sessions found")
        return
    
    print(f"Found {len(items)} student sessions:\n")
    
    for item in items:
        print(json.dumps(item, indent=2, cls=DecimalEncoder))
        print()


def query_reading_sessions():
    """Query all reading sessions"""
    print("\n" + "="*60)
    print("READING SESSIONS TABLE")
    print("="*60 + "\n")
    
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table('reading_sessions')
    
    response = table.scan(Limit=10)
    items = response.get('Items', [])
    
    if not items:
        print("No reading sessions found (table is empty)")
        return
    
    print(f"Found {len(items)} reading sessions (showing first 10):\n")
    
    for item in items:
        print(json.dumps(item, indent=2, cls=DecimalEncoder))
        print()


def main():
    """Main execution"""
    print("\n" + "="*60)
    print("DynamoDB Data Query Tool")
    print("Region: us-west-2")
    print("="*60)
    
    try:
        # Query each table
        query_books()
        query_student_profiles()
        query_student_sessions()
        query_reading_sessions()
        
        print("\n" + "="*60)
        print("Query Complete")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
