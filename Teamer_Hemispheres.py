#
#	FILE:	 Teamer_Hemispheres.py
#	AUTHOR:  Aineias Symphalios
#	Adapted from Ben Sarsgard's Hemispheres.py


from CvPythonExtensions import *
import CvUtil
import CvMapGeneratorUtil
from CvMapGeneratorUtil import FractalWorld
from CvMapGeneratorUtil import TerrainGenerator
from CvMapGeneratorUtil import FeatureGenerator
from CvMapGeneratorUtil import BonusBalancer
balancer = BonusBalancer()

bTeamPlacement = False
teamRegionMap = {}
teamAreaMap = {}
_START_PLOT_MAP = None
_THEM_REGION_RECTS = {}
bDebugSignsEnabled = True

def getDescription():
	desc = "Hemispheres.py with customizations intended for multiplayer teamer games."
	desc += "Recommended sizes: TBD"
	return desc

def isAdvancedMap():
	"This map should not show up in simple mode"
	return 0

def getNumCustomMapOptions():
	return 8
	
def getCustomMapOptionName(argsList):
	[iOption] = argsList
	if iOption == 0:
		return "Continent Size"
	elif iOption == 1:
		return "Island Size"
	elif iOption == 2:
		return "Number of Continents"
	elif iOption == 3:
		return "World Wrap"
	elif iOption == 4:
		return "Axial Tilt"
	elif iOption == 5:
		return "Teamer Resource Balancing"
	elif iOption == 6:
		return "Debug Signs"
	elif iOption == 7:
		return "StartPlot Min Land Food"
	return ""
	
def getNumCustomMapOptionValues(argsList):
	[iOption] = argsList
	if iOption == 0: return 4
	elif iOption == 1: return 2
	elif iOption == 2: return 5
	elif iOption == 3: return 3
	elif iOption == 4: return 2
	elif iOption == 5: return 2
	elif iOption == 6: return 2
	elif iOption == 7: return 4
	return 0
	
def getCustomMapOptionDescAt(argsList):
	[iOption, iSelection] = argsList
	if iOption == 0:
		if iSelection == 0: return "Massive Continents"
		elif iSelection == 1: return "Normal Continents"
		elif iSelection == 2: return "Snaky Continents"
		return "Varied"
	elif iOption == 1:
		if iSelection == 0: return "Islands"
		return "Tiny Islands"
	elif iOption == 2:
		if iSelection == 0: return "2"
		elif iSelection == 1: return "3"
		elif iSelection == 2: return "4"
		elif iSelection == 3: return "5"
		return "6"
	elif iOption == 3:
		if iSelection == 0: return "Flat"
		elif iSelection == 1: return "Cylindrical"
		return "Toroidal"
	elif iOption == 4:
		if iSelection == 0: return "0 Degrees"
		return "90 Degrees"
	elif iOption == 5:
		if iSelection == 0: return "Disabled"
		return "Enabled"
	elif iOption == 6:
		if iSelection == 0: return "Disabled"
		return "Enabled"
	elif iOption == 7:
		if iSelection == 0: return "Disabled"
		elif iSelection == 1: return "At least 1"
		elif iSelection == 2: return "At least 2"
		return "At least 3"
	return ""

def getCustomMapOptionDefault(argsList):
	[iOption] = argsList
	if iOption == 0: return 0
	elif iOption == 1: return 1
	elif iOption == 2: return 0
	elif iOption == 3: return 1
	elif iOption == 4: return 0
	elif iOption == 5: return 1
	elif iOption == 6: return 1
	elif iOption == 7: return 1
	return 0

def getWrapX():
	map = CyMap()
	return (map.getCustomMapOption(3) == 1 or map.getCustomMapOption(3) == 2)

def getWrapY():
	map = CyMap()
	return (map.getCustomMapOption(3) == 2)

def minStartingDistanceModifier():
	return -12

def beforeGeneration():
	global xShiftRoll
	global yShiftRoll
	global ySplitRoll
	global yPortionRoll
	global bTeamPlacement
	global teamRegionMap
	global teamAreaMap
	global _START_PLOT_MAP
	global bDebugSignsEnabled
	gc = CyGlobalContext()
	map = CyMap()
	dice = gc.getGame().getMapRand()

	# Binary shift roll (for horizontal shifting if Island Region Separate).
	xShiftRoll = dice.get(2, "Region Shift, Horizontal - Left and Right PYTHON")
	yShiftRoll = dice.get(2, "Region Shift, Vertical - Left and Right PYTHON")
	ySplitRoll = dice.get(2, "Region Split, Vertical - Left and Right PYTHON")
	yPortionRoll = dice.get(2, "Region Portioning, Vertical - Left and Right PYTHON")
	print xShiftRoll

	_START_PLOT_MAP = None
	teamRegionMap.clear()
	teamAreaMap.clear()
	bTeamPlacement = False
	bDebugSignsEnabled = (map.getCustomMapOption(6) == 1)

	activeTeams = []
	for iPlayer in range(gc.getMAX_CIV_PLAYERS()):
		pPlayer = gc.getPlayer(iPlayer)
		if pPlayer.isEverAlive():
			iTeam = pPlayer.getTeam()
			if iTeam not in activeTeams:
				activeTeams.append(iTeam)

	activeTeams.sort()
	iNumTeams = len(activeTeams)
	iRegionCount = 2 + map.getCustomMapOption(2)
	vSplitPrimary, vSplitSecondary, vSplitTertiary, tripleSplit = THemContinentRegionBuilder.getSplitSettings(iRegionCount)

	if iNumTeams == 2:
		bTeamPlacement = True
		teamRegionMap[activeTeams[0]] = "primary"
		teamRegionMap[activeTeams[1]] = "secondary"
	elif iNumTeams == 3 and tripleSplit:
		bTeamPlacement = True
		teamRegionMap[activeTeams[0]] = "primary"
		teamRegionMap[activeTeams[1]] = "secondary"
		teamRegionMap[activeTeams[2]] = "tertiary"

	if bTeamPlacement:
		print "THem team placement enabled:", teamRegionMap

class THemMultilayeredFractal(CvMapGeneratorUtil.MultilayeredFractal):
	def generateIslandRegion(self, minTinies, extraTinies, iWestX, iSouthY, iWidth, iHeight, iGrain):
		numTinies = minTinies + self.dice.get(extraTinies, "Tiny Islands - Custom Continents PYTHON")
		print("Patches of Tiny Islands: ", numTinies)
		if numTinies:
			for tiny_loop in range(numTinies):
				tinyWidth = int(self.iW * 0.20)
				tinyHeight = int(self.iH * 0.20)
				iXRange = iWidth - tinyWidth
				iYRange = iHeight - tinyHeight
				if iXRange < 0:
					iXRange = 0
					tinyWidth = iWidth
				if iYRange < 0:
					iYRange = 0
					tinyHeight = iHeight
				tinyWestX = iWestX
				tinySouthY = iSouthY
				if iXRange > 0:
					tinyWestX += self.dice.get(iXRange, "Tiny Longitude - Custom Continents PYTHON")
				if iYRange > 0:
					tinySouthY += self.dice.get(iYRange, "Tiny Latitude - Custom Continents PYTHON")

				self.generatePlotsInRegion(85,
										   tinyWidth, tinyHeight,
										   tinyWestX, tinySouthY,
										   iGrain, 3,
										   0, self.iTerrainFlags,
										   6, 5,
										   True, 3,
										   -1, False,
										   False
										   )
		return 0

	def generateContinentRegion(self, iWater, iWidth, iHeight, iWestX, iSouthY, iGrain, xExp):
		self.generatePlotsInRegion(iWater,
								   iWidth, iHeight,
								   iWestX, iSouthY,
								   iGrain, 4,
								   self.iRoundFlags, self.iTerrainFlags,
								   xExp, 6,
								   True, 15,
								   -1, False,
								   False
								   )
		return 0

	def generatePlotsByRegion(self, region_data):
		for data in region_data:
			kind = data[0]
			if kind == "continent":
				name, iWater, iWestX, iSouthY, iWidth, iHeight, iGrain, xExp = data[1:]
				print(name, "West:", iWestX, "South:", iSouthY, "Width:", iWidth, "Height:", iHeight)
				self.generateContinentRegion(iWater, iWidth, iHeight, iWestX, iSouthY, iGrain, xExp)
			elif kind == "islands":
				name, minTinies, extraTinies, iWestX, iSouthY, iWidth, iHeight, iGrain = data[1:]
				print(name, "West:", iWestX, "South:", iSouthY, "Width:", iWidth, "Height:", iHeight)
				self.generateIslandRegion(minTinies, extraTinies, iWestX, iSouthY, iWidth, iHeight, iGrain)

		print "Done"
		return self.wholeworldPlotTypes

class THemContinentRegionBuilder:
	def __init__(self, map, gc):
		self.map = map
		self.gc = gc
		self.iW = map.getGridWidth()
		self.iH = map.getGridHeight()
		self.regionRects = {}

	def getSplitSettings(iRegionCount):
		if iRegionCount == 2:
			return (0, 0, 0, 0)
		elif iRegionCount == 3:
			return (0, 0, 0, 1)
		elif iRegionCount == 4:
			return (1, 1, 0, 0)
		elif iRegionCount == 5:
			return (0, 1, 1, 1)
		elif iRegionCount == 6:
			return (1, 1, 1, 1)
		return (0, 0, 0, 0)
	getSplitSettings = staticmethod(getSplitSettings)

	def getContinentSettings(self):
		iSeaLevelChange = self.gc.getSeaLevelInfo(self.map.getSeaLevel()).getSeaLevelChange()
		print("getSeaLevelChange", iSeaLevelChange)

		iContinentOption = self.map.getCustomMapOption(0)
		if iContinentOption == 3:
			return {
				"primary": (1, 80 + iSeaLevelChange),
				"secondary": (3, 70 + iSeaLevelChange),
				"tertiary": (2, 75 + iSeaLevelChange)
				}
		elif iContinentOption == 0:
			iGrain = 1
		else:
			iGrain = 2 + iContinentOption

		return {
			"primary": (iGrain, 70 + iSeaLevelChange),
			"secondary": (iGrain, 70 + iSeaLevelChange),
			"tertiary": (iGrain, 70 + iSeaLevelChange)
			}

	def shrinkRegion(self, iWestX, iSouthY, iWidth, iHeight):
		iMarginX = int(0.05 * self.iW)
		iMarginY = int(0.0 * self.iH)

		if iMarginX < 1: iMarginX = 1
		if iMarginY < 1: iMarginY = 1

		if iWidth <= (2 * iMarginX) + 4:
			iMarginX = 0
		if iHeight <= (2 * iMarginY) + 4:
			iMarginY = 0

		return (iWestX + iMarginX, iSouthY + iMarginY, iWidth - (2 * iMarginX), iHeight - (2 * iMarginY))

	def getCoreRegion(self, iWestX, iSouthY, iWidth, iHeight):
		iCoreWidth = int(0.50 * iWidth)
		iCoreHeight = int(0.60 * iHeight)

		if iCoreWidth < 4: iCoreWidth = iWidth
		if iCoreHeight < 4: iCoreHeight = iHeight

		iCoreWestX = iWestX + ((iWidth - iCoreWidth) / 2)
		iCoreSouthY = iSouthY + ((iHeight - iCoreHeight) / 2)
		return (iCoreWestX, iCoreSouthY, iCoreWidth, iCoreHeight)

	def getHorizontalBand(self, label, tripleSplit):
		global xShiftRoll

		if label == "tertiary":
			westShift = int(0.66 * self.iW)
			eastShift = 0
		elif label == "primary":
			if tripleSplit:
				if xShiftRoll:
					westShift = int(0.33 * self.iW)
					eastShift = int(0.33 * self.iW)
				else:
					westShift = 0
					eastShift = int(0.66 * self.iW)
			else:
				if xShiftRoll:
					westShift = int(0.5 * self.iW)
					eastShift = 0
				else:
					westShift = 0
					eastShift = int(0.5 * self.iW)
		else:
			if tripleSplit:
				if xShiftRoll:
					westShift = 0
					eastShift = int(0.66 * self.iW)
				else:
					westShift = int(0.33 * self.iW)
					eastShift = int(0.33 * self.iW)
			else:
				if xShiftRoll:
					westShift = 0
					eastShift = int(0.5 * self.iW)
				else:
					westShift = int(0.5 * self.iW)
					eastShift = 0

		iWestX = westShift
		iEastX = self.iW - eastShift
		return (iWestX, iEastX - iWestX)

	def getVerticalBands(self, vSplit):
		global yShiftRoll
		global yPortionRoll

		if not vSplit:
			return [(0, self.iH)]

		splitYBigger = 0.5
		splitYSmaller = 0.5
		splitYBuffer = 0.1

		if yPortionRoll:
			if yShiftRoll:
				firstNorth = int(splitYBuffer * self.iH)
				firstSouth = int(splitYBigger * self.iH)
				secondNorth = int(splitYSmaller * self.iH)
				secondSouth = int(splitYBuffer * self.iH)
			else:
				firstNorth = int(splitYSmaller * self.iH)
				firstSouth = int(splitYBuffer * self.iH)
				secondNorth = int(splitYBuffer * self.iH)
				secondSouth = int(splitYBigger * self.iH)
		else:
			if yShiftRoll:
				firstNorth = int(splitYBuffer * self.iH)
				firstSouth = int(splitYSmaller * self.iH)
				secondNorth = int(splitYBigger * self.iH)
				secondSouth = int(splitYBuffer * self.iH)
			else:
				firstNorth = int(splitYBigger * self.iH)
				firstSouth = int(splitYBuffer * self.iH)
				secondNorth = int(splitYBuffer * self.iH)
				secondSouth = int(splitYSmaller * self.iH)

		return [
			(firstSouth, self.iH - firstNorth - firstSouth),
			(secondSouth, self.iH - secondNorth - secondSouth)
			]

	def getIslandStripRegions(self, iWestX, iSouthY, iWidth, iHeight):
		iCutHeight = int(0.20 * self.iH)
		if iCutHeight < 1:
			iCutHeight = 1
		if iCutHeight > iHeight:
			iCutHeight = iHeight

		return (
			(iWestX, iSouthY, iWidth, iCutHeight),
			(iWestX, iSouthY + iHeight - iCutHeight, iWidth, iCutHeight)
			)

	def getIslandCounts(self, label, vSplit):
		if vSplit:
			minTinies = 1
			extraTinies = 2
			if label != "primary":
				minTinies = 2
				extraTinies = 3
		else:
			minTinies = 2
			extraTinies = 3
			if label != "primary":
				minTinies = 3
				extraTinies = 4
		return (minTinies, extraTinies)

	def appendRegionRect(self, label, rect):
		if not self.regionRects.has_key(label):
			self.regionRects[label] = []
		self.regionRects[label].append(rect)

	def addContinentRegions(self, region_data, label, vSplit, tripleSplit, settings, iIslandsGrain, tinyIslandOverlap):
		iWestX, iWidth = self.getHorizontalBand(label, tripleSplit)
		iGrain, iWater = settings[label]
		xExp = 6
		bands = self.getVerticalBands(vSplit)
		minTinies, extraTinies = self.getIslandCounts(label, vSplit)

		for i in range(len(bands)):
			iSouthY, iHeight = bands[i]
			iContWestX, iContSouthY, iContWidth, iContHeight = self.shrinkRegion(iWestX, iSouthY, iWidth, iHeight)
			region_data.append(("continent", label + " shoreline", iWater, iContWestX, iContSouthY, iContWidth, iContHeight, iGrain, xExp))
			iCoreWestX, iCoreSouthY, iCoreWidth, iCoreHeight = self.getCoreRegion(iContWestX, iContSouthY, iContWidth, iContHeight)
			region_data.append(("continent", label + " core", 30, iCoreWestX, iCoreSouthY, iCoreWidth, iCoreHeight, 1, xExp))
			self.appendRegionRect(label, (iContWestX, iContSouthY, iContWidth, iContHeight))
			if tinyIslandOverlap == 0:
				islandRects = self.getIslandStripRegions(iContWestX, iContSouthY, iContWidth, iContHeight)
				iIslandWestX, iIslandSouthY, iIslandWidth, iIslandHeight = islandRects[0]
				region_data.append(("islands", label + " south islands", minTinies, extraTinies, iIslandWestX, iIslandSouthY, iIslandWidth, iIslandHeight, iIslandsGrain))
				iIslandWestX, iIslandSouthY, iIslandWidth, iIslandHeight = islandRects[1]
				region_data.append(("islands", label + " north islands", minTinies, extraTinies, iIslandWestX, iIslandSouthY, iIslandWidth, iIslandHeight, iIslandsGrain))

	def buildRegionData(self):
		self.regionRects = {}
		settings = self.getContinentSettings()
		iIslandsGrain = 4 + self.map.getCustomMapOption(1)
		tinyIslandOverlap = 0
		iRegionCount = 2 + self.map.getCustomMapOption(2)
		vSplitPrimary, vSplitSecondary, vSplitTertiary, tripleSplit = THemContinentRegionBuilder.getSplitSettings(iRegionCount)
		region_data = []

		if tinyIslandOverlap:
			region_data.append(("islands", "overlap islands", 4, 6, 0, 0, self.iW, self.iH, iIslandsGrain))

		self.addContinentRegions(region_data, "primary", vSplitPrimary, tripleSplit, settings, iIslandsGrain, tinyIslandOverlap)
		self.addContinentRegions(region_data, "secondary", vSplitSecondary, tripleSplit, settings, iIslandsGrain, tinyIslandOverlap)
		if tripleSplit:
			self.addContinentRegions(region_data, "tertiary", vSplitTertiary, tripleSplit, settings, iIslandsGrain, tinyIslandOverlap)

		return region_data

	def copyRegionRects(self):
		rectsCopy = {}
		for label in self.regionRects.keys():
			rectsCopy[label] = []
			for rect in self.regionRects[label]:
				rectsCopy[label].append(rect)
		return rectsCopy

	def countRegionLand(self, plotTypes):
		counts = {}
		for label in self.regionRects.keys():
			iCount = 0
			for rect in self.regionRects[label]:
				iWestX, iSouthY, iWidth, iHeight = rect
				for x in range(iWestX, iWestX + iWidth):
					for y in range(iSouthY, iSouthY + iHeight):
						i = y * self.iW + x
						if plotTypes[i] != PlotTypes.PLOT_OCEAN:
							iCount += 1
			counts[label] = iCount
		return counts

	def getLandBalanceScore(self, counts):
		labels = counts.keys()
		if len(labels) < 2:
			return 0

		iTotal = 0
		for label in labels:
			iTotal += counts[label]

		if iTotal == 0:
			return 0

		iRegions = len(labels)
		iWorst = 0
		for label in labels:
			iScore = abs(((counts[label] * iRegions * 10000) / iTotal) - 10000)
			if iScore > iWorst:
				iWorst = iScore

		return iWorst

	def isLandBalanceAcceptable(self, counts):
		labels = counts.keys()
		if len(labels) < 2:
			return True

		iTotal = 0
		for label in labels:
			iTotal += counts[label]

		if iTotal == 0:
			return True

		iRegions = len(labels)
		for label in labels:
			iScaled = counts[label] * iRegions * 100
			# +/- 3%
			if iScaled < iTotal * 97:
				return False
			if iScaled > iTotal * 103:
				return False

		return True

	def printLandBalance(self, iAttempt, counts, bAccepted):
		labels = counts.keys()
		labels.sort()
		sStatus = "rejected"
		if bAccepted:
			sStatus = "accepted"
		print "THem land balance attempt %d %s" % (iAttempt, sStatus)
		for label in labels:
			print "  %s land: %d" % (label, counts[label])

def generatePlotTypes():
	global _THEM_REGION_RECTS

	print "THem generatePlotTypes entered"
	NiTextOut("Setting Plot Types (Python Custom Continents) ...")
	gc = CyGlobalContext()
	map = CyMap()
	iMaxAttempts = 20
	bestPlotTypes = None
	bestRects = None
	iBestScore = -1

	for iAttempt in range(1, iMaxAttempts + 1):
		builder = THemContinentRegionBuilder(map, gc)
		region_data = builder.buildRegionData()
		fractal_world = THemMultilayeredFractal()
		plotTypes = fractal_world.generatePlotsByRegion(region_data)
		counts = builder.countRegionLand(plotTypes)
		bAccepted = builder.isLandBalanceAcceptable(counts)
		builder.printLandBalance(iAttempt, counts, bAccepted)
		if bAccepted:
			_THEM_REGION_RECTS = builder.copyRegionRects()
			return plotTypes

		iScore = builder.getLandBalanceScore(counts)
		if iBestScore == -1 or iScore < iBestScore:
			iBestScore = iScore
			bestPlotTypes = plotTypes
			bestRects = builder.copyRegionRects()

	if bestRects != None:
		_THEM_REGION_RECTS = bestRects
	print "THem land balance fallback after %d attempts" % (iMaxAttempts)
	return bestPlotTypes

def _get_dominant_area_for_region(label, usedAreas):
	global _THEM_REGION_RECTS

	map = CyMap()
	areaCounts = {}
	rects = _THEM_REGION_RECTS.get(label, [])
	for rect in rects:
		iWestX, iSouthY, iWidth, iHeight = rect
		for x in range(iWestX, iWestX + iWidth):
			for y in range(iSouthY, iSouthY + iHeight):
				pPlot = map.plot(x, y)
				if pPlot.isWater() or pPlot.isPeak(): continue
				iArea = pPlot.getArea()
				if not areaCounts.has_key(iArea):
					areaCounts[iArea] = 0
				areaCounts[iArea] += 1

	bestArea = -1
	bestCount = -1
	for iArea in areaCounts.keys():
		if usedAreas.has_key(iArea): continue
		if areaCounts[iArea] > bestCount:
			bestArea = iArea
			bestCount = areaCounts[iArea]

	return bestArea

def _resolve_team_areas():
	global bTeamPlacement
	global teamRegionMap
	global teamAreaMap

	if not bTeamPlacement:
		return False

	map = CyMap()
	map.recalculateAreas()
	teamAreaMap.clear()
	usedAreas = {}

	sortedTeams = teamRegionMap.keys()
	sortedTeams.sort()
	for iTeam in sortedTeams:
		label = teamRegionMap[iTeam]
		iArea = _get_dominant_area_for_region(label, usedAreas)
		if iArea == -1:
			print "THem could not resolve area for team %d region %s" % (iTeam, label)
			bTeamPlacement = False
			teamAreaMap.clear()
			return False

		teamAreaMap[iTeam] = iArea
		usedAreas[iArea] = 1
		print "THem team %d assigned to area %d from %s" % (iTeam, iArea, label)

	return True

def _get_team_region_bounds(label, iW, iH):
	global _THEM_REGION_RECTS

	rects = _THEM_REGION_RECTS.get(label, [])
	if len(rects) == 0:
		return (0, iW - 1, 0, iH - 1)

	xMin = iW - 1
	xMax = 0
	yMin = iH - 1
	yMax = 0

	for rect in rects:
		iWestX, iSouthY, iWidth, iHeight = rect
		iEastX = iWestX + iWidth - 1
		iNorthY = iSouthY + iHeight - 1
		if iWestX < xMin: xMin = iWestX
		if iEastX > xMax: xMax = iEastX
		if iSouthY < yMin: yMin = iSouthY
		if iNorthY > yMax: yMax = iNorthY

	if xMin < 0: xMin = 0
	if xMax > iW - 1: xMax = iW - 1
	if yMin < 0: yMin = 0
	if yMax > iH - 1: yMax = iH - 1

	return (xMin, xMax, yMin, yMax)

def _assign_all_starting_plots():
	global bTeamPlacement
	global teamRegionMap
	global teamAreaMap

	gc = CyGlobalContext()
	map = CyMap()
	mapRand = gc.getGame().getMapRand()
	iW = map.getGridWidth()
	iH = map.getGridHeight()

	if not _resolve_team_areas():
		return None

	teamPlayersMap = {}
	for iPlayer in range(gc.getMAX_CIV_PLAYERS()):
		pPlayer = gc.getPlayer(iPlayer)
		if pPlayer.isEverAlive():
			iTeam = pPlayer.getTeam()
			if not teamPlayersMap.has_key(iTeam):
				teamPlayersMap[iTeam] = []
			teamPlayersMap[iTeam].append(iPlayer)

	sortedTeams = teamPlayersMap.keys()
	sortedTeams.sort()
	assignments = {}
	assigned_plots = []

	for iTeam in sortedTeams:
		if not teamAreaMap.has_key(iTeam):
			bTeamPlacement = False
			return None

		teamPlayers = teamPlayersMap[iTeam]
		teamPlayers.sort()
		numInTeam = len(teamPlayers)
		iTargetArea = teamAreaMap[iTeam]
		label = teamRegionMap.get(iTeam, "")
		(teamXMin, teamXMax, teamYMin, teamYMax) = _get_team_region_bounds(label, iW, iH)

		sliceOrder = []
		for s in range(numInTeam):
			sliceOrder.append(s)

		for i in range(numInTeam):
			j = mapRand.get(numInTeam, "Shuffle Slices")
			temp = sliceOrder[i]
			sliceOrder[i] = sliceOrder[j]
			sliceOrder[j] = temp

		for i in range(numInTeam):
			playerID = teamPlayers[i]
			player = gc.getPlayer(playerID)
			player.AI_updateFoundValues(True)

			xMin, xMax = teamXMin, teamXMax
			yMin, yMax = teamYMin, teamYMax
			availXMin, availXMax = teamXMin, teamXMax
			availYMin, availYMax = teamYMin, teamYMax

			sliceIdx = sliceOrder[i]
			fullXMin, fullXMax = xMin, xMax
			fullYMin, fullYMax = yMin, yMax
			sliceHeight = (availYMax - availYMin) / numInTeam
			fullYMin = availYMin + (sliceIdx * sliceHeight)
			fullYMax = fullYMin + sliceHeight
			fullXMin = availXMin
			fullXMax = availXMax
			xMin = fullXMin
			xMax = fullXMax
			yMin = fullYMin
			yMax = fullYMax
			if sliceHeight > 8:
				iSliceMargin = 4
				yMin = fullYMin + iSliceMargin
				yMax = fullYMax - iSliceMargin

			yMin = max(0, yMin - 2)
			yMax = min(iH - 1, yMax + 2)
			xMin = max(0, xMin)
			xMax = min(iW - 1, xMax)
			fullXMin = max(0, fullXMin)
			fullXMax = min(iW - 1, fullXMax)
			fullYMin = max(0, fullYMin)
			fullYMax = min(iH - 1, fullYMax)

			searchBoxes = [(xMin, xMax, yMin, yMax)]
			if fullXMin != xMin or fullXMax != xMax or fullYMin != yMin or fullYMax != yMax:
				searchBoxes.append((fullXMin, fullXMax, fullYMin, fullYMax))

			plotAssigned = False
			for (searchXMin, searchXMax, searchYMin, searchYMax) in searchBoxes:
				currentMinDist = 10
				while currentMinDist >= 5 and not plotAssigned:
					bestVal = -1
					bestPlot = None

					for x in range(searchXMin, searchXMax + 1):
						for y in range(searchYMin, searchYMax + 1):
							pPlot = map.plot(x, y)
							if pPlot.isWater() or pPlot.isPeak(): continue
							if pPlot.getArea() != iTargetArea: continue

							tooClose = False
							for (ax, ay) in assigned_plots:
								if plotDistance(x, y, ax, ay) < currentMinDist:
									tooClose = True
									break
							if tooClose: continue

							val = pPlot.getFoundValue(playerID)
							iEdgeDist = min(y - fullYMin, fullYMax - y)
							if iEdgeDist < 0: iEdgeDist = 0
							val -= (10 - min(10, iEdgeDist)) * 8
							if val > bestVal:
								bestVal = val
								bestPlot = pPlot

					if bestPlot is not None:
						assignments[playerID] = map.plotNum(bestPlot.getX(), bestPlot.getY())
						assigned_plots.append((bestPlot.getX(), bestPlot.getY()))
						plotAssigned = True
					else:
						currentMinDist -= 1
				if plotAssigned: break

			if not plotAssigned:
				for x in range(fullXMin, fullXMax + 1):
					for y in range(fullYMin, fullYMax + 1):
						pPlot = map.plot(x, y)
						if pPlot.isWater() or pPlot.isPeak(): continue
						if pPlot.getArea() != iTargetArea: continue
						tooClose = False
						for (ax, ay) in assigned_plots:
							if plotDistance(x, y, ax, ay) < 5:
								tooClose = True
								break
						if tooClose: continue
						assignments[playerID] = map.plotNum(x, y)
						assigned_plots.append((x, y))
						plotAssigned = True
						break
					if plotAssigned: break

			if not plotAssigned:
				print "THem failed to assign starting plot for player %d" % playerID
				bTeamPlacement = False
				return None

	return assignments

def findStartingPlot(argsList):
	global bTeamPlacement
	global _START_PLOT_MAP

	playerID = argsList[0]
	if not bTeamPlacement:
		return -1

	if _START_PLOT_MAP is None:
		_START_PLOT_MAP = _assign_all_starting_plots()
		if _START_PLOT_MAP is None:
			return -1

	return _START_PLOT_MAP.get(playerID, -1)

def normalizeStartingPlotLocations():
	global bTeamPlacement

	if bTeamPlacement:
		return None

	CyPythonMgr().allowDefaultImpl()
	return None

def getTHemLatitude(iX, iY):
	map = CyMap()
	iTiltOption = map.getCustomMapOption(4)
	iW = map.getGridWidth()
	iH = map.getGridHeight()

	if iW <= 1: iW = 2
	if iH <= 1: iH = 2

	if iTiltOption == 1:
		lat = abs((iW / 2) - iX) / float(iW / 2)
	else:
		lat = abs((iH / 2) - iY) / float(iH / 2)

	if lat < 0:
		lat = 0.0
	if lat > 1:
		lat = 1.0

	return lat

class THemTerrainGenerator(CvMapGeneratorUtil.TerrainGenerator):
	def getLatitudeAtPlot(self, iX, iY):
		lat = getTHemLatitude(iX, iY)

		# Adjust latitude using self.variation fractal, to mix things up:
		lat += (128 - self.variation.getHeight(iX, iY))/(255.0 * 5.0)

		if lat < 0:
			lat = 0.0
		if lat > 1:
			lat = 1.0

		return lat

def generateTerrainTypes():
	NiTextOut("Generating Terrain (Python Custom Continents) ...")
	terraingen = THemTerrainGenerator()
	terrainTypes = terraingen.generateTerrain()
	return terrainTypes

class THemFeatureGenerator(CvMapGeneratorUtil.FeatureGenerator):
	def getLatitudeAtPlot(self, iX, iY):
		return getTHemLatitude(iX, iY)

def addFeatures():
	NiTextOut("Adding Features (Python Custom Continents) ...")
	featuregen = THemFeatureGenerator()
	featuregen.addFeatures()
	return 0

class ResourceManager:
	def __init__(self, map_obj, gc, dice):
		self.map = map_obj
		self.gc = gc
		self.dice = dice
		self.engine = CyEngine()
		self.iW = map_obj.getGridWidth()
		self.iH = map_obj.getGridHeight()

	def _bonus_id(self, name):
		return self.gc.getInfoTypeForString(name)

	def _bonus_name_from_id(self, iBonus):
		return self.gc.getBonusInfo(iBonus).getType()

	def _debug_sign(self, pPlot, msg):
		global bDebugSignsEnabled

		if not bDebugSignsEnabled: return
		if pPlot is None: return
		if pPlot.isNone(): return
		self.engine.addSign(pPlot, -1, msg)

	def swap_resources(self, target_name, replace_name):
		iTarget = self._bonus_id(target_name)
		iReplace = -1
		if replace_name is not None:
			iReplace = self._bonus_id(replace_name)

		for i in range(self.map.numPlots()):
			pPlot = self.map.plotByIndex(i)
			if pPlot.getBonusType(-1) == iTarget:
				pPlot.setBonusType(iReplace)

	def _shuffle_list(self, source_list, log_label):
		shuffled = []
		for item in source_list:
			shuffled.append(item)

		for i in range(len(shuffled)):
			j = self.dice.get(len(shuffled), log_label)
			temp = shuffled[i]
			shuffled[i] = shuffled[j]
			shuffled[j] = temp

		return shuffled

	def _get_area_id_for_region_label(self, label):
		global bTeamPlacement
		global teamRegionMap
		global teamAreaMap

		if bTeamPlacement and len(teamAreaMap) == 0:
			_resolve_team_areas()

		for iTeam in teamRegionMap.keys():
			if teamRegionMap[iTeam] == label:
				if teamAreaMap.has_key(iTeam):
					return teamAreaMap[iTeam]

		return _get_dominant_area_for_region(label, {})

	def _get_player_count_for_region(self, region):
		global teamRegionMap

		if type(region) == type("") or type(region) == type(u""):
			for iTeam in teamRegionMap.keys():
				if teamRegionMap[iTeam] == region:
					iCount = 0
					for iPlayer in range(self.gc.getMAX_CIV_PLAYERS()):
						pPlayer = self.gc.getPlayer(iPlayer)
						if pPlayer.isEverAlive() and pPlayer.getTeam() == iTeam:
							iCount += 1
					if iCount > 0:
						return iCount

		return self.gc.getGame().countCivPlayersEverAlive()

	def _get_player_count_for_team(self, iTeam):
		iCount = 0
		for iPlayer in range(self.gc.getMAX_CIV_PLAYERS()):
			pPlayer = self.gc.getPlayer(iPlayer)
			if pPlayer.isEverAlive() and pPlayer.getTeam() == iTeam:
				iCount += 1
		return iCount

	def _get_team_region_plots(self, iTeam):
		global teamRegionMap
		global teamAreaMap
		global _THEM_REGION_RECTS

		plots = []
		if not teamRegionMap.has_key(iTeam):
			return plots

		label = teamRegionMap[iTeam]
		rects = _THEM_REGION_RECTS.get(label, [])
		iArea = -1
		if teamAreaMap.has_key(iTeam):
			iArea = teamAreaMap[iTeam]

		for rect in rects:
			iWestX, iSouthY, iWidth, iHeight = rect
			for x in range(iWestX, iWestX + iWidth):
				for y in range(iSouthY, iSouthY + iHeight):
					if x < 0 or x >= self.iW: continue
					if y < 0 or y >= self.iH: continue
					pPlot = self.map.plot(x, y)
					if pPlot.isNone(): continue
					if iArea != -1 and not pPlot.isWater():
						if pPlot.getArea() != iArea: continue
					plots.append(pPlot)

		return plots

	def _get_team_start_radius_plots(self, iTeam, radius):
		plots = []
		used = {}

		if radius < 0:
			radius = 0

		for iPlayer in range(self.gc.getMAX_CIV_PLAYERS()):
			pPlayer = self.gc.getPlayer(iPlayer)
			if pPlayer.isEverAlive() and pPlayer.getTeam() == iTeam:
				pStart = pPlayer.getStartingPlot()
				if pStart and not pStart.isNone():
					sx = pStart.getX()
					sy = pStart.getY()
					for dx in range(-radius, radius + 1):
						for dy in range(-radius, radius + 1):
							nx = sx + dx
							ny = sy + dy
							if nx >= 0 and nx < self.iW and ny >= 0 and ny < self.iH:
								if plotDistance(sx, sy, nx, ny) <= radius:
									key = ny * self.iW + nx
									if not used.has_key(key):
										pPlot = self.map.plot(nx, ny)
										if not pPlot.isNone():
											used[key] = 1
											plots.append(pPlot)

		return plots

	def _get_region_plots(self, region):
		plots = []

		if hasattr(region, "getID"):
			iArea = region.getID()
			for i in range(self.map.numPlots()):
				pPlot = self.map.plotByIndex(i)
				if pPlot.getArea() == iArea:
					plots.append(pPlot)
		elif type(region) == type(0):
			for i in range(self.map.numPlots()):
				pPlot = self.map.plotByIndex(i)
				if pPlot.getArea() == region:
					plots.append(pPlot)
		elif type(region) == type("") or type(region) == type(u""):
			iArea = self._get_area_id_for_region_label(region)
			if iArea != -1:
				for i in range(self.map.numPlots()):
					pPlot = self.map.plotByIndex(i)
					if pPlot.getArea() == iArea:
						plots.append(pPlot)
			if len(plots) == 0:
				iArea = _get_dominant_area_for_region(region, {})
				if iArea != -1:
					for i in range(self.map.numPlots()):
						pPlot = self.map.plotByIndex(i)
						if pPlot.getArea() == iArea:
							plots.append(pPlot)
		else:
			for item in region:
				pPlot = None
				if type(item) == type(()):
					if len(item) >= 2:
						pPlot = self.map.plot(item[0], item[1])
				else:
					pPlot = item
				if pPlot is None: continue
				if pPlot.isNone(): continue
				plots.append(pPlot)

		return plots

	def _get_adjacent_water_plots(self, land_plots):
		waterPlots = []
		seen = {}
		for pLand in land_plots:
			x = pLand.getX()
			y = pLand.getY()
			for dx in range(-1, 2):
				for dy in range(-1, 2):
					if dx == 0 and dy == 0: continue
					iX = x + dx
					iY = y + dy
					if iX < 0 or iX >= self.iW: continue
					if iY < 0 or iY >= self.iH: continue
					pPlot = self.map.plot(iX, iY)
					if pPlot.isNone(): continue
					if not pPlot.isWater(): continue
					iPlot = self.map.plotNum(iX, iY)
					if seen.has_key(iPlot): continue
					seen[iPlot] = 1
					waterPlots.append(pPlot)
		return waterPlots

	def _get_region_plots_for_bonus(self, region, iBonus):
		region_plots = self._get_region_plots(region)
		if self._bonus_is_water(iBonus):
			return self._get_adjacent_water_plots(region_plots)
		return region_plots

	def _bonus_ids_from_names(self, bonusNames):
		bonusIDs = []
		for bonusName in bonusNames:
			bonusIDs.append(self._bonus_id(bonusName))
		return bonusIDs

	def _present_bonus_types(self, region_plots, bonusIDs):
		wanted = {}
		for iBonus in bonusIDs:
			wanted[iBonus] = 1

		present = {}
		for pPlot in region_plots:
			iBonus = pPlot.getBonusType(-1)
			if wanted.has_key(iBonus):
				present[iBonus] = 1

		return present.keys()

	def _start_plot_lookup(self):
		startLookup = {}
		for i in range(self.gc.getMAX_CIV_PLAYERS()):
			player = self.gc.getPlayer(i)
			if player.isEverAlive():
				pStart = player.getStartingPlot()
				if pStart and not pStart.isNone():
					startLookup[(pStart.getX(), pStart.getY())] = 1
		return startLookup

	def _is_player_start_plot(self, pPlot, startLookup):
		if pPlot.isStartingPlot():
			return True
		return startLookup.has_key((pPlot.getX(), pPlot.getY()))

	def _valid_bonus_plots(self, region_plots, iBonus):
		validPlots = []
		startLookup = self._start_plot_lookup()
		for pPlot in region_plots:
			if pPlot.getBonusType(-1) != -1: continue
			if self._is_player_start_plot(pPlot, startLookup): continue
			if not pPlot.canHaveBonus(iBonus, True): continue
			validPlots.append(pPlot)
		return validPlots

	def _bonus_matches_plot_type(self, pPlot, iBonus):
		bonusInfo = self.gc.getBonusInfo(iBonus)

		if self._bonus_is_water(iBonus):
			return pPlot.isWater()

		if pPlot.isWater() or pPlot.isPeak():
			return False

		if pPlot.isHills():
			return bonusInfo.isHills()

		return bonusInfo.isFlatlands()

	def _bonus_is_water(self, iBonus):
		bonusInfo = self.gc.getBonusInfo(iBonus)
		iCoast = self.gc.getInfoTypeForString("TERRAIN_COAST")
		iOcean = self.gc.getInfoTypeForString("TERRAIN_OCEAN")

		if iCoast != -1:
			if bonusInfo.isTerrain(iCoast):
				return True
		if iOcean != -1:
			if bonusInfo.isTerrain(iOcean):
				return True
		return False

	def _fallback_bonus_plots(self, region_plots, iBonus, bMatchPlotType):
		bWaterBonus = self._bonus_is_water(iBonus)
		fallbackPlots = []
		startLookup = self._start_plot_lookup()
		for pPlot in region_plots:
			if pPlot.getBonusType(-1) != -1: continue
			if self._is_player_start_plot(pPlot, startLookup): continue
			if bMatchPlotType:
				if not self._bonus_matches_plot_type(pPlot, iBonus): continue
			else:
				if bWaterBonus:
					if not pPlot.isWater(): continue
				else:
					if pPlot.isWater() or pPlot.isPeak(): continue
			fallbackPlots.append(pPlot)
		return fallbackPlots

	def _is_bonus_appropriate_for_plot(self, iBonus, pPlot):
		bonusInfo = self.gc.getBonusInfo(iBonus)

		if pPlot.isHills():
			if not bonusInfo.isHills(): return False
		else:
			if not bonusInfo.isFlatlands(): return False

		if not bonusInfo.isTerrain(pPlot.getTerrainType()):
			return False

		iFeature = pPlot.getFeatureType()
		if iFeature != -1:
			if not bonusInfo.isFeature(iFeature):
				iFloodplains = self.gc.getInfoTypeForString("FEATURE_FLOOD_PLAINS")
				if iFeature == iFloodplains: return False
				if not bonusInfo.isTerrain(pPlot.getTerrainType()):
					return False

		return True

	def place_bonus_in_radius(self, bonus_list, iTargetCount, iCopies, radius):
		if iTargetCount < 1: iTargetCount = 1
		if iCopies < 1: iCopies = 1

		ids = []
		for b in bonus_list:
			ids.append(self._bonus_id(b))

		players = []
		startLookup = self._start_plot_lookup()
		for i in range(self.gc.getMAX_CIV_PLAYERS()):
			player = self.gc.getPlayer(i)
			if player.isEverAlive():
				pStart = player.getStartingPlot()
				if pStart and not pStart.isNone():
					players.append((player.getID(), pStart.getX(), pStart.getY()))

		for (pid, sx, sy) in players:
			present = {}

			for dx in range(-radius, radius + 1):
				for dy in range(-radius, radius + 1):
					nx = sx + dx
					ny = sy + dy
					if nx >= 0 and nx < self.iW and ny >= 0 and ny < self.iH:
						if plotDistance(sx, sy, nx, ny) <= radius:
							pPlot = self.map.plot(nx, ny)
							iBonus = pPlot.getBonusType(TeamTypes.NO_TEAM)
							if iBonus in ids:
								present[iBonus] = 1

			iPresent = len(present.keys())
			if iPresent >= iTargetCount:
				print "THem radius bonus skipped player %d. Found %d existing bonus types" % (pid, iPresent)
				continue

			missing_ids = []
			for iBonus in ids:
				if not present.has_key(iBonus):
					missing_ids.append(iBonus)

			missing_ids = self._shuffle_list(missing_ids, "THem Radius Bonus Type")
			iNeededTypes = iTargetCount - iPresent
			if iNeededTypes > len(missing_ids): iNeededTypes = len(missing_ids)

			for iType in range(iNeededTypes):
				chosen_id = missing_ids[iType]
				placed = 0

				for iCopy in range(iCopies):
					tier1_plots = []
					for dx in range(-radius, radius + 1):
						for dy in range(-radius, radius + 1):
							nx = sx + dx
							ny = sy + dy
							if nx >= 0 and nx < self.iW and ny >= 0 and ny < self.iH:
								if plotDistance(sx, sy, nx, ny) <= radius:
									pPlot = self.map.plot(nx, ny)
									if self._is_player_start_plot(pPlot, startLookup) or pPlot.getBonusType(-1) != -1: continue
									if pPlot.isWater() or pPlot.isPeak(): continue

									if self._is_bonus_appropriate_for_plot(chosen_id, pPlot):
										tier1_plots.append(pPlot)

					target_plot = None
					if len(tier1_plots) > 0:
						target_plot = tier1_plots[self.dice.get(len(tier1_plots), "THem Radius T1")]
					else:
						emergency_plots = []
						for dx in range(-radius, radius + 1):
							for dy in range(-radius, radius + 1):
								nx = sx + dx
								ny = sy + dy
								if nx >= 0 and nx < self.iW and ny >= 0 and ny < self.iH:
									if plotDistance(sx, sy, nx, ny) <= radius:
										pPlot = self.map.plot(nx, ny)
										if not pPlot.isWater() and not pPlot.isPeak() and not self._is_player_start_plot(pPlot, startLookup):
											if pPlot.getBonusType(-1) == -1:
												emergency_plots.append(pPlot)

						if len(emergency_plots) > 0:
							target_plot = emergency_plots[self.dice.get(len(emergency_plots), "THem Radius Emergency")]

					if target_plot:
						target_plot.setBonusType(chosen_id)
						bonus_name = self.gc.getBonusInfo(chosen_id).getType()
						self._debug_sign(target_plot, "THem radius " + bonus_name + " P" + str(pid))
						print "THem radius placed %s for player %d at (%d, %d)" % (bonus_name, pid, target_plot.getX(), target_plot.getY())
						placed += 1

				if placed < iCopies:
					print "THem radius placed only %d of %d copies for player %d" % (placed, iCopies, pid)

	def place_food_bonus_in_BFC(self, bonusNames, iTargetCount, bCheckExisting):
		if iTargetCount <= 0:
			return

		bonusIDs = self._bonus_ids_from_names(bonusNames)
		iPlains = self.gc.getInfoTypeForString("TERRAIN_PLAINS")
		iFloodplains = self.gc.getInfoTypeForString("FEATURE_FLOOD_PLAINS")

		bfcOffsets = []
		for dx in range(-2, 3):
			for dy in range(-2, 3):
				if dx == 0 and dy == 0: continue
				if abs(dx) == 2 and abs(dy) == 2: continue
				bfcOffsets.append((dx, dy))

		for iPlayer in range(self.gc.getMAX_CIV_PLAYERS()):
			pPlayer = self.gc.getPlayer(iPlayer)
			if not pPlayer.isEverAlive(): continue
			pStart = pPlayer.getStartingPlot()
			if pStart is None: continue
			if pStart.isNone(): continue

			iExisting = 0
			if bCheckExisting:
				for dx, dy in bfcOffsets:
					x = pStart.getX() + dx
					y = pStart.getY() + dy
					if x < 0 or x >= self.iW: continue
					if y < 0 or y >= self.iH: continue
					pPlot = self.map.plot(x, y)
					if pPlot.isStartingPlot(): continue
					if pPlot.getBonusType(-1) in bonusIDs:
						iExisting += 1

			iNeeded = iTargetCount - iExisting
			for i in range(iNeeded):
				shuffledBonusIDs = self._shuffle_list(bonusIDs, "Start Food Bonus Shuffle")
				bPlaced = False

				for iBonus in shuffledBonusIDs:
					validPlots = []
					for dx, dy in bfcOffsets:
						x = pStart.getX() + dx
						y = pStart.getY() + dy
						if x < 0 or x >= self.iW: continue
						if y < 0 or y >= self.iH: continue
						pPlot = self.map.plot(x, y)
						if pPlot.isStartingPlot(): continue
						if pPlot.getBonusType(-1) != -1: continue
						if pPlot.isWater() or pPlot.isPeak(): continue
						if self._is_bonus_appropriate_for_plot(iBonus, pPlot):
							validPlots.append(pPlot)

					if len(validPlots) > 0:
						pTarget = validPlots[self.dice.get(len(validPlots), "Start Food Plot")]
						iFeature = pTarget.getFeatureType()
						if iFeature != -1 and iFeature != iFloodplains:
							if not pTarget.canHaveBonus(iBonus, True):
								pTarget.setFeatureType(FeatureTypes.NO_FEATURE, -1)
						pTarget.setBonusType(iBonus)
						self._debug_sign(pTarget, "THem start food P%d %s" % (iPlayer, self._bonus_name_from_id(iBonus)))
						bPlaced = True
						break

				if not bPlaced:
					emergencyPlots = []
					for dx, dy in bfcOffsets:
						x = pStart.getX() + dx
						y = pStart.getY() + dy
						if x < 0 or x >= self.iW: continue
						if y < 0 or y >= self.iH: continue
						pPlot = self.map.plot(x, y)
						if pPlot.isStartingPlot(): continue
						if pPlot.getBonusType(-1) != -1: continue
						if pPlot.isWater() or pPlot.isPeak(): continue
						if pPlot.calculateNatureYield(YieldTypes.YIELD_FOOD, TeamTypes.NO_TEAM, False) == 0:
							emergencyPlots.append(pPlot)
						elif pPlot.getFeatureType() == iFloodplains:
							emergencyPlots.append(pPlot)

					if len(emergencyPlots) > 0:
						pTarget = emergencyPlots[self.dice.get(len(emergencyPlots), "Start Food Emergency Plot")]
						pTarget.setPlotType(PlotTypes.PLOT_LAND, True, True)
						pTarget.setTerrainType(iPlains, True, True)
						pTarget.setFeatureType(FeatureTypes.NO_FEATURE, -1)

						for iBonus in shuffledBonusIDs:
							if self._is_bonus_appropriate_for_plot(iBonus, pTarget):
								pTarget.setBonusType(iBonus)
								self._debug_sign(pTarget, "THem emergency start food P%d %s" % (iPlayer, self._bonus_name_from_id(iBonus)))
								bPlaced = True
								break

						if not bPlaced:
							pTarget.setBonusType(shuffledBonusIDs[0])
							self._debug_sign(pTarget, "THem fallback start food P%d %s" % (iPlayer, self._bonus_name_from_id(shuffledBonusIDs[0])))

	def _place_bonus_copies(self, region_plots, iBonus, iCopies, regionName, bonusName, iPlayerCount):
		if iCopies < 1: iCopies = 1

		validPlots = self._valid_bonus_plots(region_plots, iBonus)
		validPlots = self._shuffle_list(validPlots, "Region Bonus Placement")

		placed = 0
		for pPlot in validPlots:
			if placed >= iCopies: break
			pPlot.setBonusType(iBonus)
			self._debug_sign(pPlot, "THem added " + bonusName + " in " + regionName + " P" + str(iPlayerCount))
			placed += 1

		if placed < iCopies:
			print "THem using relaxed placement for %s in %s, valid plots exhausted" % (bonusName, regionName)
			relaxedPlots = self._fallback_bonus_plots(region_plots, iBonus, True)
			relaxedPlots = self._shuffle_list(relaxedPlots, "Relaxed Region Bonus Placement")
			for pPlot in relaxedPlots:
				if placed >= iCopies: break
				pPlot.setBonusType(iBonus)
				self._debug_sign(pPlot, "THem relaxed " + bonusName + " in " + regionName + " P" + str(iPlayerCount))
				placed += 1

		if placed < iCopies:
			print "THem using last-ditch placement for %s in %s, relaxed plots exhausted" % (bonusName, regionName)
			fallbackPlots = self._fallback_bonus_plots(region_plots, iBonus, False)
			fallbackPlots = self._shuffle_list(fallbackPlots, "Last Ditch Region Bonus Placement")
			for pPlot in fallbackPlots:
				if placed >= iCopies: break
				pPlot.setBonusType(iBonus)
				self._debug_sign(pPlot, "THem fallback " + bonusName + " in " + regionName + " P" + str(iPlayerCount))
				placed += 1

		return placed

	def _wipe_bonus_types_in_plots(self, region_plots, bonusIDs, regionName):
		removeLookup = {}
		for iBonus in bonusIDs:
			removeLookup[iBonus] = 1

		iRemoved = 0
		for pPlot in region_plots:
			iBonus = pPlot.getBonusType(-1)
			if removeLookup.has_key(iBonus):
				self._debug_sign(pPlot, "THem removed " + self._bonus_name_from_id(iBonus) + " in " + regionName)
				pPlot.setBonusType(-1)
				iRemoved += 1

		if iRemoved > 0:
			print "THem wiped %d listed bonuses in %s" % (iRemoved, regionName)
		return iRemoved

	def place_balanced_team_resource(self, iTeam, bonusNames, iTargetCount, iCopies, bPlaceNear=False, radius=5):
		bonusIDs = self._bonus_ids_from_names(bonusNames)
		regionName = "team " + str(iTeam)
		wipeRegionName = regionName

		wipe_plots = self._get_team_region_plots(iTeam)
		self._wipe_bonus_types_in_plots(wipe_plots, bonusIDs, wipeRegionName)

		if bPlaceNear:
			region_plots = self._get_team_start_radius_plots(iTeam, radius)
			regionName = regionName + " near starts"
		else:
			bWaterGroup = False
			for iBonus in bonusIDs:
				if self._bonus_is_water(iBonus):
					bWaterGroup = True
					break
			if bWaterGroup:
				region_plots = self._get_adjacent_water_plots(wipe_plots)
			else:
				region_plots = wipe_plots

		iPlayerCount = self._get_player_count_for_team(iTeam)

		if len(region_plots) == 0:
			print "THem balance found no plots for %s" % regionName
			return 0

		bonusIDs = self._shuffle_list(bonusIDs, "THem Region Bonus Types")
		iNeeded = iTargetCount
		if iNeeded > len(bonusIDs): iNeeded = len(bonusIDs)

		iAttempted = 0
		for i in range(iNeeded):
			iBonus = bonusIDs[i]
			self._place_bonus_copies(region_plots, iBonus, iCopies, regionName, self._bonus_name_from_id(iBonus), iPlayerCount)
			iAttempted += 1

		return iAttempted

	def balance_bonus_types_in_continent(self, region, bonusNames, iTargetCount, iCopies):
		regionName = str(region)
		bonusIDs = self._bonus_ids_from_names(bonusNames)
		iPlayerCount = self._get_player_count_for_region(region)
		region_plots = self._get_region_plots(region)
		if len(region_plots) == 0:
			print "THem balance found no plots for region %s" % regionName
			return 0
		present = self._present_bonus_types(region_plots, bonusIDs)
		iPresent = len(present)

		if iPresent < iTargetCount:
			presentLookup = {}
			for iBonus in present:
				presentLookup[iBonus] = 1

			missing = []
			for iBonus in bonusIDs:
				if not presentLookup.has_key(iBonus):
					missing.append(iBonus)

			missing = self._shuffle_list(missing, "Region Bonus Missing Types")
			iNeeded = iTargetCount - iPresent

			for i in range(iNeeded):
				if i >= len(missing): break
				self.add_bonus_types_to_continent(region, [self._bonus_name_from_id(missing[i])], iCopies)

			present = self._present_bonus_types(region_plots, bonusIDs)
			return len(present)

		if iPresent > iTargetCount:
			excess = self._shuffle_list(present, "Region Bonus Excess Types")
			iRemoveCount = iPresent - iTargetCount
			removeLookup = {}
			for i in range(iRemoveCount):
				removeLookup[excess[i]] = 1

			for pPlot in region_plots:
				iBonus = pPlot.getBonusType(-1)
				if removeLookup.has_key(iBonus):
					self._debug_sign(pPlot, "THem removed " + self._bonus_name_from_id(iBonus) + " in " + regionName)
					pPlot.setBonusType(-1)

			present = self._present_bonus_types(region_plots, bonusIDs)
			return len(present)

		return iPresent

	def add_bonus_types_to_continent(self, region, bonusNames, iQuantity):
		if iQuantity <= 0:
			return 0

		regionName = str(region)
		bonusIDs = self._bonus_ids_from_names(bonusNames)
		placed = 0
		bonusQueue = self._shuffle_list(bonusIDs, "Region Add Bonus Types")
		for i in range(iQuantity):
			if len(bonusQueue) == 0: break
			iBonus = bonusQueue[i % len(bonusQueue)]
			iPlayerCount = self._get_player_count_for_region(region)
			region_plots = self._get_region_plots_for_bonus(region, iBonus)
			if len(region_plots) == 0:
				print "THem add bonuses found no plots for %s in region %s" % (self._bonus_name_from_id(iBonus), regionName)
				continue
			placed += self._place_bonus_copies(region_plots, iBonus, 1, regionName, self._bonus_name_from_id(iBonus), iPlayerCount)

		return placed

	def place_resource_near_team_member(self, bonus_name):
		iBonus = self._bonus_id(bonus_name)

		teamStartPlots = {}
		teamSizes = {}
		for iPlayer in range(self.gc.getMAX_CIV_PLAYERS()):
			pPlayer = self.gc.getPlayer(iPlayer)
			if pPlayer.isEverAlive():
				pStartPlot = pPlayer.getStartingPlot()
				if pStartPlot is None: continue
				if pStartPlot.isNone(): continue

				iTeam = pPlayer.getTeam()
				if not teamStartPlots.has_key(iTeam):
					teamStartPlots[iTeam] = []
					teamSizes[iTeam] = 0
				teamStartPlots[iTeam].append((pStartPlot.getX(), pStartPlot.getY()))
				teamSizes[iTeam] += 1

		sortedTeams = teamStartPlots.keys()
		sortedTeams.sort()

		for iTeam in sortedTeams:
			memberPlots = teamStartPlots[iTeam]
			if len(memberPlots) == 0: continue

			count = teamSizes[iTeam] / 2
			if count < 1: count = 1

			shuffledPlots = []
			for p in memberPlots:
				shuffledPlots.append(p)

			for i in range(len(shuffledPlots)):
				j = self.dice.get(len(shuffledPlots), "Member Shuffle")
				temp = shuffledPlots[i]
				shuffledPlots[i] = shuffledPlots[j]
				shuffledPlots[j] = temp

			for i in range(count):
				originCoords = shuffledPlots[i % len(shuffledPlots)]
				originX, originY = originCoords

				bestPlot = None
				bestValue = -1

				for dx in range(-6, 7):
					for dy in range(-6, 7):
						dist = plotDistance(originX, originY, originX + dx, originY + dy)
						if dist >= 3 and dist <= 5:
							pPlot = self.map.plot(originX + dx, originY + dy)

							if pPlot.isNone(): continue
							if pPlot.isWater() or pPlot.isPeak(): continue
							if pPlot.getBonusType(-1) != -1: continue
							if pPlot.isStartingPlot(): continue

							val = 0
							if pPlot.canHaveBonus(iBonus, True):
								val = 100 + self.dice.get(100, "Resource Randomizer")
							else:
								val = 10 + self.dice.get(50, "Resource Randomizer")

							if val > bestValue:
								bestValue = val
								bestPlot = pPlot

				if bestPlot is not None:
					bestPlot.setBonusType(iBonus)
					if not bestPlot.canHaveBonus(iBonus, False):
						bestPlot.setFeatureType(FeatureTypes.NO_FEATURE, -1)

def normalizeAddExtras():
	gc = CyGlobalContext()
	map = CyMap()
	dice = gc.getGame().getMapRand()
	map.recalculateAreas()
	rm = ResourceManager(map, gc, dice)

	iTeamerBalancingOption = map.getCustomMapOption(5)
	iStartFoodOption = map.getCustomMapOption(7)
	bCustomBalancing = False

	if bTeamPlacement and iTeamerBalancingOption == 1:
		if _resolve_team_areas():
			bCustomBalancing = True

	if bCustomBalancing:
		print "PY: Teamer balancing regional resource groups..."

		Strategics = ["BONUS_IRON", "BONUS_COPPER", "BONUS_HORSE"]
		SemiStrategics = ["BONUS_IVORY", "BONUS_STONE", "BONUS_MARBLE"]
		PreciousMetals = ["BONUS_GOLD", "BONUS_SILVER", "BONUS_GEMS"]
		EarlyHappiness = ["BONUS_FUR", "BONUS_WINE"]
		CalendarBonus = ["BONUS_SPICES", "BONUS_SUGAR", "BONUS_BANANA", "BONUS_DYE", "BONUS_INCENSE", "BONUS_SILK"]
		WaterBonus = ["BONUS_FISH", "BONUS_CRAB", "BONUS_CRAB", "BONUS_WHALE"]

		rm.swap_resources("BONUS_IVORY", None)
		rm.place_bonus_in_radius(Strategics, 3, 1, 5)

		sortedTeams = teamRegionMap.keys()
		sortedTeams.sort()
		for iTeam in sortedTeams:
			iPlayerCount = rm._get_player_count_for_team(iTeam)
			iRoundedDown = int(0.5 * iPlayerCount)
			iRoundedUp = int(0.5 * iPlayerCount + 1)
			if iRoundedDown < 1: iRoundedDown = 1

			rm.place_balanced_team_resource(iTeam, CalendarBonus, 4, iRoundedDown)
			rm.place_balanced_team_resource(iTeam, PreciousMetals, 3, iRoundedUp)
			rm.place_balanced_team_resource(iTeam, EarlyHappiness, 2, iRoundedUp)
			rm.place_balanced_team_resource(iTeam, SemiStrategics, 3, iRoundedDown, True, 4)

	if iStartFoodOption > 0:
		print "PY: Teamer adding starting plot food bonuses..."
		FoodBonus = ["BONUS_WHEAT", "BONUS_RICE", "BONUS_CORN", "BONUS_COW", "BONUS_SHEEP", "BONUS_PIG", "BONUS_DEER"]
		rm.place_food_bonus_in_BFC(FoodBonus, iStartFoodOption, True)

	if not bCustomBalancing:
		CyPythonMgr().allowDefaultImpl()
