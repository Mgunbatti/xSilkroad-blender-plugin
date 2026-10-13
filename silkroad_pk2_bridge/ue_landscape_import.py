# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute in Unreal 5.8 editor after enabling SilkroadLandscapeBridge.
Set SILKROAD_LANDSCAPE_MANIFEST to a full Landscape.json path before execution.
Optional SILKROAD_LANDSCAPE_ASSET_ROOT selects a NEW asset folder.
"""
import unreal as u,json
from pathlib import Path

def import_bundle(filename, asset_root='/Game/SilkroadJanganLandscape'):
    path=Path(filename).resolve();manifest=json.loads(path.read_text());sub=u.get_editor_subsystem(u.EditorAssetSubsystem);lib=u.MaterialEditingLibrary;tools=u.AssetToolsHelpers.get_asset_tools()
    if not hasattr(u,'SilkroadLandscapeLibrary'):raise RuntimeError('Build and enable the supplied SilkroadLandscapeBridge editor plugin first')
    if sub.does_directory_exist(asset_root):raise RuntimeError('Choose a new asset root; existing Landscape materials are preserved')
    m=tools.create_asset('M_JanganLandscape',asset_root+'/Materials',u.Material,u.MaterialFactoryNew());assert m
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    def node(cls):return lib.create_material_expression(m,cls)
    def connect(a,out,b,pin):assert lib.connect_material_expressions(a,out,b,pin)
    def constant(v):n=node(u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
    def vector(v):n=node(u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v,1));return n
    def mul(a,b):n=node(u.MaterialExpressionMultiply);connect(a,'',n,'A');connect(b,'',n,'B');return n
    wp=node(u.MaterialExpressionWorldPosition);xy=node(u.MaterialExpressionComponentMask)
    for c in ('r','g','b','a'):xy.set_editor_property(c,c in ('r','g'))
    connect(wp,'',xy,'');uv=mul(xy,constant(1/240))
    def channel(sample):
        n=node(u.MaterialExpressionComponentMask)
        for c in ('r','g','b','a'):n.set_editor_property(c,c!='a')
        connect(sample,'',n,'');return n
    def texture(name,normal=False):
        file=path.parent/'Textures'/(name+'.png')
        if not file.exists():return None
        task=u.AssetImportTask();task.filename=str(file);task.destination_path=asset_root+'/Textures';task.destination_name=name;task.automated=True;task.save=False;tools.import_asset_tasks([task]);tex=sub.load_asset(asset_root+'/Textures/'+name);assert tex
        if normal:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('srgb',False)
        elif name.endswith('Rough'):tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS);tex.set_editor_property('srgb',False)
        tex.set_editor_property('power_of_two_mode',u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
        tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
        sub.save_loaded_asset(tex,only_if_is_dirty=False)
        n=node(u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',name);n.set_editor_property('texture',tex);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else (u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_MASKS));connect(uv,'',n,lib.get_material_expression_input_names(n)[0]);return channel(n)
    base=vector((0,0,0));normal=vector((0,0,0));rough=constant(0)
    colors={'Soil':(.18,.115,.055),'Grass':(.06,.105,.025),'DryGrass':(.28,.25,.12),
            'WetSoil':(.12,.105,.07),'Rock':(.16,.16,.145),'Paving':(.25,.235,.21)}
    for layer in manifest['layers']:
        name=layer['name']
        if name=='Visibility':continue
        color=colors[name]
        tint=node(u.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name',name+'_Tint');tint.set_editor_property('default_value',u.LinearColor(*color,1))
        tex=texture(name+'_BaseColor');value=tex if tex else tint
        for kind,value0,previous in [('color',value,base),('normal',texture(name+'_Normal',True) or vector((0,0,1)),normal),('rough',texture(name+'_Rough') or constant(.85),rough)]:
            blend=node(u.MaterialExpressionLandscapeLayerWeight);blend.set_editor_property('parameter_name',name);blend.set_editor_property('preview_weight',1 if name=='Grass' else 0);connect(previous,'',blend,'Base');connect(value0,'',blend,'Layer')
            if kind=='color':base=blend
            elif kind=='normal':normal=blend
            else:rough=blend
    assert lib.connect_material_property(base,'',u.MaterialProperty.MP_BASE_COLOR);assert lib.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL);assert lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    # Broad, continuous color variation avoids a uniformly repeated ground texture.
    noise=node(u.MaterialExpressionNoise);noise.set_editor_property('scale',.0002);noise.set_editor_property('levels',2);noise.set_editor_property('quality',1)
    connect(wp,'',noise,lib.get_material_expression_input_names(noise)[0])
    variation=node(u.MaterialExpressionAdd);connect(mul(noise,constant(.15)),'',variation,'A');connect(constant(.93),'',variation,'B')
    assert lib.connect_material_property(mul(base,variation),'',u.MaterialProperty.MP_BASE_COLOR)
    vis=node(u.MaterialExpressionLandscapeVisibilityMask);assert lib.connect_material_property(vis,'',u.MaterialProperty.MP_OPACITY_MASK);lib.recompile_material(m);sub.save_loaded_asset(m,only_if_is_dirty=False)
    result=u.SilkroadLandscapeLibrary.import_manifest(str(path),m,asset_root)
    landscape,error=result if isinstance(result,tuple) else (result,'')
    if not landscape:raise RuntimeError(error or 'Landscape import failed')
    sub.save_directory(asset_root,only_if_is_dirty=False,recursive=True)
    return landscape,manifest

if 'SILKROAD_LANDSCAPE_MANIFEST' in globals():
    landscape,manifest=import_bundle(SILKROAD_LANDSCAPE_MANIFEST,globals().get('SILKROAD_LANDSCAPE_ASSET_ROOT','/Game/SilkroadJanganLandscape'))
    print('JANGAN_LANDSCAPE_IMPORTED',landscape.get_path_name(),manifest['quantization_error_cm'])
