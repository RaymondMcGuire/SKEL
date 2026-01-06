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
import sys
import torch
from skel.skel_model import SKEL
from skel.kin_skel import skel_joints_name
import trimesh
import numpy as np

import skel.config as cg

# Predefined body shape configurations
# Format: (name, beta[0](height), beta[1](weight), description)
# NOTE: Based on empirical testing, NEGATIVE beta values correspond to LARGER body mass
#       Positive beta → thinner/lighter body, Negative beta → heavier/larger body
BODY_SHAPES = {
    'very_thin_short': (-1.5, 2.0, 'Very thin & short (~45kg, ~155cm)'),
    'thin_short': (-1.0, 1.5, 'Thin & short (~50kg, ~160cm)'),
    'average_short': (-1.0, 0.0, 'Average weight, short (~60kg, ~160cm)'),

    'very_thin_avg': (0.0, 2.0, 'Very thin, average height (~45kg, ~165cm)'),
    'thin_avg': (0.0, 1.0, 'Thin, average height (~55kg, ~165cm)'),
    'average': (0.0, 0.0, 'Average body type (default, ~60kg, ~165cm)'),
    'heavy_avg': (0.0, -1.0, 'Heavy, average height (~80kg, ~165cm)'),
    'very_heavy_avg': (0.0, -2.0, 'Very heavy, average height (~100-120kg, ~165cm)'),

    'thin_tall': (1.5, 1.0, 'Thin & tall (~60kg, ~175cm)'),
    'average_tall': (1.5, 0.0, 'Average weight, tall (~70kg, ~175cm)'),
    'heavy_tall': (1.5, -1.0, 'Heavy & tall (~90kg, ~175cm)'),
    'very_heavy_tall': (1.5, -2.0, 'Very heavy & tall (~110-130kg, ~175cm)'),
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


def compute_per_bone_scale_from_skel(skel_model, betas, device='cpu'):
    """
    Compute per-bone scale factors using SKEL's internal bone scaling logic.
    Returns a dict {bone_name: np.array([sx, sy, sz])}.
    """
    with torch.no_grad():
        # Recreate the minimal forward pass pieces needed for scaling
        B = 1
        betas_t = betas.to(device)
        skin_v0 = skel_model.skin_template_v[None, :].to(device)
        shapedirs = skel_model.shapedirs.view(-1,
                                              skel_model.num_betas)[None, :].to(device)
        v_shaped = skin_v0 + \
            torch.matmul(shapedirs, betas_t[0:1]).view(B, skin_v0.shape[1], 3)

        # Joints and bone vectors
        J = torch.einsum(
            'bik,ji->bjk', [v_shaped, skel_model.J_regressor_osim])  # BxJx3
        J_ = J.clone()
        J_[:, 1:, :] = J[:, 1:, :] - J[:, skel_model.parent, :]

        is_unique_beta = True  # single-shape export
        bone_scale = skel_model.compute_bone_scale(
            J_, v_shaped, skin_v0, is_unique_beta)  # BxJx3

    bone_scale_np = bone_scale[0].cpu().numpy()
    bone_names = skel_joints_name
    return {bn: bone_scale_np[i] for i, bn in enumerate(bone_names)}


def export_geometry_bones(osim_path, bone_scales, output_dir, subdivide=0):
    """
    Load per-bone meshes from the OSIM Geometry folder, apply per-bone scaling, and export as OBJ.
    """
    # Lazy import to keep SKEL-only path working if smpl2ab isn't installed
    try:
        from skel.osim_aug import OsimAug
    except Exception as e:
        print(f"WARNING: Failed to import OsimAug for geometry export: {e}")
        return 0

    oa = OsimAug(osim_path=osim_path)
    os.makedirs(output_dir, exist_ok=True)

    exported = 0
    for node_name in oa.node_names:
        mesh = oa.get_bone_submesh(node_name)
        if mesh is None:
            continue
        # Apply per-bone scale if available
        scale = bone_scales.get(node_name, None)
        if scale is not None:
            mesh = mesh.copy()
            mesh.vertices[:] = mesh.vertices * scale

        # Optional subdivision
        if subdivide > 0:
            for _ in range(subdivide):
                mesh = mesh.subdivide_loop()

        out_path = os.path.join(output_dir, f"{node_name}.obj")
        mesh.export(out_path)
        exported += 1
    return exported


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
    # Shoulder is about 30cm below top
    shoulder_height = vertices[:, 1].max() - 0.3
    shoulder_verts = vertices[np.abs(vertices[:, 1] - shoulder_height) < 0.1]
    if len(shoulder_verts) > 0:
        shoulder_width = shoulder_verts[:,
                                        0].max() - shoulder_verts[:, 0].min()
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
    parser = argparse.ArgumentParser(
        description='Explore SKEL body shape parameters')
    parser.add_argument('--gender', type=str, default='female', choices=['female', 'male'],
                        help='Gender')
    parser.add_argument('--export_meshes', action='store_true',
                        help='Export mesh files to output/body_shapes/')
    parser.add_argument('--subdivide', type=int, default=0, choices=[0, 1, 2, 3],
                        help='Subdivision level for exported meshes (0=no subdivision, 1-3=finer detail). '
                        'Each level ~4x more faces. Recommended: 1 or 2')
    parser.add_argument('--separate_bones', action='store_true',
                        help='Export each bone as a separate mesh file (24 bones: pelvis, femur_r/l, tibia_r/l, etc.)')
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
        print(
            f'  Height: {measurements["height"]:.3f} m ({measurements["height"]*100:.1f} cm)')
        print(
            f'  Shoulder width: {measurements["shoulder_width"]:.3f} m ({measurements["shoulder_width"]*100:.1f} cm)')
        print(
            f'  Arm span: {measurements["arm_span"]:.3f} m ({measurements["arm_span"]*100:.1f} cm)')

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

            # Apply subdivision if requested
            if args.subdivide > 0:
                print(
                    f'\nApplying Loop subdivision (level {args.subdivide})...')
                print(f'  Original skin mesh: {len(skin_mesh.faces):,} faces')
                for _ in range(args.subdivide):
                    skin_mesh = skin_mesh.subdivide_loop()
                print(
                    f'  Subdivided skin mesh: {len(skin_mesh.faces):,} faces')

                print(
                    f'  Original skeleton mesh: {len(skel_mesh.faces):,} faces')
                for _ in range(args.subdivide):
                    skel_mesh = skel_mesh.subdivide_loop()
                print(
                    f'  Subdivided skeleton mesh: {len(skel_mesh.faces):,} faces')

            # Export skin mesh
            skin_mesh.export(skin_path)

            # Export skeleton - either as one complete mesh or separate bones
            if args.separate_bones:
                print(
                    f'\nExporting per-bone meshes from Geometry with SKEL-derived scales...')
                bones_dir = os.path.join(output_dir, f'{filename}_bones')
                bone_scales = compute_per_bone_scale_from_skel(
                    skel, betas, device)
                exported = export_geometry_bones(
                    cg.osim_model_path, bone_scales, bones_dir, subdivide=args.subdivide)
                print(f'  Exported {exported} bones to {bones_dir}/')
            else:
                skel_mesh.export(skel_path)

            print(f'\nMeshes saved to {output_dir}/')

    else:
        # Generate all predefined body shapes
        print(f'\nGenerating predefined body shape variations...\n')
        print(
            f'{"Name":<20} {"Height β":<10} {"Weight β":<10} {"Description":<40} {"Est. Height":<12}')
        print('-' * 100)

        outputs = {}
        for name, (h, w, desc) in BODY_SHAPES.items():
            output, betas = create_body_with_shape(skel, h, w, device)
            measurements = estimate_body_measurements(output)

            height_cm = measurements['height'] * 100
            print(
                f'{name:<20} {h:<10.1f} {w:<10.1f} {desc:<40} {height_cm:<12.1f} cm')

            outputs[name] = output

            # Export meshes
            if args.export_meshes:
                output_dir = 'output/body_shapes'
                os.makedirs(output_dir, exist_ok=True)

                skin_path = os.path.join(
                    output_dir, f'{args.gender}_{name}_skin.obj')
                skel_path = os.path.join(
                    output_dir, f'{args.gender}_{name}_skel.obj')

                skin_mesh = trimesh.Trimesh(
                    vertices=output.skin_verts[0].cpu().numpy(),
                    faces=skel.skin_f.cpu().numpy()
                )
                skel_mesh = trimesh.Trimesh(
                    vertices=output.skel_verts[0].cpu().numpy(),
                    faces=skel.skel_f.cpu().numpy()
                )

                # Apply subdivision if requested
                if args.subdivide > 0:
                    for _ in range(args.subdivide):
                        skin_mesh = skin_mesh.subdivide_loop()
                        skel_mesh = skel_mesh.subdivide_loop()

                # Export skin mesh
                skin_mesh.export(skin_path)

                # Export skeleton - either as one complete mesh or separate bones
                if args.separate_bones:
                    bones_dir = os.path.join(
                        output_dir, f'{args.gender}_{name}_bones')
                    bone_scales = compute_per_bone_scale_from_skel(
                        skel, betas, device)
                    exported = export_geometry_bones(
                        cg.osim_model_path, bone_scales, bones_dir, subdivide=args.subdivide)
                    print(f'Exported {exported} bones to {bones_dir}/')
                else:
                    skel_mesh.export(skel_path)

        if args.export_meshes:
            if args.subdivide > 0:
                print(
                    f'\nAll meshes exported with Loop subdivision level {args.subdivide} to output/body_shapes/')
            else:
                print(f'\nAll meshes saved to output/body_shapes/')

    # Visualize (if requested)
    if args.visualize:
        try:
            from aitviewer.viewer import Viewer
            from skel.viewer.renderables.skel import SKELSequence

            print('\nLaunching AITViewer...')
            v = Viewer()

            # Add several representative body shapes to scene
            representative_shapes = ['very_thin_avg',
                                     'average', 'heavy_avg', 'very_heavy_avg']
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
            print(
                'Tip: Use --export_meshes to export meshes, then view in other software')


if __name__ == '__main__':
    main()
