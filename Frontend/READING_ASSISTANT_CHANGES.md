# Reading Assistant Conversion

This document outlines the changes made to convert the application into a reading assistant for children with book selection functionality.

## Changes Made

### 1. Student Login System
- **New Component**: `Frontend/src/components/StudentLogin.js`
- **Styling**: `Frontend/src/components/StudentLogin.css`
- **Features**:
  - Dropdown with two student profiles:
    - StudentA - Reading Level 2 (Beginning reader)
    - StudentB - Reading Level 3 (Intermediate reader)
  - Submit button to proceed to book selection
  - Child-friendly design with gradient background

### 2. Book Selection System
- **New Component**: `Frontend/src/components/BookSelection.js`
- **Styling**: `Frontend/src/components/BookSelection.css`
- **Features**:
  - Fetches books from backend API based on reading level
  - Displays books in card format with details (author, pages, description)
  - Single book selection with visual feedback
  - Fallback to mock data if API is unavailable
  - Loading states and error handling
  - Back to login functionality

### 3. Backend Books API
- **New API Handler**: `Backend/api_handler.py`
- **Features**:
  - RESTful API endpoint: `GET /api/books?level=X`
  - DynamoDB integration for book storage
  - CORS support for frontend requests
  - Mock data fallback for development
  - Error handling and logging

### 4. Database Setup
- **Setup Script**: `Backend/setup_books_table.py`
- **Features**:
  - Creates DynamoDB 'books' table
  - Populates with sample books for levels 2 and 3
  - Includes classic children's books with metadata
  - Verification of inserted data

### 5. Updated Student Profiles
- **File**: `Frontend/src/helper/config.js`
- **Changes**:
  - Added two new reading-focused profiles at the top of DemoProfiles array
  - StudentA uses "Tiffany" voice with Level 2 reading prompts
  - StudentB uses "Amy" voice with Level 3 reading prompts
  - Both profiles include reading assistance tools and age-appropriate system prompts

### 6. Modified Application Flow
- **File**: `Frontend/src/App.js`
- **Changes**:
  - Added state management for current student and selected book
  - Three-step flow: Login → Book Selection → Reading Session
  - Passes student and book context to main chat component

### 7. Updated Chat Interface
- **File**: `Frontend/src/s2s.js`
- **Changes**:
  - Automatically selects appropriate reading profile based on student login
  - Updated header to show "Reading Assistant"
  - Added student welcome message and selected book display
  - Added "Switch Student" button for logout functionality
  - Hidden profile selector (since it's now determined by login)
  - Changed conversation header to "Reading Conversation"
  - Updated input placeholder to be reading-focused
  - Changed button text to "Start Reading Session"

### 8. Enhanced Styling
- **Files**: `Frontend/src/s2s.css`, component CSS files
- **Changes**:
  - Added styling for student info and book display
  - Added styling for logout/switch student button
  - Child-friendly color scheme with purple/blue gradients
  - Responsive card layouts for book selection

### 9. Backend Server Updates
- **File**: `Backend/server.py`
- **Changes**:
  - Integrated new BooksAPIHandler
  - Added API server on separate port (8080)
  - Replaced health check with full API functionality
  - Environment variable configuration

### 10. Configuration Files
- **Backend**: `.env.example` for server configuration
- **Frontend**: `.env.example` for API endpoints
- Environment-based configuration for different deployments

## Application Flow

1. **Student Login**: User selects reading level profile
2. **Book Selection**: System fetches books for that level from DynamoDB
3. **Book Choice**: Student selects a specific book to read
4. **Reading Session**: Personalized AI assistant helps with the selected book

## API Endpoints

### GET /api/books?level={reading_level}
- **Purpose**: Fetch books for a specific reading level
- **Parameters**: 
  - `level` (required): Reading level (2 or 3)
- **Response**:
  ```json
  {
    "books": [
      {
        "book_id": "book_2_1",
        "name": "The Cat in the Hat",
        "level": 2,
        "description": "A fun story about a cat...",
        "author": "Dr. Seuss",
        "pages": 62
      }
    ],
    "level": 2,
    "count": 5
  }
  ```

## Database Schema

### DynamoDB Table: 'books'
- **Partition Key**: `book_id` (String)
- **Attributes**:
  - `name`: Book title
  - `level`: Reading level (2 or 3)
  - `description`: Book summary
  - `author`: Author name
  - `pages`: Number of pages
  - `genre`: Book genre
  - `published_year`: Publication year

## Reading Level Differences

### StudentA (Level 2)
- Simple, clear language for beginning readers
- Focus on basic vocabulary and word recognition
- Pronunciation help and encouragement
- Uses Tiffany voice (US Female)
- Books: Dr. Seuss classics, simple picture books

### StudentB (Level 3)
- More complex vocabulary for intermediate readers
- Reading comprehension support
- Story theme and character discussions
- Uses Amy voice (GB Female)
- Books: Classic children's literature, longer stories

## Setup Instructions

### Backend Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and configure AWS credentials
3. Set up DynamoDB table: `python setup_books_table.py`
4. Start server: `python server.py`

### Frontend Setup
1. Install dependencies: `npm install`
2. Copy `.env.example` to `.env` and configure API URL
3. Start development server: `npm start`

### AWS Requirements
- DynamoDB access for books table
- Bedrock access for AI assistant
- Appropriate IAM permissions

## Development Notes

- API includes mock data fallback for development without AWS
- CORS enabled for local development
- Error handling throughout the application
- Responsive design for different screen sizes
- Logging and monitoring capabilities