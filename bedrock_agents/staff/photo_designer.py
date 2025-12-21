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
            filename = self._queue_comfyui(positive_prompt, category)
            if filename:
                return filename
                
        except Exception as e:
            print(f"⚠️ Generation Failed: {e}")

        # 4. Fallback if generation failed or returned None
        print(f"🔄 Using Stock Fallback for {category}...")
        return self._get_fallback_image(category)

    def _queue_comfyui(self, positive_prompt, category):
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
            # 2. Queue Prompt via API
            host_parts = COMFYUI_HOST.replace("http://", "").replace("https://", "").split(":")
            conn_host = host_parts[0]
            conn_port = int(host_parts[1]) if len(host_parts) > 1 else 8188
            
            headers = {"Content-Type": "application/json"}
            
            # Submit the prompt and get prompt_id (allow time for SSH tunnel latency)
            conn = http.client.HTTPConnection(conn_host, conn_port, timeout=120)
            prompt_id = None
            
            try:
                conn.request("POST", "/prompt", json.dumps(payload), headers)
                response = conn.getresponse()
                response_data = response.read()
                
                if response.status != 200:
                    print(f"⚠️ ComfyUI Error ({response.status}): {response_data.decode('utf-8')}")
                    conn.close()
                    return self._get_fallback_image(category)
                
                # Extract prompt_id from response
                result = json.loads(response_data)
                prompt_id = result.get('prompt_id')
                conn.close()
                
            except TimeoutError:
                # SSH tunnel latency caused timeout, but prompt likely queued successfully
                # We'll poll /history to find the most recent prompt
                print("   ⏰ Initial response timed out (SSH tunnel latency)")
                print("   🔍 Checking history for recent prompt...")
                conn.close()
                
                try:
                    # Get recent history to find our prompt
                    time.sleep(2)  # Give it a moment to appear in history
                    conn = http.client.HTTPConnection(conn_host, conn_port, timeout=10)
                    conn.request("GET", "/history")
                    hist_response = conn.getresponse()
                    all_history = json.loads(hist_response.read())
                    conn.close()
                    
                    # Get the most recent prompt_id
                    if all_history:
                        # History is a dict with prompt_ids as keys
                        prompt_ids = list(all_history.keys())
                        if prompt_ids:
                            prompt_id = prompt_ids[-1]  # Most recent
                            print(f"   ✅ Found recent prompt: {prompt_id}")
                except Exception as hist_error:
                    print(f"   ⚠️ Could not retrieve history: {hist_error}")
            
            if not prompt_id:
                print("⚠️ No prompt_id available")
                return self._get_fallback_image(category)
            
            print(f"   ⏳ Rendering... (prompt_id: {prompt_id}, max 120s)")
            
            # 3. Poll /history endpoint until the prompt is complete
            start_time = time.time()
            image_data = None
            
            while time.time() - start_time < 120:
                try:
                    # Check history for this prompt
                    conn = http.client.HTTPConnection(conn_host, conn_port, timeout=10)
                    conn.request("GET", f"/history/{prompt_id}")
                    hist_response = conn.getresponse()
                    hist_data = json.loads(hist_response.read())
                    conn.close()
                    
                    if prompt_id in hist_data:
                        prompt_history = hist_data[prompt_id]
                        
                        # Check if completed
                        if prompt_history.get('status', {}).get('completed', False):
                            # Extract image filename from outputs
                            outputs = prompt_history.get('outputs', {})
                            
                            # Find the SaveImage node output (node "9" in our workflow)
                            for node_id, node_output in outputs.items():
                                if 'images' in node_output:
                                    images = node_output['images']
                                    if images:
                                        # Get the first image
                                        img_info = images[0]
                                        filename = img_info['filename']
                                        subfolder = img_info.get('subfolder', '')
                                        img_type = img_info.get('type', 'output')
                                        
                                        print(f"   ✅ Image generated: {filename}")
                                        
                                        # 4. Fetch image via /view endpoint
                                        view_params = f"filename={filename}&type={img_type}"
                                        if subfolder:
                                            view_params += f"&subfolder={subfolder}"
                                        
                                        conn = http.client.HTTPConnection(conn_host, conn_port, timeout=30)
                                        conn.request("GET", f"/view?{view_params}")
                                        img_response = conn.getresponse()
                                        
                                        if img_response.status == 200:
                                            image_data = img_response.read()
                                            conn.close()
                                            
                                            # Save to assets directory
                                            dest_filename = "bedrock_latest.png"
                                            dest_path = os.path.join(ASSETS_DIR, dest_filename)
                                            
                                            with open(dest_path, 'wb') as f:
                                                f.write(image_data)
                                            
                                            print(f"   ✅ Image saved to {dest_path}")
                                            return f"/assets/{dest_filename}"
                                        else:
                                            conn.close()
                                            print(f"⚠️ Failed to fetch image: {img_response.status}")
                                            break
                            
                            # If we got here, outputs didn't have images
                            print("⚠️ Prompt completed but no images found in output")
                            break
                        
                        # Check if there was an error
                        if 'status' in prompt_history and 'status_str' in prompt_history['status']:
                            status_str = prompt_history['status']['status_str']
                            if 'error' in status_str.lower():
                                print(f"⚠️ ComfyUI execution error: {status_str}")
                                break
                    
                    # Not complete yet, wait and retry
                    time.sleep(3)
                    
                except Exception as poll_error:
                    print(f"⚠️ Polling error: {poll_error}")
                    time.sleep(3)
            
            # If we got here without image_data, use fallback
            if not image_data:
                print("⚠️ Timeout or error during image generation")
                return self._get_fallback_image(category)
            
        except Exception as e:
            print(f"⚠️ ComfyUI Connection Failed: {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_image(category)

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
