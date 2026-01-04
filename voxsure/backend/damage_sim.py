import trimesh
import numpy as np
import os

def create_damaged_version(input_path, output_path):
    print(f"🛠️  Loading {input_path}...")
    mesh = trimesh.load(input_path)
    
    # Define a bounding box for the "damage"
    # Let's slice off a chunk of the tail or a rotor
    # We'll use a boolean subtraction or just filter faces
    
    print("🧨 Simulating impact damage...")
    center = mesh.bounds.mean(axis=0)
    size = mesh.extents.max()
    
    # Target the tail (assuming X is long axis)
    sphere_center = center + [size*0.35, 0, 0]
    radius = size * 0.15
    
    # Filter faces
    face_centers = mesh.triangles_center
    dist = np.linalg.norm(face_centers - sphere_center, axis=1)
    keep_mask = dist > radius
    
    # Create NEW mesh to avoid tracking/caching issues
    damaged_mesh = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces[keep_mask])
    damaged_mesh.remove_unreferenced_vertices()
    
    print(f"✅ Damage simulated. Removed {np.sum(~keep_mask)} faces.")
    damaged_mesh.export(output_path)
    print(f"📦 Final Size: {os.path.getsize(output_path)} bytes")

if __name__ == "__main__":
    src = "/Users/daviddswayne/.gemini/antigravity/scratch/voxel_projects/voxel_archive/voxel_project/Helicopter.stl"
    dsts = [
        "/Users/daviddswayne/.gemini/antigravity/scratch/voxel_projects/voxel_archive/voxel_project/Helicopter_damaged.stl",
        "/Users/daviddswayne/.gemini/antigravity/scratch/voxel_studio/client/Helicopter_damaged.stl",
        "/Users/daviddswayne/.gemini/antigravity/scratch/voxsure/app/Helicopter_damaged.stl",
        "/Users/daviddswayne/.gemini/antigravity/scratch/Helicopter_damaged.stl"
    ]
    
    if os.path.exists(src):
        for dst in dsts:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                create_damaged_version(src, dst)
                print(f"✅ Saved to: {dst}")
            except Exception as e:
                print(f"❌ Failed to save to {dst}: {e}")
    else:
        print(f"❌ Source file not found: {src}")
