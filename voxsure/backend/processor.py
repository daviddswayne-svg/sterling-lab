import trimesh
import numpy as np
from PIL import Image
import os

def voxelize(file_path: str, ext: str, resolution: int = 128):
    """
    Converts 3D models (OBJ/STL) or 2D images into a voxel grid.
    Returns a dictionary with voxel positions and colors.
    """
    if ext in ['.obj', '.stl']:
        return voxelize_3d(file_path, resolution)
    elif ext in ['.png', '.jpg', '.jpeg']:
        return voxelize_2d(file_path, resolution)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def voxelize_3d(file_path: str, resolution: int):
    # Load mesh
    mesh = trimesh.load(file_path)
    
    # Voxelize
    # We use a fixed resolution to protect RAM on M1/M3
    voxel_grid = mesh.voxelized(pitch=mesh.extents.max() / resolution)
    
    # Get occupied centers
    centers = voxel_grid.points
    
    # Normalize Z so the object sits on the grid (floor)
    min_z = centers[:, 2].min()
    centers[:, 2] -= min_z
    
    # For a portfolio app, we could add vertex color logic here if available
    # For now, default to a "forensic blue" or "safety orange"
    voxels = []
    for center in centers:
        voxels.append({
            "pos": center.tolist(),
            "color": "#00f2ff" # Neon Cyan
        })
        
    return {
        "type": "3d",
        "voxels": voxels,
        "count": len(voxels)
    }

def voxelize_2d(file_path: str, resolution: int):
    img = Image.open(file_path).convert('RGB')
    # Resize to resolution for voxel density
    img.thumbnail((resolution, resolution))
    
    pixels = np.array(img)
    h, w, _ = pixels.shape
    
    voxels = []
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[y, x]
            # Simple gray check to skip "empty" space (background)
            if r + g + b < 50: # Threshold for "dark/empty"
                continue
                
            # Extrude based on brightness (Z-axis)
            brightness = (int(r) + int(g) + int(b)) / 3
            z_height = int(brightness / 25) # Max 10 blocks high
            
            color = "#{:02x}{:02x}{:02x}".format(r, g, b)
            
            for z in range(z_height):
                voxels.append({
                    "pos": [float(x), float(h - y), float(z)],
                    "color": color
                })
                
    return {
        "type": "2d",
        "voxels": voxels,
        "count": len(voxels)
    }

def compare_voxels(baseline_voxels: list, damage_voxels: list):
    """
    Compares two voxel grids and categorizes them.
    Using coarser rounding (1 decimal) to handle potential floating point noise.
    """
    if not baseline_voxels or not damage_voxels:
        return {"voxels": [], "count": 0, "metrics": {"lost": 0, "added": 0, "matching": 0}}

    # Use spatial hashing for O(N) comparison
    def get_key(pos):
        # Rounding to 1 decimal place (e.g. 0.1mm accuracy) to avoid ghost noise
        return tuple(np.round(pos, 1))

    baseline_set = {get_key(v['pos']): v for v in baseline_voxels}
    damage_set = {get_key(v['pos']): v for v in damage_voxels}

    comparison = []

    # Check for loss or match
    for key, v in baseline_set.items():
        if key not in damage_set:
            comparison.append({
                "pos": v['pos'],
                "color": "#ff3333", # Impact Red
                "status": "lost"
            })
        else:
            comparison.append({
                "pos": v['pos'],
                "color": v.get('color', "#444444"), # Keep original color for matches
                "status": "match"
            })

    # Check for added material
    for key, v in damage_set.items():
        if key not in baseline_set:
            comparison.append({
                "pos": v['pos'],
                "color": "#ff9d00", # Debris Orange
                "status": "added"
            })

    return {
        "voxels": comparison,
        "count": len(comparison),
        "metrics": {
            "lost": sum(1 for v in comparison if v['status'] == 'lost'),
            "added": sum(1 for v in comparison if v['status'] == 'added'),
            "matching": sum(1 for v in comparison if v['status'] == 'match')
        }
    }
