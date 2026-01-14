#!/usr/bin/env python3
"""
DynamoDB Sync Script
Checks existing DynamoDB tables and aligns codebase configuration
"""
import boto3
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DynamoDBSync:
    """Sync and verify DynamoDB configuration"""
    
    def __init__(self, region: str = 'us-west-2'):
        self.region = region
        
        # Use credentials from environment
        session_kwargs = {'region_name': region}
        
        # Check if credentials are in environment
        if os.getenv('AWS_ACCESS_KEY_ID'):
            session_kwargs['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID')
        if os.getenv('AWS_SECRET_ACCESS_KEY'):
            session_kwargs['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY')
        if os.getenv('AWS_SESSION_TOKEN'):
            session_kwargs['aws_session_token'] = os.getenv('AWS_SESSION_TOKEN')
        
        self.dynamodb = boto3.client('dynamodb', **session_kwargs)
        self.dynamodb_resource = boto3.resource('dynamodb', **session_kwargs)
        
    def list_tables(self) -> List[str]:
        """List all DynamoDB tables"""
        print(f"\n{'='*60}")
        print(f"Scanning DynamoDB tables in region: {self.region}")
        print(f"{'='*60}\n")
        
        response = self.dynamodb.list_tables()
        tables = response.get('TableNames', [])
        
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
        
        return tables
    
    def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Get detailed table information"""
        print(f"\n{'='*60}")
        print(f"Table: {table_name}")
        print(f"{'='*60}")
        
        response = self.dynamodb.describe_table(TableName=table_name)
        table_info = response['Table']
        
        # Basic info
        print(f"Status: {table_info['TableStatus']}")
        print(f"Item Count: {table_info['ItemCount']}")
        print(f"Size: {table_info['TableSizeBytes']} bytes")
        print(f"Created: {datetime.fromtimestamp(table_info['CreationDateTime'].timestamp())}")
        
        # Key schema
        print(f"\nKey Schema:")
        for key in table_info['KeySchema']:
            attr_type = next(
                (attr['AttributeType'] for attr in table_info['AttributeDefinitions'] 
                 if attr['AttributeName'] == key['AttributeName']),
                'Unknown'
            )
            print(f"  {key['KeyType']}: {key['AttributeName']} ({attr_type})")
        
        # Global Secondary Indexes
        if 'GlobalSecondaryIndexes' in table_info:
            print(f"\nGlobal Secondary Indexes:")
            for gsi in table_info['GlobalSecondaryIndexes']:
                print(f"  {gsi['IndexName']}:")
                for key in gsi['KeySchema']:
                    attr_type = next(
                        (attr['AttributeType'] for attr in table_info['AttributeDefinitions'] 
                         if attr['AttributeName'] == key['AttributeName']),
                        'Unknown'
                    )
                    print(f"    {key['KeyType']}: {key['AttributeName']} ({attr_type})")
        
        # TTL
        try:
            ttl_response = self.dynamodb.describe_time_to_live(TableName=table_name)
            ttl_status = ttl_response.get('TimeToLiveDescription', {})
            if ttl_status.get('TimeToLiveStatus') == 'ENABLED':
                print(f"\nTTL: Enabled on attribute '{ttl_status.get('AttributeName')}'")
            else:
                print(f"\nTTL: Disabled")
        except Exception as e:
            print(f"\nTTL: Unable to check ({e})")
        
        return table_info
    
    def scan_table_sample(self, table_name: str, limit: int = 5) -> List[Dict]:
        """Get sample items from table"""
        print(f"\nSample Items (limit {limit}):")
        
        try:
            table = self.dynamodb_resource.Table(table_name)
            response = table.scan(Limit=limit)
            items = response.get('Items', [])
            
            if items:
                for i, item in enumerate(items, 1):
                    print(f"\n  Item {i}:")
                    # Show only keys and a few important fields
                    for key in ['PK', 'SK', 'Type', 'SessionId', 'student_id', 'session_id', 'book_id']:
                        if key in item:
                            print(f"    {key}: {item[key]}")
            else:
                print("  (No items found)")
            
            return items
            
        except Exception as e:
            print(f"  Error scanning table: {e}")
            return []
    
    def verify_reading_sessions_table(self, table_name: str = 'reading_sessions') -> bool:
        """Verify reading_sessions table matches expected schema"""
        print(f"\n{'='*60}")
        print(f"Verifying '{table_name}' table schema")
        print(f"{'='*60}\n")
        
        try:
            table_info = self.dynamodb.describe_table(TableName=table_name)['Table']
            
            # Expected schema
            expected_keys = {'PK': 'HASH', 'SK': 'RANGE'}
            expected_gsis = {'GSI1', 'GSI2'}
            
            # Check keys
            actual_keys = {
                key['AttributeName']: key['KeyType'] 
                for key in table_info['KeySchema']
            }
            
            keys_match = actual_keys == expected_keys
            print(f"✓ Primary Keys: {'MATCH' if keys_match else 'MISMATCH'}")
            if not keys_match:
                print(f"  Expected: {expected_keys}")
                print(f"  Actual: {actual_keys}")
            
            # Check GSIs
            actual_gsis = set()
            if 'GlobalSecondaryIndexes' in table_info:
                actual_gsis = {gsi['IndexName'] for gsi in table_info['GlobalSecondaryIndexes']}
            
            gsis_match = expected_gsis.issubset(actual_gsis)
            print(f"✓ GSIs: {'MATCH' if gsis_match else 'MISMATCH'}")
            if not gsis_match:
                print(f"  Expected: {expected_gsis}")
                print(f"  Actual: {actual_gsis}")
            
            compatible = keys_match and gsis_match
            
            if compatible:
                print(f"\n✅ Table '{table_name}' is COMPATIBLE with codebase")
            else:
                print(f"\n❌ Table '{table_name}' has SCHEMA MISMATCH")
            
            return compatible
            
        except Exception as e:
            print(f"❌ Error verifying table: {e}")
            return False
    
    def update_env_file(self, env_path: str = '.env'):
        """Update .env file with correct DynamoDB configuration"""
        print(f"\n{'='*60}")
        print(f"Updating {env_path}")
        print(f"{'='*60}\n")
        
        env_file = Path(env_path)
        if not env_file.exists():
            print(f"❌ File not found: {env_path}")
            return False
        
        # Read current content
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Update specific lines
        updates = {
            'DYNAMODB_REGION': self.region,
            'ENABLE_DYNAMODB_PERSISTENCE': 'true'
        }
        
        new_lines = []
        updated_keys = set()
        
        for line in lines:
            updated = False
            for key, value in updates.items():
                if line.startswith(f'{key}='):
                    old_value = line.split('=', 1)[1].strip()
                    new_lines.append(f'{key}={value}\n')
                    print(f"  {key}: {old_value} → {value}")
                    updated_keys.add(key)
                    updated = True
                    break
            
            if not updated:
                new_lines.append(line)
        
        # Add missing keys
        for key, value in updates.items():
            if key not in updated_keys:
                new_lines.append(f'\n{key}={value}\n')
                print(f"  {key}: (added) → {value}")
        
        # Write back
        with open(env_file, 'w') as f:
            f.writelines(new_lines)
        
        print(f"\n✅ Updated {env_path}")
        return True
    
    def analyze_other_tables(self, tables: List[str]):
        """Analyze other tables for potential integration"""
        print(f"\n{'='*60}")
        print(f"Analyzing Other Tables")
        print(f"{'='*60}\n")
        
        other_tables = [t for t in tables if t != 'reading_sessions']
        
        for table_name in other_tables:
            table_info = self.dynamodb.describe_table(TableName=table_name)['Table']
            
            print(f"\n{table_name}:")
            print(f"  Items: {table_info['ItemCount']}")
            print(f"  Keys: {', '.join([k['AttributeName'] for k in table_info['KeySchema']])}")
            
            # Get sample to understand structure
            if table_info['ItemCount'] > 0:
                self.scan_table_sample(table_name, limit=2)
    
    def list_local_sessions(self, sessions_dir: str = 'Server/sessions') -> List[Path]:
        """List local JSON session files"""
        print(f"\n{'='*60}")
        print(f"Local Session Files")
        print(f"{'='*60}\n")
        
        sessions_path = Path(sessions_dir)
        if not sessions_path.exists():
            print(f"  Directory not found: {sessions_dir}")
            return []
        
        json_files = list(sessions_path.glob('session_*.json'))
        print(f"Found {len(json_files)} local session files")
        
        if json_files:
            print("\nRecent sessions:")
            for f in sorted(json_files, reverse=True)[:5]:
                size_kb = f.stat().st_size / 1024
                print(f"  - {f.name} ({size_kb:.1f} KB)")
        
        return json_files
    
    def generate_migration_plan(self, json_files: List[Path]):
        """Generate migration plan for local sessions"""
        if not json_files:
            return
        
        print(f"\n{'='*60}")
        print(f"Migration Plan")
        print(f"{'='*60}\n")
        
        print(f"To migrate {len(json_files)} local sessions to DynamoDB:")
        print(f"  1. Enable DynamoDB persistence (ENABLE_DYNAMODB_PERSISTENCE=true)")
        print(f"  2. Run migration script (to be created)")
        print(f"  3. Verify data in DynamoDB")
        print(f"  4. Archive local JSON files")
        
        total_size = sum(f.stat().st_size for f in json_files) / (1024 * 1024)
        print(f"\nTotal data size: {total_size:.2f} MB")


def main():
    """Main execution"""
    print("\n" + "="*60)
    print("DynamoDB Sync & Verification Tool")
    print("="*60)
    
    # Initialize
    sync = DynamoDBSync(region='us-west-2')
    
    # 1. List all tables
    tables = sync.list_tables()
    
    if not tables:
        print("\n❌ No tables found in region us-west-2")
        return
    
    # 2. Describe each table
    for table_name in tables:
        sync.describe_table(table_name)
        if table_name != 'reading_sessions':
            sync.scan_table_sample(table_name, limit=2)
    
    # 3. Verify reading_sessions table
    if 'reading_sessions' in tables:
        is_compatible = sync.verify_reading_sessions_table('reading_sessions')
        
        if is_compatible:
            # 4. Update .env file
            sync.update_env_file('.env')
    else:
        print("\n⚠️  'reading_sessions' table not found!")
        print("   You may need to create it using the CloudFormation template.")
    
    # 5. Analyze other tables
    sync.analyze_other_tables(tables)
    
    # 6. Check local sessions
    json_files = sync.list_local_sessions('sessions')
    
    # 7. Generate migration plan
    if json_files:
        sync.generate_migration_plan(json_files)
    
    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}\n")
    print(f"✓ Region: us-west-2")
    print(f"✓ Tables found: {len(tables)}")
    print(f"✓ reading_sessions: {'Compatible' if 'reading_sessions' in tables else 'Not found'}")
    print(f"✓ Local sessions: {len(json_files) if json_files else 0}")
    print(f"\nNext steps:")
    print(f"  1. Review the updated .env file")
    print(f"  2. Restart the server to enable DynamoDB persistence")
    print(f"  3. Test by creating a new reading session")
    print(f"  4. Verify data appears in DynamoDB console")
    print()


if __name__ == '__main__':
    main()
