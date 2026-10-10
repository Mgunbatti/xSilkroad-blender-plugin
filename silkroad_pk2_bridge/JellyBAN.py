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
	"name": "Silkroad JMXVBAN",
	"version": (2,1,3),
	"description": ("Import and export Sikroad Online animations"),
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
from bpy.props import StringProperty, BoolProperty, CollectionProperty, FloatProperty, IntProperty
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

# Import JMXVBAN command
class Import_JMXVBAN_0102(Operator):
	"""Imports a JMXVBAN 0102 file from Silkroad Online"""
	bl_idname = "silkroad_import.jmxvban_0102" # bpy.ops.silkroad_import.jmxvban_0102
	bl_label = "Select .ban file"
	# Filter only .ban files
	filter_glob: StringProperty(
		default="*.ban",
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
		description="Apply animation object scale",
		default=1.0,
		min=0.001,
		max=1000.0
	)
	setting_interpolation_constant : BoolProperty(
		name="Constant interpolation",
		description="Set all keyframes to constant interpolation by default",
		default=False,
	)
	settings_rot_x_axis: FloatProperty(
		name="X",
		description="Apply degrees rotation at X axis",
		default=0.0,
		min=-360,
		max=360
	)
	settings_rot_y_axis: FloatProperty(
		name="Y",
		description="Apply degrees rotation at X axis",
		default=0.0,
		min=-360,
		max=360
	)
	settings_rot_z_axis: FloatProperty(
		name="Z",
		description="Apply degrees rotation at X axis",
		default=0.0,
		min=-360,
		max=360
	)
	# Execute command
	def execute(self, Context):
		return execute_import(self, Context, ".ban")
	# Run this as dialog
	def invoke(self, context, event):
		wm = context.window_manager
		wm.fileselect_add(self)
		return {'RUNNING_MODAL'}
	# Drawing dialog
	def draw(self, Context):
		layout = self.layout
		layout.prop(self,'setting_scale')
		layout.prop(self,'setting_interpolation_constant')
		layout_row = layout.row()
		layout_row.prop(self,'settings_rot_x_axis')
		layout_row.prop(self,'settings_rot_y_axis')
		layout_row.prop(self,'settings_rot_z_axis')
	# Loads file to blender
	def LoadFile(self, Context, FullPath):
		# Try to read file
		br = None
		with open(FullPath, 'rb') as f:
			br = BinaryReader(f.read())
			# Check file signature
			if br.Length < 12 or br.ReadAscii(12) != "JMXVBAN 0102":
				raise ValueError("Invalid BAN signature")
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
			print('Error loading JMXVBAN file:'+FullPath)
			raise

		# Import data to blender
		userMode = BlenderGetMode()

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
		# Skip empty values
		br.SeekRead(8,1)

		# Read general info
		result['name'] = br.ReadAscii(br.ReadUInt())
		result['duration'] = br.ReadUInt()
		result['fps'] = br.ReadUInt()
		result['is_cyclic'] = br.ReadUInt() == 1

		# Keyframe times
		keyframes = []
		result['keyframes'] = keyframes
		keyframeCount = br.ReadUInt()
		for i in range(keyframeCount):
			keyframes.append(br.ReadUInt())

		# Bones with transformations
		bones = []
		result['bones'] = bones
		boneCount = br.ReadUInt()
		for i in range(boneCount):
			bone = {}
			bones.append(bone)
			bone['name'] = br.ReadAscii(br.ReadUInt())
			boneKeyframeCount = br.ReadUInt()
			boneKeyframes = []
			bone['keyframes'] = boneKeyframes
			for j in range(boneKeyframeCount):
				boneKeyframe = {} 
				x,y,z,w = br.ReadFloat(), br.ReadFloat(), br.ReadFloat(), br.ReadFloat()
				boneKeyframe['parent_rotation'] = Quaternion((w,x,y,z))
				x,y,z = br.ReadFloat(), br.ReadFloat(), br.ReadFloat()
				boneKeyframe['parent_translation'] = Vector((x,y,z))
				boneKeyframe['parent_translation'].negate() # Fix opposite vector values
				boneKeyframes.append(boneKeyframe)

		# Return data
		return result

	# Process data from file into Blender
	def ProcessData(self, Context, data, name):
		# Find all objects selected with skeletons
		objs = [o for o in Context.selected_objects if o.type == 'ARMATURE']
		if objs:
			# Apply fps synchronization (1 Frame = 1000 SRO Frames)
			sync_fps = 1000 / data['fps']

			# Prepare basic info for scene
			Context.scene.render.fps = data['fps']
			Context.scene.frame_start = 0
			Context.scene.frame_end = round(data['duration']/sync_fps)

			# Try to apply animation to all skeletons found
			for obj in objs:
				# Cache curves: millions of linear F-Curve lookups are expensive.
				self._fcurve_cache = {}
				# Create animation set for this object
				if not obj.animation_data:
					obj.animation_data_create()
				nla_track = None

				# Set mode to apply bone animation
				BlenderSetMode('POSE')
				# Insert keyframes in order
				for i in range(len(data['keyframes'])):
					# Into each bone
					for bone in data['bones']:
						# Try to find this bone into this object
						poseBone = obj.pose.bones.get(bone['name'],None)
						if poseBone == None:
							continue
						# Get keyframe data from this bone
						keyframeData = bone['keyframes'][i]
						frame = data['keyframes'][i]/sync_fps

						# Set transformation relative to parent
						if poseBone.parent:
							matrix_parent_relative = poseBone.parent.matrix
						else:
							matrix_parent_relative = Matrix() @ Euler((radians(-90),0.0,radians(180)),'XYZ').to_matrix().to_4x4()
							# Apply rotation to root bones only
							if self.settings_rot_x_axis or self.settings_rot_y_axis or self.settings_rot_z_axis:
								matrix_parent_relative @= Euler((radians(self.settings_rot_y_axis),radians(self.settings_rot_z_axis),radians(self.settings_rot_x_axis)),'XYZ').to_matrix().to_4x4()
						# Check for custom scale
						if self.setting_scale != 1.0:
							loc,rot,sca = matrix_parent_relative.decompose()
							matrix_parent_relative = Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ Matrix.Scale(self.setting_scale,4)
						
						# Set pose transformation
						poseBone.matrix = matrix_parent_relative @ Matrix.Translation(keyframeData['parent_translation']) @ keyframeData['parent_rotation'].to_matrix().to_4x4()

						# Create this set as Non Linear Animation
						if nla_track == None:
							# Create action
							action = bpy.data.actions.new(data['name'])
							action.use_fake_user = True
							action.use_cyclic = data['is_cyclic']
							obj.animation_data.action = action
							# Blender 4.4+ actions are slotted/layered, and Blender 5.0
							# removed Action.fcurves. Create a matching slot BEFORE NLA.
							if hasattr(action, 'slots'):
								slot = action.slots.new(obj.id_type, obj.name)
								layer_strip = action.layers.new('Base Layer').strips.new(type='KEYFRAME')
								layer_strip.channelbag(slot, ensure=True)
								obj.animation_data.action_slot = slot
							# Create NLA track on armature
							nla_track = obj.animation_data.nla_tracks.new()
							nla_track.select = True
							nla_track.mute = True
							nla_track.name = name
							# Strip options
							strip = nla_track.strips.new(action.name,0,action)
							strip.action_frame_start = Context.scene.frame_start
							strip.action_frame_end = Context.scene.frame_end
							strip.use_animated_time_cyclic = data['is_cyclic']

						# FCurve values for location
						dataPath = 'pose.bones["'+bone['name']+'"].location'
						self.ActionFCurve(obj.animation_data.action,obj,dataPath,frame,poseBone.location.x,0)
						self.ActionFCurve(obj.animation_data.action,obj,dataPath,frame,poseBone.location.y,1)
						self.ActionFCurve(obj.animation_data.action,obj,dataPath,frame,poseBone.location.z,2)
						# FCurve values for rotation
						dataPath = 'pose.bones["'+bone['name']+'"].rotation_quaternion'
						self.ActionFCurve(obj.animation_data.action,obj,dataPath,frame,poseBone.rotation_quaternion.w,0)
						self.ActionFCurve(obj.animation_data.action,obj,dataPath,frame,poseBone.rotation_quaternion.x,1)
						self.ActionFCurve(obj.animation_data.action,obj,dataPath,frame,poseBone.rotation_quaternion.y,2)
						self.ActionFCurve(obj.animation_data.action,obj,dataPath,frame,poseBone.rotation_quaternion.z,3)

				# If some animation has been loaded, reset pose bones
				if nla_track:
					# Reset pose bones to rest pose
					for poseBone in obj.pose.bones:
						poseBone.matrix_basis.identity()

	# Applies FCurve to the Action slot of this skeleton.
	def ActionFCurve(self, Action, Owner, DataPath, Frame, Value, Index):
		key = (DataPath, Index)
		cache = getattr(self, '_fcurve_cache', None)
		if cache is not None:
			fcurve = cache.get(key)
		else:
			fcurve = None
		if fcurve is None:
			if hasattr(Action, 'fcurve_ensure_for_datablock'):
				# Blender 4.4+; official replacement for Action.fcurves
				fcurve = Action.fcurve_ensure_for_datablock(Owner, DataPath, index=Index)
			else:
				# Blender 4.2/4.3 compatibility
				fcurve = Action.fcurves.find(DataPath, index=Index)
				if fcurve is None:
					fcurve = Action.fcurves.new(DataPath, index=Index)
			if cache is not None:
				cache[key] = fcurve
		kp = fcurve.keyframe_points.insert(Frame, Value, options={'FAST'})
		if self.setting_interpolation_constant:
			kp.interpolation = 'CONSTANT'

# Export JMXVBAN command
class Export_JMXVBAN_0102(Operator):
	"""Exports a JMXVBAN 0102 file from Silkroad Online using the current scene"""
	bl_idname = "silkroad_export.jmxvban_0102" # bpy.ops.silkroad_export.jmxvban_0102
	bl_label = "Save .ban files"
	# Directory path selected
	directory: StringProperty(
		subtype='DIR_PATH'
	)
	# Show .ban files
	filter_glob: StringProperty(
		default="*.ban",
		options={'HIDDEN'},
		maxlen=255  # Max internal buffer length, longer would be clamped.
	)
	# Settings
	setting_overwrite: BoolProperty(
		name="Overwrite existing files",
		description="Overwrites existing file with the same name",
		default=False,
	)
	setting_is_cyclic: BoolProperty(
		name="Cyclic",
		description="Set animation as cyclic sequence",
		default=False,
	)
	setting_fps: IntProperty(
		name="FPS",
		description="Frames per second. Blender FPS setting is being used as default",
		default=24,
		min=1,
		max=120,
		step=100,
	)
	# Execute command
	def execute(self, Context):
		# Overwrite into file selected
		self.SaveFile(Context)
		# execution finished
		return {'FINISHED'}
	# Run this as dialog
	def invoke(self, Context, event):
		self.setting_fps = round(Context.scene.render.fps)
		# Find the active armature or the first one selected
		armatureObj = None
		if Context.active_object and Context.active_object.type == 'ARMATURE':
			armatureObj = Context.active_object
		else:
			for o in Context.selected_objects:
				if o.type == 'ARMATURE':
					armatureObj = o
					break
		# Check action being set
		if armatureObj and armatureObj.animation_data and armatureObj.animation_data.action:
			self.setting_is_cyclic = armatureObj.animation_data.action.use_cyclic
		Context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	# Drawing dialog
	def draw(self, Context):
		layout = self.layout
		layout.prop(self,'setting_overwrite')
		layout.prop(self,'setting_is_cyclic')
		layout.prop(self,'setting_fps')
	# Save JMXVBAN file structure
	def SaveData(self, Context, FilePath, Obj, Action):
		# Rotate the object to match import
		Obj.matrix_world @= Euler((radians(-90),0.0,radians(180)),'XYZ').to_matrix().to_4x4()
		BlenderSetMode('OBJECT')
		bpy.ops.object.transform_apply()
		BlenderSetMode('POSE')

		# Apply fps synchronization (1 Frame = 1000 SRO Frames)
		sync_fps = 1000 / self.setting_fps

		# Save file structure
		bw = BinaryWriter()
		# Header
		bw.WriteAscii('JMXVBAN 0102')
		bw.WriteUInt(0)
		bw.WriteUInt(0)
		bw.WriteUInt(len(Action.name))
		bw.WriteAscii(Action.name)
		bw.WriteUInt(round(Action.frame_range[1] * sync_fps))
		bw.WriteUInt(self.setting_fps)
		bw.WriteUInt(self.setting_is_cyclic)

		# Reset pose bones to rest pose
		for poseBone in Obj.pose.bones:
			poseBone.matrix_basis.identity()
		# Keyframes to be set
		keyframes = self.GetKeyframeSets(Action,Obj.animation_data.action_slot if hasattr(Obj.animation_data, "action_slot") else None)
		bw.WriteUInt(len(keyframes))
		for keyframe in keyframes:
			bw.WriteUInt(round(keyframe * sync_fps))

		# Set maximum frames to record
		Context.scene.frame_end = int(Action.frame_range[1])

		animatedBones = self.GetAnimatedBones(Obj,keyframes,Context)
		# Transformations given to every bone
		bw.WriteUInt(len(animatedBones))
		for poseBone in Obj.pose.bones:
			# Check if this bone requires animations
			if not poseBone.name in animatedBones:
				continue
			bw.WriteUInt(len(poseBone.name))
			bw.WriteAscii(poseBone.name)
			bw.WriteUInt(len(keyframes))
			for kf in keyframes:
				# Set frame with transformation
				Context.scene.frame_set(kf)
				# Matrix relative to parent
				matrix_parent_relative = (poseBone.parent.matrix.inverted() @ poseBone.matrix) if poseBone.parent else poseBone.matrix
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
		# Reset frame to zero
		Context.scene.frame_set(0)

		# Rotate the object as original
		Obj.matrix_world @= Euler((radians(-90),0.0,radians(180)),'XYZ').to_matrix().to_4x4()
		BlenderSetMode('OBJECT')
		bpy.ops.object.transform_apply()
		BlenderSetMode('POSE')

		# Overwrite file
		with open(FilePath,'wb') as f:
			f.write(bw.Buffer)

	# Returns all keyframes used for an action
	def GetKeyframeSets(self,Action,Slot=None):
		frames = set()
		if hasattr(Action, 'fcurves'):
			curves = Action.fcurves  # Blender <=4.3
		else:
			from bpy_extras import anim_utils
			if Slot is None and len(Action.slots):
				Slot = Action.slots[0]
			bag = anim_utils.action_get_channelbag_for_slot(Action, Slot) if Slot else None
			curves = bag.fcurves if bag else []
		for fc in curves:
			for kp in fc.keyframe_points:
				frames.add(int(kp.co[0]))
		return sorted(frames)
	# Get all bones which has been animated
	def GetAnimatedBones(self,Obj,Keyframes,Context):
		bones = []
		matrixIdentity = Matrix.Identity(4)
		for poseBone in Obj.pose.bones:
			for kf in Keyframes:
				Context.scene.frame_set(kf)
				if poseBone.matrix_basis != matrixIdentity:
					bones.append(poseBone.name)
					break
		return bones
	# Saves file from blender
	def SaveFile(self, Context):
		# List all objects with skeletons
		objs = [o for o in Context.selected_objects if o.type == 'ARMATURE']
		if not objs:
			return
		# Keep current mode
		userMode = BlenderGetMode()
		
		for obj in objs:
			# Check if there is an action selected on armature
			if not obj.animation_data or not obj.animation_data.action:
				continue
			action = obj.animation_data.action

			# Check if file can be overwritten
			filepath = os.path.join(self.directory,action.name)+'.ban'
			if os.path.exists(filepath) and not self.setting_overwrite:
				continue

			# Save data structure
			try:
				self.SaveData(Context,filepath,obj,action)
			except Exception as ex:
				print('Error saving JMXVBAN file: '+action.name+' ['+str(ex)+']')
				continue

			# Success
			print('Saved:'+filepath)

		# Get back to normal
		BlenderSetMode(userMode)

# Add dynamic menu into Import
def menu_func_import(self, Context):
	self.layout.operator(Import_JMXVBAN_0102.bl_idname, text="JMXVBAN 0102 (.ban)")
# Add dynamic menu into Export
def menu_func_export(self, Context):
	self.layout.operator(Export_JMXVBAN_0102.bl_idname, text="JMXVBAN 0102 (.ban)")

# Register module
def register():
	bpy.utils.register_class(Import_JMXVBAN_0102)
	bpy.utils.register_class(Export_JMXVBAN_0102)
	bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
	bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

# Unregister module
def unregister():
	# unregister backwards to avoid issues
	bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
	bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
	bpy.utils.unregister_class(Export_JMXVBAN_0102)
	bpy.utils.unregister_class(Import_JMXVBAN_0102)