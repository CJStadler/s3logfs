class LargeFile(object):
	"""docstring for LargeFile"""
	NUMBER_OF_BLOCKS = 16
	BLOCK_SIZE = 512
	POINTER_SIZE = 4
	NUMBER_OF_DIRECT_BLOCKS = 13

	def __init__(self):
		assert(self.NUMBER_OF_DIRECT_BLOCKS <= self.NUMBER_OF_BLOCKS)
		assert(0 < self.NUMBER_OF_DIRECT_BLOCKS)
		assert(self.POINTER_SIZE < self.BLOCK_SIZE)
		self.INDIRECT_BLOCKS = self.NUMBER_OF_BLOCKS - self.NUMBER_OF_DIRECT_BLOCKS
		self.pointersPerBlock = self.BLOCK_SIZE//self.POINTER_SIZE
		self.directBlocksSize = self.NUMBER_OF_DIRECT_BLOCKS*self.BLOCK_SIZE 

	def printAll(self):
		print (self.NUMBER_OF_BLOCKS)

	def findStartingPosIndirect(self, startPos, maxLevel, possibleSize):

		possibleSize = possibleSize//self.pointersPerBlock
		index = startPos // possibleSize
		offset = startPos - index * possibleSize
		path = [index]

		if(maxLevel>0):
			return path + self.findStartingPosIndirect(offset, maxLevel-1, possibleSize)

		return path + [offset]

	def findStartingPos(self, startPos):
		if(startPos < self.directBlocksSize):
			return [startPos//self.BLOCK_SIZE, startPos%self.BLOCK_SIZE]
		startPos -= self.directBlocksSize

		possibleSize = self.BLOCK_SIZE
		for i in range(self.INDIRECT_BLOCKS):
			possibleSize = possibleSize * self.pointersPerBlock 
			blockIndex = self.NUMBER_OF_DIRECT_BLOCKS + i;
			if startPos < possibleSize:
				return [blockIndex] + self.findStartingPosIndirect(startPos, i, possibleSize)
			else :
				startPos -= possibleSize

		print ("error")

	def findAllPos(self, startPos, size):
		paths = []
		path = self.findStartingPos(startPos)
		size -= (self.BLOCK_SIZE - path[len(path)-1])
		paths.append(path)
		while size > 0:
			path = self.findNextPos(path)
			paths.append(path)
			size -= (self.BLOCK_SIZE - path[len(path)-1])
		return paths

	def findPosition(self, path):
		if(len(path) == 2):
			return path[0]*self.BLOCK_SIZE+path[1]

		startPos = self.directBlocksSize
		maxLevel = len(path)-2
		for i in range(1, len(path)-2):
			startPos +=  self.BLOCK_SIZE * (self.pointersPerBlock ** (maxLevel-i))
		for i in range(1, len(path)-1):
			startPos += path[i] * self.BLOCK_SIZE * (self.pointersPerBlock ** (maxLevel-i))
		startPos += path[maxLevel+1]
		return startPos

	def findNextPos(self, path):
		position = self.findPosition(path)
		position += (self.BLOCK_SIZE - path[len(path)-1])
		return self.findStartingPos(position)

x = LargeFile()
# print (x.findAllPos(101, 100000))
print (x.findAllPos(300+512*130, 10000))