import React, { useState, useEffect } from 'react';
import { Container, Header, Button, SpaceBetween, Box, Cards, Badge, Alert, Spinner } from '@cloudscape-design/components';
import './BookSelection.css';

const BookSelection = ({ currentStudent, onBookSelect, onBack }) => {
    const [books, setBooks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedBook, setSelectedBook] = useState(null);

    useEffect(() => {
        fetchBooks();
    }, [currentStudent]);

    const fetchBooks = async () => {
        try {
            setLoading(true);
            setError(null);
            
            const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8080';
            const response = await fetch(`${apiUrl}/api/books?level=${currentStudent.readingLevel}`);
            
            if (!response.ok) {
                throw new Error(`Failed to fetch books: ${response.status}`);
            }
            
            const data = await response.json();
            setBooks(data.books || []);
        } catch (err) {
            console.error('Error fetching books:', err);
            setError(err.message);
            // Fallback to empty array if API is unavailable - no mock data
            setBooks([]);
        } finally {
            setLoading(false);
        }
    };

    const handleBookSelect = (book) => {
        setSelectedBook(book);
    };

    const handleStartReading = () => {
        if (selectedBook) {
            onBookSelect(selectedBook);
        }
    };

    if (loading) {
        return (
            <div className="book-selection-container">
                <Container>
                    <Box textAlign="center" padding="xxl">
                        <Spinner size="large" />
                        <Box variant="h3" padding={{ top: "m" }}>
                            Loading books for {currentStudent.label}...
                        </Box>
                    </Box>
                </Container>
            </div>
        );
    }

    return (
        <div className="book-selection-container">
            <Container>
                <div className="book-selection-content">
                    <Header
                        variant="h1"
                        description={`Choose a book that matches your reading level (Level ${currentStudent.readingLevel})`}
                        actions={
                            <Button
                                variant="normal"
                                onClick={onBack}
                            >
                                ← Back to Login
                            </Button>
                        }
                    >
                        📚 Choose Your Book
                    </Header>

                    {error && (
                        <Alert
                            statusIconAriaLabel="Warning"
                            type="warning"
                            header="Unable to load books from server"
                        >
                            {error}. Showing sample books instead.
                        </Alert>
                    )}

                    <SpaceBetween size="l">
                        <div className="student-welcome">
                            <Badge color="blue">
                                Welcome, {currentStudent.label.split(' - ')[0]}!
                            </Badge>
                        </div>

                        {books.length === 0 ? (
                            <Box textAlign="center" padding="xxl">
                                <Box variant="h3" color="text-status-error">
                                    No books found for Reading Level {currentStudent.readingLevel}
                                </Box>
                                <Box variant="p" padding={{ top: "s" }}>
                                    Please try again later or contact your teacher.
                                </Box>
                            </Box>
                        ) : (
                            <>
                                <Cards
                                    cardDefinition={{
                                        header: item => (
                                            <div className="book-card-header">
                                                <span className="book-title">{item.name}</span>
                                                <Badge color="green">Level {item.level}</Badge>
                                            </div>
                                        ),
                                        sections: [
                                            {
                                                content: item => (
                                                    <div className="book-details">
                                                        {item.thumbnail && (
                                                            <div className="book-thumbnail">
                                                                <img 
                                                                    src={item.thumbnail} 
                                                                    alt={`${item.name} cover`}
                                                                    className="book-cover-image"
                                                                />
                                                            </div>
                                                        )}
                                                        <div className="book-info">
                                                            <div className="book-id">
                                                                <strong>Book ID:</strong> {item.book_id}
                                                            </div>
                                                            {item.file && (
                                                                <div className="book-file">
                                                                    <strong>File:</strong> {item.file}
                                                                </div>
                                                            )}
                                                            {item.markdown && (
                                                                <div className="book-preview">
                                                                    <strong>Preview:</strong>
                                                                    <div className="markdown-preview">
                                                                        {item.markdown.substring(0, 100)}...
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                )
                                            }
                                        ]
                                    }}
                                    cardsPerRow={[
                                        { cards: 1 },
                                        { minWidth: 500, cards: 2 },
                                        { minWidth: 800, cards: 3 }
                                    ]}
                                    items={books}
                                    selectionType="single"
                                    selectedItems={selectedBook ? [selectedBook] : []}
                                    onSelectionChange={({ detail }) => {
                                        const selected = detail.selectedItems[0];
                                        handleBookSelect(selected);
                                    }}
                                    empty={
                                        <Box textAlign="center" color="inherit">
                                            <b>No books available</b>
                                            <Box variant="p" color="inherit">
                                                No books found for your reading level.
                                            </Box>
                                        </Box>
                                    }
                                />

                                <Box textAlign="center">
                                    <Button
                                        variant="primary"
                                        size="large"
                                        onClick={handleStartReading}
                                        disabled={!selectedBook}
                                    >
                                        Start Reading "{selectedBook?.name || 'Selected Book'}"
                                    </Button>
                                </Box>
                            </>
                        )}
                    </SpaceBetween>
                </div>
            </Container>
        </div>
    );
};

export default BookSelection;