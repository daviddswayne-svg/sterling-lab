# VoxelAudit: 3D Insurance Asset Documentation

A portfolio-grade app that converts images and 3D models into stylistic voxel dioramas for "insurance documentation." It demonstrates end-to-end engineering, 3D rendering, and resource-aware processing on Apple Silicon.

## Core Features
1. **Asset Upload**: Support for Images (PNG/JPG) and 3D files (OBJ/STL).
2. **Voxelization Engine**:
    - Images: Depth-based extrusion to voxels.
    - 3D Models: Grid binning to voxel grids.
3. **Insurance Metadata**: Attach "Claim ID", "Value", and "Risk Level" to the 3D diorama.
4. **M1/M3 Optimization**: A single-worker queue to prevent OOM on high-res models.
5. **Premium UI**: Glassmorphic dashboard with Three.js preview.

## Tech Stack
- **Frontend**: Vanilla HTML/JS, Three.js (Rendering), CSS (Glassmorphism).
- **Backend**: FastAPI (Python), Trimesh (3D processing), Pillow (Image processing).
- **Concurrency**: Simple file-based or memory-based lock for "one-at-a-time" processing.
