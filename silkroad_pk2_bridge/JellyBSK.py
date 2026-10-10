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
	"name": "Silkroad JMXVBSK",
	"version": (2,0,4),
	"description": ("Import and export Sikroad Online skeletons"),
	"blender": (4,2,0),
	"category": "Import-Export",
	"location": "File > Import/Export",
	"author": "JellyBitz",
}

# Import stuffs
import os
from .import_runtime import execute_import
import struct
import bpy
import bmesh
from bpy.props import StringProperty, BoolProperty, CollectionProperty
from bpy.types import Operator, OperatorFileListElement
from math import radians
from mathutils import Vector, Matrix, Quaternion, Euler

# Get current mode from blender
def BlenderGetMode():
	return bpy.context.object.mode if bpy.context.object else 'OBJECT'

# Switch mode from blender without context errors
def BlenderSetMode(NewMode):
	mode = BlenderGetMode()
	if mode != NewMode:
		bpy.ops.object.mode_set(mode=NewMode)

# Fix the NaN/Infinite values for a fixed one
def FixNaN(value, default):
	return default if value != value else value

# Reads binary data
class BinaryReader():
	# Constructor
	def __init__(self, Buffer):
		self.Buffer = Buffer
		self.Length = len(Buffer)
		self.Position = 0
	# Set the cursor position for reading
	def SeekRead(self,Offset,SeekOrigin=0):
		if SeekOrigin == 1: # Current
			self.Position += Offset
		elif SeekOrigin == 2: # End
			self.Position = self.Length + Offset
		else: # Begin
			self.Position = Offset
	# Generic Python way for reading and moving the cursor
	def ReadPython(self,Format,Size):
		result = struct.unpack_from(Format,self.Buffer,self.Position)[0]
		self.Position += Size
		return result
	# Reads an array of chars
	def ReadBytes(self,Count):
		return self.ReadPython('<'+str(Count)+'s',Count)
	# Reads a byte
	def ReadByte(self):
		return self.ReadPython('<B',1)
	# Reads a signed byte
	def ReadSByte(self):
		return self.ReadPython('<b',1)
	# Reads an unsigned short
	def ReadUShort(self):
		return self.ReadPython('<H',2)
	# Reads a short
	def ReadShort(self):
		return self.ReadPython('<h',2)
	# Reads an unsigned integer
	def ReadUInt(self):
		return self.ReadPython('<I',4)
	# Reads an integer
	def ReadInt(self):
		return self.ReadPython('<i',4)
	# Reads a floating point
	def ReadFloat(self):
		return self.ReadPython('<f',4)
	# Reads an string by codepage
	def ReadString(self, Count, CodePage):
		return self.ReadBytes(Count).decode(CodePage)
	# Reads an string as ascii
	def ReadAscii(self, Count):
		return self.ReadString(Count,'cp1252')

# Writes binary data
class BinaryWriter():
	# Constructor
	def __init__(self,Buffer=b''):
		self.Buffer = Buffer
		self.Length = 0
		self.Position = 0
	# Set the cursor position for writing
	def SeekWrite(self,Offset,SeekOrigin=0):
		if SeekOrigin == 1: # Current
			self.Position += Offset
		elif SeekOrigin == 2: # End
			self.Position = self.Length + Offset
		else: # Begin
			self.Position = Offset
	# Generic Python way for writing and moving the cursor
	def WritePython(self,Format,Size,Value):
		# insert value into current buffer
		self.Buffer = self.Buffer[:self.Position] + struct.pack(Format,Value) + self.Buffer[self.Position+Size:]
		self.Length = len(self.Buffer)
		self.Position += Size
	# Writes an array of chars
	def WriteBytes(self,Bytes):
		length = len(Bytes)
		self.WritePython('<'+str(length)+'s',length,Bytes)
	# Removes an amount of bytes from buffer using the current position
	def RemoveBytes(self,Count):
		self.Buffer = self.Buffer[:self.Position] + self.Buffer[self.Position+Count:]
		self.Length = len(self.Buffer)
	# Writes a byte
	def WriteByte(self,Value):
		self.WritePython('<B',1,Value)
	# Writes a signed byte
	def WriteSByte(self,Value):
		self.WritePython('<b',1,Value)
	# Writes an unsigned short
	def WriteUShort(self,Value):
		self.WritePython('<H',2,Value)
	# Writes a short
	def WriteShort(self,Value):
		self.WritePython('<h',2,Value)
	# Writes an unsigned integer
	def WriteUInt(self,Value):
		self.WritePython('<I',4,Value)
	# Writes an integer
	def WriteInt(self,Value):
		self.WritePython('<i',4,Value)
	# Writes a floating point
	def WriteFloat(self,Value):
		self.WritePython('<f',4,Value)
	# Writes an string by codepage
	def WriteString(self,StrValue,CodePage):
		self.WriteBytes(StrValue.encode(CodePage))
	# Writes an string as ascii
	def WriteAscii(self,StrValue):
		self.WriteString(StrValue,'cp1252')

# Import JMXVBSK command
class Import_JMXVBSK_0110(Operator):
	"""Imports a JMXVBSK 0101 file from Silkroad Online"""
	bl_idname = "silkroad_import.jmxvbsk_0110" # bpy.ops.silkroad_import.jmxvbsk_0110
	bl_label = "Select .bsk file"
	# Filter only .bsk files
	filter_glob: StringProperty(
		default="*.bsk",
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
	setting_skeleton_mode: BoolProperty(
		name="Create skeleton model",
		description="Creates a skeleton used for modeling",
		default=False,
	)
	# Execute command
	def execute(self, Context):
		return execute_import(self, Context, ".bsk")
	# Run this as dialog
	def invoke(self, context, event):
		wm = context.window_manager
		wm.fileselect_add(self)
		return {'RUNNING_MODAL'}
	# Loads file to blender
	def LoadFile(self, Context, FullPath):
		# Try to read file
		br = None
		with open(FullPath, 'rb') as f:
			br = BinaryReader(f.read())
			# Check file signature
			if br.Length < 12 or br.ReadAscii(12) != "JMXVBSK 0101":
				raise ValueError("Invalid BSK signature")
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
			print('Error loading bsk file:'+FullPath)
			raise

		# Import data to blender
		userMode = BlenderGetMode()

		# Process Data
		self.ProcessData(Context,data,os.path.splitext(os.path.basename(FullPath))[0])

		# Get back to normal
		BlenderSetMode(userMode)

		# Success
		print('Loaded:'+FullPath)
		return True
	# Loads the data from file structure
	def LoadData(self, br):
		result = {}

		# Skip header
		br.SeekRead(12,1)

		# Load bones
		bones = {}
		result['bones'] = bones
		
		boneCount = br.ReadUInt()
		for i in range(boneCount):
			bone = {}
			# Bone info
			bone['type'] = br.ReadByte()
			bone['name'] = br.ReadAscii(br.ReadUInt())
			bone['parent_name'] = br.ReadAscii(br.ReadUInt())

			# Transform relative to parent bone
			x,y,z,w = FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0)
			bone['parent_rotation'] = Quaternion((w,x,y,z))
			x,y,z = FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0)
			bone['parent_translation'] = Vector((x,y,z))
			bone['parent_translation'].negate() # Fix opposite vector values

			# Transform relative to world origin
			x,y,z,w = FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0)
			bone['origin_rotation'] = Quaternion((w,x,y,z))
			x,y,z = FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0)
			bone['origin_translation'] = Vector((x,y,z))
			bone['origin_translation'].negate() # Fix opposite vector values

			# Transform relative to local armature
			x,y,z,w = FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0)
			bone['local_rotation'] = Quaternion((w,x,y,z))
			x,y,z = FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0), FixNaN(br.ReadFloat(),0)
			bone['local_translation'] = Vector((x,y,z))
			bone['local_translation'].negate() # Fix opposite vector values

			boneChilds = []
			bone['childs'] = boneChilds

			childBoneCount = br.ReadUInt()
			for i in range(childBoneCount):
				boneChilds.append(br.ReadAscii(br.ReadUInt()))

			bones[bone['name']] = bone

		#unkUInt01 = br.ReadUInt()
		#unkUInt02 = br.ReadUInt()

		return result

	# Process data from file into Blender
	def ProcessData(self, Context, data, name):
		# Create armature
		BlenderSetMode('OBJECT')
		bpy.ops.object.armature_add(enter_editmode=False)
		armature = bpy.context.view_layer.objects.active
		armature.name = armature.data.name = name
		armature.show_in_front = True
		armature.data.display_type = 'STICK' if not self.setting_skeleton_mode else 'OCTAHEDRAL'
		if self.setting_skeleton_mode:
			armature.matrix_world @= Euler((radians(-90),0.0,radians(180)),'XYZ').to_matrix().to_4x4()
		# Delete default bones
		BlenderSetMode('EDIT')
		for b in armature.data.edit_bones:
			armature.data.edit_bones.remove(b)

		# Create bone by bone
		for name in data['bones']:
			bone = data['bones'][name]
			parent_name = bone['parent_name']
			# Create bone
			editBone = armature.data.edit_bones.new(name=name)
			editBone.use_connect = False

			# Set parent
			if parent_name:
				editBone.parent = armature.data.edit_bones[parent_name]

			# Check which skeleton is going to be loaded
			if self.setting_skeleton_mode:
				# Connected bones
				editBone.head = bone['origin_translation']
				editBone.tail = editBone.parent.head if parent_name else editBone.head
				# Make sure is not going to be deleted by Blender
				if editBone.length <= 0.001:
					editBone.length = 0.001
			else:
				# Disconnected bones
				editBone.length = 0.001
				# Set transformation relative to parent
				if parent_name:
					editBone.matrix = editBone.parent.matrix
				else:
					editBone.matrix = Matrix() @ Euler((radians(-90),0.0,radians(180)),'XYZ').to_matrix().to_4x4()
				editBone.matrix = editBone.matrix @ Matrix.Translation(bone['parent_translation']) @ bone['parent_rotation'].to_matrix().to_4x4()

		# Fix root bones
		for editBone in armature.data.edit_bones:
			if not editBone.parent:
				# Merge into one
				childs = data['bones'][editBone.name]['childs']
				for boneName in childs:
					childBone = armature.data.edit_bones.get(boneName)
					if childBone != None and childBone.parent == None:
						childBone.parent = editBone

		# Fix direction from skeleton mode
		if self.setting_skeleton_mode:
			for editBone in armature.data.edit_bones:
				# Just try switch direction
				if len(editBone.children) >= 1:
					editBone.tail = editBone.children[0].head
				else:
					# Leaf bone
					oldBoneHead = editBone.head.copy()
					rotation = Matrix.Rotation(radians(180), 4, editBone.x_axis.normalized())   
					editBone.transform(rotation, roll=True) 
					offset_vec = -(editBone.head - oldBoneHead)
					editBone.head += offset_vec
					editBone.tail += offset_vec

	

# Export JMXVBSK command
class Export_JMXVBSK_0110(Operator):
	"""Exports a JMXVBSK 0101 file from Silkroad Online using the current selected objects"""
	bl_idname = "silkroad_export.jmxvbsk_0101" # bpy.ops.silkroad_export.jmxvbsk_0101
	bl_label = "Save .bsk files"
	# Directory path selected
	directory: StringProperty(
		subtype='DIR_PATH'
	)
	# Show .bsk files
	filter_glob: StringProperty(
		default="*.bsk",
		options={'HIDDEN'},
		maxlen=255  # Max internal buffer length, longer would be clamped.
	)
	# Settings
	setting_overwrite: BoolProperty(
		name="Overwrite existing files",
		description="Overwrites existing file with the same armature name",
		default=False,
	)
	# Execute command
	def execute(self, Context):
		# Overwrite into file selected
		self.SaveFile(Context)
		# execution finished
		return {'FINISHED'}
	# Run this as dialog
	def invoke(self, Context, Event):
		wm = Context.window_manager
		wm.fileselect_add(self)
		return {'RUNNING_MODAL'}
	# Save JMXVBSK file structure
	def SaveData(self, Context, FilePath, Obj):
		# Reset all pose bones to rest position
		BlenderSetMode('POSE')
		for poseBone in Obj.pose.bones:
			poseBone.matrix_basis.identity()
		# Rotate the object to match import
		Obj.matrix_world @= Euler((radians(-90),0.0,radians(180)),'XYZ').to_matrix().to_4x4()
		BlenderSetMode('OBJECT')
		bpy.ops.object.transform_apply()
		BlenderSetMode('POSE')

		# Save file structure
		bw = BinaryWriter()
		# Header
		bw.WriteAscii('JMXVBSK 0101')

		boneCount = len(Obj.pose.bones)
		# Fix root bone if possible
		rootBones = []
		for poseBone in Obj.pose.bones:
			if poseBone.parent == None:
				rootBones.append(poseBone.name)
		boneCount += (1 if len(rootBones) > 1 else 0)

		# Bones
		bw.WriteUInt(boneCount)

		# Insert root bone
		if len(rootBones) > 1:
			bw.WriteByte(0) # Type
			name = '[root]' # Default Name
			bw.WriteUInt(len(name))
			bw.WriteAscii(name)
			bw.WriteUInt(0) # Parent name
			# Rotations and translations
			bw.WriteBytes(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
			bw.WriteBytes(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
			bw.WriteBytes(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
			# Root childs
			bw.WriteUInt(len(rootBones))
			for name in rootBones:
				bw.WriteUInt(len(name))
				bw.WriteAscii(name)

		# Writing bone by bone
		for poseBone in Obj.pose.bones:
			# Type
			bw.WriteByte(0)
			# Name
			bw.WriteUInt(len(poseBone.bone.name))
			bw.WriteAscii(poseBone.bone.name)
			# Parent info
			if poseBone.parent == None:
				parentName = ''
				matrix_parent_relative = poseBone.matrix
			else:
				parentName = poseBone.bone.parent.name
				matrix_parent_relative = poseBone.parent.matrix.inverted_safe() @ poseBone.matrix
			bw.WriteUInt(len(parentName))
			bw.WriteAscii(parentName)
			# Matrix relative to parent
			rotation = matrix_parent_relative.to_quaternion()
			bw.WriteFloat(rotation.x)
			bw.WriteFloat(rotation.y)
			bw.WriteFloat(rotation.z)
			bw.WriteFloat(rotation.w)
			translation = matrix_parent_relative.to_translation()
			translation.negate()
			bw.WriteFloat(translation.x)
			bw.WriteFloat(translation.y)
			bw.WriteFloat(translation.z)
			# Matrix relative to origin
			matrix_origin_relative = Obj.matrix_world.inverted_safe() @ poseBone.matrix
			rotation = matrix_origin_relative.to_quaternion()
			bw.WriteFloat(rotation.x)
			bw.WriteFloat(rotation.y)
			bw.WriteFloat(rotation.z)
			bw.WriteFloat(rotation.w)
			translation = matrix_origin_relative.to_translation()
			translation.negate()
			bw.WriteFloat(translation.x)
			bw.WriteFloat(translation.y)
			bw.WriteFloat(translation.z)
			# Matrix relative to armature
			matrix_local_relative = poseBone.bone.matrix_local.inverted_safe()
			rotation = matrix_local_relative.to_quaternion()
			bw.WriteFloat(rotation.x)
			bw.WriteFloat(rotation.y)
			bw.WriteFloat(rotation.z)
			bw.WriteFloat(rotation.w)
			translation = matrix_local_relative.to_translation()
			translation.negate()
			bw.WriteFloat(translation.x)
			bw.WriteFloat(translation.y)
			bw.WriteFloat(translation.z)
			# Bone children
			bw.WriteUInt(len(poseBone.children))
			for child in poseBone.children:
				bw.WriteUInt(len(child.name))
				bw.WriteAscii(child.name)

		# Unknown data
		bw.WriteUInt(0)
		bw.WriteUInt(0)

		# Rotate the object as original
		Obj.matrix_world @= Euler((radians(-90),0.0,radians(180)),'XYZ').to_matrix().to_4x4()
		BlenderSetMode('OBJECT')
		bpy.ops.object.transform_apply()
		BlenderSetMode('POSE')

		# Overwrite file
		with open(FilePath,'wb') as f:
			f.write(bw.Buffer)

	# Saves file from blender
	def SaveFile(self, Context):
		# List all objects with skeletons
		objs = [o for o in Context.selected_objects if o.type == 'ARMATURE']
		if not objs:
			return
		# Keep current mode
		userMode = BlenderGetMode()

		# Check saving mode
		for obj in objs:
			# Check if file can be overwritten
			filepath = os.path.join(self.directory,obj.name)+'.bsk'
			if os.path.exists(filepath) and not self.setting_overwrite:
				continue
				
			# Save data structure
			try:
				self.SaveData(Context,filepath,obj)
			except Exception as ex:
				print('Error saving JMXVBSK file: '+obj.name+' ['+str(ex)+']')
				continue

			# Success
			print('Saved:'+filepath)

		# Get back to normal
		BlenderSetMode(userMode)

# Add dynamic menu into Import
def menu_func_import(self, Context):
	self.layout.operator(Import_JMXVBSK_0110.bl_idname, text="JMXVBSK 0101 (.bsk)")
# Add dynamic menu into Export
def menu_func_export(self, Context):
	self.layout.operator(Export_JMXVBSK_0110.bl_idname, text="JMXVBSK 0101 (.bsk)")

# Register module
def register():
	bpy.utils.register_class(Import_JMXVBSK_0110)
	bpy.utils.register_class(Export_JMXVBSK_0110)
	bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
	bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

# Unregister module
def unregister():
	# unregister backwards to avoid issues
	bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
	bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
	bpy.utils.unregister_class(Export_JMXVBSK_0110)
	bpy.utils.unregister_class(Import_JMXVBSK_0110)