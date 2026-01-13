import React, { useState } from 'react';
import { Container, Header, FormField, Select, Button, SpaceBetween, Box } from '@cloudscape-design/components';
import './StudentLogin.css';

const StudentProfiles = [
    {
        label: "StudentA - Reading Level 2",
        value: "studentA",
        description: "Beginning reader with basic vocabulary",
        readingLevel: 2
    },
    {
        label: "StudentB - Reading Level 3", 
        value: "studentB",
        description: "Intermediate reader with expanded vocabulary",
        readingLevel: 3
    }
];

const StudentLogin = ({ onLogin }) => {
    const [selectedStudent, setSelectedStudent] = useState(null);

    const handleSubmit = () => {
        if (selectedStudent) {
            onLogin(selectedStudent);
        }
    };

    return (
        <div className="student-login-container">
            <Container>
                <div className="login-content">
                    <Header
                        variant="h1"
                        description="Select your student profile to begin your reading session"
                    >
                        📚 Reading Assistant Login
                    </Header>
                    
                    <SpaceBetween size="l">
                        <FormField
                            label="Student Profile"
                            description="Choose your reading level to get personalized assistance"
                        >
                            <Select
                                selectedOption={selectedStudent}
                                onChange={({ detail }) => setSelectedStudent(detail.selectedOption)}
                                options={StudentProfiles}
                                placeholder="Select a student profile..."
                                expandToViewport
                            />
                        </FormField>

                        <Box textAlign="center">
                            <Button
                                variant="primary"
                                size="large"
                                onClick={handleSubmit}
                                disabled={!selectedStudent}
                            >
                                Start Reading Session
                            </Button>
                        </Box>
                    </SpaceBetween>
                </div>
            </Container>
        </div>
    );
};

export { StudentProfiles };
export default StudentLogin;