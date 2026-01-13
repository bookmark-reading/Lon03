#!/usr/bin/env python3
"""
Script to verify the 'books' DynamoDB table structure.
This script checks that the table exists and shows the current schema.
"""

import boto3
import json
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_books_table():
    """Verify the books DynamoDB table exists and show its structure"""
    dynamodb = boto3.resource('dynamodb')
    
    try:
        table = dynamodb.Table('books')
        table.load()
        logger.info("Table 'books' exists")
        
        # Show table info
        logger.info(f"Table status: {table.table_status}")
        logger.info(f"Item count: {table.item_count}")
        
        # Show key schema
        logger.info("Key Schema:")
        for key in table.key_schema:
            logger.info(f"  {key['AttributeName']} ({key['KeyType']})")
        
        return table
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.error("Table 'books' does not exist")
            logger.error("Please create the table with the following schema:")
            logger.error("- Partition Key: book_id (String)")
            logger.error("- Fields: book_id, file, level, name, markdown, thumbnail")
            return None
        else:
            logger.error(f"Error accessing table: {e}")
            raise

def show_sample_data(table, limit=3):
    """Show sample data from the books table"""
    try:
        logger.info(f"Sample data (first {limit} items):")
        
        response = table.scan(Limit=limit)
        items = response.get('Items', [])
        
        if not items:
            logger.info("No items found in the table")
            return
        
        for i, item in enumerate(items, 1):
            logger.info(f"Item {i}:")
            logger.info(f"  book_id: {item.get('book_id', 'N/A')}")
            logger.info(f"  name: {item.get('name', 'N/A')}")
            logger.info(f"  level: {item.get('level', 'N/A')}")
            logger.info(f"  file: {item.get('file', 'N/A')}")
            logger.info(f"  thumbnail: {item.get('thumbnail', 'N/A')}")
            logger.info(f"  markdown: {str(item.get('markdown', 'N/A'))[:50]}...")
            logger.info("")
            
    except Exception as e:
        logger.error(f"Error reading sample data: {e}")

def check_levels(table):
    """Check what reading levels are available in the table"""
    try:
        response = table.scan(
            ProjectionExpression='#level',
            ExpressionAttributeNames={'#level': 'level'}
        )
        
        levels = set()
        for item in response.get('Items', []):
            if 'level' in item:
                levels.add(int(item['level']))
        
        logger.info(f"Available reading levels: {sorted(levels)}")
        
        # Count books per level
        for level in sorted(levels):
            count_response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('level').eq(level),
                Select='COUNT'
            )
            count = count_response.get('Count', 0)
            logger.info(f"Level {level}: {count} books")
            
    except Exception as e:
        logger.error(f"Error checking levels: {e}")

def main():
    """Main function to verify the books table"""
    try:
        logger.info("Verifying books table...")
        
        # Verify table exists
        table = verify_books_table()
        if not table:
            return
        
        # Show sample data
        show_sample_data(table)
        
        # Check available levels
        check_levels(table)
        
        logger.info("Books table verification completed!")
        
    except Exception as e:
        logger.error(f"Error verifying books table: {e}")
        raise

if __name__ == "__main__":
    main()