
from diffusers import (StableDiffusionXLPipeline,
                       StableDiffusionXLImg2ImgPipeline,
                       StableDiffusionLatentUpscalePipeline)
import random
import torch
import logging


SDXL_MODEL_BASE = "stabilityai/stable-diffusion-xl-base-1.0"
SDXL_MODEL_REFINER = "stabilityai/stable-diffusion-xl-refiner-1.0"
SDXL_MODEL_UPSCALER = "stabilityai/stable-diffusion-x4-upscaler"

MAX_SEED = 2**32 - 1
WIDTH = 1024
HEIGHT = 768
GUIDANCE = 7.0
STEPS_BASE = 40
STEPS_REFINER = 40

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
            self.MODEL[0].enable_vae_slicing()
            self.MODEL[0].enable_xformers_memory_efficient_attention()


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


class SDXLEditor(ModelLoader):
    # 7.5 GB at fp16
    DESTINATION = "cuda:3"
    MODEL = []

    def __init__(self):
        super().__init__()

    def init_model(self):
        model = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            SDXL_MODEL_BASE,
            variant="fp16",
            use_safetensors=True,
            torch_dtype=torch.float16)
        return model


class SDXLRefiner(ModelLoader):
    # 6.5 GB at fp16
    DESTINATION = "cuda:1"
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


class SDXLUpscaler(ModelLoader):
    # 2.4 GB at fp16
    DESTINATION = "cuda:0"
    MODEL = []

    def __init__(self):
        super().__init__()

    def init_model(self):
        model = StableDiffusionLatentUpscalePipeline.from_pretrained(
            SDXL_MODEL_UPSCALER,
            variant="fp16",
            use_safetensors=True,
            torch_dtype=torch.float16)
        return model


def init_models():
    # Just init the models as they are singletons
    SDXLBase()
    SDXLEditor()
    SDXLRefiner()
    SDXLUpscaler()


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
