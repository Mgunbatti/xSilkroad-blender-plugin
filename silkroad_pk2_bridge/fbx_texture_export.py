# SPDX-License-Identifier: GPL-3.0-or-later
"""Non-destructive FBX export with portable PNG texture references.

Only run on Blender's main thread. The original image IDs, materials, armatures,
mesh geometry, animations and PK2 archives are never rewritten here.
"""

from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
import shutil
import tempfile

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


@dataclass
class ExportSummary:
    fbx: Path
    texture_folder: Path | None
    converted: int
    missing: list
    report: Path


def clean_filename(value):
    """Avoid path traversal and Windows reserved filename chars in texture names."""
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value))
    safe = re.sub(r'\s+', '_', safe).strip(' ._')[:65]
    if not safe or safe.upper().split('.')[0] in {
            'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
            *(f'LPT{i}' for i in range(1, 10))}:
        safe = 'texture'
    return safe


def texture_filename(image):
    # Different image data-blocks with the same name can have different source paths.
    identifier = f'{image.name}|{getattr(image, "filepath", "")}|{getattr(image, "library", "")}'
    short_hash = sha256(identifier.encode('utf-8', errors='replace')).hexdigest()[:12]
    stem = Path(str(image.name).replace('\\', '/')).stem
    return f'{clean_filename(stem)}_{short_hash}.png'


def free_texture_folder(parent, fbx_stem):
    name = clean_filename(fbx_stem) + '_textures'
    suffix = 1
    while (parent / name).exists():
        suffix += 1
        name = f'{clean_filename(fbx_stem)}_textures_{suffix:02d}'
    return name


def _format_source(image):
    raw = getattr(image, 'filepath', '')
    return raw or '<packed/generated>'


@contextmanager
def isolated_png_scene(bpy):
    """Private scene for image encoding, never modify the user's render settings.

    A DDS opened by Blender can report `image.file_format == ""`: this is NOT a
    valid enum value for restoring after `image.file_format = 'PNG'`.  The old
    approach wrote a PNG then raised during the restore and deleted the PNG.
    `Image.save_render(scene=...)` bypasses that property completely.
    """
    scene = bpy.data.scenes.new("Silkroad_PNG_Export_Temporary")
    try:
        settings = scene.render.image_settings
        settings.file_format = 'PNG'
        settings.color_mode = 'RGBA'
        settings.color_depth = '8'
        settings.compression = 15
        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
        # On current Blender builds, None is the neutral look for Standard.
        # Some custom OCIO configs do not expose it; no user scene is affected.
        try:
            scene.view_settings.look = 'None'
        except (AttributeError, ValueError, TypeError):
            pass
        yield scene
    finally:
        bpy.data.scenes.remove(scene)


def _write_png(image, dest, scene):
    """Encode the already loaded DDS pixels as PNG without touching its ID.

    `save_render` reads the image buffer and the supplied scene's output format.
    For data/normal maps use the Raw view transform so color-management does not
    apply an sRGB display transform to numeric channel values.
    """
    if getattr(image, 'source', 'FILE') not in {'FILE', 'GENERATED'}:
        raise ValueError('UDIM/video/sequence textures are not supported')
    colorspace = str(getattr(getattr(image, 'colorspace_settings', None), 'name', '')).lower()
    is_data = any(part in colorspace for part in ('non-color', 'non color', 'raw', 'data'))
    scene.view_settings.view_transform = 'Raw' if is_data else 'Standard'
    image.save_render(str(dest), scene=scene)
    if not dest.is_file() or dest.stat().st_size < len(PNG_SIGNATURE) + 12:
        raise RuntimeError('PNG output was not written')
    with dest.open('rb') as png_input:
        signature = png_input.read(8)
    if signature != PNG_SIGNATURE:
        raise RuntimeError('Image save did not produce a real PNG')


@contextmanager
def temporary_png_materials(bpy, objects, texture_dir, enabled=True):
    """Temporarily assign cloned materials/images to exported mesh slots.

    Originals remain untouched and are restored before cleanup in *all* cases.
    """
    with isolated_png_scene(bpy) if enabled else nullcontext(None) as png_scene:
        old_slots = []
        new_materials = []
        new_images = []
        material_cache = {}
        image_cache = {}
        missing = []
        touched = []
        try:
            if enabled:
                for obj in objects:
                    if getattr(obj, 'type', None) != 'MESH':
                        continue
                    for slot in obj.material_slots:
                        original = slot.material
                        if original is None:
                            continue
                        mat_id = original.as_pointer()
                        if mat_id not in material_cache:
                            clone = original.copy()
                            new_materials.append(clone)
                            material_cache[mat_id] = clone
                            if getattr(clone, 'use_nodes', False) and clone.node_tree:
                                for node in clone.node_tree.nodes:
                                    if getattr(node, 'type', None) != 'TEX_IMAGE':
                                        continue
                                    image = getattr(node, 'image', None)
                                    if image is None:
                                        missing.append(f'{original.name}: empty image node ({node.name})')
                                        continue
                                    image_id = image.as_pointer()
                                    if image_id not in image_cache:
                                        target = texture_dir / texture_filename(image)
                                        # Images with same name/path but different ID might hash alike.
                                        if target.exists():
                                            count = len(image_cache) + 1
                                            target = texture_dir / f'{target.stem}_{count}.png'
                                        try:
                                            _write_png(image, target, png_scene)
                                            loaded = bpy.data.images.load(str(target), check_existing=False)
                                            new_images.append(loaded)
                                            try:
                                                loaded.colorspace_settings.name = image.colorspace_settings.name
                                            except (AttributeError, TypeError, ValueError):
                                                pass
                                            image_cache[image_id] = loaded
                                            touched.append((str(image.name), str(target.name)))
                                        except Exception as exc:
                                            # No stale DDS references in the export. Report a grey
                                            # material rather than silently sending a broken path.
                                            target.unlink(missing_ok=True)
                                            image_cache[image_id] = None
                                            missing.append(f'{image.name} [{_format_source(image)}]: {exc}')
                                    node.image = image_cache[image_id]
                        old_slots.append((slot, original))
                        slot.material = material_cache[mat_id]
            yield (touched, missing)
        finally:
            for slot, original in reversed(old_slots):
                slot.material = original
            for mat in reversed(new_materials):
                bpy.data.materials.remove(mat, do_unlink=True)
            for img in reversed(new_images):
                bpy.data.images.remove(img, do_unlink=True)


def _write_report(path, converted, missing, fbx_name, folder_name):
    lines = [
        f'Silkroad PK2 Editor FBX texture report - {fbx_name}',
        f'Portable texture directory: {folder_name if folder_name else "(disabled)"}',
        'Textures are referenced as external PNGs. Keep this folder beside the FBX.',
        f'Converted: {len(converted)}',
        f'Missing / unsupported: {len(missing)}', '',
        'Converted textures:',
        *(f'  {old} -> {new}' for old, new in converted), '',
        'Missing / failed:',
        *(f'  {msg}' for msg in missing), '',
        'Note: UE may still require manual material/normal/alpha hookup.',
        'Original DDS files and Blender materials were not modified.',
    ]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def export_fbx_with_textures(bpy, filepath, objects, *, textures=True, animation=True):
    """Stage an FBX + PNG sidecar, move only after exporter succeeds.

    On failure, the existing destination FBX and sidecar are left untouched.
    Blender export action data uses the currently active Action (not All Actions).
    """
    path = Path(filepath).expanduser().absolute()
    if path.suffix.lower() != '.fbx':
        raise ValueError('FBX extension must be .fbx')
    if not path.parent.is_dir():
        raise FileNotFoundError(f'Output folder does not exist: {path.parent}')
    meshes = [obj for obj in objects if getattr(obj, 'type', None) == 'MESH']
    rigs = [obj for obj in objects if getattr(obj, 'type', None) == 'ARMATURE']
    if not meshes:
        raise ValueError('Select at least one Mesh (Armature is recommended).')
    # Static props can be exported without a rig; animated mobs should include it.
    folder_name = free_texture_folder(path.parent, path.stem) if textures else None
    with tempfile.TemporaryDirectory(prefix='.silkroad_fbx_', dir=path.parent) as tmp:
        stage = Path(tmp)
        staged_fbx = stage / path.name
        tex_dir = stage / folder_name if folder_name else stage / '_no_textures'
        if textures:
            tex_dir.mkdir()
        with temporary_png_materials(bpy, objects, tex_dir, enabled=textures) as (converted, missing):
            params = dict(
                filepath=str(staged_fbx),
                use_selection=True,
                object_types={'MESH', 'ARMATURE'},
                add_leaf_bones=False,
                axis_forward='-Y', axis_up='Z',
                path_mode='RELATIVE', embed_textures=False,
                bake_anim=bool(animation),
                bake_anim_use_nla_strips=False,
                bake_anim_use_all_actions=False,
                bake_anim_use_all_bones=True,
                bake_anim_force_startend_keying=True,
                bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
                mesh_smooth_type='FACE',
            )
            result = bpy.ops.export_scene.fbx('EXEC_DEFAULT', **params)
            if 'FINISHED' not in result:
                raise RuntimeError(f'Blender FBX export failed: {result}')
        if not staged_fbx.is_file() or staged_fbx.stat().st_size == 0:
            raise RuntimeError('Blender did not generate an FBX output file')
        report_name = f'{path.stem}_TextureReport.txt'
        staged_report = stage / report_name
        if animation and not rigs:
            missing.append('No armature selected: FBX contains no skeletal animation.')
        _write_report(staged_report, converted, missing, path.name, folder_name)
        published_dir = path.parent / folder_name if folder_name else None
        try:
            if published_dir is not None:
                shutil.move(str(tex_dir), str(published_dir))
            try:
                staged_fbx.replace(path)
            except Exception:
                if published_dir is not None:
                    shutil.rmtree(published_dir)
                raise
            staged_report.replace(path.parent / report_name)
        except Exception:
            raise
        return ExportSummary(path, published_dir, len(converted), list(missing), path.parent / report_name)
