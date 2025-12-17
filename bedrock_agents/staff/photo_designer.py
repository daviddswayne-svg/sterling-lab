import json
import os
import time
import requests
import http.client
import shutil
import random
import ollama
from ..config import OLLAMA_HOST, COMFYUI_HOST, MODELS, ASSETS_DIR, DATA_DIR

class PhotoDesigner:
    def __init__(self):
        self.client = ollama.Client(host=OLLAMA_HOST)
        self.model = MODELS["designer"]
        
        # Load prompts
        prompts_path = os.path.join(DATA_DIR, "prompts.json")
        with open(prompts_path, "r") as f:
            self.prompts = json.load(f)["photo_designer"]

    def generate_image(self, theme, concept):
        """Generates an image via ComfyUI based on the theme and concept."""
        print(f"🎨 Photo Designer ({self.model}) is composing an image for '{theme}'...")
        
        # 1. Determine Category (Home or Auto)
        category = "Home" if "Home" in theme or "House" in theme else "Auto"
        if "Auto" not in theme and "Home" not in theme:
             # Fallback logic if theme implies one
             if "Car" in theme or "Drive" in theme: category = "Auto"
        
        guideline = self.prompts["guidelines"].get(category, self.prompts["guidelines"]["Home"])
        
        # 2. Refine Prompt with LLM
        prompt_instruction = f"""
        {self.prompts['system_prompt']}
        
        Input Concept: {concept}
        Category Context: {category} - {guideline}
        
        Task: 
        1. Write a detailed, comma-separated image generation prompt. Focus on lighting, texture, and composition. No people.
        2. Create a short, punchy, 2-3 word marketing slogan relevant to the concept (e.g., "SECURE FUTURE", "SAFE HOME").
        
        Output Format:
        Positive Prompt: [Your detailed prompt here]
        Slogan: [Your slogan here]
        """
        
        try:
            response = self.client.chat(model=self.model, messages=[
                {'role': 'user', 'content': prompt_instruction}
            ])
            content = response['message']['content'].strip()
            
            # Parse output
            positive_prompt = ""
            slogan = ""
            
            for line in content.split('\n'):
                if line.startswith("Positive Prompt:"):
                    positive_prompt = line.replace("Positive Prompt:", "").strip()
                elif line.startswith("Slogan:"):
                    slogan = line.replace("Slogan:", "").strip().replace('"', '')
            
            # Fallback parsing if strict format fails
            if not positive_prompt: positive_prompt = content
            
            # Enhance prompt with slogan for Flux
            if slogan:
                positive_prompt += f', the text "{slogan}" is written in large, bold, modern, cinematic 3D typography superimposed in the center'
            
            print(f"   Category: {category}")
            print(f"   Slogan: {slogan}")
            print(f"   Prompt: {positive_prompt[:100]}...")
            
            # 3. Queue to ComfyUI
            filename = self._queue_comfyui(positive_prompt)
            if filename:
                return filename
                
        except Exception as e:
            print(f"⚠️ Generation Failed: {e}")

        # 4. Fallback if generation failed or returned None
        print(f"🔄 Using Stock Fallback for {category}...")
        return self._get_fallback_image(category)

    def _queue_comfyui(self, positive_prompt):
        """Standard ComfyUI API Workflow."""
        # ... (Existing ComfyUI logic) ...
        # Generating a random seed
        seed = random.randint(1, 1000000000)
        
        # Flux.1 [dev] Workflow
        payload = {
            "prompt": {
                "3": {
                    "class_type": "KSamplerSelect",
                    "inputs": {"sampler_name": "euler"}
                },
                "4": {
                    "class_type": "BasicScheduler",
                    "inputs": {
                        "scheduler": "simple",
                        "steps": 20,
                        "denoise": 1.0,
                        "model": ["10", 0]
                    }
                },
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {"width": 1024, "height": 1024, "batch_size": 1}
                },
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": positive_prompt,
                        "clip": ["11", 0]
                    }
                },
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": self.prompts["negative_prompt"], # Flux doesn't use neg prompt much, but BasicGuider takes it
                        "clip": ["11", 0]
                    }
                },
                "8": {
                    "class_type": "VAEDecode",
                    "inputs": {"samples": ["13", 0], "vae": ["12", 0]}
                },
                "9": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": "Bedrock_Flux_Gen",
                        "images": ["8", 0]
                    }
                },
                "10": {
                    "class_type": "UNETLoader",
                    "inputs": {"unet_name": "flux1-dev-fp8.safetensors", "weight_dtype": "default"}
                },
                "11": {
                    "class_type": "DualCLIPLoader",
                    "inputs": {
                        "clip_name1": "t5xxl_fp16.safetensors",
                        "clip_name2": "clip_l.safetensors",
                        "type": "flux"
                    }
                },
                "12": {
                    "class_type": "VAELoader",
                    "inputs": {"vae_name": "ae.safetensors"}
                },
                "13": {
                    "class_type": "SamplerCustomAdvanced",
                    "inputs": {
                        "noise": ["14", 0],
                        "guider": ["15", 0],
                        "sampler": ["3", 0],
                        "sigmas": ["4", 0],
                        "latent_image": ["5", 0]
                    }
                },
                "14": {
                    "class_type": "RandomNoise",
                    "inputs": {"noise_seed": random.randint(1, 1000000000)}
                },
                "15": {
                    "class_type": "BasicGuider",
                    "inputs": {
                        "model": ["10", 0],
                        "conditioning": ["6", 0]
                    }
                }
            }
        }
        
        try:
            # 2. Queue Prompt
            # Use COMFYUI_HOST for connection details
            host_parts = COMFYUI_HOST.replace("http://", "").split(":")
            conn_host = host_parts[0]
            conn_port = int(host_parts[1]) if len(host_parts) > 1 else 80 # Default to 80 if no port
            
            conn = http.client.HTTPConnection(conn_host, conn_port)
            p = payload # The entire workflow is the payload for the /prompt endpoint
            headers = {"Content-Type": "application/json"}
            conn.request("POST", "/prompt", json.dumps(p), headers)
            response = conn.getresponse()
            
            if response.status != 200:
                print(f"⚠️ ComfyUI Error: {response.read().decode('utf-8')}")
                return self._get_fallback_image(category)
            
            # 3. Wait/Poll for Image
            # Since we don't have websocket here, we'll watch the output dir for a new file
            # Night Shift Output Dir (User configured)
            # This path should ideally be configurable or derived from ComfyUI config
            output_dir = "/Users/daviddswayne/.gemini/antigravity/scratch/night_shift_studio/output" 
            
            if not os.path.exists(output_dir):
                print(f"⚠️ ComfyUI output directory not found: {output_dir}")
                return self._get_fallback_image(category)

            print("   ⏳ Rendering (Waiting up to 120s)...")
            
            # Simple polling: check for files matching prefix created > now
            file_prefix = "Bedrock_Flux_Gen"
            start_time = time.time()
            found_file = None
            
            while time.time() - start_time < 120:
                # Look for files matching prefix
                candidates = [f for f in os.listdir(output_dir) if f.startswith(file_prefix)]
                if candidates:
                    # Sort by modification time, newest first
                    candidates.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
                    newest = candidates[0]
                    # Check if it was created after we submitted
                    if os.path.getmtime(os.path.join(output_dir, newest)) > start_time:
                        found_file = os.path.join(output_dir, newest)
                        break
                time.sleep(2)
                
            if found_file:
                # Copy to Dashboard Assets
                dest_filename = f"bedrock_latest.png"
                dest_path = os.path.join(ASSETS_DIR, dest_filename)
                
                # Use shutil copy
                shutil.copy(found_file, dest_path)
                    
                print(f"✅ Image Rendered and Saved to {dest_path}")
                # Return absolute path for HTML (web root view)
                return f"/assets/{dest_filename}" 
            else:
                print("⚠️ Timeout waiting for image.")
                return self._get_fallback_image(category)
            
        except Exception as e:
            print(f"⚠️ ComfyUI Connection Failed (is it running?): {e}")
            return None

    def _get_fallback_image(self, category):
        """Pick a random image from the stock directory."""
        stock_dir = os.path.join(ASSETS_DIR, "stock", category)
        if os.path.exists(stock_dir):
            files = [f for f in os.listdir(stock_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if files:
                selected = random.choice(files)
                # Return absolute path
                return f"/assets/stock/{category}/{selected}"
        
        return "/assets/placeholder.jpg"


if __name__ == "__main__":
    designer = PhotoDesigner()
    designer.generate_image("Home Protection", "A secure cozy house at night")
