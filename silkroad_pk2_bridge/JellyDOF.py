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
	"name": "Silkroad JMXVDOF",
	"version": (2,0,2),
	"description": ("Import Sikroad Online Dungeon File Data"),
	"blender": (4,2,0),
	"category": "Import-Export",
	"location": "File > Import",
	"author": "JellyBitz",
}

# Import stuffs
import os
from .map_data import parse_dof
from .import_runtime import execute_import
import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty, FloatProperty
from bpy.types import Operator, OperatorFileListElement
from .JellyBMS import BinaryReader, BlenderGetMode, BlenderSetMode
from .JellyBSR import GetViewLayerCollection, GetActiveViewLayerCollection, SetActiveViewLayerCollection

# Get children from collection by name
def GetLayerCollection(collection,name):
	if collection.name == name:
		return collection
	for child in collection.children:
		result = GetLayerCollection(child,name)
		if result:
			return result
	return None

# Import JMXVDOF command
class Import_JMXVDOF(Operator):
	"""Imports a Dungeon File from Silkroad Online"""
	bl_idname = "silkroad_import.jmxvdof_0101" # bpy.ops.silkroad_import.JMXVDOF_0101
	bl_label = "Select .dof file"
	# Filter only .ban files
	filter_glob: StringProperty(
		default="*.dof",
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
	setting_block_offset: BoolProperty(
		name="Block Offset",
		description="Keep the offset position from the blocks",
		default=True,
	)
	setting_data_pk2_path: StringProperty(
		name='Data Path',
		description='Path to the DATA folder from server files',
		default='C:\\Silkroad\\#Server\\Files - Test_In\\Data',
		maxlen=255,
	)
	setting_navmesh: BoolProperty(
		name="NavMesh",
		description="Load Navigation Mesh from objects",
		default=False,
	)
	setting_load_objects: BoolProperty(
		name="Objects",
		description="Load individual objects from dungeon",
		default=False,
	)
	# Execute command
	def execute(self, Context):
		return execute_import(self, Context, ".dof")
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
		layout.prop(self,'setting_block_offset')
		layout.prop(self,'setting_navmesh')
		layout.prop(self,'setting_load_objects')
	# Loads file to blender
	def LoadFile(self, Context, Path, FileName):
		# Try to read file
		br = None
		filePath = os.path.join(Path,FileName)
		with open(filePath, 'rb') as f:
			br = BinaryReader(f.read())
			# Check file signature
			if br.Length < 12 or br.ReadAscii(12) != "JMXVDOF 0101":
				raise ValueError("Invalid DOF signature")
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
			print('Error loading JMXVDOF file:'+FileName+' ['+str(ex)+']')
			raise

		# Import data to blender
		userMode = BlenderGetMode()

		# Process Data
		name = os.path.splitext(FileName)[0]
		self.ProcessData(Context,data,name)

		# Get back to normal
		BlenderSetMode(userMode)

		# Success
		print('Loaded:'+filePath)
		return True
	# Loads the data from file structure
	def LoadData(self, br):
		data = parse_dof(br.Buffer)
		# Load mesh and mtrl from each block and objects	
		if self.setting_data_pk2_path:
			for block in data['blocks']:
				block['mesh'],block['mtrl'] = self.GetMeshAndMtrlFromResource(os.path.join(self.setting_data_pk2_path,block['path']))
				if self.setting_load_objects:
					for obj in block['objects']:
						obj['mesh'],obj['mtrl'] = self.GetMeshAndMtrlFromResource(os.path.join(self.setting_data_pk2_path,obj['path']))

		# Return data
		return data
	# Load the mesh and material from binary resource (.bsr)
	def GetMeshAndMtrlFromResource(self,res_path):
		mesh = []
		mtrl = ''
		# Check existence
		if os.path.exists(res_path):
			with open(res_path,'rb') as f:
				br = BinaryReader(f.read())
				# Check file signature
				if br.Length > 12 and br.ReadAscii(12) == "JMXVRES 0109":
					# Read file format
					fileOffsetMtrl = br.ReadUInt()
					fileOffsetMesh = br.ReadUInt()
					br.SeekRead(6*4,1)
					meshFlags = br.ReadUInt()
					# Set cursor at meshes
					br.SeekRead(fileOffsetMesh)
					meshCount = br.ReadUInt()
					for i in range(meshCount):
						meshPath = br.ReadAscii(br.ReadUInt())
						# Make sure it exists
						meshPath = os.path.join(self.setting_data_pk2_path,meshPath)
						if os.path.exists(meshPath):
							mesh.append(meshPath)
						# continue reading file format
						if meshFlags & 1:
							br.SeekRead(4,1)
					# Set cursor at mtrl
					br.SeekRead(fileOffsetMtrl)
					mtrlCount = br.ReadUInt()
					for i in range(mtrlCount):
						br.SeekRead(4,1)
						# Set first one only
						mtrl = br.ReadAscii(br.ReadUInt())
						break
		return mesh,mtrl

	# Process data from file into Blender
	def ProcessData(self, Context, data, name):
		BlenderSetMode('OBJECT')

		# Keep current collection
		parentCollection = GetActiveViewLayerCollection(Context).collection

		# Check all blocks
		for block in data['blocks']:
			# Collection with everything into each block
			collection = bpy.data.collections.new(name+' - Block['+str(block['index'])+'] ['+str(block['name'])+']')
			parentCollection.children.link(collection)
			SetActiveViewLayerCollection(Context,collection.name)

			# Make sure there is a mesh to load
			if block['mesh']:
				# Load meshes from block
				bpy.ops.silkroad_import.jmxvbms_0110(
					directory=self.setting_data_pk2_path,
					files=[{'name':path} for path in block['mesh']],
					setting_navmesh=self.setting_navmesh,
					setting_material_filepath=os.path.join(self.setting_data_pk2_path,block['mtrl']),
				)
				# Move meshes to their positions
				for o in Context.selected_objects:
					if self.setting_block_offset:
						o.location = (block['position'][0]*self.setting_scale, block['position'][1]*self.setting_scale, block['position'][2]*self.setting_scale)
					o.rotation_euler[2] = block['yaw']
					o.scale = [self.setting_scale,self.setting_scale,self.setting_scale]
			# Load objects if there is any
			if self.setting_load_objects and block['objects']:
				# Collection with all objects from block
				objCollection = bpy.data.collections.new('Block['+str(block['index'])+'] - Objects')
				collection.children.link(objCollection)
				SetActiveViewLayerCollection(Context,objCollection.name)
				# Load all objects
				for obj in block['objects']:
					# Make sure there is a mesh at least
					if obj['mesh']:
						# Load meshes from block
						bpy.ops.silkroad_import.jmxvbms_0110(
							directory=self.setting_data_pk2_path,
							files=[{'name':path} for path in obj['mesh']],
							setting_navmesh=self.setting_navmesh,
							setting_material_filepath=os.path.join(self.setting_data_pk2_path,obj['mtrl']),
						)
					# Move meshes to their positions
					for o in Context.selected_objects:
						o.location = (obj['position'][0]*self.setting_scale, obj['position'][1]*self.setting_scale, obj['position'][2]*self.setting_scale)
						o.rotation_euler = obj['rotation']
						o.scale = [self.setting_scale*obj['scale'][0],self.setting_scale*obj['scale'][1],self.setting_scale*obj['scale'][2]]

		# Return selected collection to the original
		SetActiveViewLayerCollection(Context,parentCollection.name)

# Add dynamic menu into Import
def menu_func_import(self, Context):
	self.layout.operator(Import_JMXVDOF.bl_idname, text="JMXVDOF 0101 (.dof)")

# Register module
def register():
	bpy.utils.register_class(Import_JMXVDOF)
	bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

# Unregister module
def unregister():
	# unregister backwards to avoid issues
	bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
	bpy.utils.unregister_class(Import_JMXVDOF)