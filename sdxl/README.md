# SDXL Image Generation API

An OpenAI-compatible image generation service using Stable Diffusion XL.

## Features

- OpenAI-compatible API endpoint at `/v1/images/generations`
- Supports all standard image generation parameters
- Base64-encoded image responses
- Model loading optimization
- Health check endpoint

## API Endpoints

### Generate Images
```
POST /v1/images/generations
```

**Request Body:**
```json
{
  "prompt": "A character portrait of a bearded warrior from a RPG / D&D style game. Style: detailed, fine pencil illustration with dynamic lighting. The character is facing forward, having a determined, slightly angry face, and wearing armor.",
  "negative_prompt": "blurry, low quality, deformed, text, watermark",
  "width": 1024,
  "height": 768,
  "guidance_scale": 7.0,
  "num_inference_steps": 40,
  "seed": 12345
}
```

**Response:**
```json
{
  "created": 1701504000,
  "data": [
    {
      "b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    }
  ]
}
```

### Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy"
}
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python sdxl/sdxl_server.py
```

The server will start on `http://0.0.0.0:8115`

## Usage Example

```bash
curl -X POST "http://localhost:8113/v1/images/generations" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A character portrait of a RPG game bearded warrior with a stern expression. Grayscale pencil sketch.",
    "width": 1024,
    "height": 768
  }'
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| prompt | string | Required | The image prompt |
| negative_prompt | string | "blurry, low quality, deformed, text, watermark" | Negative prompt |
| width | integer | 1024 | Image width |
| height | integer | 768 | Image height |
| guidance_scale | float | 7.0 | CFG scale |
| num_inference_steps | integer | 40 | Number of inference steps |
| seed | integer | Random | Random seed |
