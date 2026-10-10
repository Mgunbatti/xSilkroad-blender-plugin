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

from .asset_binary import BinaryReader

def debug_print(*args):
    pass

def parse_dof(contents):
	br = BinaryReader(contents)
	if br.ReadAscii(12) != "JMXVDOF 0101":
		raise ValueError("Invalid DOF signature")
	br.SeekRead(0)
	data = {
		'blocks':[]
	}

	# Skip Signature
	br.SeekRead(12,1)
	fileOffsetBlocks = br.ReadUInt()

	# Set cursor at blocks
	br.SeekRead(fileOffsetBlocks)

	blockCount = br.ReadUInt()
	for i in range(blockCount):
		block = {'index':i}
		data['blocks'].append(block)

		block['path'] = br.ReadAscii(br.ReadUInt())
		block['name'] = br.ReadAscii(br.ReadUInt())
		br.SeekRead(4,1)
		x,z,y = br.ReadFloat(),br.ReadFloat(),br.ReadFloat()
		block['position'] = [x,y,z]
		block['yaw'] = br.ReadFloat()
		block['is_entrance'] = br.ReadUInt() != 0
		bbox = [br.ReadFloat(),br.ReadFloat(),br.ReadFloat()]
		bbox += [br.ReadFloat(),br.ReadFloat(),br.ReadFloat()]
		block['bbox'] = [
			bbox[0],bbox[2],bbox[1],
			bbox[3],bbox[5],bbox[4],
		]
		br.SeekRead(4,1)
		br.SeekRead(4,1) # Color
		br.SeekRead(4,1) # NearPlane
		br.SeekRead(4,1) # FarPlane
		br.SeekRead(4,1) # Intensity
		hasHeightFog = br.ReadByte() == 1 # hasHeightFog
		if hasHeightFog:
			br.SeekRead(16,1)
		unkByte = br.ReadByte()
		if unkByte == 2:
			br.SeekRead(28,1)
		br.SeekRead(br.ReadUInt(),1)
		br.SeekRead(4,1)
		br.SeekRead(4,1)
		br.SeekRead(br.ReadUInt()*4,1) # Connected blocks
		br.SeekRead(br.ReadUInt()*4,1) # Visible blocks
		objCount = br.ReadUInt()
		block['objects'] = []
		br.SeekRead(4,1)
		for j in range(objCount):
			obj = {}
			block['objects'].append(obj)

			obj['name'] = br.ReadAscii(br.ReadUInt())
			obj['path'] = br.ReadAscii(br.ReadUInt())
			x,z,y = br.ReadFloat(),br.ReadFloat(),br.ReadFloat()
			obj['position'] = [x,y,z]
			x,z,y = br.ReadFloat(),br.ReadFloat(),br.ReadFloat()
			obj['rotation'] = [x,y,z]
			x,z,y = br.ReadFloat(),br.ReadFloat(),br.ReadFloat()
			obj['scale'] = [x,y,z]
			obj['flags'] = br.ReadUInt() # 0 = None; 2 = ColObj; 4 = WaterObj
			br.SeekRead(4,1)
			br.SeekRead(4,1)
			if obj['flags'] & 4:
				br.SeekRead(4,1)
		lightCount = br.ReadUInt()
		for j in range(lightCount):
			br.SeekRead(br.ReadUInt(),1) # name
			br.SeekRead(12*4,1)
			br.SeekRead(4*3,1)

	return data

def parse_nvm(contents):
	br = BinaryReader(contents)
	if br.ReadAscii(12) != "JMXVNVM 1000":
		raise ValueError("Invalid NVM signature")
	br.SeekRead(0)
	data = {
		'objects':[],
		'cells':[],
		'heightmap_faces':[],
		'heightmap_vertices':[]
	}

	# Skip Signature
	br.SeekRead(12,1)

	# Objects
	count = br.ReadUShort()
	for i in range(count):
		# read object data
		obj = {}
		obj['asset_id'] = br.ReadUInt()

		x,z,y = br.ReadFloat(),br.ReadFloat(),br.ReadFloat()
		obj['local_position'] = [x,y,z]
		obj['type'] = br.ReadUShort()
		obj['yaw'] = br.ReadFloat()
		obj['local_uid'] = br.ReadUShort()

		br.SeekRead(2,1)
		br.SeekRead(1,1)
		obj['is_struct'] = br.ReadByte() == 1
		obj['RID'] = br.ReadUShort()

		# ...
		linkedEdgesCount = br.ReadUShort()
		for j in range(linkedEdgesCount):
			br.SeekRead(2,1)
			br.SeekRead(2,1)
			br.SeekRead(2,1)

		# save object
		data['objects'].append(obj)

	# Terrain Mesh - Cells (Quads)
	cellsCount = br.ReadUInt()
	walkableCellsCount = br.ReadUInt()
	debug_print('cellsCount',cellsCount)
	debug_print('walkableCellsCount',walkableCellsCount)
	for i in range(cellsCount):
		cell = {}
		cell['global_edges'] = []
		cell['internal_edges'] = []

		cell['min'] = [br.ReadFloat(),br.ReadFloat()]
		cell['max'] = [br.ReadFloat(),br.ReadFloat()]
		cell['objects_indices'] = []

		cellObjCount = br.ReadByte()
		for j in range(cellObjCount):
			cell['objects_indices'].append(br.ReadUShort())

		# save cell
		data['cells'].append(cell)

	# Terrain Mesh - Edges Outside Collisions
	count = br.ReadUInt()
	for i in range(count):
		edge = {}
		edge['min'] = [br.ReadFloat(),br.ReadFloat()]
		edge['max'] = [br.ReadFloat(),br.ReadFloat()]
		edge['flags'] = br.ReadByte()
		edge['assoc_cell_direction01'] = br.ReadByte()
		edge['assoc_cell_direction02'] = br.ReadByte()

		cellIdx = br.ReadShort()
		edges = data['cells'][cellIdx]['global_edges']
		edges.append(edge)

		cellIdx = br.ReadShort()
		if cellIdx != -1:
			if cellIdx < len(data['cells']):
				edges = data['cells'][cellIdx]['global_edges']
				edges.append(edge)
			else:
				debug_print('error index',cellIdx)

		br.SeekRead(2,1)
		br.SeekRead(2,1)

	# Terrain Mesh - Edges Inside Collisions
	count = br.ReadUInt()
	for i in range(count):
		edge = {}
		edge['min'] = [br.ReadFloat(),br.ReadFloat()]
		edge['max'] = [br.ReadFloat(),br.ReadFloat()]
		edge['flags'] = br.ReadByte()
		edge['assoc_cell_direction01'] = br.ReadByte()
		edge['assoc_cell_direction02'] = br.ReadByte()

		cellIdx = br.ReadShort()
		edges = data['cells'][cellIdx]['internal_edges']
		edges.append(edge)

		cellIdx = br.ReadShort()
		if cellIdx != -1:
			if cellIdx < len(data['cells']):
				edges = data['cells'][cellIdx]['internal_edges']
				edges.append(edge)
			else:
				debug_print('error index',cellIdx)

	# TileMap
	heightmap_faces = data['heightmap_faces']
	for i in range(96):
		for j in range(96):
			face = {}
			face['id'] = br.ReadUInt()
			face['flags'] = br.ReadUShort()
			face['tile_id'] = br.ReadUShort()
			heightmap_faces.append(face)

	# HeightMap
	heightmap = data['heightmap_vertices']
	for y in range(97):
		for x in range(97):
			heightmap.append([x*20,y*20,br.ReadFloat()])

	# Return data
	return data
