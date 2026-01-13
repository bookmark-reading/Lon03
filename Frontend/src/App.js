import { useState, useRef } from "react";
import * as React from "react";
import { withAuthenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import { AppLayout, SideNavigation } from '@cloudscape-design/components';
import TopNavigation from "@cloudscape-design/components/top-navigation";
import S2sChatBot from './s2s';
import StudentLogin from './components/StudentLogin';
import BookSelection from './components/BookSelection';


const App = ({ signOut, user }) => {
  const [displayTopMenu] = useState(window.self === window.top);
  const [currentStudent, setCurrentStudent] = useState(() => {
    // Restore student from localStorage on initial load
    try {
      const saved = localStorage.getItem('currentStudent');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });
  const [selectedBook, setSelectedBook] = useState(() => {
    // Restore book from localStorage on initial load
    try {
      const saved = localStorage.getItem('selectedBook');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });

  const handleLogin = (studentProfile) => {
    setCurrentStudent(studentProfile);
    // Save to localStorage
    localStorage.setItem('currentStudent', JSON.stringify(studentProfile));
  };

  const handleBookSelect = (book) => {
    setSelectedBook(book);
    // Save to localStorage
    localStorage.setItem('selectedBook', JSON.stringify(book));
  };

  const handleLogout = () => {
    setCurrentStudent(null);
    setSelectedBook(null);
    // Clear from localStorage
    localStorage.removeItem('currentStudent');
    localStorage.removeItem('selectedBook');
  };

  const handleBackToLogin = () => {
    setCurrentStudent(null);
    setSelectedBook(null);
    // Clear from localStorage
    localStorage.removeItem('currentStudent');
    localStorage.removeItem('selectedBook');
  };

  const handleChangeBook = () => {
    // Keep student, only clear book to go back to book selection
    setSelectedBook(null);
    localStorage.removeItem('selectedBook');
  };

  // Show login page if no student is selected
  if (!currentStudent) {
    return <StudentLogin onLogin={handleLogin} />;
  }

  // Show book selection if student is selected but no book is chosen
  if (currentStudent && !selectedBook) {
    return (
      <BookSelection 
        currentStudent={currentStudent}
        onBookSelect={handleBookSelect}
        onBack={handleBackToLogin}
      />
    );
  }

  // Show main application with student and book context
  return (
    <div>
      <S2sChatBot 
        currentStudent={currentStudent}
        selectedBook={selectedBook}
        onLogout={handleLogout}
        onChangeBook={handleChangeBook}
      />
    </div>
  );
}
export default App;
