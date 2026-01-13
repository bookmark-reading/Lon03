import json
import logging
import boto3
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from botocore.exceptions import ClientError
from decimal import Decimal

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal objects from DynamoDB"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert Decimal to int if it's a whole number, otherwise to float
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)

class BooksAPIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Initialize DynamoDB client
        self.dynamodb = boto3.resource('dynamodb')
        self.books_table = self.dynamodb.Table('books')
        super().__init__(*args, **kwargs)

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        client_ip = self.client_address[0]
        logger.info(f"API request received from {client_ip} for path: {self.path}")

        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)

            if path == "/api/books":
                self.handle_get_books(query_params)
            elif path == "/health" or path == "/":
                self.handle_health_check()
            else:
                self.send_error_response(404, "Not Found")
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.send_error_response(500, "Internal Server Error")

    def handle_get_books(self, query_params):
        """Handle GET /api/books?level=X"""
        try:
            # Get reading level from query parameters
            level_param = query_params.get('level', [])
            if not level_param:
                self.send_error_response(400, "Missing 'level' parameter")
                return

            try:
                reading_level = int(level_param[0])
            except ValueError:
                self.send_error_response(400, "Invalid 'level' parameter - must be a number")
                return

            # Query DynamoDB for books by reading level
            books = self.get_books_by_level(reading_level)
            
            response_data = {
                "books": books,
                "level": reading_level,
                "count": len(books)
            }

            self.send_json_response(200, response_data)
            logger.info(f"Returned {len(books)} books for level {reading_level}")

        except Exception as e:
            logger.error(f"Error fetching books: {e}")
            self.send_error_response(500, f"Error fetching books: {str(e)}")

    def get_books_by_level(self, reading_level):
        """Query DynamoDB for books by reading level"""
        try:
            # Query the books table for the specified reading level
            response = self.books_table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('level').eq(reading_level)
            )
            
            books = response.get('Items', [])
            
            # Convert DynamoDB response using only the actual table fields
            formatted_books = []
            for book in books:
                formatted_book = {
                    'book_id': book.get('book_id', ''),
                    'name': book.get('name', ''),
                    'level': book.get('level', reading_level),
                    'file': book.get('file', ''),
                    'markdown': book.get('markdown', ''),
                    'thumbnail': book.get('thumbnail', '')
                }
                formatted_books.append(formatted_book)
            
            return formatted_books

        except ClientError as e:
            logger.error(f"DynamoDB error: {e}")
            raise Exception(f"Failed to fetch books from DynamoDB: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error querying books: {e}")
            raise Exception(f"Database error: {str(e)}")

    def handle_health_check(self):
        """Handle health check requests"""
        response_data = {"status": "healthy", "service": "books-api"}
        self.send_json_response(200, response_data)

    def send_json_response(self, status_code, data):
        """Send a JSON response"""
        self.send_response(status_code)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        # Use custom encoder to handle Decimal objects
        response_json = json.dumps(data, cls=DecimalEncoder)
        self.wfile.write(response_json.encode("utf-8"))

    def send_error_response(self, status_code, message):
        """Send an error response"""
        error_data = {"error": message, "status": status_code}
        self.send_json_response(status_code, error_data)

    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def log_message(self, format, *args):
        """Override to use our logger instead of default logging"""
        logger.info(format % args)