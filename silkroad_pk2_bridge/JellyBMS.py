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
	"name": "Silkroad JMXVBMS",
	"version": (2,5,8),
	"description": ("Import and export Sikroad Online objects"),
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
import math
from bpy.props import StringProperty, BoolProperty, CollectionProperty, IntProperty, FloatProperty
from mathutils import Vector
import colorsys

LOG_DEBUG = False
# Write text for debugging
def debug_print(*args):
	if LOG_DEBUG:
		print(' '.join(map(str, args)))

# Creates a unique key from an edge
def GetEdgeKey(vertex_index_a,vertex_index_b):
	return ( str(vertex_index_a)+','+str(vertex_index_b) ) if (vertex_index_a < vertex_index_b) else ( str(vertex_index_b)+','+str(vertex_index_a) )

# Get current mode from blender
def BlenderGetMode():
	return bpy.context.object.mode if bpy.context.object else 'OBJECT'

# Switch mode from Blender without context errors
def BlenderSetMode(NewMode):
	mode = BlenderGetMode()
	if mode != NewMode:
		bpy.ops.object.mode_set(mode=NewMode)

# Switch Viewport Mode from Blender
def BlenderSetViewport(Context, NewType):
	for window in Context.window_manager.windows:
		for area in window.screen.areas: # iterate through areas in current screen
			if area.type == 'VIEW_3D':
				for space in area.spaces: # iterate through spaces in current VIEW_3D area
					if space.type == 'VIEW_3D': # check if space is a 3D view
						space.shading.type = NewType

# Reads binary data
from .asset_binary import BinaryReader

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

# Import JMXVBMS command
class Import_JMXVBMS_0110(bpy.types.Operator):
	"""Imports a JMXVBMS 0110 file from Silkroad Online"""
	bl_idname = "silkroad_import.jmxvbms_0110" # bpy.ops.silkroad_import.jmxvbms_0110
	bl_label = "Select .bms file"
	# Filter only .bms files
	filter_glob: StringProperty(
		default="*.bms",
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
	# Settings
	setting_bounding_box: BoolProperty(
		name="Bounding Box",
		description="Load Bounding Box from object",
		default=False,
	)
	setting_navmesh: BoolProperty(
		name="NavMesh",
		description="Load Navigation Mesh from object",
		default=True,
	)
	setting_material_filepath: StringProperty(
		name='Mtrl Path',
		description='(Optional) Set the path to the material setting file (.bmt).\n\nExample: "C:\\Silkroad\\Server\\Data\\prim\\mtrl\\char\\china\\man\\chinaman_adventurer.bmt"',
		default='',
		maxlen=255,
	)
	# Execute command
	def execute(self, Context):
		return execute_import(self, Context, ".bms")
	# Run this as dialog
	def invoke(self, context, event):
		wm = context.window_manager
		wm.fileselect_add(self)
		return {'RUNNING_MODAL'}
	# Drawing dialog
	def draw(self, Context):
		layout = self.layout
		layout.prop(self,'setting_bounding_box')
		layout.prop(self,'setting_navmesh')
	# Loads file to blender
	def LoadFile(self, Context, Path, FileName):
		# Try to read file
		br = None
		filePath = os.path.join(Path,FileName)
		with open(filePath, 'rb') as f:
			br = BinaryReader(f.read())
			# Check file signature
			if br.Length < 12 or br.ReadAscii(12) != "JMXVBMS 0110":
				raise ValueError("Invalid BMS signature")
		if not br:
			raise ValueError("Empty binary reader")

		# Try to load file
		data = None
		# Reset cursor
		br.SeekRead(0)
		
		try:
			data = self.LoadData(br)
		except Exception as ex:
			# Error
			print('Error loading bms file:'+FileName+' ['+str(ex)+']')
			raise

		# Import data to blender
		userMode = BlenderGetMode()

		# Process Data
		self.ProcessData(Context,Path,data,data['name'])

		# Get back to normal
		BlenderSetMode(userMode)

		# Success
		print('Loaded:'+filePath)
		return True
	# Loads the data from file structure
	def LoadData(self, br):
		# data to be loaded
		data = {
			'name':'',
			'material':'',
			'vertices':[],
			'vertices_uv':[],
			'lightmap_uv':[],
			'lightmap_path':'',
			'vertex_groups':[],
			'faces':[],
			'vertex_clothes':{},
			'edge_clothes':{},
			'cloth_settings':{},
			'bounding_box':{},
			'nav_vertices':[],
			'nav_vertices_normals':[],
			'nav_cells':[],
			'nav_collision_edges':{},
			'nav_events':[]
		}

		# Skip header
		br.SeekRead(12,1)

		# File Offsets (Vertices, Vertex Groups, Faces, Vertex Clothes, Edge Clothes, Bounding Box, OcclusionPortals, NavMesh, Skinned NavMesh, Unknown09)
		br.SeekRead(28,1)
		offsetNavMesh = br.ReadUInt()
		br.SeekRead(4,1)
		br.SeekRead(4,1)
		br.SeekRead(4,1)
		navFlag = br.ReadUInt() # 0 = None, 1 = Edge, 2 = Cell, 4 = Event
		br.SeekRead(4,1)
		vertexFlag = br.ReadUInt()
		br.SeekRead(4,1)

		# Name & Material
		data['name'] = br.ReadAscii(br.ReadInt())
		data['material'] = br.ReadAscii(br.ReadInt())
		br.SeekRead(4,1)

		# File Offset: Vertices
		vertices = data['vertices']
		vertices_uv = data['vertices_uv']
		lightmap_uv = data['lightmap_uv']
		verticesCount = br.ReadUInt()
		for i in range(verticesCount):
			# Location
			x = br.ReadFloat()
			z = br.ReadFloat()
			y = br.ReadFloat()
			vertices.append([x,y,z])
			# Normal
			br.SeekRead(12,1)
			# UV Location
			u = br.ReadFloat()
			v = br.ReadFloat()
			vertices_uv.append([u,1-v])
			# Check LightMap
			if vertexFlag & 0x400:
				u = br.ReadFloat()
				v = br.ReadFloat()
				lightmap_uv.append([u,1-v])
			# Check MorphingData
			# Check MorphingData
			if vertexFlag & 0x800:
				x,y = vertices_uv.pop()
				lightmap_uv.append([x,1-y])
				br.SeekRead(40,1)
				u,v = br.ReadFloat(),br.ReadFloat()
				vertices_uv.append([u,1-v])
				continue
			br.SeekRead(12,1)
		# LightMap Path
		if vertexFlag & 0x400:
			data['lightmap_path'] = br.ReadAscii(br.ReadUInt())
		# ISROR vertex data
		if vertexFlag & 0x1000:
			br.SeekRead(br.ReadUInt()*24,1)

		# File Offset: Vertex Groups
		vertexGroups = data['vertex_groups']
		vertexGroupsCount = br.ReadUInt()
		if vertexGroupsCount:
			for i in range(vertexGroupsCount):
				name = br.ReadAscii(br.ReadInt())
				# Add vertex group
				vertexGroups.append({'name':name,'vertex_index':[],'vertex_weight':[]})
			for i in range(verticesCount):
				# Weights limit by mesh (2)
				for j in range(2):
					vertexGroupIndex = br.ReadByte()
					vertexWeight = br.ReadUShort()
					if vertexGroupIndex != 0xFF:
						# Add weight to vertex
						vg = vertexGroups[vertexGroupIndex]
						vg['vertex_index'].append(i)
						vg['vertex_weight'].append(vertexWeight/0xFFFF)

		# File Offset: Faces
		faces = data['faces']
		facesCount = br.ReadUInt()
		for i in range(facesCount):
			# Indices to vertices (triangle mesh)
			a = br.ReadUShort()
			b = br.ReadUShort()
			c = br.ReadUShort()
			# Add face
			# Swapping Y/Z changes handedness; reverse winding with the axes.
			faces.append([a,c,b])

		# File Offset: Vertex Clothes
		vertexClothes = data['vertex_clothes']
		vertexClothesCount = br.ReadUInt()
		for i in range(vertexClothesCount):
			distance = br.ReadFloat()
			isPinned = br.ReadUInt() == 1
			# Add cloth from vertex
			vertexClothes[i] = {'distance':distance,'is_pinned':isPinned}

		# File Offset: Edge Clothes
		edgeClothes = data['edge_clothes']
		edgeClothesCount = br.ReadUInt()
		if edgeClothesCount:
			for i in range(edgeClothesCount):
				a = br.ReadUInt()
				b = br.ReadUInt()
				distance = br.ReadFloat()
				# Add it
				edgeClothes[GetEdgeKey(a,b)] = {'vertex_index_a':a,'vertex_index_b':b,'distance':distance}
			# skip it
			br.SeekRead(edgeClothesCount*4,1)

			# Cloth simulation parameters
			cloth_settings = data['cloth_settings']

			cloth_settings['type'] = br.ReadUInt()
			cloth_settings['offset_x'] = br.ReadFloat()
			cloth_settings['offset_z'] = br.ReadFloat()
			cloth_settings['offset_y'] = br.ReadFloat()
			cloth_settings['speed'] = br.ReadFloat()
			unkUInt01 = br.ReadFloat()
			unkUInt02 = br.ReadFloat()
			cloth_settings['elasticity'] = br.ReadFloat()
			cloth_settings['movements'] = br.ReadInt()

			# Debugging stuffs
			debug_print('Cloth.unk01:',unkUInt01)
			debug_print('Cloth.unk02:',unkUInt02)

		# File Offset: BoundingBox
		bbox = data['bounding_box']
		for i in range(2):
			x = br.ReadFloat()
			z = br.ReadFloat()
			y = br.ReadFloat()
			bbox['min' if i == 0 else 'max'] = [x,y,z]

		# hasOcclusionPortal = br.ReadUInt()
		# ...
		# unknown = br.ReadUInt()

		# FileOffset: NavMesh
		if offsetNavMesh:
			br.SeekRead(offsetNavMesh)

			navVertices = data['nav_vertices']
			navVerticesNormals = data['nav_vertices_normals']
			navVerticesCount = br.ReadUInt()
			for i in range(navVerticesCount):
				# Add navigation vertex
				x = br.ReadFloat()
				z = br.ReadFloat()
				y = br.ReadFloat()
				navVertices.append([x,y,z])
				# Encoded normals
				normalIndex = br.ReadByte()
				navVerticesNormals.append(normalIndex)

			navCells = data['nav_cells']
			navCellsCount = br.ReadUInt()
			for i in range(navCellsCount):
				# Add indices to navigation vertices (triangle cell)
				a = br.ReadUShort()
				b = br.ReadUShort()
				c = br.ReadUShort()
				navCells.append([a,b,c])
				# Skip
				br.SeekRead(2,1)
				if navFlag & 2:
					br.SeekRead(1,1)

			navCollisionEdges = data['nav_collision_edges']
			navCollisionEdgesCount = br.ReadUInt()
			for i in range(navCollisionEdgesCount):
				a = br.ReadUShort()
				b = br.ReadUShort()
				br.SeekRead(4,1)
				flag = br.ReadByte()
				# Add outline edge
				navCollisionEdges[GetEdgeKey(a,b)] = {'is_outline':True,'flag':flag}
				# Skip
				if navFlag & 1:
					br.SeekRead(1,1)
			navCollisionEdgesCount = br.ReadUInt()
			for i in range(navCollisionEdgesCount):
				a = br.ReadUShort()
				b = br.ReadUShort()
				br.SeekRead(4,1)
				flag = br.ReadByte()
				# Skip
				if navFlag & 1:
					br.SeekRead(1,1)
				# Add inline edge
				navCollisionEdges[GetEdgeKey(a,b)] = {'is_outline':False,'flag':flag}

			# For display only
			if navFlag & 4:
				navEvents = data['nav_events']
				eventCount = br.ReadUInt()
				for i in range(eventCount):
					navEvents.append(br.ReadAscii(br.ReadUInt()))

			## Outline Lookup Grid - Skip it, doing nothing with it at the moment
			# br.SeekRead(8,1)
			# width = br.ReadUInt()
			# height = br.ReadUInt()
			# br.SeekRead(4,1)
			# for h in range(height):
			# 	for w in range(width):
			# 		count = br.ReadUInt()
			# 		lst = []
			# 		for c in range(count):
			# 			lst.append(br.ReadUShort())

		return data
	# Process data from file into Blender
	def ProcessData(self, Context, Path, data, name):
		# Create object
		BlenderSetMode('OBJECT')
		mesh = bpy.data.meshes.new("Mesh")
		obj = bpy.data.objects.new(data['name'], mesh)
		Context.collection.objects.link(obj)
		Context.view_layer.objects.active = obj # Set active object to work with
		obj.select_set(True)

		# Create mesh
		faces = data['faces']
		mesh.from_pydata(data['vertices'], [], faces)

		# Add Vertex Groups
		vertexGroups = data['vertex_groups']
		for vg in vertexGroups:
			group = obj.vertex_groups.new(name=vg['name'])
			group.add(vg['vertex_index'],1,'ADD')
		# Set weight from vertices
		for v in obj.data.vertices:
			for g in v.groups:
				vg = vertexGroups[g.group]
				for i, index in enumerate(vg['vertex_index']):
					if v.index == index:
						g.weight = vg['vertex_weight'][i]

		# Add Texture Map
		vertices_uv = data['vertices_uv']
		uv_layer = mesh.uv_layers.new(name='UVMap')
		for i, face in enumerate(mesh.polygons):
			# Smooth faces
			face.use_smooth = True
			# Set uv coordinates
			for j, loopindex in enumerate(face.loop_indices):
				# Select the face
				f = faces[i]
				# Select the vertex index
				uv = vertices_uv[f[j]]
				# Set UV values
				uv_layer.data[loopindex].uv = uv

		# Add Lightmap if exists
		lightmap_uv = data['lightmap_uv']
		if lightmap_uv:
			uv_layer = mesh.uv_layers.new(name='LightMap')
			for i, face in enumerate(mesh.polygons):
				for j, loopindex in enumerate(face.loop_indices):
					# Select the face
					f = faces[i]
					# Select the vertex index
					uv = lightmap_uv[f[j]]
					# Set UV values
					uv_layer.data[loopindex].uv = uv
			# pk2 path
			mesh['SilkroadOnline_LightMapSettings'] = {'path':data['lightmap_path']}

		# Create data layers thorugh bmesh
		BlenderSetMode('EDIT')
		bm = bmesh.from_edit_mesh(mesh)

		# Add Cloth from vertices
		vertexClothes = data['vertex_clothes']
		vertexClothesLayer = bm.verts.layers.float.new('vertex_clothes')
		if vertexClothes:
			for v in bm.verts:
				# Set vertex info
				v[vertexClothesLayer] = vertexClothes[v.index]['distance'] if v.index in vertexClothes else 0.0

		# Add Cloth from edges
		edgeClothes = data['edge_clothes']
		edgeClothesLayer = bm.edges.layers.float.new('edge_clothes')
		if edgeClothes:
			for e in bm.edges:
				# Get edge
				a = e.verts[0].index
				b = e.verts[1].index
				edgeKey = GetEdgeKey(a,b)
				# Set edge info
				e[edgeClothesLayer] = edgeClothes[edgeKey]['distance'] if edgeKey in edgeClothes else 0.0
			# Save property - cloth settings
			mesh['SilkroadOnline_ClothSettings'] = data['cloth_settings']

		# Assign material or create it
		BlenderSetMode('OBJECT')
		mat = bpy.data.materials.get(data['material'])
		if not mat:
			mat = bpy.data.materials.new(name=data['material'])
			mat.use_nodes = True
			mat.node_tree.nodes.clear()
		# Set material
		if obj.data.materials:
			obj.data.materials[0] = mat
		else:
			obj.data.materials.append(mat)
		# Set base nodes, link them and set texture if exists
		mat.use_nodes = True
		nodes = mat.node_tree.nodes
		output = nodes['ShaderNodeOutputMaterial'] if 'ShaderNodeOutputMaterial' in nodes else nodes.new('ShaderNodeOutputMaterial')
		output.name = 'ShaderNodeOutputMaterial'
		output.location = (380,0)
		bsdf = nodes['ShaderNodeBsdfPrincipled'] if 'ShaderNodeBsdfPrincipled' in nodes else nodes.new('ShaderNodeBsdfPrincipled')
		bsdf.name = 'ShaderNodeBsdfPrincipled'
		bsdf.location = (100,0)
		mat.node_tree.links.new(output.inputs['Surface'], bsdf.outputs['BSDF'])
		# Set material path to node
		data['material_filepath'] = None
		# Read optional .bmt with bounds checks: broken material metadata must
		# never abort a valid mesh/skeleton import (e.g. Harrison / Karkadann).
		if self.setting_material_filepath and os.path.isfile(self.setting_material_filepath):
			try:
				try:
					from .bmt_safe import parse_bmt_safe
				except ImportError:
					from bmt_safe import parse_bmt_safe
				with open(self.setting_material_filepath, 'rb') as f:
					materials, warning = parse_bmt_safe(f.read())
				if warning:
					print('[Silkroad PK2 Editor] Warning: invalid BMT material file:',
						  self.setting_material_filepath, '|', warning,
						  '| Continuing without invalid material entries')
				for record in materials:
					if data['material'] != record.name:
						continue
					mtrlPath = record.texture_path
					if record.relative_to_data:
						normalized = self.setting_material_filepath.replace('/', '\\').lower()
						dataRootIndex = normalized.find('\\data\\prim\\')
						if dataRootIndex != -1:
							dataRoot = self.setting_material_filepath[:dataRootIndex+5]
						else:
							primIndex = normalized.find('\\prim\\')
							dataRoot = self.setting_material_filepath[:primIndex] if primIndex != -1 else os.path.dirname(self.setting_material_filepath)
						mtrlPath = os.path.join(dataRoot, mtrlPath.replace('\\', os.sep).replace('/', os.sep))
					else:
						mtrlPath = os.path.join(os.path.dirname(self.setting_material_filepath), mtrlPath.replace('\\', os.sep).replace('/', os.sep))
					if os.path.isfile(mtrlPath):
						data['material_filepath'] = mtrlPath
					break
			except (OSError, ValueError) as exc:
				print('[Silkroad PK2 Editor] Warning: BMT material lookup failed:',
					  self.setting_material_filepath, '|', exc,
					  '| Continuing without this material')
		# Try to find texture name at the same folder
		if not data['material_filepath']:
			mtrlExtensions = ['dds','png','jpg','tga','jpeg','ddj']
			for ext in mtrlExtensions:
				mtrlPath = os.path.join(Path,data['material']+'.'+ext)
				if os.path.exists(mtrlPath):
					data['material_filepath'] = mtrlPath
					break
		# Convert DDJ to DDS
		if data['material_filepath'] and data['material_filepath'].lower().endswith('.ddj'):
			mtrlPath = os.path.splitext(data['material_filepath'])[0]+'.dds'
			if not os.path.exists(mtrlPath):
				# Remove header from DDJ
				with open(data['material_filepath'], 'rb') as fr:
					fr.seek(20,os.SEEK_SET)
					# Write into DDS
					with open(mtrlPath, 'wb') as fw:
						fw.write(fr.read())
			data['material_filepath'] = mtrlPath
		# Load texture
		if data['material_filepath']:
			pathHash = str(hash(data['material_filepath']))
			if pathHash in nodes:
				texImgNode = nodes[pathHash]
			else:
				# Calculate position by checking the nodes on with the same column
				xloc = -185
				yloc = 0
				for n in nodes:
					if n.type == 'TEX_IMAGE' and n.location[0] == xloc and n.location[1] <= yloc:
						yloc = n.location[1] - 290 # fixed node height							
				# Create node
				texImgNode = nodes.new('ShaderNodeTexImage')
				texImgNode.name = pathHash
				texImgNode.location = (xloc,yloc)
			# Try to load image if doesn't have one yet
			if not (texImgNode.image and texImgNode.image.has_data):
				try:
					texImgNode.image = bpy.data.images.load(data['material_filepath'])
				except Exception as exc:
					print('Texture load warning:', data['material_filepath'], exc)
			# Link texture
			mat.node_tree.links.new(bsdf.inputs['Base Color'], texImgNode.outputs['Color'])

		# Create BBOX
		if self.setting_bounding_box:
			# Make sure bbox has right values to use
			values = data['bounding_box']['min'] + data['bounding_box']['max']
			createBBox = True
			for value in values:
				if math.isnan(value):
					createBBox = False
					break
			if createBBox:
				# Create object
				mesh = bpy.data.meshes.new("Mesh")
				objBBox = bpy.data.objects.new(data['name']+'.BoundingBox', mesh)
				Context.collection.objects.link(objBBox)
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

		# Check NavMesh data
		if self.setting_navmesh and data['nav_vertices']:
			# Create object
			mesh = bpy.data.meshes.new("Mesh")
			objNav = bpy.data.objects.new(obj.name+'.NavMesh', mesh)
			Context.collection.objects.link(objNav)
			objNav.select_set(True)
			# Create mesh
			mesh.from_pydata(data['nav_vertices'], [], data['nav_cells'])

			# Create layers which contains collisions
			BlenderSetMode('EDIT')
			bm = bmesh.from_edit_mesh(mesh)

			# Add collision data from edges
			navCollisionEdges = data['nav_collision_edges']
			navEdgesOptionsLayer = bm.edges.layers.int.new('nav_edges_options')

			# Set edge options
			if navCollisionEdges:
				for e in bm.edges:
					# Get edge
					a = e.verts[0].index
					b = e.verts[1].index
					edgeData = navCollisionEdges[GetEdgeKey(a,b)]
					# Set flags data
					e[navEdgesOptionsLayer] = edgeData['flag']
			# Save property - NavMesh Events
			mesh['SilkroadOnline_NavMeshEvents'] = data['nav_events']

# Export JMXVBMS command
class Export_JMXVBMS_0110(bpy.types.Operator):
	"""Exports a JMXVBMS 0110 file from Silkroad Online using the current selected objects"""
	bl_idname = "silkroad_export.jmxvbms_0110" # bpy.ops.silkroad_export.jmxvbms_0110
	bl_label = "Save .bms files"
	# Directory path selected
	directory: StringProperty(
		subtype='DIR_PATH'
	)
	# Show .bms files
	filter_glob: StringProperty(
		default="*.bms",
		options={'HIDDEN'},
		maxlen=255  # Max internal buffer length, longer would be clamped.
	)
	# Settings
	setting_overwrite: BoolProperty(
		name="Overwrite existing files",
		description="Overwrites existing file with the same object name",
		default=False,
	)
	setting_apply_clothes: BoolProperty(
		name="Apply Clothes",
		description="Save all mesh info about clothes",
		default=False,
	)
	setting_cloth_deformation_type: IntProperty(
		name="Type",
		description="Deformation Type (0 = To wind; 1 = To ground)",
		default=1,
		min=0,
		max=1,
	)
	setting_cloth_deformation_offset_x: FloatProperty(
		name="X",
		description="Deformation from X axis",
		default=0
	)
	setting_cloth_deformation_offset_y: FloatProperty(
		name="Y",
		description="Deformation from Y axis",
		default=0
	)
	setting_cloth_deformation_offset_z: FloatProperty(
		name="Z",
		description="Deformation from Z axis",
		default=0
	)
	setting_cloth_deformation_speed: FloatProperty(
		name="Speed",
		description="Deformation Speed",
		default=10,
		min=0.01
	)
	setting_cloth_elasticity: FloatProperty(
		name="Elasticity",
		description="Weight from cloth elasticity",
		default=1.0,
		min=0.01,
		max=1.0
	)
	setting_cloth_movements: IntProperty(
		name="Movements",
		description="Randomly generated movements on cloth",
		default=1,
		min=1,
		max=100
	)
	setting_lightmap_path: StringProperty(
		name='LightMap',
		description='Path to the lightmap texture inside pk2 (Example: "prim/lightmap/texturemap.ddj").\n"LightMap" layer from UV Maps is required to do this action.',
		default='',
		maxlen=255,
	)
	setting_navmesh: BoolProperty(
		name="NavMesh",
		description="Save Navigation Mesh from object",
		default=True,
	)
	setting_navmesh_events: StringProperty(
		name='Events',
		description='Event names used on Dungeon triggers (if you need more than one, separate them by comma)',
		default='',
		maxlen=255,
	)
	# Execute command
	def execute(self, Context):
		# Overwrite into file selected
		self.SaveFile(Context)
		# execution finished
		return {'FINISHED'}
	# Run this as dialog
	def invoke(self, Context, Event):
		# Set default cloth settings from active object or the first one with it
		cloth_settings = None
		if Context.active_object and Context.active_object.type == 'MESH' and 'SilkroadOnline_ClothSettings' in Context.active_object.data:
			cloth_settings = Context.active_object.data.get('SilkroadOnline_ClothSettings')
		else:
			for o in Context.selected_objects:
				if o.type == 'MESH' and 'SilkroadOnline_ClothSettings' in o.data:
					cloth_settings = o.data.get('SilkroadOnline_ClothSettings')
					break
		if cloth_settings:
			self.setting_apply_clothes = True
			self.setting_cloth_elasticity = cloth_settings['elasticity']
			self.setting_cloth_deformation_type = cloth_settings['type']
			self.setting_cloth_deformation_offset_x = cloth_settings['offset_x']
			self.setting_cloth_deformation_offset_y = cloth_settings['offset_y']
			self.setting_cloth_deformation_offset_z = cloth_settings['offset_z']
			self.setting_cloth_deformation_speed = cloth_settings['speed']
			self.setting_cloth_movements = cloth_settings['movements']
		# Set LightMap
		if Context.active_object and Context.active_object.type == 'MESH' and 'SilkroadOnline_LightMapSettings' in Context.active_object.data:
			lightmap_settings = Context.active_object.data.get('SilkroadOnline_LightMapSettings')
			if lightmap_settings:
				self.setting_lightmap_path = lightmap_settings['path']
		# Set default navmesh settings from active object or the first one with it
		navmesh_events = None
		if Context.active_object and Context.active_object.type == 'MESH' and not Context.active_object.name.endswith('.NavMesh'):
			navObj = self.GetNavMeshObject(Context.active_object)
			if navObj and 'SilkroadOnline_NavMeshEvents' in navObj.data:
				navmesh_events = navObj.data.get('SilkroadOnline_NavMeshEvents')
		else:
			for o in Context.selected_objects:
				if o.type == 'MESH' and not Context.active_object.name.endswith('.NavMesh'):
					navObj = self.GetNavMeshObject(Context.active_object)
					if navObj:
						navmesh_events = o.data.get('SilkroadOnline_NavMeshEvents')
						break
		if navmesh_events:
			self.setting_navmesh_events = ','.join(navmesh_events)
		# Run file dialog
		Context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	# Drawing dialog
	def draw(self, Context):
		layout = self.layout
		layout.prop(self,'setting_overwrite')

		layout.prop(self,'setting_apply_clothes')
		layout_col = layout.column()
		if not self.setting_apply_clothes:
			layout_col.enabled = False
		layout_col.row().prop(self,'setting_cloth_elasticity')
		layout_col.row().prop(self,'setting_cloth_deformation_type')
		layout_col_row = layout_col.row()
		layout_col_row.prop(self,'setting_cloth_deformation_offset_x')
		layout_col_row.prop(self,'setting_cloth_deformation_offset_y')
		layout_col_row.prop(self,'setting_cloth_deformation_offset_z')
		layout_col.row().prop(self,'setting_cloth_deformation_speed')
		layout_col.row().prop(self,'setting_cloth_movements')

		layout.prop(self,'setting_lightmap_path')

		layout.prop(self,'setting_navmesh')
		layout_col = layout.column()
		if not self.setting_navmesh:
			layout_col.enabled = False
		layout_col.row().prop(self,'setting_navmesh_events')

	# Saves file from blender
	def SaveFile(self, Context):
		# List all objects with meshes
		objs = [o for o in Context.selected_objects if o.type == 'MESH' and not o.name.endswith('.NavMesh')]
		if not objs:
			return

		# Keep current mode
		userMode = BlenderGetMode()

		for obj in objs:
			# Check if file can be overwritten
			filepath = os.path.join(self.directory,obj.name)+'.bms'
			if os.path.exists(filepath) and not self.setting_overwrite:
				continue

			# Save data structure
			try:
				self.SaveData(Context,filepath,obj)
			except Exception as ex:
				print('Error saving JMXVBMS file: '+obj.name+' ['+str(ex)+']')
				continue

			# Success
			print('Saved:'+filepath)

		# Get back to normal
		BlenderSetMode(userMode)
			
	# Save JMXVBMS file structure
	def SaveData(self, Context, FilePath, Obj):
		# Retrieve data required to create the file
		BlenderSetMode('EDIT')
		materialName = Obj.data.materials[0].name if len(Obj.data.materials) else ''
		mesh = Obj.data
		vertices = mesh.vertices
		vertexGroups = Obj.vertex_groups
		faces = mesh.polygons
		lightMapPath = ''
		navObj = self.GetNavMeshObject(Obj) if self.setting_navmesh else None
		navEvents = []
		if navObj:
			navEvents = self.setting_navmesh_events.split(',')
			navEvents = [e for e in navEvents if e] # Remove empty values
		bm = bmesh.from_edit_mesh(mesh)
		# Check texture uv layer
		if self.GetUVLayer(Obj) == None: # default layer
			raise ValueError("Mesh does not have UV layer assigned")
		else:
			bmDefaultUVLayer = bm.loops.layers.uv.active
			if self.RequiresVertexUVFix(bm,bmDefaultUVLayer):
				print("Warning: Vertex found with more than one UV coordinate assigned.\nPlease, try to import the model as .gltf format to avoid further issues.")
		# Check lightmap uv layer
		if self.setting_lightmap_path:
			lightMapUVLayer = self.GetUVLayer(Obj,'LightMap')
			if lightMapUVLayer:
				lightMapPath = self.setting_lightmap_path

		# Write binary file structure
		bw = BinaryWriter()

		# Signature
		bw.WriteAscii('JMXVBMS 0110')
		
		# File Offsets
		bw.WriteUInt(0) # Vertices
		bw.WriteUInt(0) # Vertex Groups
		bw.WriteUInt(0) # Faces
		bw.WriteUInt(0) # Vertex Clothes
		bw.WriteUInt(0) # Edge Clothes
		bw.WriteUInt(0) # Bounding Box
		bw.WriteUInt(0) # Occlusion Portals
		bw.WriteUInt(0) # NavMesh
		bw.WriteUInt(0) # SkinnedNavMesh
		bw.WriteUInt(0) # Unknown

		# Flags
		bw.WriteUInt(0) # unkUInt01


		bw.WriteUInt(4 if len(navEvents) else 0) # NavFlag
		bw.WriteUInt(1) # SubPrimCount
		bw.WriteUInt(0x400 if lightMapPath else 0) # VertexFlag
		bw.WriteUInt(0)

		# Object info
		bw.WriteUInt(len(Obj.name))
		bw.WriteAscii(Obj.name)
		bw.WriteUInt(len(materialName))
		bw.WriteAscii(materialName)
		bw.WriteUInt(0)

		# File Offset: Vertices
		offsetVertices = bw.Position

		BlenderSetMode('OBJECT')
		defaultUVLayer = self.GetUVLayer(Obj)
		lightMapUVLayer = self.GetUVLayer(Obj,'LightMap')

		bw.WriteUInt(len(vertices))
		for v in vertices:
			# Location
			bw.WriteFloat(v.co[0])
			bw.WriteFloat(v.co[2])
			bw.WriteFloat(v.co[1])
			# Normals
			bw.WriteFloat(v.normal[0])
			bw.WriteFloat(v.normal[2])
			bw.WriteFloat(v.normal[1])
			# Find UV location from active UV layer 
			uv = self.GetUVFromVertex(Obj,v.index,defaultUVLayer)
			if uv == None:
				print('Vertex (',v.co[0],',',v.co[1],',',v.co[2],') has no UV location assigned on active UV Map!')
				bw.WriteFloat(0)
				bw.WriteFloat(0)
			else:
				bw.WriteFloat(uv[0])
				bw.WriteFloat(1-uv[1])
			# Find UV location from 
			if lightMapPath:
				uv = self.GetUVFromVertex(Obj,v.index,lightMapUVLayer)
				if uv == None:
					print('Vertex (',v.co[0],',',v.co[1],',',v.co[2],') has no UV location assigned on "LightMap"')
					bw.WriteFloat(0)
					bw.WriteFloat(0)
				else:
					bw.WriteFloat(uv[0])
					bw.WriteFloat(1-uv[1])
			# Related to bones
			bw.WriteFloat(0)
			bw.WriteUInt(0xFFFFFFFF)
			bw.WriteUInt(0)
		if lightMapPath:
			bw.WriteUInt(len(lightMapPath))
			bw.WriteAscii(lightMapPath)

		# File Offset: Vertex Groups
		offsetVertexGroups = bw.Position

		bw.WriteUInt(len(vertexGroups))
		if len(vertexGroups):
			# Vertex Groups Names
			for vg in vertexGroups:
				bw.WriteUInt(len(vg.name))
				bw.WriteAscii(vg.name)
			# Vertex Groups Weights
			for v in vertices:
				# Throw fatal exception
				if len(v.groups) == 0:
					raise ValueError('Vertex Group not found from (',v.co[0],',',v.co[1],',',v.co[2],')')
				# Weights limit by mesh (2)
				# 1st
				bw.WriteByte(v.groups[0].group)
				bw.WriteUShort(round(round(v.groups[0].weight,3)*0xFFFF))
				# 2nd
				if len(v.groups) > 1:
					bw.WriteByte(v.groups[1].group)
					bw.WriteUShort(round(round(v.groups[1].weight,3)*0xFFFF))
				else:
					bw.WriteByte(0xFF)
					bw.WriteUShort(0)

		# File Offset: Faces
		offsetFaces = bw.Position

		bw.WriteUInt(len(faces))
		for f in faces:
			# Make sure it's a triangle face
			for i in range(3):
				# Restore source winding when returning to the game axes.
				bw.WriteUShort(f.vertices[(0,2,1)[i]])

		# File Offset: Vertex Clothes
		offsetVertexClothes = bw.Position

		BlenderSetMode('EDIT')
		bm = bmesh.from_edit_mesh(mesh)
		vertexClothesLayer = bm.verts.layers.float.get('vertex_clothes') or bm.verts.layers.float.new('vertex_clothes')
		if self.LayerDataCheck(vertexClothesLayer, bm.verts, lambda value: value != 0):
			# Cloth info from all vertices
			bw.WriteUInt(len(bm.verts))
			for v in bm.verts:
				distance = v[vertexClothesLayer]
				bw.WriteFloat(distance)
				bw.WriteUInt(0 if distance else 1)
		else:
			bw.WriteUInt(0)

		# File Offset: Edge Clothes
		offsetEdgeClothes = bw.Position

		edgeClothesLayer = bm.edges.layers.float.get('edge_clothes') or bm.edges.layers.float.new('edge_clothes')
		dataCount = self.LayerDataCount(edgeClothesLayer, bm.edges, lambda value: value > 0)
		bw.WriteUInt(dataCount)
		if dataCount:
			# Cloth info from edges with changes
			for e in bm.edges:
				distance = e[edgeClothesLayer]
				if distance > 0:
					bw.WriteUInt(e.verts[0].index)
					bw.WriteUInt(e.verts[1].index)
					bw.WriteFloat(distance)
			# Order from changed edges
			for i in range(dataCount):
				bw.WriteUInt(i)

			# Cloth simulation parameters
			bw.WriteUInt(self.setting_cloth_deformation_type) # Deformation (0 = Deformation to wind; 1 = Deformation to ground)
			bw.WriteFloat(self.setting_cloth_deformation_offset_x) # X Offset
			bw.WriteFloat(self.setting_cloth_deformation_offset_z) # Z Offset
			bw.WriteFloat(self.setting_cloth_deformation_offset_y) # Y Offset
			bw.WriteFloat(self.setting_cloth_deformation_speed) # Falling speed
			bw.WriteFloat(1.0)
			bw.WriteFloat(1.0)
			bw.WriteFloat(self.setting_cloth_elasticity)
			bw.WriteUInt(self.setting_cloth_movements)

		# File Offset: Bounding Box
		offsetBoundingBox = bw.Position

		bboxMin,bboxMax = self.GetBoundingBox(Obj)
		bw.WriteFloat(bboxMin[0])
		bw.WriteFloat(bboxMin[2])
		bw.WriteFloat(bboxMin[1])
		bw.WriteFloat(bboxMax[0])
		bw.WriteFloat(bboxMax[2])
		bw.WriteFloat(bboxMax[1])

		# File Offset: Occlusion Portals
		offsetOcclusionPortals = bw.Position
		bw.WriteUInt(0) # Not implemented

		# File Offset: Unknown
		offsetUnknown = bw.Position
		bw.WriteUInt(0) # Always zero

		# File Offset: NavMesh
		offsetNavMesh = 0

		# Add NavMesh
		if navObj != None:
			offsetNavMesh = bw.Position

			# Data required to save navmesh
			navMesh = navObj.data
			navCells = navMesh.polygons
			bm = bmesh.new()
			bm.from_mesh(navMesh)
			navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options') or bm.edges.layers.int.new('nav_edges_options')
			inlineEdgesCount = self.GetInlineEdgesCount(bm)
			outlineEdgesCount = len(bm.edges) - inlineEdgesCount
			vertexNormalsEncoded = self.GetVertexNormalsEncoded(bm)
			# NavMesh vertices
			bw.WriteUInt(len(bm.verts))
			for v in bm.verts:
				# Location
				bw.WriteFloat(v.co[0])
				bw.WriteFloat(v.co[2])
				bw.WriteFloat(v.co[1])
				# Normal 2D encoded as byte
				normalIndex = vertexNormalsEncoded[v.index] if v.index in vertexNormalsEncoded else 0
				bw.WriteByte(normalIndex)

			# NavMesh cells
			bw.WriteUInt(len(navCells))
			for c in navCells:
				# Make sure it's a triangle cell
				for i in range(3):
					bw.WriteUShort(c.vertices[i])
				bw.WriteUShort(0) # Unknown Flags
			# Outline edges
			bw.WriteUInt(outlineEdgesCount)
			for e in bm.edges:
				if len(e.link_faces) <= 1:
					bw.WriteUShort(e.verts[0].index)
					bw.WriteUShort(e.verts[1].index)
					bw.WriteUShort(e.link_faces[0].index) # source
					bw.WriteUShort(0xFFFF) # destination (-1)
					bw.WriteByte((e[navEdgesOptionsLayer] & 0xF3) | 0)
			# Inline Edges
			bw.WriteUInt(inlineEdgesCount)
			for e in bm.edges:
				if len(e.link_faces) > 1:
					bw.WriteUShort(e.verts[0].index)
					bw.WriteUShort(e.verts[1].index)
					# sort indexes
					src,dest = (e.link_faces[0].index,e.link_faces[1].index) if e.link_faces[0].index < e.link_faces[1].index else (e.link_faces[1].index,e.link_faces[0].index)
					bw.WriteUShort(src) # source
					bw.WriteUShort(dest) # destination
					bw.WriteByte((e[navEdgesOptionsLayer] & 0xF3) | 4)
			# Set events
			if self.setting_navmesh_events:
				bw.WriteUInt(len(navEvents))
				for e in navEvents:
					bw.WriteUInt(len(e))
					bw.WriteAscii(e)

			# Lookup Grid Cells
			bboxMin,bboxMax = self.GetBoundingBox(navObj)
			lookupGrid = self.Generate2DLookupGrid(bm, bboxMin, bboxMax)
			bw.WriteFloat(bboxMin[0])
			bw.WriteFloat(bboxMin[1])
			bw.WriteUInt(lookupGrid['width'])
			bw.WriteUInt(lookupGrid['height'])
			bw.WriteUInt(lookupGrid['width']*lookupGrid['height']) # Cell Count
			grid = lookupGrid['grid']
			for h in range(lookupGrid['height']):
				for w in range(lookupGrid['width']):
					key = str(w)+'x'+str(h)
					globalCells = grid[key]
					bw.WriteUInt(len(globalCells))
					for cellIndex in globalCells:
						bw.WriteUShort(cellIndex)

		# Write File Offsets
		bw.SeekWrite(12) # Signature
		bw.WriteUInt(offsetVertices) # Vertices
		bw.WriteUInt(offsetVertexGroups) # Vertex Groups
		bw.WriteUInt(offsetFaces) # Faces
		bw.WriteUInt(offsetVertexClothes) # Vertex Clothes
		bw.WriteUInt(offsetEdgeClothes) # Edge Clothes
		bw.WriteUInt(offsetBoundingBox) # Bounding Box
		bw.WriteUInt(offsetOcclusionPortals) # Occlusion Portals
		bw.WriteUInt(offsetNavMesh) # NavMesh
		bw.WriteUInt(0) # SkinnedNavMesh
		bw.WriteUInt(offsetUnknown) # Unknown

		# Overwrite file
		with open(FilePath,'wb') as f:
			f.write(bw.Buffer)
	# Round values from 2d vector
	def Vector2RoundDown(self, vector,decimals):
		factor = 10 ** decimals
		return (math.floor(vector[0] * factor) / factor, math.floor(vector[1] * factor) / factor)
	# Check if the mesh requires uv fix (a vertex cannot have multiples UV)
	def RequiresVertexUVFix(self, bm, UVLayer):
		for v in bm.verts:
			uv = None
			for loop in v.link_loops:
				if uv == None:
					uv = self.Vector2RoundDown(loop[UVLayer].uv,3)
				elif uv != self.Vector2RoundDown(loop[UVLayer].uv,3):
					return True
		return False
	# Find UV Map Layer from object
	def GetUVLayer(self, Obj, UVLayerName=''):
		if UVLayerName == '':
			return Obj.data.uv_layers.active
		for uv_layer in Obj.data.uv_layers:
			if uv_layer.name == UVLayerName:
				return uv_layer
		return None
	# Returns UV coordinate from vertex at object
	def GetUVFromVertex(self, Obj, VertexIndex, UVLayer=None):
		# Slow process
		for face in Obj.data.polygons:
			for loop_index, vertex_index in enumerate(face.vertices):
				if VertexIndex == vertex_index:
					# Use active UV Map
					if UVLayer == None:
						return Obj.data.uv_layers.active.data[face.loop_indices[loop_index]].uv
					else:
						# Use layer provided
						return UVLayer.data[face.loop_indices[loop_index]].uv
		return None
	# Find Bounding Box from any object
	def GetBoundingBox(self, Obj):
		# vertices corners from box
		bboxCorners = [Obj.matrix_world @ Vector(corner) for corner in Obj.bound_box]
		# make a list separately
		bboxVectorsX = [bbox_corner[0] for bbox_corner in bboxCorners]
		bboxVectorsY = [bbox_corner[1] for bbox_corner in bboxCorners]
		bboxVectorsZ = [bbox_corner[2] for bbox_corner in bboxCorners]
		# find min, max
		bboxMin = [min(bboxVectorsX),min(bboxVectorsY),min(bboxVectorsZ)]
		bboxMax = [max(bboxVectorsX),max(bboxVectorsY),max(bboxVectorsZ)]
		return bboxMin, bboxMax
	# Find navmesh related to the given object
	def GetNavMeshObject(self, Obj):
		meshName = Obj.name+'.NavMesh'
		for o in bpy.data.objects:
			if o.type == 'MESH' and o.name == meshName:
				return o
		return None
	# Check data from layer
	def LayerDataCheck(self, Layer, Items, _lambda):
		# Check data from each item
		for item in Items:
			if _lambda(item[Layer]):
				return True
		return False
	# Count data from layer
	def LayerDataCount(self, Layer, Items, _lambda):
		dataCount = 0
		# Check data from each item 
		for item in Items:
			# Check if data is not default
			if _lambda(item[Layer]):
				dataCount += 1
		return dataCount
	# Count all inline edges from object
	def GetInlineEdgesCount(self, bm):
		count = 0
		for e in bm.edges:
			# check if is an inline edge
			if len(e.link_faces) > 1:
				count +=1
		return count
	def GetVertexNormalsEncoded(self, bm):
		bm.edges.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.ensure_lookup_table()
		# Generate edge normals
		edgeNormals = {}
		for f in bm.faces:
			for e in f.edges:
				# Check if it's an outline edge
				if len(e.link_faces) > 1:
					continue
				# Organize the triangle points
				a = e.verts[0].co.to_2d()
				b = e.verts[1].co.to_2d()
				for v in f.verts:
					if e.verts[0].index != v.index and e.verts[1].index != v.index:
						c = v.co.to_2d()
						break
				# Get the normal from ab
				ab = b-a
				ac = c-a
				abNormal = ab.orthogonal().normalized()
				# Fix the normal direction
				angleABAC = ab.angle_signed(ac,0)
				if angleABAC < 0:
					abNormal.negate()
				# Save it
				edgeNormals[e.index] = abNormal
		# Generate vertex normals from edges
		vertexNormalsEncoded = {}
		for v in bm.verts:
			edges = []
			# Create it using two outline edges
			for e in v.link_edges:
				if len(e.link_faces) > 1:
					continue
				edges.append(e.index)
			if edges:
				vertexNormal = edgeNormals[edges[0]]
				for x in range(1,len(edges)):
					vertexNormal += edgeNormals[edges[x]]
				vertexNormal.normalize()
				angle = math.atan2(vertexNormal.y,vertexNormal.x) * 180.0 / math.pi
				# Encode angle generated into byte handled by Silkroad
				if angle < 0: # fix negative
					angle += 360
				if angle: # inverse it
					angle = (360-angle)
				normalIndex = round(angle*255/360)
				vertexNormalsEncoded[v.index] = normalIndex
		return vertexNormalsEncoded
	# Creates lookup grid handled from collisions
	def Generate2DLookupGrid(self, bm, BBoxMin, BBoxMax):
		# Update everything just in case
		bm.edges.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		bm.verts.ensure_lookup_table()
		# Find all outline edges
		navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options')
		edgesIndices = []
		edgesIndicesFixed = {}
		edgesIndicesCount = 0
		for e in bm.edges:
			# Check if it's a outline edge
			if len(e.link_faces) <= 1:
				# Check if it's locked
				edgesIndices.append(e.index)
				edgesIndicesFixed[e.index] = edgesIndicesCount
				edgesIndicesCount += 1
		# List all edges contained by cells
		grid = {}
		cellWidth = 100.0
		cellHeight = 100.0
		width = math.ceil((BBoxMax[0]-BBoxMin[0])/cellWidth)
		height = math.ceil((BBoxMax[1]-BBoxMin[1])/cellHeight)
		for hIndex in range(height):
			for wIndex in range(width):
				# Calc edges from cell
				cellX = BBoxMin[0] + wIndex*cellWidth
				cellY = BBoxMin[1] + hIndex*cellHeight
				cellW = cellX + cellWidth
				cellH = cellY + cellHeight
				# Create cell
				key = str(wIndex)+'x'+str(hIndex)
				cellData = set()
				# Check if edges are crossing this cell
				for eIndex in edgesIndices:
					e = bm.edges[eIndex]
					# Check if some vertex is inside cell
					if self.IsPointOnRect(cellX,cellY,cellW,cellH,e.verts[0].co) or self.IsPointOnRect(cellX,cellY,cellW,cellH,e.verts[1].co):
						cellData.add(edgesIndicesFixed[eIndex])
						continue
					# Check if edge intersects some border from cell
					if self.IsRectIntersected(cellX,cellY,cellW,cellH,e.verts[0].co,e.verts[1].co):
						cellData.add(edgesIndicesFixed[eIndex])
						continue
				# Get sorted edges indices from cell
				grid[key] = sorted(cellData)
		# return grid
		return {'grid':grid,'width':width,'height':height}
	# To find orientation of ordered triplet (p1,p2,p3)
	def PointsRotationDirection(self, p1, p2, p3):
			val = (p3[1] - p1[1]) * (p2[0] - p1[0])
			val2 = (p2[1] - p1[1]) * (p3[0] - p1[0])
			if val > val2:
				return 1
			if val == val2:
				return 0
			return -1
	# Check if point 'p' is on segment 's'
	def LineSegmentContainsPoint(self, s1, s2, p):
		if s1[0] < s2[0] and s1[0] < p[0] and p[0] < s2[0]:
			return True
		if s2[0] < s1[0] and s2[0] < p[0] and p[0] < s1[0]:
			return True
		if s1[1] < s2[1] and s1[1] < p[1] and p[1] < s2[1]:
			return True
		if s2[1] < s1[1] and s2[1] < p[1] and p[1] < s1[1]:
			return True
		if (s1[0] == p[0] and s1[1] == p[1]) or (s2[0] == p[0] and s2[1] == p[1]):
			return True
		return False
	# Check if line from 'p1p2' intersects line 'p3p4'
	def IsLineIntersected(self, p1, p2, p3, p4):
		f1 = self.PointsRotationDirection(p1, p2, p4);
		f2 = self.PointsRotationDirection(p1, p2, p3);
		f3 = self.PointsRotationDirection(p1, p3, p4);
		f4 = self.PointsRotationDirection(p2, p3, p4);
		# If the faces rotate opposite directions, they intersect.
		result = f1 != f2 and f3 != f4
		# If the segments are on the same line, we have to check for overlap.
		if f1 == 0 and f2 == 0 and f3 == 0 and f4 == 0:
			result = self.LineSegmentContainsPoint(p1, p2, p3) or self.LineSegmentContainsPoint(p1, p2, p4) or self.LineSegmentContainsPoint(p3, p4, p1) or self.LineSegmentContainsPoint(p3, p4, p2)
		return result
	# Check if line intersects a rectangle
	def IsRectIntersected(self, x,y,x_right,y_top,p,q):
		if self.IsLineIntersected([x,y],[x_right,y],p,q):
			return True
		if self.IsLineIntersected([x,y_top],[x_right,y_top],p,q):
			return True
		if self.IsLineIntersected([x,y],[x,y_top],p,q):
			return True
		if self.IsLineIntersected([x_right,y],[x_right,y_top],p,q):
			return True
		return False
	# Check if point 'p' is inside rectangle
	def IsPointOnRect(self, x,y,x_right,y_top,p):
		if p[0] >= x and p[0] <= x_right and p[1] >= y and p[1] <= y_top:
			return True
		return False

# Panel to show extra properties used for Silkroad
class Panel_SilkroadProperties(bpy.types.Panel):
	bl_idname = "OBJECT_PT_SilkroadProperties"
	bl_label = "Silkroad Online"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'Silkroad'
	bl_context = 'mesh_edit'
	Properties = {'selected_vertices':[],'selected_edges':[],'is_drawing':False}
	# Draw/update all items on panel
	def draw(self, Context):
		self.Properties['is_drawing'] = True
		# Get the first object selected with bmesh
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)

		if obj.name.endswith('.NavMesh'):
			self.OnDrawNavMesh(Context, bm)
		else:
			self.OnDrawClothesPanel(Context, bm)
		self.Properties['is_drawing'] = False
	# Draw panel from mesh objects
	def OnDrawClothesPanel(self, Context, bm):
		col = self.layout.column()
		wm = Context.window_manager

		# Find selected vertices
		bm.verts.ensure_lookup_table()
		selectedVertices = []
		for v in bm.verts:
			if v.select:
				selectedVertices.append(v.index)
		self.Properties['selected_vertices'] = selectedVertices

		# Draw "Cloth by vertex" option
		row = col.row()
		if selectedVertices:
			vertexClothesLayer = bm.verts.layers.float.get('vertex_clothes') or bm.verts.layers.float.new('vertex_clothes')
			wm.SROProperties.ClothByVertex = round(bm.verts[selectedVertices[0]][vertexClothesLayer],5)
		else:
			row.enabled = False
			wm.SROProperties.ClothByVertex = 0.0
		row.prop(wm.SROProperties,'ClothByVertex')

		# Find selected edges
		bm.edges.ensure_lookup_table()
		selectedEdges = []
		for e in bm.edges:
			if e.select:
				selectedEdges.append(e.index)
		self.Properties['selected_edges'] = selectedEdges

		# Draw "Cloth by Edge" option
		row = col.row()
		if selectedEdges:
			edgeClothesLayer = bm.edges.layers.float.get('edge_clothes') or bm.edges.layers.float.new('edge_clothes')
			wm.SROProperties.ClothByEdge = round(bm.edges[selectedEdges[0]][edgeClothesLayer],5)
		else:
			row.enabled = False
			wm.SROProperties.ClothByEdge = 0.0
		row.prop(wm.SROProperties,'ClothByEdge')

		# Draw options
		col.row().operator("object.silkroad_properties_select_dyvertex")
		col.row().operator("object.silkroad_properties_generate_cloth_edges")
		col.row().operator("object.silkroad_properties_show_clothes")

	# Draw panel from NavMesh objects
	def OnDrawNavMesh(self, Context, bm):
		col = self.layout.column()
		wm = Context.window_manager

		# Find selected edges
		bm.edges.ensure_lookup_table()
		selectedEdges = []
		for e in bm.edges:
			if e.select:
				selectedEdges.append(e.index)
		self.Properties['selected_edges'] = selectedEdges

		# Draw "Options" option
		rowIsLockedInside = col.row()
		rowIsLockedOutside = col.row()
		rowIsInternal = col.row()
		rowIsInternal.enabled = False
		rowIsGlobal = col.row()
		rowIsUnderpass = col.row()
		rowIsEntrance = col.row()
		rowIsUnknown = col.row()
		rowIsSiege = col.row()

		if selectedEdges:
			navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options') or bm.edges.layers.int.new('nav_edges_options')
			# Check options from first edge selected
			e = bm.edges[selectedEdges[0]]
			flag = e[navEdgesOptionsLayer]
			wm.SROProperties.IsLockedInside = True if (flag & 1) else False
			wm.SROProperties.IsLockedOutside = True if (flag & 2) else False
			wm.SROProperties.IsInternal = True if (flag & 4) else False
			wm.SROProperties.IsGlobal = True if (flag & 8) else False
			wm.SROProperties.IsUnderpass = True if (flag & 16) else False
			wm.SROProperties.IsEntrance = True if (flag & 32) else False
			wm.SROProperties.IsUnknown = True if (flag & 64) else False
			wm.SROProperties.IsSiege = True if (flag & 128) else False
		else:
			rowIsLockedInside.enabled = False
			rowIsLockedOutside.enabled = False
			rowIsUnderpass.enabled = False
			rowIsEntrance.enabled = False
			rowIsUnknown.enabled = False
			rowIsSiege.enabled = False
			wm.SROProperties.IsLockedInside = False
			wm.SROProperties.IsLockedOutside = False
			wm.SROProperties.IsUnderpass = False
			wm.SROProperties.IsEntrance = False
			wm.SROProperties.IsUnknown = False
			wm.SROProperties.IsSiege = False

		rowIsLockedInside.prop(wm.SROProperties,'IsLockedInside')
		rowIsLockedOutside.prop(wm.SROProperties,'IsLockedOutside')
		rowIsInternal.prop(wm.SROProperties,'IsInternal')
		rowIsGlobal.prop(wm.SROProperties,'IsGlobal')
		rowIsUnderpass.prop(wm.SROProperties,'IsUnderpass')
		rowIsEntrance.prop(wm.SROProperties,'IsEntrance')
		rowIsUnknown.prop(wm.SROProperties,'IsUnknown')
		rowIsSiege.prop(wm.SROProperties,'IsSiege')

		# Draw some actions
		col.row().operator("object.silkroad_properties_show_locked_edges")

# Silkroad Properties used on UI panel
class SilkroadProperties(bpy.types.PropertyGroup):
	# Buffer to keep last values selected and apply actions if required
	Buffer = {'selected_vertices':[],'selected_edges':[]} 
	# Called when value has been changed
	def OnClothByVertexUpdate(self, Context):
		# Avoid non-user updates
		if Panel_SilkroadProperties.Properties['is_drawing']:
			return
		# Check if there is a change to update it
		selectedVertices = Panel_SilkroadProperties.Properties['selected_vertices']
		if not selectedVertices:
			return
		# Apply change to vertices from object selected
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)
		vertexClothesLayer = bm.verts.layers.float.get('vertex_clothes')
		for i in selectedVertices:
			bm.verts[i][vertexClothesLayer] = self.ClothByVertex
	# Called when value has been changed
	def OnClothByEdgeUpdate(self, Context):
		# Avoid non-user updates
		if Panel_SilkroadProperties.Properties['is_drawing']:
			return
		# Check if there is a change to update it
		selectedEdges = Panel_SilkroadProperties.Properties['selected_edges']
		if not selectedEdges:
			return
		# Apply change to edges from object selected
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)
		edgeClothesLayer = bm.edges.layers.float.get('edge_clothes')
		for i in selectedEdges:
			bm.edges[i][edgeClothesLayer] = self.ClothByEdge
	# Called when value has been changed
	def OnIsLockedInsideUpdate(self, Context):
		# Avoid non-user updates
		if Panel_SilkroadProperties.Properties['is_drawing']:
			return
		# Check if there is a change to update it
		selectedEdges = Panel_SilkroadProperties.Properties['selected_edges']
		if not selectedEdges:
			return
		# Apply change to edges from object selected
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)
		navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options')
		for i in selectedEdges:
			e = bm.edges[i]
			# Update edges
			if self.IsLockedInside:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] | 1 # set
			else:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] & 0xFE # unset
	# Called when value has been changed
	def OnIsLockedOutsideUpdate(self, Context):
		# Avoid non-user updates
		if Panel_SilkroadProperties.Properties['is_drawing']:
			return
		# Check if there is a change to update it
		selectedEdges = Panel_SilkroadProperties.Properties['selected_edges']
		if not selectedEdges:
			return
		# Apply change to edges from object selected
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)
		navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options')
		for i in selectedEdges:
			e = bm.edges[i]
			# Update edges
			if self.IsLockedOutside:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] | 2 # set
			else:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] & 0xFD # unset
	# Called when value has been changed
	def OnIsGlobalUpdate(self, Context):
		# Avoid non-user updates
		if Panel_SilkroadProperties.Properties['is_drawing']:
			return
		# Check if there is a change to update it
		selectedEdges = Panel_SilkroadProperties.Properties['selected_edges']
		if not selectedEdges:
			return
		# Apply change to edges from object selected
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)
		navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options')
		for i in selectedEdges:
			e = bm.edges[i]
			# Update edges
			if self.IsGlobal:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] | 8 # set
			else:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] & 0xF7 # unset
	# Called when value has been changed
	def OnIsUnderpassUpdate(self, Context):
		# Avoid non-user updates
		if Panel_SilkroadProperties.Properties['is_drawing']:
			return
		# Check if there is a change to update it
		selectedEdges = Panel_SilkroadProperties.Properties['selected_edges']
		if not selectedEdges:
			return
		# Apply change to edges from object selected
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)
		navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options')
		for i in selectedEdges:
			e = bm.edges[i]
			# Update edges
			if self.IsUnderpass:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] | 16 # set
			else:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] & 0xEF # unset
	# Called when value has been changed
	def OnIsEntranceUpdate(self, Context):
		# Avoid non-user updates
		if Panel_SilkroadProperties.Properties['is_drawing']:
			return
		# Check if there is a change to update it
		selectedEdges = Panel_SilkroadProperties.Properties['selected_edges']
		if not selectedEdges:
			return
		# Apply change to edges from object selected
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)
		navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options')
		for i in selectedEdges:
			e = bm.edges[i]
			# Update edges
			if self.IsEntrance:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] | 32 # set
			else:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] & 0xD7 # unset
	# Called when value has been changed
	def OnIsUnknownUpdate(self, Context):
		# Avoid non-user updates
		if Panel_SilkroadProperties.Properties['is_drawing']:
			return
		# Check if there is a change to update it
		selectedEdges = Panel_SilkroadProperties.Properties['selected_edges']
		if not selectedEdges:
			return
		# Apply change to edges from object selected
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)
		navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options')
		for i in selectedEdges:
			e = bm.edges[i]
			# Update edges
			if self.IsUnknown:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] | 64 # set
			else:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] & 0xB7 # unset
	# Called when value has been changed
	def OnIsSiegeUpdate(self, Context):
		# Avoid non-user updates
		if Panel_SilkroadProperties.Properties['is_drawing']:
			return
		# Check if there is a change to update it
		selectedEdges = Panel_SilkroadProperties.Properties['selected_edges']
		if not selectedEdges:
			return
		# Apply change to edges from object selected
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)
		navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options')
		for i in selectedEdges:
			e = bm.edges[i]
			# Update edges
			if self.IsSiege:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] | 128 # set
			else:
				e[navEdgesOptionsLayer] = e[navEdgesOptionsLayer] & 0x7F # unset
	# Properties
	ClothByVertex: bpy.props.FloatProperty(
		name="Cloth by Vertex(s)",
		description="Set maximum distance from vertice to be able to move",
		default=0.0,min=0.0,max=100,
		update=OnClothByVertexUpdate
	)
	ClothByEdge: bpy.props.FloatProperty(
		name="Cloth by Edge(s)",
		description="Set maximum distance from edge to be stretched or shrunken",
		default=0.0,min=0.0,max=100,
		update=OnClothByEdgeUpdate
	)
	IsLockedInside: bpy.props.BoolProperty(
		name="Locked Inside",
		description="Lock walking from inside",
		default=False,
		update=OnIsLockedInsideUpdate
	)
	IsLockedOutside: bpy.props.BoolProperty(
		name="Locked Outside",
		description="Lock walking from outside",
		default=False,
		update=OnIsLockedOutsideUpdate
	)
	IsInternal: bpy.props.BoolProperty(
		name="Internal Edge",
		description="Internal edge from navmesh",
		default=False,
	)
	IsGlobal: bpy.props.BoolProperty(
		name="Global Edge",
		description="External edge from region",
		default=False,
	)
	IsUnderpass: bpy.props.BoolProperty(
		name="Underpass",
		description="Locked walk both ways except lower levels",
		default=False,
		update=OnIsUnderpassUpdate
	)
	IsEntrance: bpy.props.BoolProperty(
		name="Entrance",
		description="Dungeon entrance",
		default=False,
		update=OnIsEntranceUpdate
	)
	IsUnknown: bpy.props.BoolProperty(
		name="Bit7",
		description="Unknown",
		default=False,
		update=OnIsUnknownUpdate
	)
	IsSiege: bpy.props.BoolProperty(
		name="Siege",
		description="Fortress walls passthrough attacks",
		default=False,
		update=OnIsSiegeUpdate
	)

class SilkroadPropertiesOperator_SelectDyVertex(bpy.types.Operator):
	"""Select all dynamic vertices (known as Cloth)"""
	bl_idname = "object.silkroad_properties_select_dyvertex"
	bl_label = "Select DyVertex"
	# Define button state
	@classmethod
	def poll(cls, Context):
		return True
	# Execute action
	def execute(self, Context):
		# Deselect all
		bpy.ops.mesh.select_all(action='DESELECT')
		# Get the selected object with bmesh
		mesh = Context.active_object.data
		bm = bmesh.from_edit_mesh(mesh)

		# Select all dynamic vertices
		vertexClothesLayer = bm.verts.layers.float.get('vertex_clothes')
		for v in bm.verts:
			# Check if vertex has dynamics
			v.select_set(True if v[vertexClothesLayer] else False)

		bm.select_mode |= {'VERT'}
		bm.select_flush_mode()

		# Update it visually
		bmesh.update_edit_mesh(mesh,loop_triangles=True)
		return {'FINISHED'}

class SilkroadPropertiesOperator_GenerateClothByEdges(bpy.types.Operator):
	"""Generate default cloth values from edges selected"""
	bl_idname = "object.silkroad_properties_generate_cloth_edges"
	bl_label = "Generate Cloth by Edges"
	# Define button state
	@classmethod
	def poll(cls, Context):
		return True
	# Execute action
	def execute(self, Context):
		# Get the selected object with bmesh
		mesh = Context.active_object.data
		bm = bmesh.from_edit_mesh(mesh)

		# Select all dynamics
		vertexClothesLayer = bm.verts.layers.float.get('vertex_clothes')
		edgeClothesLayer = bm.edges.layers.float.get('edge_clothes')
		for v in bm.verts:
			# Check if is selected
			if v.select:
				# Check if vertex is dynamic
				if v[vertexClothesLayer]:
					# Calculate length from edges
					for e in v.link_edges:
						e[edgeClothesLayer] = e.calc_length()

		# Update it visually
		bmesh.update_edit_mesh(mesh,loop_triangles=True)
		return {'FINISHED'}

class SilkroadPropertiesOperator_ShowClothes(bpy.types.Operator):
	"""Create Blue to Red color layer using cloth info from vertices"""
	bl_idname = "object.silkroad_properties_show_clothes"
	bl_label = "Show Clothes"
	# Define button state
	@classmethod
	def poll(cls, Context):
		return True
	# Execute action
	def execute(self, Context):
		# Get the first object selected with bmesh
		obj = Context.active_object
		bm = bmesh.from_edit_mesh(obj.data)

		# Get data from vertices
		vertexClothesLayer = bm.verts.layers.float.get('vertex_clothes')
		data = {}
		for v in bm.verts:
			data[v.index] = v[vertexClothesLayer]

		# Create color layer
		BlenderSetMode('OBJECT')
		vertexClothesColorLayer = obj.data.vertex_colors.get('DyVertex') or obj.data.vertex_colors.new(name='DyVertex')
		for v in obj.data.vertices:
			# Set color range
			value = (1-data[v.index])*0.667 # Red ~ Blue (HSV)
			value = colorsys.hsv_to_rgb(value, 1.0, 1.0) + (1.0,) # add alpha channel
			self.SetVertexColor(obj,vertexClothesColorLayer,v.index,value)

		# Activate color layer and switch mode
		vertexClothesColorLayer.active = True

		BlenderSetViewport(Context,'SOLID')
		BlenderSetMode('VERTEX_PAINT')
		return {'FINISHED'}

	# Set vertex color from layer
	def SetVertexColor(self, Obj, Layer, VertexIndex, Color):
		for loop in Obj.data.loops:
			if loop.vertex_index == VertexIndex:
				Layer.data[loop.index].color = Color

class SilkroadPropertiesOperator_ShowLockedEdges(bpy.types.Operator):
	"""Mark as "Seam/Sharp" all edges with collisions"""
	bl_idname = "object.silkroad_properties_show_locked_edges"
	bl_label = "Show Locked Edges"
	# Define button state
	@classmethod
	def poll(cls, Context):
		return True
	# Execute action
	def execute(self, Context):
		# List all meshes
		objs = [o for o in Context.selected_objects if o.type == 'MESH']
		for obj in objs:
			# Get the first object selected with bmesh
			Context.view_layer.objects.active = obj
			BlenderSetMode('EDIT')
			bm = bmesh.from_edit_mesh(obj.data)

			# Find all edges locked from inside and mark them as "sharp"
			navEdgesOptionsLayer = bm.edges.layers.int.get('nav_edges_options') or bm.edges.layers.int.new('nav_edges_options')
			for e in bm.edges:
				flags = e[navEdgesOptionsLayer]
				e.seam = False
				e.smooth = True
				# Check flags contains lock inside/outside or underpass
				if flags & 0x01:
					e.seam = True # visualize edges as red
				elif flags & 0x02 or flags & 0x10:
					e.smooth = False # visualize edges as blue

			# Update it visually
			bmesh.update_edit_mesh(obj.data,loop_triangles=True)
		return {'FINISHED'}

# Add dynamic menu into Import
def menu_func_import(self, Context):
	self.layout.operator(Import_JMXVBMS_0110.bl_idname, text="JMXVBMS 0110 (.bms)")
# Add dynamic menu into Export
def menu_func_export(self, Context):
	self.layout.operator(Export_JMXVBMS_0110.bl_idname, text="JMXVBMS 0110 (.bms)")

# Register module
def register():
	# Add classes
	bpy.utils.register_class(SilkroadPropertiesOperator_ShowLockedEdges)
	bpy.utils.register_class(SilkroadPropertiesOperator_SelectDyVertex)
	bpy.utils.register_class(SilkroadPropertiesOperator_GenerateClothByEdges)
	bpy.utils.register_class(SilkroadPropertiesOperator_ShowClothes)
	bpy.utils.register_class(SilkroadProperties)
	bpy.utils.register_class(Panel_SilkroadProperties)
	bpy.utils.register_class(Import_JMXVBMS_0110)
	bpy.utils.register_class(Export_JMXVBMS_0110)
	# Add custom properties
	bpy.types.WindowManager.SROProperties = bpy.props.PointerProperty(type=SilkroadProperties)
	# Add UI options
	bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
	bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

# Unregister module (backwards to avoid issues)
def unregister():
	# Remove UI options
	bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
	bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
	# Remove Custom properties
	delattr(bpy.types.WindowManager,'SROProperties')
	# Remove classes
	bpy.utils.unregister_class(Export_JMXVBMS_0110)
	bpy.utils.unregister_class(Import_JMXVBMS_0110)
	bpy.utils.unregister_class(Panel_SilkroadProperties)
	bpy.utils.unregister_class(SilkroadProperties)
	bpy.utils.unregister_class(SilkroadPropertiesOperator_SelectDyVertex)
	bpy.utils.unregister_class(SilkroadPropertiesOperator_GenerateClothByEdges)
	bpy.utils.unregister_class(SilkroadPropertiesOperator_ShowClothes)
	bpy.utils.unregister_class(SilkroadPropertiesOperator_ShowLockedEdges)
