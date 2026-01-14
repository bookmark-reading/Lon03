# Reading Transcript Analysis API

A FastAPI-based service that analyzes reading transcripts to identify reading miscues and calculate performance KPIs using AWS Bedrock (Claude 3.5 Sonnet v2).

## Features

- **8 Miscue Types Detected**: omissions, insertions, substitutions, repetitions, self-corrections, hesitations, questions, agent interventions
- **Performance KPIs**: accuracy, words per minute (WPM), error counts
- **RESTful API**: Fast, scalable FastAPI server
- **Interactive Docs**: Auto-generated Swagger/OpenAPI documentation
- **AWS Bedrock Integration**: Claude 3.5 Sonnet v2 via cross-region inference profile

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0
```

> **Note**: Uses AWS Bedrock **inference profile** for better availability across us-east-1, us-east-2, us-west-2

### 3. Run the API

```bash
python api.py
```

Server starts at: **http://localhost:8000**

## API Endpoints

### `POST /analyze`
Analyze a reading transcript

**Request:**
```json
{
  "passage": "Mia packed her blue bag and ran to the park.\nIt was windy, so her kite tugged hard at the string.",
  "transcript": "STUDENT: Mia packed her... her blue bag and ran to park.\nSTUDENT: It was... um... window... no, windy, so her kite tug tugged hard at the the string."
}
```

**Response:**
```json
{
  "cleaned_passage": "Mia packed [repetition]her[/repetition] blue bag and ran to [omission]the[/omission] park.\n[hesitation]...[/hesitation] It was [substitution]window[/substitution] [self-correction]windy[/self-correction], so her kite [substitution]tug[/substitution] tugged hard at [repetition]the[/repetition] the string.",
  "kpis": {
    "omissions": 1,
    "insertions": 0,
    "substitutions": 2,
    "repetitions": 2,
    "self_corrections": 1,
    "hesitations": 2,
    "questions": 0,
    "agent_interventions": 0,
    "words_per_minute": 45.0,
    "accuracy": 75.0,
    "total_words": 20,
    "words_read_correctly": 15
  }
}
```

### `GET /health`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "model": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
  "region": "us-west-2"
}
```

### `GET /docs`
Interactive API documentation (Swagger UI)

Visit: http://localhost:8000/docs

## Example Usage

### cURL
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "passage": "The cat sat on the mat.",
    "transcript": "STUDENT: The cat... cat sit on the mat. STUDENT: Wait, I mean sat on mat."
  }'
```

### Python
```python
import requests

response = requests.post(
    "http://localhost:8000/analyze",
    json={
        "passage": "The cat sat on the mat.",
        "transcript": "STUDENT: The cat sit on mat."
    }
)

print(response.json())
```

### JavaScript
```javascript
const response = await fetch('http://localhost:8000/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    passage: 'The cat sat on the mat.',
    transcript: 'STUDENT: The cat sit on mat.'
  })
});

const result = await response.json();
console.log(result);
```

## Transcript Format

Use **STUDENT:** and **AGENT:** labels in transcripts:

```
STUDENT: Mia packed her... her blue bag and ran to park.
STUDENT: It was... um... window... no, windy.
STUDENT: How do you say this word?
AGENT: That word is 'tight'.
STUDENT: Hold tight, Dad said, smiling.
```

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### AWS Lambda
Use AWS Lambda Web Adapter with the FastAPI app

### AWS ECS/Fargate
Deploy as a containerized service

## Project Structure

```
analyse/
├── api.py                  # FastAPI server
├── reading_agent.py        # LangGraph agent
├── miscue_detector.py      # Heuristic detector
├── graph.py               # LangGraph Studio export
├── langgraph.json         # LangGraph config
├── requirements.txt       # Dependencies
├── .env.example          # Environment template
└── README.md             # This file
```

## Troubleshooting

**Inference profile error:**
```
ValidationException: Invocation of model ID ... with on-demand throughput isn't supported
```
Solution: Ensure `BEDROCK_MODEL_ID` uses inference profile format: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`

**Protobuf conflict:**
```bash
pip uninstall -y fireworks-ai
```

**Port already in use:**
```bash
lsof -ti:8000 | xargs kill -9
```

## License

MIT

