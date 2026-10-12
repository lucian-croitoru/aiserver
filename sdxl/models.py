
from diffusers import (StableDiffusionXLPipeline,
                       StableDiffusionXLImg2ImgPipeline)
import random
import torch
import logging
import cv2
import numpy as np
from PIL import Image

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

SDXL_MODEL_BASE = "stabilityai/stable-diffusion-xl-base-1.0"
SDXL_MODEL_REFINER = "stabilityai/stable-diffusion-xl-refiner-1.0"
SDXL_MODEL_UPSCALER = "stabilityai/stable-diffusion-x4-upscaler"
SDXL_MODEL_INPAINT = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"

MAX_SEED = 2**32 - 1
WIDTH = 1024
HEIGHT = 768
GUIDANCE = 7
STEPS_BASE = 20
STEPS_REFINER = 20

NEGATIVE_PROMPT = "blurry, low quality, deformed, text, watermark"


logger = logging.getLogger(__name__)


class ModelLoader:
    DESTINATION = None  # Specify CUDA destination in child classes
    MODEL = None        # Initialize empty list in child classes

    def __init__(self):
        if not self.MODEL:
            logger.info(f"Initializing {__class__}...")
            self.MODEL.append(self.init_model().to(self.DESTINATION))
            self.optimize_model()
        self.model = self.MODEL[0]

    def init_model(self):
        raise NotImplementedError

    def optimize_model(self):
        if self.MODEL:
            self.MODEL[0].enable_attention_slicing()
            self.MODEL[0].vae.enable_slicing()
            self.MODEL[0].enable_xformers_memory_efficient_attention() # transformers >=5.x: works on Ampere and more recent GPUs


class SDXLBase(ModelLoader):
    # 7.5 GB at fp16
    DESTINATION = "cuda:2"
    MODEL = []

    def __init__(self):
        super().__init__()

    def init_model(self):
        model = StableDiffusionXLPipeline.from_pretrained(
            SDXL_MODEL_BASE,
            variant="fp16",
            use_safetensors=True,
            torch_dtype=torch.float16)
        return model


class SDXLRefiner(ModelLoader):
    # 6.5 GB at fp16
    DESTINATION = "cuda:3"
    MODEL = []

    def __init__(self):
        super().__init__()

    def init_model(self):
        model = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            SDXL_MODEL_REFINER,
            variant="fp16",
            use_safetensors=True,
            torch_dtype=torch.float16)
        return model



def init_models():
    # Just init the models as they are singletons
    SDXLBase()
    SDXLRefiner()


def upscale_image(image, scale=2):
    if not isinstance(image, Image.Image):
        raise TypeError(f"Expected PIL image, got {type(image)}")
    img = np.array(image)
    up = cv2.resize(
        img,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_LANCZOS4
    )
    return Image.fromarray(up)


def generate_image(prompt: str,
                   negative_prompt: str = NEGATIVE_PROMPT,
                   width: int = WIDTH,
                   height: int = HEIGHT, 
                   guidance_scale: float = GUIDANCE,
                   num_inference_steps: int = STEPS_BASE,
                   seed: int = None):
    
    if seed is None:
        seed = random.randint(0, MAX_SEED)
    
    base_model = SDXLBase()
    generator = torch.Generator(device=base_model.DESTINATION).manual_seed(seed)
    base_model = base_model.model
    refiner_model = SDXLRefiner().model
    
    logger.info("Generating base image...")
    base_image = base_model(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        guidance_scale=guidance_scale,
        num_inference_steps=num_inference_steps,
        generator=generator
    ).images[0]
    # base_image.save("base.png")
 
    logger.info("Refining image details...")
    refined_image = refiner_model(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=base_image,
        guidance_scale=guidance_scale,
        num_inference_steps=STEPS_REFINER,
        strength=0.45
    ).images[0]
    # refined_image.save("refined.png")
 
    # logger.info("Upscaling...")
    # upscaled_image = upscale_image(refined_image, 2)
    # upscaled_image.save("upscaled.png")
    # return upscaled_image, seed
    
    return refined_image, seed