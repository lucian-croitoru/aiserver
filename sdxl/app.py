import base64
import io
import time
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import traceback
from uuid import uuid4

from sdxl.models import (NEGATIVE_PROMPT,
                         WIDTH,
                         HEIGHT,
                         GUIDANCE,
                         STEPS_BASE,
                         generate_image)


# Initialize FastAPI app
app = FastAPI(title="SDXL Image Generation API", description="OpenAI-compatible image generation API using Stable Diffusion XL")

# Global model instances
base_model = None
refiner_model = None

class ImageRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = NEGATIVE_PROMPT
    width: Optional[int] = WIDTH
    height: Optional[int] = HEIGHT
    guidance_scale: Optional[float] = GUIDANCE
    num_inference_steps: Optional[int] = STEPS_BASE
    seed: Optional[int] = None
    response_type: Literal["file", "b64_json"] = "file"

class ImageResponse(BaseModel):
    created: int
    data: list

@app.get("/")
async def root():
    return {"message": "SDXL Image Generation API - Use /v1/images/generations endpoint"}

@app.post("/v1/images/generations")
async def generate_images(request: ImageRequest):
    try:
        # Generate the image
        image, seed = generate_image(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or NEGATIVE_PROMPT,
            width=request.width,
            height=request.height,
            guidance_scale=request.guidance_scale,
            num_inference_steps=request.num_inference_steps,
            seed=request.seed
        )
        
        # Encode image to base64 (used by both paths)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        if request.response_type == "b64_json":
            image_b64 = base64.b64encode(buffer.getvalue()).decode()
            return ImageResponse(
                created=int(time.time()),
                data=[{"b64_json": image_b64, "seed": seed}]
            )

        # Default: return downloadable file
        return Response(
            content=buffer.getvalue(),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{uuid4()}_seed_{seed}.png"'}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

# Add a simple health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
