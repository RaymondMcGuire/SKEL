@echo off
cd ..

REM ============================================================
REM Explore SKEL Body Shape Parameters
REM Uncomment one line below to run different configurations
REM ============================================================

REM Option 1: Show all predefined body shapes (no export)
REM uv run python examples/explore_body_shape.py --gender female

REM Option 2: Export all predefined body shapes as meshes
REM uv run python examples/explore_body_shape.py --gender female --export_meshes

REM Option 2b: Export with subdivision for higher detail (recommended: --subdivide 1 or 2)
REM Level 1: ~4x faces, Level 2: ~16x faces, Level 3: ~64x faces
REM uv run python examples/explore_body_shape.py --gender female --export_meshes --subdivide 1

REM Option 3: Male body shapes
REM uv run python examples/explore_body_shape.py --gender male --export_meshes

REM Option 4: Generate 60kg body (average weight, beta[1]=0.0)
REM uv run python examples/explore_body_shape.py --gender female --custom_weight 0.0 --export_meshes --subdivide 1

REM Option 5: Generate 100kg body (heavy, beta[1]=-1.8)
REM NOTE: Negative beta values correspond to LARGER body mass
REM uv run python examples/explore_body_shape.py --gender female --custom_weight -1.8 --export_meshes --subdivide 1

REM Option 6: Generate 130kg body (very heavy, beta[1]=-2.0)
uv run python examples/explore_body_shape.py --gender male --custom_height 0.0 --custom_weight -2.5 --export_meshes

REM Option 7: Generate tall heavy person (height=1.5, weight=-2.0)
REM NOTE: Positive height → taller, Negative weight → heavier
REM uv run python examples/explore_body_shape.py --gender female --custom_height 1.5 --custom_weight -2.0 --export_meshes --subdivide 1

REM Option 8: Generate short thin person (height=-1.5, weight=2.0)
REM NOTE: Negative height → shorter, Positive weight → thinner
REM uv run python examples/explore_body_shape.py --gender female --custom_height -1.5 --custom_weight 2.0 --export_meshes --subdivide 1

REM Option 9: Visualize in AITViewer (requires GUI)
REM uv run python examples/explore_body_shape.py --gender female --visualize

pause
