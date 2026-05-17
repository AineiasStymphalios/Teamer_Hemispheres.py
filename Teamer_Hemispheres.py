#
#	FILE:	 Hemispheres.py
#	AUTHOR:  Ben Sarsgard
#	PURPOSE: Global map script - Hemisphere or quadrant split with oceanic divide
#		Mostly adapted from Sirian's Big_and_Small
#	VERSION: 1.20
#-----------------------------------------------------------------------------
#	Copyright (c) 2007 Firaxis Games, Inc. All rights reserved.
#-----------------------------------------------------------------------------
#

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
	#TODO: get my own text string
	return "TXT_KEY_MAP_SCRIPT_LEFT_AND_RIGHT_DESCR"

def isAdvancedMap():
	"This map should not show up in simple mode"
	return 0

def getNumCustomMapOptions():
	return 9
	
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
		return "Resources"
	elif iOption == 6:
		return "Teamer Balancing"
	elif iOption == 7:
		return "Debug Signs"
	elif iOption == 8:
		return "Starting Plot Min. Food"
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
	elif iOption == 7: return 2
	elif iOption == 8: return 4
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
		return "Balanced"
	elif iOption == 6:
		if iSelection == 0: return "Disabled"
		return "Enabled"
	elif iOption == 7:
		if iSelection == 0: return "Disabled"
		return "Enabled"
	elif iOption == 8:
		if iSelection == 0: return "Disabled"
		elif iSelection == 1: return "At least 1"
		elif iSelection == 2: return "At least 2"
		return "At least 3"
	return ""

def getCustomMapOptionDefault(argsList):
	[iOption] = argsList
	if iOption == 0: return 1
	elif iOption == 1: return 1
	elif iOption == 2: return 0
	elif iOption == 3: return 1
	elif iOption == 4: return 0
	elif iOption == 5: return 0
	elif iOption == 6: return 1
	elif iOption == 7: return 1
	elif iOption == 8: return 1
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
	bDebugSignsEnabled = (map.getCustomMapOption(7) == 1)

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
	vSplitPrimary, vSplitSecondary, vSplitTertiary, tripleSplit = getTHemSplitSettings(iRegionCount)

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
				tinyWidth = int(self.iW * 0.15)
				tinyHeight = int(self.iH * 0.15)
				tinyWestX = iWestX + self.dice.get(iWidth - tinyWidth, "Tiny Longitude - Custom Continents PYTHON")
				tinySouthY = iSouthY + self.dice.get(iHeight - tinyHeight, "Tiny Latitude - Custom Continents PYTHON")

				self.generatePlotsInRegion(80,
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

def getTHemContinentSettings(map, gc):
	iSeaLevelChange = gc.getSeaLevelInfo(map.getSeaLevel()).getSeaLevelChange()
	print("getSeaLevelChange", iSeaLevelChange)

	iContinentOption = map.getCustomMapOption(0)
	if iContinentOption == 3:
		settings = {
			"primary": (1, 80 + iSeaLevelChange),
			"secondary": (3, 70 + iSeaLevelChange),
			"tertiary": (2, 75 + iSeaLevelChange)
			}
	elif iContinentOption == 0:
		iGrain = 1
		settings = {
			"primary": (iGrain, 70 + iSeaLevelChange),
			"secondary": (iGrain, 70 + iSeaLevelChange),
			"tertiary": (iGrain, 70 + iSeaLevelChange)
			}
	else:
		iGrain = 2 + iContinentOption
		settings = {
			"primary": (iGrain, 70 + iSeaLevelChange),
			"secondary": (iGrain, 70 + iSeaLevelChange),
			"tertiary": (iGrain, 70 + iSeaLevelChange)
			}
	return settings

def shrinkTHemRegion(iW, iH, iWestX, iSouthY, iWidth, iHeight):
	iMarginX = int(0.05 * iW)
	iMarginY = int(0.0 * iH)

	if iMarginX < 1: iMarginX = 1
	if iMarginY < 1: iMarginY = 1

	if iWidth <= (2 * iMarginX) + 4:
		iMarginX = 0
	if iHeight <= (2 * iMarginY) + 4:
		iMarginY = 0

	return (iWestX + iMarginX, iSouthY + iMarginY, iWidth - (2 * iMarginX), iHeight - (2 * iMarginY))

def getTHemCoreRegion(iWestX, iSouthY, iWidth, iHeight):
	iCoreWidth = int(0.50 * iWidth)
	iCoreHeight = int(0.60 * iHeight)

	if iCoreWidth < 4: iCoreWidth = iWidth
	if iCoreHeight < 4: iCoreHeight = iHeight

	iCoreWestX = iWestX + ((iWidth - iCoreWidth) / 2)
	iCoreSouthY = iSouthY + ((iHeight - iCoreHeight) / 2)
	return (iCoreWestX, iCoreSouthY, iCoreWidth, iCoreHeight)

def getTHemSplitSettings(iRegionCount):
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

def getTHemHorizontalBand(iW, label, tripleSplit):
	global xShiftRoll

	if label == "tertiary":
		westShift = int(0.66 * iW)
		eastShift = 0
	elif label == "primary":
		if tripleSplit:
			if xShiftRoll:
				westShift = int(0.33 * iW)
				eastShift = int(0.33 * iW)
			else:
				westShift = 0
				eastShift = int(0.66 * iW)
		else:
			if xShiftRoll:
				westShift = int(0.5 * iW)
				eastShift = 0
			else:
				westShift = 0
				eastShift = int(0.5 * iW)
	else:
		if tripleSplit:
			if xShiftRoll:
				westShift = 0
				eastShift = int(0.66 * iW)
			else:
				westShift = int(0.33 * iW)
				eastShift = int(0.33 * iW)
		else:
			if xShiftRoll:
				westShift = 0
				eastShift = int(0.5 * iW)
			else:
				westShift = int(0.5 * iW)
				eastShift = 0

	iWestX = westShift
	iEastX = iW - eastShift
	return (iWestX, iEastX - iWestX)

def getTHemVerticalBands(iH, vSplit):
	global yShiftRoll
	global yPortionRoll

	if not vSplit:
		return [(0, iH)]

	splitYBigger = 0.5
	splitYSmaller = 0.5
	splitYBuffer = 0.1

	if yPortionRoll:
		if yShiftRoll:
			firstNorth = int(splitYBuffer * iH)
			firstSouth = int(splitYBigger * iH)
			secondNorth = int(splitYSmaller * iH)
			secondSouth = int(splitYBuffer * iH)
		else:
			firstNorth = int(splitYSmaller * iH)
			firstSouth = int(splitYBuffer * iH)
			secondNorth = int(splitYBuffer * iH)
			secondSouth = int(splitYBigger * iH)
	else:
		if yShiftRoll:
			firstNorth = int(splitYBuffer * iH)
			firstSouth = int(splitYSmaller * iH)
			secondNorth = int(splitYBigger * iH)
			secondSouth = int(splitYBuffer * iH)
		else:
			firstNorth = int(splitYBigger * iH)
			firstSouth = int(splitYBuffer * iH)
			secondNorth = int(splitYBuffer * iH)
			secondSouth = int(splitYSmaller * iH)

	return [
		(firstSouth, iH - firstNorth - firstSouth),
		(secondSouth, iH - secondNorth - secondSouth)
		]

def addTHemContinentRegions(region_data, label, iW, iH, vSplit, tripleSplit, settings, iIslandsGrain, tinyIslandOverlap):
	global _THEM_REGION_RECTS

	map = CyMap()
	iWestX, iWidth = getTHemHorizontalBand(iW, label, tripleSplit)
	iGrain, iWater = settings[label]
	xExp = 6
	bands = getTHemVerticalBands(iH, vSplit)

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

	for i in range(len(bands)):
		iSouthY, iHeight = bands[i]
		iContWestX, iContSouthY, iContWidth, iContHeight = shrinkTHemRegion(iW, iH, iWestX, iSouthY, iWidth, iHeight)
		region_data.append(("continent", label + " shoreline", iWater, iContWestX, iContSouthY, iContWidth, iContHeight, iGrain, xExp))
		iCoreWestX, iCoreSouthY, iCoreWidth, iCoreHeight = getTHemCoreRegion(iContWestX, iContSouthY, iContWidth, iContHeight)
		region_data.append(("continent", label + " core", 30, iCoreWestX, iCoreSouthY, iCoreWidth, iCoreHeight, 1, xExp))
		if not _THEM_REGION_RECTS.has_key(label):
			_THEM_REGION_RECTS[label] = []
		_THEM_REGION_RECTS[label].append((iContWestX, iContSouthY, iContWidth, iContHeight))
		if tinyIslandOverlap == 0:
			region_data.append(("islands", label + " islands", minTinies, extraTinies, iContWestX, iContSouthY, iContWidth, iContHeight, iIslandsGrain))

def buildTHemRegionData(map, gc):
	global _THEM_REGION_RECTS

	_THEM_REGION_RECTS = {}
	iW = map.getGridWidth()
	iH = map.getGridHeight()
	settings = getTHemContinentSettings(map, gc)
	iIslandsGrain = 3 + map.getCustomMapOption(1)
	tinyIslandOverlap = 0
	iRegionCount = 2 + map.getCustomMapOption(2)
	vSplitPrimary, vSplitSecondary, vSplitTertiary, tripleSplit = getTHemSplitSettings(iRegionCount)
	region_data = []

	if tinyIslandOverlap:
		region_data.append(("islands", "overlap islands", 4, 6, 0, 0, iW, iH, iIslandsGrain))

	addTHemContinentRegions(region_data, "primary", iW, iH, vSplitPrimary, tripleSplit, settings, iIslandsGrain, tinyIslandOverlap)
	addTHemContinentRegions(region_data, "secondary", iW, iH, vSplitSecondary, tripleSplit, settings, iIslandsGrain, tinyIslandOverlap)
	if tripleSplit:
		addTHemContinentRegions(region_data, "tertiary", iW, iH, vSplitTertiary, tripleSplit, settings, iIslandsGrain, tinyIslandOverlap)

	return region_data

def copyTHemRegionRects():
	global _THEM_REGION_RECTS

	rectsCopy = {}
	for label in _THEM_REGION_RECTS.keys():
		rectsCopy[label] = []
		for rect in _THEM_REGION_RECTS[label]:
			rectsCopy[label].append(rect)
	return rectsCopy

def countTHemRegionLand(plotTypes, iW):
	global _THEM_REGION_RECTS

	counts = {}
	for label in _THEM_REGION_RECTS.keys():
		iCount = 0
		for rect in _THEM_REGION_RECTS[label]:
			iWestX, iSouthY, iWidth, iHeight = rect
			for x in range(iWestX, iWestX + iWidth):
				for y in range(iSouthY, iSouthY + iHeight):
					i = y * iW + x
					if plotTypes[i] != PlotTypes.PLOT_OCEAN:
						iCount += 1
		counts[label] = iCount
	return counts

def getTHemLandBalanceScore(counts):
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

def isTHemLandBalanceAcceptable(counts):
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

def printTHemLandBalance(iAttempt, counts, bAccepted):
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
	iW = map.getGridWidth()
	iMaxAttempts = 20
	bestPlotTypes = None
	bestRects = None
	iBestScore = -1

	for iAttempt in range(1, iMaxAttempts + 1):
		region_data = buildTHemRegionData(map, gc)
		fractal_world = THemMultilayeredFractal()
		plotTypes = fractal_world.generatePlotsByRegion(region_data)
		counts = countTHemRegionLand(plotTypes, iW)
		bAccepted = isTHemLandBalanceAcceptable(counts)
		printTHemLandBalance(iAttempt, counts, bAccepted)
		if bAccepted:
			return plotTypes

		iScore = getTHemLandBalanceScore(counts)
		if iBestScore == -1 or iScore < iBestScore:
			iBestScore = iScore
			bestPlotTypes = plotTypes
			bestRects = copyTHemRegionRects()

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

def _assign_all_starting_plots():
	global bTeamPlacement
	global teamAreaMap

	gc = CyGlobalContext()
	map = CyMap()

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
		iTargetArea = teamAreaMap[iTeam]

		for playerID in teamPlayers:
			player = gc.getPlayer(playerID)
			player.AI_updateFoundValues(True)

			currentMinDist = 10
			plotAssigned = False
			while currentMinDist >= 0 and not plotAssigned:
				bestVal = -1
				bestPlot = None

				for x in range(map.getGridWidth()):
					for y in range(map.getGridHeight()):
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
						if val > bestVal:
							bestVal = val
							bestPlot = pPlot

				if bestPlot is not None:
					assignments[playerID] = map.plotNum(bestPlot.getX(), bestPlot.getY())
					assigned_plots.append((bestPlot.getX(), bestPlot.getY()))
					plotAssigned = True
				else:
					currentMinDist -= 1

			if not plotAssigned:
				for x in range(map.getGridWidth()):
					for y in range(map.getGridHeight()):
						pPlot = map.plot(x, y)
						if pPlot.isWater() or pPlot.isPeak(): continue
						if pPlot.getArea() != iTargetArea: continue
						if (x, y) in assigned_plots: continue
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

	def _valid_bonus_plots(self, region_plots, iBonus):
		validPlots = []
		for pPlot in region_plots:
			if pPlot.getBonusType(-1) != -1: continue
			if pPlot.isStartingPlot(): continue
			if not pPlot.canHaveBonus(iBonus, True): continue
			validPlots.append(pPlot)
		return validPlots

	def _forced_bonus_plots(self, region_plots):
		forcedPlots = []
		for pPlot in region_plots:
			if pPlot.getBonusType(-1) != -1: continue
			if pPlot.isStartingPlot(): continue
			if pPlot.isWater() or pPlot.isPeak(): continue
			forcedPlots.append(pPlot)
		return forcedPlots

	def _bonus_terrain_candidates(self, iBonus):
		bonusInfo = self.gc.getBonusInfo(iBonus)
		terrains = []
		for iTerrain in range(self.gc.getNumTerrainInfos()):
			if bonusInfo.isTerrain(iTerrain):
				terrains.append(iTerrain)

		if len(terrains) == 0:
			terrains.append(self.gc.getInfoTypeForString("TERRAIN_GRASS"))
			terrains.append(self.gc.getInfoTypeForString("TERRAIN_PLAINS"))
			terrains.append(self.gc.getInfoTypeForString("TERRAIN_DESERT"))
			terrains.append(self.gc.getInfoTypeForString("TERRAIN_TUNDRA"))

		return terrains

	def _bonus_feature_candidates(self, iBonus):
		bonusInfo = self.gc.getBonusInfo(iBonus)
		features = [FeatureTypes.NO_FEATURE]
		for iFeature in range(self.gc.getNumFeatureInfos()):
			if bonusInfo.isFeature(iFeature):
				features.append(iFeature)
		return features

	def _try_shape_bonus_plot(self, pPlot, iBonus, iPlotType, iTerrain, iFeature):
		pPlot.setPlotType(iPlotType, True, True)
		pPlot.setTerrainType(iTerrain, True, True)
		pPlot.setFeatureType(iFeature, -1)
		if pPlot.canHaveBonus(iBonus, True):
			pPlot.setBonusType(iBonus)
			return True
		return False

	def _force_bonus_on_plot(self, pPlot, iBonus):
		terrains = self._bonus_terrain_candidates(iBonus)
		features = self._bonus_feature_candidates(iBonus)
		plotTypes = [PlotTypes.PLOT_LAND, PlotTypes.PLOT_HILLS]

		for iPlotType in plotTypes:
			for iTerrain in terrains:
				for iFeature in features:
					if self._try_shape_bonus_plot(pPlot, iBonus, iPlotType, iTerrain, iFeature):
						return True

		iGrass = self.gc.getInfoTypeForString("TERRAIN_GRASS")
		pPlot.setPlotType(PlotTypes.PLOT_LAND, True, True)
		pPlot.setTerrainType(iGrass, True, True)
		pPlot.setFeatureType(FeatureTypes.NO_FEATURE, -1)
		pPlot.setBonusType(iBonus)
		return False

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
			print "THem forcing %s in %s, valid plots exhausted" % (bonusName, regionName)
			forcedPlots = self._forced_bonus_plots(region_plots)
			forcedPlots = self._shuffle_list(forcedPlots, "Forced Region Bonus Placement")
			for pPlot in forcedPlots:
				if placed >= iCopies: break
				bNaturalShape = self._force_bonus_on_plot(pPlot, iBonus)
				if bNaturalShape:
					self._debug_sign(pPlot, "THem forced " + bonusName + " in " + regionName + " P" + str(iPlayerCount))
				else:
					self._debug_sign(pPlot, "THem fallback " + bonusName + " in " + regionName + " P" + str(iPlayerCount))
				placed += 1

		return placed

	def balance_bonus_types_in_continent(self, region, bonusNames, iTargetCount):
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
			iCopies = int(0.5 * iPlayerCount)
			if iCopies < 1: iCopies = 1

			for i in range(iNeeded):
				if i >= len(missing): break
				self._place_bonus_copies(region_plots, missing[i], iCopies, regionName, self._bonus_name_from_id(missing[i]), iPlayerCount)

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
	if bTeamPlacement:
		_resolve_team_areas()
	rm = ResourceManager(map, gc, dice)

	iResourceOption = map.getCustomMapOption(5)
	iTeamerBalancingOption = map.getCustomMapOption(6)
	iStartFoodOption = map.getCustomMapOption(8)

	if iResourceOption == 1:
		balancer.normalizeAddExtras()

	if iTeamerBalancingOption == 1:
		print "PY: Teamer balancing regional resource groups..."
		CalendarBonus = ["BONUS_SPICES", "BONUS_SUGAR", "BONUS_BANANA", "BONUS_DYE", "BONUS_INCENSE", "BONUS_SILK"]
		Strategics = ["BONUS_IRON", "BONUS_COPPER", "BONUS_HORSE"] # This will be redundant if Balanced resources is on
		SemiStrategics = ["BONUS_IVORY", "BONUS_STONE", "BONUS_MARBLE"]
		PreciousMetals = ["BONUS_GOLD", "BONUS_SILVER", "BONUS_GEMS"]
		EarlyHappiness = ["BONUS_FUR", "BONUS_WINE"]

		teamRegions = []
		sortedTeams = teamRegionMap.keys()
		sortedTeams.sort()
		for iTeam in sortedTeams:
			teamRegions.append(teamRegionMap[iTeam])

		for teamRegion in teamRegions:
			rm.balance_bonus_types_in_continent(teamRegion, CalendarBonus, 4)
			rm.balance_bonus_types_in_continent(teamRegion, SemiStrategics, 3)
			rm.balance_bonus_types_in_continent(teamRegion, PreciousMetals, 2)
			rm.balance_bonus_types_in_continent(teamRegion, EarlyHappiness, 2)

	if iStartFoodOption > 0:
		print "PY: Teamer adding starting plot food bonuses..."
		FoodBonus = ["BONUS_WHEAT", "BONUS_RICE", "BONUS_CORN", "BONUS_COW", "BONUS_SHEEP", "BONUS_PIG", "BONUS_DEER"]
		rm.place_food_bonus_in_BFC(FoodBonus, iStartFoodOption, True)

	CyPythonMgr().allowDefaultImpl()
