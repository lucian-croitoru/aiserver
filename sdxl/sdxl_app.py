import base64
import io
import random
import time
from typing import Optional

import torch
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel

MAX_SEED = 2**32 - 1
MODEL_BASE = "stabilityai/stable-diffusion-xl-base-1.0"
MODEL_REFINER = "stabilityai/stable-diffusion-xl-refiner-1.0"
WIDTH = 1024
HEIGHT = 768
GUIDANCE = 7.0
STEPS_BASE = 40
STEPS_REFINER = 40

NEGATIVE_PROMPT = "blurry, low quality, deformed, text, watermark"

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

class ImageResponse(BaseModel):
    created: int
    data: list

def load_models():
    global base_model, refiner_model
    if base_model is None and refiner_model is None:
        print("Loading SDXL Base model...")
        base_model = StableDiffusionXLPipeline.from_pretrained(
            MODEL_BASE,
            variant="fp16",
            use_safetensors=True,
            torch_dtype=torch.float16,
        ).to("cuda:2")

        base_model.enable_attention_slicing()
        base_model.enable_vae_slicing()
        base_model.enable_xformers_memory_efficient_attention()

        print("Loading SDXL Refiner model...")
        refiner_model = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            MODEL_REFINER,
            variant="fp16",
            use_safetensors=True,
            torch_dtype=torch.float16,
        ).to("cuda:3")

        refiner_model.enable_attention_slicing()
        refiner_model.enable_vae_slicing()
        refiner_model.enable_xformers_memory_efficient_attention()

def generate_image(prompt: str, negative_prompt: str = NEGATIVE_PROMPT, width: int = WIDTH, height: int = HEIGHT, 
                   guidance_scale: float = GUIDANCE, num_inference_steps: int = STEPS_BASE, seed: int = None):
    load_models()
    
    if seed is None:
        seed = random.randint(0, MAX_SEED)
    
    generator = torch.Generator(device="cuda:0").manual_seed(seed)
    
    print("Generating base image...")
    base_image = base_model(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        guidance_scale=guidance_scale,
        num_inference_steps=num_inference_steps,
        generator=generator
    ).images[0]
    base_image.save("base.png")
    
    print("Refining image details...")
    final_image = refiner_model(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=base_image,
        guidance_scale=guidance_scale,
        num_inference_steps=STEPS_REFINER,
    ).images[0]
    final_image.save("refined.png")
    
    return final_image

@app.get("/")
async def root():
    return {"message": "SDXL Image Generation API - Use /v1/images/generations endpoint"}

@app.post("/v1/images/generations")
async def generate_images(request: ImageRequest):
    try:
        # Generate the image
        image = generate_image(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or NEGATIVE_PROMPT,
            width=request.width,
            height=request.height,
            guidance_scale=request.guidance_scale,
            num_inference_steps=request.num_inference_steps,
            seed=request.seed
        )
        
        # Convert image to base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        image_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Return response in OpenAI format
        response = ImageResponse(
            created=int(time.time()),
            data=[{"b64_json": image_b64}]
        )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add a simple health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
