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
  const [currentStudent, setCurrentStudent] = useState(null);
  const [selectedBook, setSelectedBook] = useState(null);

  const handleLogin = (studentProfile) => {
    setCurrentStudent(studentProfile);
  };

  const handleBookSelect = (book) => {
    setSelectedBook(book);
  };

  const handleLogout = () => {
    setCurrentStudent(null);
    setSelectedBook(null);
  };

  const handleBackToLogin = () => {
    setCurrentStudent(null);
    setSelectedBook(null);
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
      />
    </div>
  );
}
export default App;
