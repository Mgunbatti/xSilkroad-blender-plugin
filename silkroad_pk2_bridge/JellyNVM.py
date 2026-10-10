# Copyright (C) 2023-2026 Engels Quintero
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://gnu.org>.

# Plugin Information
bl_info = {
	"name": "Silkroad JMXVNVM",
	"version": (2,2,0),
	"description": ("Import Sikroad Online Navigation Mesh Data"),
	"blender": (4,2,0),
	"category": "Import-Export",
	"location": "File > Import",
	"author": "JellyBitz",
}

# Import stuffs
import os
from .map_data import parse_nvm
from .import_runtime import execute_import
import re
import bpy
import bmesh
from bpy.props import StringProperty, BoolProperty, CollectionProperty, FloatProperty
from bpy.types import Operator, OperatorFileListElement
from .JellyBMS import BinaryReader, BinaryWriter, BlenderGetMode, BlenderSetMode
from .JellyBSR import GetViewLayerCollection, GetActiveViewLayerCollection, SetActiveViewLayerCollection

LOG_DEBUG = False
# Write text for debugging
def debug_print(*args):
	if LOG_DEBUG:
		print(' '.join(map(str, args)))

# Import JMXVNVM command
class Import_JMXVNVM(Operator):
	"""Imports a AINavData file from Silkroad Online"""
	bl_idname = "silkroad_import.jmxvnvm_1000" # bpy.ops.silkroad_import.jmxvnvm_1000
	bl_label = "Select .nvm file"
	# Filter only .ban files
	filter_glob: StringProperty(
		default="*.nvm",
		options={'HIDDEN'},
		maxlen=255  # Max internal buffer length, longer would be clamped.
	)
	# Add support to select multiples files
	files: CollectionProperty(
		name="File Path",
		type=OperatorFileListElement
	)
	directory: StringProperty(
		subtype='DIR_PATH'
	)
	# Settings
	setting_scale: FloatProperty(
		name="Scale",
		description="Apply general scale",
		default=0.01,
		min=0.001,
		max=100.0
	)
	setting_region_offset: BoolProperty(
		name="Region Offset",
		description="Keep the worldmap offset position from navmesh",
		default=True,
	)
	setting_data_pk2_path: StringProperty(
		name='Data Path',
		description='Path to the DATA folder from server files',
		default='C:\\Silkroad\\#Server\\Files - Test_In\\Data',
		maxlen=255,
	)
	setting_map_pk2_path: StringProperty(
		name='Map Path',
		description='Path to the MAP folder from server files',
		default='C:\\Silkroad\\#Server\\Files - Test_In\\Map',
		maxlen=255,
	)
	setting_load_objects: BoolProperty(
		name="Objects",
		description="Load all objects from map",
		default=False,
	)
	setting_objects_collision_box: BoolProperty(
		name="Collision Box",
		description="Load Collision Box from objects",
		default=False,
	)
	setting_objects_navmesh: BoolProperty(
		name="NavMesh",
		description="Load Navigation Mesh from objects",
		default=False,
	)
	setting_terrain_collision: BoolProperty(
		name="Terrain Collisions",
		description="Load Collisions Mesh from terrain",
		default=False,
	)
	# Class (static) variables
	_objects_ifo_data = {}
	_tile2d_ifo_data = {}
	# Execute command
	def execute(self, Context):
		return execute_import(self, Context, ".nvm")
	# Run this as dialog
	def invoke(self, context, event):
		wm = context.window_manager
		wm.fileselect_add(self)
		return {'RUNNING_MODAL'}
	# Drawing dialog
	def draw(self, Context):
		layout = self.layout
		layout.prop(self,'setting_data_pk2_path')
		layout.prop(self,'setting_map_pk2_path')
		layout.prop(self,'setting_scale')
		layout.prop(self,'setting_region_offset')

		layout.prop(self,'setting_load_objects')
		layout_box = layout.box()
		layout_row = layout_box.row()
		if not self.setting_load_objects:
			layout_row.enabled = False
		layout_row.prop(self,'setting_objects_collision_box')
		layout_row.prop(self,'setting_objects_navmesh')

		layout.prop(self,'setting_terrain_collision')
	# Loads file to blender
	def LoadFile(self, Context, FullPath):
		# Try to read file
		br = None
		with open(FullPath, 'rb') as f:
			br = BinaryReader(f.read())
			# Check file signature
			if br.Length < 12 or br.ReadAscii(12) != "JMXVNVM 1000":
				raise ValueError("Invalid NVM signature")
		if not br:
			raise ValueError("Empty binary reader")

		# Try to load file
		data = None
		try:
			# Reset cursor
			br.SeekRead(0)
			data = self.LoadData(br)
		except Exception as ex:
			# Error
			print('Error loading JMXVNVM file:'+FullPath+' ['+str(ex)+']')
			raise

		# Import data to blender
		userMode = BlenderGetMode()

		# Process Data
		self.LoadObjectsData()
		self.LoadTile2dData()
		self.ProcessData(Context,data,os.path.splitext(os.path.basename(FullPath))[0])

		# Get back to normal
		BlenderSetMode(userMode)

		# Success
		print('Loaded:'+FullPath)
		return True
	# Loads the data from file structure
	def LoadData(self, br):
		data = parse_nvm(br.Buffer)
		return data

	# Process data from file into Blender
	def ProcessData(self, Context, data, name):
		BlenderSetMode('OBJECT')

		# Create collection with all the stuff from the file
		collection = bpy.data.collections.new(name)
		# Link it to the current collection active
		parentCollection = GetActiveViewLayerCollection(Context).collection
		parentCollection.children.link(collection)
		# Make current collection active temporally
		SetActiveViewLayerCollection(Context,collection.name)

		# Create HeightMap object
		mesh = bpy.data.meshes.new("Mesh")
		obj = bpy.data.objects.new(name+'.NavMesh', mesh)
		collection.objects.link(obj)
		Context.view_layer.objects.active = obj # Set active object to work with

		# Apply general scale
		obj.scale = (self.setting_scale,self.setting_scale,self.setting_scale)

		# Region
		region = 0
		match = re.search("([0-9a-fA-F]{2})([0-9a-fA-F]{2})$", name)
		if match:
			ry = int(match.group(1),16)
			rx = int(match.group(2),16)
			region = (ry << 8) | rx
			collection.name = collection.name+' [RID:'+str(region)+']'
			# Region offset position
			if self.setting_region_offset:
				obj.location = ((rx - 135) * 1920 * self.setting_scale, (ry - 92) * 1920 * self.setting_scale, 0.0)
		
		# Create Mesh from HeightMap
		w = 97
		h = 97
		heightmap_faces = []
		for i in range(h-1):
			for j in range(w-1):
				a = i*w+j
				b = a+1
				c = a+w
				d = c+1
				heightmap_faces.append([a,b,d,c])
		mesh.from_pydata(data['heightmap_vertices'], [], heightmap_faces)
		# Add default UV Map
		mesh.uv_layers.new(name='UVMap')
		# Each terrain quad samples one tile image; an empty UV map sampled one pixel.
		for polygon in mesh.polygons:
			for loop_index, uv in zip(polygon.loop_indices, ((0,0),(1,0),(1,1),(0,1))):
				mesh.uv_layers.active.data[loop_index].uv = uv

		# Set materials from each tile
		missing_tiles = {f['tile_id'] for f in data['heightmap_faces']} - self._tile2d_ifo_data.keys()
		if missing_tiles:
			print('Terrain material warning: tile2d.ifo missing tile IDs:', sorted(missing_tiles))
		if self._tile2d_ifo_data:
			heightmap_faces = data['heightmap_faces']
			for face_idx, heightmap_face in enumerate(heightmap_faces):
				tileData = self._tile2d_ifo_data.get(heightmap_face['tile_id'])
				if tileData is None:
					continue
				tileName = str(heightmap_face['tile_id'])
				# Check material existence by name
				mat = bpy.data.materials.get(tileName)
				if not mat:
					mat = bpy.data.materials.new(name=tileName)
					mat.use_nodes = True
					mat.node_tree.nodes.clear()
					# Set base nodes and link them
					mat.use_nodes = True
					nodes = mat.node_tree.nodes
					output = nodes['ShaderNodeOutputMaterial'] if 'ShaderNodeOutputMaterial' in nodes else mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
					output.name = 'ShaderNodeOutputMaterial'
					output.location = (380,300)
					bsdf = nodes['ShaderNodeBsdfPrincipled'] if 'ShaderNodeBsdfPrincipled' in nodes else mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
					bsdf.name = 'ShaderNodeBsdfPrincipled'
					bsdf.location = (100,300)
					mat.node_tree.links.new(output.inputs['Surface'], bsdf.outputs['BSDF'])					
					# Load texture
					mtrlPath = os.path.join(self.setting_map_pk2_path,'tile2d',os.path.splitext(tileData['path'])[0]+'.dds')
					if not os.path.exists(mtrlPath) and os.path.isfile(os.path.join(self.setting_map_pk2_path,'tile2d',tileData['path'])):
						# Remove header from DDJ
						with open(os.path.join(self.setting_map_pk2_path,'tile2d',tileData['path']), 'rb') as fr:
							fr.seek(20,os.SEEK_SET)
							# Write into DDS
							with open(mtrlPath, 'wb') as fw:
								fw.write(fr.read())
					# Texture node
					texImgNode = nodes.new('ShaderNodeTexImage')
					if os.path.exists(mtrlPath):
						texImgNode.image = bpy.data.images.load(mtrlPath)
					else:
						print('Terrain texture warning: missing', mtrlPath)
					texImgNode.name = tileName
					texImgNode.location = (-185,300)
					# Link texture
					mat.node_tree.links.new(bsdf.inputs['Base Color'], texImgNode.outputs['Color'])
				# Add material to object
				if not obj.data.materials.get(tileName):
					obj.data.materials.append(mat)
				material_index = 0
				for mat_idx, material in enumerate(obj.data.materials):
					if material.name == tileName:
						obj.data.polygons[face_idx].material_index = mat_idx
						break

		# Load objects from navmesh
		for fileObjectData in data['objects']:
			if not self.setting_load_objects:
				break
			# Make sure this asset has been loaded
			if not fileObjectData['asset_id'] in self._objects_ifo_data:
				continue
			# Avoid duplicated objects
			if fileObjectData['RID'] != region:
				continue
			fileObject = self._objects_ifo_data[fileObjectData['asset_id']]

			# Keep the track of collections
			collectionCount = len(collection.children)

			# Set values to execute operator
			bpy.ops.silkroad_import.jmxvres_0109(
				directory=self.setting_data_pk2_path,
				setting_data_pk2_path=self.setting_data_pk2_path,
				files=[{'name':path} for path in fileObject['res_path']],
				setting_collision_box=self.setting_objects_collision_box,
				setting_navmesh=self.setting_objects_navmesh,
			)

			# Get collections added
			collectionCount = len(collection.children) - collectionCount
			for collectionIndex in range(collectionCount):
				i = (-1)-collectionIndex
				latestCollection = collection.children[i]
				# Move objects from collection to their positions
				for o in latestCollection.all_objects:
					# Make sure is not parented with an armature
					if not o.parent:
						o.location = (obj.location[0] + fileObjectData['local_position'][0]*self.setting_scale, obj.location[1] + fileObjectData['local_position'][1]*self.setting_scale, fileObjectData['local_position'][2]*self.setting_scale)
						o.rotation_euler[2] = fileObjectData['yaw']
						o.scale = obj.scale
		
		# Add collisions from edges
		if self.setting_terrain_collision:
			Context.view_layer.objects.active = obj
			BlenderSetMode('EDIT')
			bm = bmesh.from_edit_mesh(mesh)
			bm.verts.ensure_lookup_table()
			navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options') or bm.edges.layers.int.new('nav_edges_options')

			# Check vertices to find the edge and set flags
			def FindAndSetEdgeFlags(bm, VertexIndex01,VertexIndex02,EdgeFlags):
				for e in bm.verts[VertexIndex01].link_edges:
					for v in e.verts:
						if v.index == VertexIndex02:
							# Set flags
							e[navEdgesOptionsLayer] = EdgeFlags
							return

			# Set flags from all edges
			for cell in data['cells']:
				for edge in (cell['internal_edges']+cell['global_edges']):
					jmin = int(edge['min'][0] / 20)
					imin = int(edge['min'][1] / 20)
					jmax = int(edge['max'][0] / 20)
					imax = int(edge['max'][1] / 20)
					# Find vertices with those edges
					if imin == imax:
						if imin == 0:
							for j in range(jmin+1,jmax+1,1): # top
								FindAndSetEdgeFlags(bm,imin*w+(j-1),imin*w+j,edge['flags'])
						for j in range(jmin+1,jmax+1,1): # bottom
							FindAndSetEdgeFlags(bm,imax*w+(j-1),imax*w+j,edge['flags'])
					if jmin == jmax:
						if jmin == 0:
							for i in range(imin+1,imax+1,1): # left
								FindAndSetEdgeFlags(bm,i*w+jmin,i*w+jmax,edge['flags'])
						for i in range(imin+1,imax+1,1): # right
							FindAndSetEdgeFlags(bm,(i-1)*w+jmax,i*w+jmax,edge['flags'])

		# Return selected collection to the original
		SetActiveViewLayerCollection(Context,parentCollection.name)

	# Load data required from navmesh
	def LoadObjectsData(self):
		# Abort reloading
		if self._objects_ifo_data:
			return
		# Check pk2 path
		if not self.setting_data_pk2_path:
			return
		# Try to load "object.ifo" file
		objects_ifo_path = os.path.join(self.setting_data_pk2_path,'navmesh\\object.ifo')
		if os.path.exists(objects_ifo_path):
			with open(objects_ifo_path,'r',errors='ignore') as f:
				# Read file format
				header = f.readline().rstrip('\n')
				if header == 'JMXVOBJI1000':
					count = int(f.readline().rstrip('\n'))
					for i in range(count):
						objData = f.readline().rstrip('\n').split(' ',2)
						self._objects_ifo_data[int(objData[0])] = {
							'flags':int(objData[1],16),
							'res_path':[objData[2].replace('"','')],
						}
		# Extract resources from compounds
		for idx in self._objects_ifo_data:
			fileObject = self._objects_ifo_data[idx]
			for i in range(len(fileObject['res_path'])-1,-1,-1):
				res_path = fileObject['res_path'][i]
				object_res_path = os.path.join(self.setting_data_pk2_path,res_path)
				if os.path.exists(object_res_path):
					with open(object_res_path,'rb') as f:
						br = BinaryReader(f.read())
						# Check file signature
						if br.Length < 12 or br.ReadAscii(12) != "JMXVCPD 0101":
							continue
						# Remove this path from resource
						del fileObject['res_path'][i]
						# Read file format
						br.SeekRead(4,1)
						fileOffsetResources = br.ReadUInt()
						# Set cursor at resources
						br.SeekRead(fileOffsetResources)
						resCount = br.ReadUInt()
						for j in range(resCount):
							fileObject['res_path'].append(br.ReadAscii(br.ReadUInt()))
	# Load data required from navmesh
	def LoadTile2dData(self):
		# Abort reloading
		if self._tile2d_ifo_data:
			return
		# Check pk2 path
		if not self.setting_map_pk2_path:
			return
		# Try to load "tile2d.ifo" file
		tile2d_ifo_path = os.path.join(self.setting_map_pk2_path,'tile2d.ifo')
		if os.path.exists(tile2d_ifo_path):
			with open(tile2d_ifo_path,'r') as f:
				# Read file format
				header = f.readline().rstrip('\n')
				if header == 'JMXV2DTI1001':
					count = int(f.readline().rstrip('\n'))
					for i in range(count):
						data01 = f.readline().rstrip('\n').split(' ',2)
						data02 = data01[2].split('" "')	
						data03 = data02[1].split('" ')
						grass = None
						if len(data03) > 1:
							grass = data03[1]
						else:
							data03[0] = data03[0][:-1]
						# store data
						self._tile2d_ifo_data[int(data01[0])] = {
							'type':int(data01[1],16),
							'category':data02[0][1:],
							'path':data03[0],
							'grass':grass
						}

# Export JMXVNVM command
class Export_JMXVNVM(bpy.types.Operator):
	"""Exports a JMXVNVM 1000 file from Silkroad Online using the current selected objects"""
	bl_idname = "silkroad_export.jmxvnvm_1000" # bpy.ops.silkroad_export.jmxvnvm_1000
	bl_label = "Save navmesh into .nvm file(s)"
	# Filter only .nvm files
	filter_glob: StringProperty(
		default="*.nvm",
		options={'HIDDEN'},
		maxlen=255  # Max internal buffer length, longer would be clamped.
	)
	# Add support to select multiples files
	files: CollectionProperty(
		name="File Path",
		type=bpy.types.OperatorFileListElement
	)
	directory: StringProperty(
		subtype='DIR_PATH'
	)
	# Execute command
	def execute(self, Context):
		# Write data into files selected
		for file_elem in self.files:
			if os.path.isfile(os.path.join(self.directory,file_elem.name)):
				self.SaveFile(Context,self.directory,file_elem.name)
		# execution finished
		return {'FINISHED'}
	# Run this as dialog
	def invoke(self, Context, Event):
		# Run file dialog
		Context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	# Saves file from blender
	def SaveFile(self, Context, Path, FileName):
		# List all objects with meshes
		objs = [o for o in Context.selected_objects if o.type == 'MESH' and o.name.endswith('.NavMesh')]
		if not objs:
			return

		# Keep current mode
		userMode = BlenderGetMode()

		for obj in objs:
			# Check if file can be overwritten
			filepath = os.path.join(Path,FileName)+'.nvm'

			# Save data into file
			try:
				self.SaveData(Context,filepath,obj)
			except Exception as ex:
				print('Error saving JMXVNVM file: '+obj.name+' ['+str(ex)+']')
				continue

			# Success
			print('Saved:'+filepath)

		# Get back to normal
		BlenderSetMode(userMode)

	# Save JMXVNVM data into file
	def SaveData(self, Context, FilePath, Obj):
		## WORK IN PROGRESS
		# Try to read JMXNVM file
		br = None
		with open(FilePath, 'rb') as f:
			br = BinaryReader(f.read())
			# Check file signature
			if br.Length < 12 or br.ReadAscii(12) != "JMXVNVM 1000":
				raise Exception('Wrong file format')
		## WORK IN PROGRESS


# Add dynamic menu into Import
def menu_func_import(self, Context):
	self.layout.operator(Import_JMXVNVM.bl_idname, text="JMXVNVM 1000 (.nvm)")

# Register module
def register():
	bpy.utils.register_class(Import_JMXVNVM)
	bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

# Unregister module
def unregister():
	# unregister backwards to avoid issues
	bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
	bpy.utils.unregister_class(Import_JMXVNVM)
