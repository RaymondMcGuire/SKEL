"""
Explore SKEL body shape parameters (betas)
Generate human body models with different weights and heights

Usage:
    python examples/explore_body_shape.py --gender female --export_meshes

Arguments:
    --gender: Gender (female/male)
    --export_meshes: Whether to export mesh files
    --visualize: Whether to visualize in AITViewer
"""

import argparse
import os
import torch
from skel.skel_model import SKEL
import trimesh
import numpy as np

# Predefined body shape configurations
# Format: (name, beta[0](height), beta[1](weight), description)
BODY_SHAPES = {
    'very_thin_short': (-1.5, -2.0, 'Very thin & short (~45kg, ~155cm)'),
    'thin_short': (-1.0, -1.5, 'Thin & short (~50kg, ~160cm)'),
    'average_short': (-1.0, 0.0, 'Average weight, short (~60kg, ~160cm)'),

    'very_thin_avg': (0.0, -2.0, 'Very thin, average height (~45kg, ~165cm)'),
    'thin_avg': (0.0, -1.0, 'Thin, average height (~55kg, ~165cm)'),
    'average': (0.0, 0.0, 'Average body type (default, ~60kg, ~165cm)'),
    'heavy_avg': (0.0, 1.0, 'Heavy, average height (~80kg, ~165cm)'),
    'very_heavy_avg': (0.0, 2.0, 'Very heavy, average height (~100-120kg, ~165cm)'),

    'thin_tall': (1.5, -1.0, 'Thin & tall (~60kg, ~175cm)'),
    'average_tall': (1.5, 0.0, 'Average weight, tall (~70kg, ~175cm)'),
    'heavy_tall': (1.5, 1.0, 'Heavy & tall (~90kg, ~175cm)'),
    'very_heavy_tall': (1.5, 2.0, 'Very heavy & tall (~110-130kg, ~175cm)'),
}

def create_body_with_shape(skel_model, beta_height, beta_weight, device='cpu'):
    """
    Create a human body model with specified shape

    Args:
        skel_model: SKEL model instance
        beta_height: Height coefficient (beta[0])
        beta_weight: Weight coefficient (beta[1])
        device: Compute device

    Returns:
        skel_output: SKEL model output
        betas: Beta parameters used
    """
    # Set beta parameters
    betas = torch.zeros(1, 10).to(device)
    betas[0, 0] = beta_height  # Height
    betas[0, 1] = beta_weight  # Weight

    # T-pose
    pose = torch.zeros(1, skel_model.num_q_params).to(device)
    trans = torch.zeros(1, 3).to(device)

    # Forward pass
    skel_output = skel_model(pose, betas, trans)

    return skel_output, betas

def estimate_body_measurements(skel_output):
    """
    Estimate body measurements (height, arm span, etc.)

    Args:
        skel_output: SKEL model output

    Returns:
        dict: Measurement values
    """
    vertices = skel_output.skin_verts[0].cpu().numpy()

    # Calculate height (Y-axis range)
    height = vertices[:, 1].max() - vertices[:, 1].min()

    # Calculate shoulder width (approximate X-axis shoulder range)
    # Use vertices with Y-coordinate near shoulder
    shoulder_height = vertices[:, 1].max() - 0.3  # Shoulder is about 30cm below top
    shoulder_verts = vertices[np.abs(vertices[:, 1] - shoulder_height) < 0.1]
    if len(shoulder_verts) > 0:
        shoulder_width = shoulder_verts[:, 0].max() - shoulder_verts[:, 0].min()
    else:
        shoulder_width = 0

    # Calculate arm span (X-axis range)
    arm_span = vertices[:, 0].max() - vertices[:, 0].min()

    return {
        'height': height,
        'shoulder_width': shoulder_width,
        'arm_span': arm_span,
    }

def main():
    parser = argparse.ArgumentParser(description='Explore SKEL body shape parameters')
    parser.add_argument('--gender', type=str, default='female', choices=['female', 'male'],
                       help='Gender')
    parser.add_argument('--export_meshes', action='store_true',
                       help='Export mesh files to output/body_shapes/')
    parser.add_argument('--visualize', action='store_true',
                       help='Visualize in AITViewer (requires GUI)')
    parser.add_argument('--custom_height', type=float, default=None,
                       help='Custom height coefficient (beta[0], range -2 to 2)')
    parser.add_argument('--custom_weight', type=float, default=None,
                       help='Custom weight coefficient (beta[1], range -2 to 2)')

    args = parser.parse_args()

    device = 'cpu'

    # Create SKEL model
    print(f'Loading SKEL model for {args.gender}...')
    skel = SKEL(gender=args.gender).to(device)

    # If custom parameters specified
    if args.custom_height is not None or args.custom_weight is not None:
        height = args.custom_height if args.custom_height is not None else 0.0
        weight = args.custom_weight if args.custom_weight is not None else 0.0

        print(f'\nGenerating custom body shape:')
        print(f'  Beta[0] (height): {height:.2f}')
        print(f'  Beta[1] (weight): {weight:.2f}')

        output, betas = create_body_with_shape(skel, height, weight, device)
        measurements = estimate_body_measurements(output)

        print(f'\nEstimated measurements:')
        print(f'  Height: {measurements["height"]:.3f} m ({measurements["height"]*100:.1f} cm)')
        print(f'  Shoulder width: {measurements["shoulder_width"]:.3f} m ({measurements["shoulder_width"]*100:.1f} cm)')
        print(f'  Arm span: {measurements["arm_span"]:.3f} m ({measurements["arm_span"]*100:.1f} cm)')

        if args.export_meshes:
            output_dir = 'output/body_shapes'
            os.makedirs(output_dir, exist_ok=True)

            filename = f'{args.gender}_h{height:.1f}_w{weight:.1f}'
            skin_path = os.path.join(output_dir, f'{filename}_skin.obj')
            skel_path = os.path.join(output_dir, f'{filename}_skel.obj')

            skin_mesh = trimesh.Trimesh(
                vertices=output.skin_verts[0].cpu().numpy(),
                faces=skel.skin_f.cpu().numpy()
            )
            skel_mesh = trimesh.Trimesh(
                vertices=output.skel_verts[0].cpu().numpy(),
                faces=skel.skel_f.cpu().numpy()
            )

            skin_mesh.export(skin_path)
            skel_mesh.export(skel_path)
            print(f'\nMeshes saved to {output_dir}/')

    else:
        # Generate all predefined body shapes
        print(f'\nGenerating predefined body shape variations...\n')
        print(f'{"Name":<20} {"Height β":<10} {"Weight β":<10} {"Description":<40} {"Est. Height":<12}')
        print('-' * 100)

        outputs = {}
        for name, (h, w, desc) in BODY_SHAPES.items():
            output, betas = create_body_with_shape(skel, h, w, device)
            measurements = estimate_body_measurements(output)

            height_cm = measurements['height'] * 100
            print(f'{name:<20} {h:<10.1f} {w:<10.1f} {desc:<40} {height_cm:<12.1f} cm')

            outputs[name] = output

            # Export meshes
            if args.export_meshes:
                output_dir = 'output/body_shapes'
                os.makedirs(output_dir, exist_ok=True)

                skin_path = os.path.join(output_dir, f'{args.gender}_{name}_skin.obj')
                skel_path = os.path.join(output_dir, f'{args.gender}_{name}_skel.obj')

                skin_mesh = trimesh.Trimesh(
                    vertices=output.skin_verts[0].cpu().numpy(),
                    faces=skel.skin_f.cpu().numpy()
                )
                skel_mesh = trimesh.Trimesh(
                    vertices=output.skel_verts[0].cpu().numpy(),
                    faces=skel.skel_f.cpu().numpy()
                )

                skin_mesh.export(skin_path)
                skel_mesh.export(skel_path)

        if args.export_meshes:
            print(f'\nAll meshes saved to output/body_shapes/')

    # Visualize (if requested)
    if args.visualize:
        try:
            from aitviewer.viewer import Viewer
            from skel.viewer.renderables.skel import SKELSequence

            print('\nLaunching AITViewer...')
            v = Viewer()

            # Add several representative body shapes to scene
            representative_shapes = ['very_thin_avg', 'average', 'heavy_avg', 'very_heavy_avg']
            x_offset = 0

            for i, name in enumerate(representative_shapes):
                if name in outputs:
                    h, w, desc = BODY_SHAPES[name]
                    betas = torch.zeros(1, 10)
                    betas[0, 0] = h
                    betas[0, 1] = w

                    trans = torch.zeros(1, 3)
                    trans[0, 0] = x_offset  # Horizontal arrangement

                    poses = torch.zeros(1, skel.num_q_params)

                    skel_seq = SKELSequence(
                        skel_layer=skel,
                        betas=betas,
                        poses_body=poses,
                        poses_type='skel',
                        trans=trans,
                        is_rigged=False,
                        name=f'{name} (β₁={w:.1f})',
                        z_up=False
                    )

                    v.scene.add(skel_seq)
                    x_offset += 1.0  # 1 meter spacing

            v.run()

        except ImportError:
            print('\nAITViewer not available, skipping visualization')
            print('Tip: Use --export_meshes to export meshes, then view in other software')

if __name__ == '__main__':
    main()
