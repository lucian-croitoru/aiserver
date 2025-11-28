import random
import torch
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline


MAX_SEED = 2**32 - 1
MODEL_BASE = "stabilityai/stable-diffusion-xl-base-1.0"
MODEL_REFINER = "stabilityai/stable-diffusion-xl-refiner-1.0"
WIDTH = 1024
HEIGHT = 768
GUIDANCE = 7.0
STEPS_BASE = 40
STEPS_REFINER = 40

NEGATIVE_PROMPT = "blurry, low quality, deformed, text, watermark"
PROMPT = """
         A character portait of a bearded warrior from a RPG / D&D style game, armed with a greatsword.
         Style: detailed, fine pencil illustration with dynamic lighting.
         The haracter is facing forward, having a determined, slightly angry face, and wearing armor.
         """



SEED=random.randint(0, MAX_SEED)
generator = torch.Generator(device="cuda:0").manual_seed(SEED)


print("Loading SDXL Base model...")

base = StableDiffusionXLPipeline.from_pretrained(
    MODEL_BASE,
    variant="fp16",
    use_safetensors=True,
    torch_dtype=torch.float16,
).to("cuda:0")

base.enable_attention_slicing()
base.enable_vae_slicing()
base.enable_xformers_memory_efficient_attention()

print("Generating base image...")
base_image = base(
    prompt=PROMPT,
    negative_prompt=NEGATIVE_PROMPT,
    width=WIDTH,
    height=HEIGHT,
    guidance_scale=GUIDANCE,
    num_inference_steps=STEPS_BASE,
    generator=generator
).images[0]
base_image.save("base.png")


# Delete base model to save VRAM
del base


print("Loading SDXL Refiner model...")
refiner = StableDiffusionXLImg2ImgPipeline.from_pretrained(
    MODEL_REFINER,
    variant="fp16",
    use_safetensors=True,
    torch_dtype=torch.float16,
).to("cuda:1")

refiner.enable_attention_slicing()
refiner.enable_vae_slicing()
refiner.enable_xformers_memory_efficient_attention()


print("Refining image details...")
final_image = refiner(
    prompt=PROMPT,
    negative_prompt=NEGATIVE_PROMPT,
    image=base_image,
    guidance_scale=GUIDANCE,
    num_inference_steps=STEPS_REFINER,
).images[0]
final_image.save("refined.png")
print("Done!")
