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

import struct

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
		if not 0 <= self.Position <= self.Length:
			raise ValueError("Invalid binary seek: %d" % self.Position)
	# Generic Python way for reading and moving the cursor
	def ReadPython(self,Format,Size):
		if Size < 0 or self.Position < 0 or self.Position + Size > self.Length:
			raise ValueError("Truncated binary asset at offset %d" % self.Position)
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
	# Reads an unsigned integer
	def ReadULong(self):
		return self.ReadPython('<q',8)
	# Reads an integer
	def ReadLong(self):
		return self.ReadPython('<Q',8)
	# Reads an string by codepage
	def ReadString(self, Count, CodePage):
		return self.ReadBytes(Count).decode(CodePage)
	# Reads an string as ascii
	def ReadAscii(self, Count):
		return self.ReadString(Count,'cp1252')

