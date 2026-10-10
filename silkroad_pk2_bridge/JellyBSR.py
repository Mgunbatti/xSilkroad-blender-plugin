# Copyright (C) 2023-2026 Engels Quintero <engelsquintero@gmail.com>
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
	"name": "Silkroad JMXVRES",
	"version": (2,1,2),
	"description": ("Import Sikroad Online 3D Resource"),
	"blender": (4,2,0),
	"category": "Import-Export",
	"location": "File > Import",
	"author": "JellyBitz",
}

# Import stuffs
import os
from .import_runtime import execute_import
import bpy
import math
from bpy.props import StringProperty, BoolProperty, CollectionProperty, IntProperty, FloatProperty
from bpy.types import Operator, OperatorFileListElement
from .JellyBMS import BinaryReader, BlenderGetMode, BlenderSetMode

# Get view_layer collection by name
def GetViewLayerCollection(Context,name,collection=None):
	if collection == None:
		collection = Context.view_layer.layer_collection
	# Start search
	if collection.name == name:
		return collection
	for child in collection.children:
		result = GetViewLayerCollection(Context,name,child)
		if result:
			return result
	return None

# Get active view_layer collection
def GetActiveViewLayerCollection(Context):
	return Context.view_layer.active_layer_collection

# Set active view_layer by collection name
def SetActiveViewLayerCollection(Context,name):
	Context.view_layer.active_layer_collection = GetViewLayerCollection(Context,name)

# Check file existence
def FileExists(path):
	return os.path.exists(path) and os.path.isfile(path)
# Check path existence
def DirectoryExists(path):
	return os.path.exists(path) and os.path.isdir(path)

# Import JMXVRES command
class Import_JMXVRES(Operator):
	"""Imports a 3D resource from Silkroad Online"""
	bl_idname = "silkroad_import.jmxvres_0109" # bpy.ops.silkroad_import.jmxvres_0109
	bl_label = "Select .bsr file"
	# Filter only .ban files
	filter_glob: StringProperty(
		default="*.bsr",
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
	setting_data_pk2_path: StringProperty(
		name='Data Path',
		description='Path to the DATA folder from server files',
        default='C:\\Silkroad\\#Server\\Files - Test_In\\Data',
		maxlen=255,
	)
	setting_scale: FloatProperty(
		name="Scale",
		description="Apply general scale to the object",
		default=1,
		min=0.001,
		max=100.0
	)
	setting_collision_box: BoolProperty(
		name="Collision Box",
		description="Load Collision Box from resource",
		default=False,
	)
	setting_bounding_box: BoolProperty(
		name="Bounding Box",
		description="Load Bounding Box from meshes",
		default=False,
	)
	setting_navmesh: BoolProperty(
		name="NavMesh",
		description="Load Navigation Meshes",
		default=False,
	)
	setting_armature: BoolProperty(
		name="Skeleton",
		description="Load Skeleton from resource",
		default=True,
	)
	setting_armature_animations: BoolProperty(
		name="Animations",
		description="Load Animations from resource",
		default=False,
	)
	setting_material_type: IntProperty(
		name="Texture Type",
		description="Set the TextureType to be used as material",
		default=0,
		min=0,
		max=4,
	)
	# Execute command
	def execute(self, Context):
		return execute_import(self, Context, ".bsr")
	# Run this as dialog
	def invoke(self, context, event):
		wm = context.window_manager
		wm.fileselect_add(self)
		return {'RUNNING_MODAL'}
	# Drawing dialog
	def draw(self, Context):
		layout = self.layout
		layout.prop(self,'setting_data_pk2_path')
		layout.prop(self,'setting_scale')
		layout.prop(self,'setting_collision_box')
		layout.prop(self,'setting_bounding_box')
		layout.prop(self,'setting_material_type')

		layout.prop(self,'setting_armature')
		layout_box = layout.box()
		layout_row = layout_box.row()
		if not self.setting_armature:
			layout_row.enabled = False
		layout_row.prop(self,'setting_armature_animations')

		layout.prop(self,'setting_navmesh')
	# Loads file to blender
	def LoadFile(self, Context, FullPath):
		# Try to read file
		br = None
		with open(FullPath, 'rb') as f:
			br = BinaryReader(f.read())
			# Check file signature
			if br.Length < 12 or br.ReadAscii(12) != "JMXVRES 0109":
				raise ValueError("Invalid BSR signature")
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
			print('Error loading JMXVRES file:'+FullPath+' ['+str(ex)+']')
			raise

		# Import data to blender
		userMode = BlenderGetMode()

		# Process Data
		self.ProcessData(Context,data,os.path.basename(FullPath))

		# Get back to normal
		BlenderSetMode(userMode)

		# Success
		print('Loaded:'+FullPath)
		return True
	# Loads the data from file structure
	def LoadData(self, br):
		data = {
			'name':'',
			'collision_box':{},
			'materials':[],
			'meshes':[],
			'armature':'',
			'animations':[]
		}

		# Skip signature
		br.SeekRead(12,1)

		# File offsets
		br.SeekRead(8*4,1)
		# Flags
		meshFlags = br.ReadUInt()
		br.SeekRead(4*4,1)

		# Object info
		br.SeekRead(4,1)
		data['name'] = br.ReadAscii(br.ReadUInt())
		br.SeekRead(4*2,1)
		br.SeekRead(40,1)
		
		# Collision data
		br.SeekRead(br.ReadUInt(),1)
		bbox = data['collision_box']
		for i in range(2):
			x = br.ReadFloat()
			z = br.ReadFloat()
			y = br.ReadFloat()
			bbox['min' if i == 0 else 'max'] = [x,y,z]
		br.SeekRead(24,1)
		requireCollisionMatrix = br.ReadUInt() != 0
		if requireCollisionMatrix:
			br.SeekRead(64,1)

		# Materials
		count = br.ReadUInt()
		for i in range(count):
			mtrlType = br.ReadUInt()
			mtrlPath = br.ReadAscii(br.ReadUInt())
			data['materials'].append({'type':mtrlType,'path':mtrlPath})

		# Meshes
		count = br.ReadUInt()
		for i in range(count):
			data['meshes'].append(br.ReadAscii(br.ReadUInt()))
			if meshFlags & 1:
				br.SeekRead(4,1)

		# Animations
		br.SeekRead(8,1)
		count = br.ReadUInt()
		for i in range(count):
			data['animations'].append(br.ReadAscii(br.ReadUInt()))

		# Skeleton
		hasArmature = br.ReadUInt() != 0
		if hasArmature:
			data['armature'] = br.ReadAscii(br.ReadUInt())

		# Return data
		return data

	# Process data from file into Blender
	def ProcessData(self, Context, data, filename):
		# Make sure data path has been set
		if not self.setting_data_pk2_path or not DirectoryExists(self.setting_data_pk2_path):
			return

		# Object selection poll() fails in Edit/Pose mode. Switch first.
		BlenderSetMode('OBJECT')

		# Deselect all objects
		bpy.ops.object.select_all(action='DESELECT')

		# Create collection with all the stuff from the object
		collection = bpy.data.collections.new(filename+' ['+str(data['name'])+']')
		# Link it to the current collection active
		parentCollection = GetActiveViewLayerCollection(Context).collection
		parentCollection.children.link(collection)
		# Make current collection active temporally
		SetActiveViewLayerCollection(Context,collection.name)

		# Load Collision Box
		if self.setting_collision_box:
			# Make sure bbox has right values to use
			values = data['collision_box']['min'] + data['collision_box']['max']
			createBBox = True
			for value in values:
				if math.isnan(value):
					createBBox = False
					break
			if createBBox:
				# Create object
				mesh = bpy.data.meshes.new("Mesh")
				objBBox = bpy.data.objects.new(data['name']+'.CollisionBox', mesh)
				collection.objects.link(objBBox)
				objBBox.select_set(True)
				# Create mesh
				bboxVertices = [
					[values[0],values[1],values[2]],
					[values[3],values[1],values[2]],
					[values[0],values[4],values[2]],
					[values[3],values[4],values[2]],
					[values[0],values[1],values[5]],
					[values[3],values[1],values[5]],
					[values[0],values[4],values[5]],
					[values[3],values[4],values[5]],
				]
				bboxEdges = [
					[0,1],[0,2],[1,3],[2,3],
					[0,4],[1,5],[2,6],[3,7],
					[4,5],[4,6],[5,7],[6,7],
				]
				mesh.from_pydata(bboxVertices, bboxEdges, [])
				# Apply scale to bbox
				if self.setting_scale != 1:
					objBBox.scale = (self.setting_scale,self.setting_scale,self.setting_scale)
					bpy.ops.object.transform_apply()

		# Load all meshes
		if data['meshes']:
			# Try to select material type or just take the first one
			mtrl = ''
			if data['materials']:
				mtrl = data['materials'][0]['path']
				for m in data['materials']:
					if m['type'] == self.setting_material_type:
						mtrl = m['path']
						break
			# Import mesh
			bpy.ops.silkroad_import.jmxvbms_0110(
				directory=self.setting_data_pk2_path,
				files=[{'name':path} for path in data['meshes']],
				setting_bounding_box=self.setting_bounding_box,
				setting_material_filepath=os.path.join(self.setting_data_pk2_path,mtrl),
				setting_navmesh=self.setting_navmesh,
			)
			# Apply scale to meshes
			if self.setting_scale != 1:
				for o in Context.selected_objects:
					o.scale = (self.setting_scale,self.setting_scale,self.setting_scale)
				bpy.ops.object.transform_apply()

		# Load armature
		if self.setting_armature and data['armature'] and not os.path.isfile(os.path.join(self.setting_data_pk2_path, data['armature'])):
			print('Skeleton warning: missing', data['armature'])
		if self.setting_armature_animations:
			missing_animations = [path for path in data['animations'] if not os.path.isfile(os.path.join(self.setting_data_pk2_path,path))]
			if missing_animations:
				print('Animation warning: missing', missing_animations)
		if self.setting_armature and data['armature'] and os.path.isfile(os.path.join(self.setting_data_pk2_path, data['armature'])):
			# Import armature
			bpy.ops.silkroad_import.jmxvbsk_0110(
				directory=self.setting_data_pk2_path,
				files=[{'name':data['armature']}],
			)
			# Apply scale to armature
			if self.setting_scale != 1:
				for o in Context.selected_objects:
					o.scale = (self.setting_scale,self.setting_scale,self.setting_scale)
				bpy.ops.object.transform_apply()

			# Check if armature loaded
			if Context.selected_objects:
				arm = Context.selected_objects[0]
				# Set Armature Deform modifier to meshes
				meshes = [o for o in collection.all_objects if o.type == 'MESH' and not o.name.endswith('.BoundingBox') and not o.name.endswith('.NavMesh') and not o.name.endswith('.CollisionBox')]
				for mesh in meshes:
					# Add modifier
					mod = mesh.modifiers.new('Armature', 'ARMATURE')
					# Set parent
					mod.object = mesh.parent = arm
				# Load animations
				if self.setting_armature_animations and any(os.path.isfile(os.path.join(self.setting_data_pk2_path,path)) for path in data['animations']):
					# Import animations into selected armature
					bpy.ops.silkroad_import.jmxvban_0102(
						directory=self.setting_data_pk2_path,
						files=[{'name':path} for path in data['animations'] if os.path.isfile(os.path.join(self.setting_data_pk2_path,path))],
						setting_scale=self.setting_scale,
					)
		# Return selected collection to the original
		SetActiveViewLayerCollection(Context,parentCollection.name)

# Add dynamic menu into Import
def menu_func_import(self, Context):
	self.layout.operator(Import_JMXVRES.bl_idname, text="JMXVRES 0109 (.bsr)")

# Register module
def register():
	bpy.utils.register_class(Import_JMXVRES)
	bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

# Unregister module
def unregister():
	# unregister backwards to avoid issues
	bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
	bpy.utils.unregister_class(Import_JMXVRES)
