"""
Enhanced reading analysis with hybrid approach:
- LLM for complex pattern recognition
- Heuristic algorithms for structured analysis
"""

from typing import List, Tuple, Dict
import re
from difflib import SequenceMatcher


class MiscueDetector:
    """
    Heuristic-based miscue detection to complement LLM analysis
    """
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text into words, preserving case"""
        # Remove speaker labels like "Reader:", "Tutor:"
        text = re.sub(r'(Reader|Tutor|Agent):\s*', '', text)
        # Split on whitespace and punctuation, keeping words
        words = re.findall(r'\b\w+\b', text)
        return words
    
    @staticmethod
    def align_sequences(passage_words: List[str], spoken_words: List[str]) -> List[Tuple[str, str, str]]:
        """
        Align passage words with spoken words using sequence matching
        
        Returns:
            List of tuples (passage_word, spoken_word, operation)
            where operation is 'match', 'substitution', 'omission', or 'insertion'
        """
        alignments = []
        matcher = SequenceMatcher(None, passage_words, spoken_words)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Words match
                for k in range(i2 - i1):
                    alignments.append((passage_words[i1 + k], spoken_words[j1 + k], 'match'))
            
            elif tag == 'replace':
                # Substitution
                # Handle case where multiple words are involved
                for k in range(max(i2 - i1, j2 - j1)):
                    pass_word = passage_words[i1 + k] if i1 + k < i2 else None
                    spok_word = spoken_words[j1 + k] if j1 + k < j2 else None
                    
                    if pass_word and spok_word:
                        alignments.append((pass_word, spok_word, 'substitution'))
                    elif pass_word:
                        alignments.append((pass_word, None, 'omission'))
                    elif spok_word:
                        alignments.append((None, spok_word, 'insertion'))
            
            elif tag == 'delete':
                # Omission (word in passage but not spoken)
                for k in range(i2 - i1):
                    alignments.append((passage_words[i1 + k], None, 'omission'))
            
            elif tag == 'insert':
                # Insertion (word spoken but not in passage)
                for k in range(j2 - j1):
                    alignments.append((None, spoken_words[j1 + k], 'insertion'))
        
        return alignments
    
    @staticmethod
    def detect_repetitions(words: List[str]) -> List[int]:
        """
        Detect repeated words in sequence
        
        Returns:
            List of indices where repetitions occur
        """
        repetitions = []
        for i in range(len(words) - 1):
            if words[i].lower() == words[i + 1].lower():
                repetitions.append(i)
        return repetitions
    
    @staticmethod
    def detect_hesitations(transcript: str) -> List[str]:
        """
        Detect hesitation markers in transcript
        
        Returns:
            List of hesitation patterns found
        """
        hesitation_patterns = [
            r'\.\.\.',  # Ellipsis
            r'\bum\b',
            r'\buh\b',
            r'\ber\b',
            r'\bahh?\b',
            r'\(pause\)',
            r'\(long pause\)',
        ]
        
        hesitations = []
        for pattern in hesitation_patterns:
            matches = re.finditer(pattern, transcript, re.IGNORECASE)
            hesitations.extend([m.group() for m in matches])
        
        return hesitations
    
    @staticmethod
    def detect_questions(transcript: str) -> List[str]:
        """
        Extract questions from reader in transcript
        
        Returns:
            List of questions asked by the reader
        """
        questions = []
        
        # Find Reader lines
        reader_lines = re.findall(r'Reader:\s*(.+?)(?=(?:Reader:|Tutor:|Agent:|$))', 
                                  transcript, re.DOTALL | re.IGNORECASE)
        
        for line in reader_lines:
            # Check if line contains a question
            if '?' in line:
                questions.append(line.strip())
            # Common question patterns
            elif re.search(r'\b(how|what|can you|help|don\'t know)\b', line, re.IGNORECASE):
                questions.append(line.strip())
        
        return questions
    
    @staticmethod
    def detect_agent_interventions(transcript: str) -> List[str]:
        """
        Extract agent/tutor interventions from transcript
        
        Returns:
            List of tutor/agent utterances
        """
        interventions = []
        
        # Find Tutor/Agent lines
        tutor_lines = re.findall(r'(?:Tutor|Agent):\s*(.+?)(?=(?:Reader:|Tutor:|Agent:|$))', 
                                transcript, re.DOTALL | re.IGNORECASE)
        
        for line in tutor_lines:
            line = line.strip()
            # Filter out procedural instructions
            if line and not re.match(r'(please read|read this|begin|start)', line, re.IGNORECASE):
                interventions.append(line)
        
        return interventions
    
    @staticmethod
    def calculate_wpm(passage: str, time_seconds: float = None) -> float:
        """
        Calculate words per minute
        
        Args:
            passage: The passage text
            time_seconds: Time taken in seconds (if None, returns 0)
            
        Returns:
            Words per minute
        """
        if not time_seconds or time_seconds <= 0:
            return 0.0
        
        word_count = len(MiscueDetector.tokenize(passage))
        wpm = (word_count / time_seconds) * 60
        return round(wpm, 1)
    
    @staticmethod
    def calculate_accuracy(total_words: int, omissions: int, substitutions: int, 
                          agent_interventions: int) -> float:
        """
        Calculate reading accuracy percentage
        
        Args:
            total_words: Total words in passage
            omissions: Number of omitted words
            substitutions: Number of substituted words
            agent_interventions: Number of tutor-supplied words
            
        Returns:
            Accuracy as percentage (0-100)
        """
        if total_words == 0:
            return 0.0
        
        errors = omissions + substitutions + agent_interventions
        correct_words = max(0, total_words - errors)
        accuracy = (correct_words / total_words) * 100
        
        return round(accuracy, 1)
    
    @staticmethod
    def analyze_transcript(passage: str, transcript: str, 
                          time_seconds: float = None) -> Dict:
        """
        Perform heuristic analysis of transcript
        
        Args:
            passage: The passage text
            transcript: The reading transcript
            time_seconds: Optional time taken to read
            
        Returns:
            Dictionary with analysis results
        """
        # Tokenize
        passage_words = MiscueDetector.tokenize(passage)
        
        # Extract only reader's words from transcript
        reader_text = ' '.join(re.findall(r'Reader:\s*(.+?)(?=(?:Reader:|Tutor:|Agent:|$))', 
                                          transcript, re.DOTALL | re.IGNORECASE))
        spoken_words = MiscueDetector.tokenize(reader_text)
        
        # Align sequences
        alignments = MiscueDetector.align_sequences(passage_words, spoken_words)
        
        # Count miscues
        omissions = sum(1 for _, _, op in alignments if op == 'omission')
        insertions = sum(1 for _, _, op in alignments if op == 'insertion')
        substitutions = sum(1 for _, _, op in alignments if op == 'substitution')
        
        # Detect patterns
        repetitions = MiscueDetector.detect_repetitions(spoken_words)
        hesitations = MiscueDetector.detect_hesitations(transcript)
        questions = MiscueDetector.detect_questions(transcript)
        interventions = MiscueDetector.detect_agent_interventions(transcript)
        
        # Calculate metrics
        total_words = len(passage_words)
        wpm = MiscueDetector.calculate_wpm(passage, time_seconds)
        accuracy = MiscueDetector.calculate_accuracy(
            total_words, omissions, substitutions, len(interventions)
        )
        
        return {
            'alignments': alignments,
            'kpis': {
                'omissions': omissions,
                'insertions': insertions,
                'substitutions': substitutions,
                'repetitions': len(repetitions),
                'hesitations': len(hesitations),
                'questions': len(questions),
                'agent_interventions': len(interventions),
                'words_per_minute': wpm,
                'accuracy': accuracy,
                'total_words': total_words,
                'words_read_correctly': total_words - omissions - substitutions - len(interventions)
            },
            'details': {
                'repetition_indices': repetitions,
                'hesitation_markers': hesitations,
                'question_texts': questions,
                'intervention_texts': interventions
            }
        }


if __name__ == "__main__":
    # Test the detector
    passage = "The cat is orange."
    transcript = """
Tutor: Please read this sentence.
Reader: The... The cat is ... um... how do I pronounce this word?
Tutor: "orange."
Reader: "orange."
"""
    
    detector = MiscueDetector()
    results = detector.analyze_transcript(passage, transcript, time_seconds=8.0)
    
    print("Heuristic Analysis Results:")
    print(f"KPIs: {results['kpis']}")
    print(f"\nDetails:")
    print(f"Questions: {results['details']['question_texts']}")
    print(f"Interventions: {results['details']['intervention_texts']}")
