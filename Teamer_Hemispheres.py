#
#	FILE:	Teamer_Hemispheres.py
#	AUTHOR:	Aineias the Stymphalian
#	Adapted from Ben Sarsgard's Hemispheres.py. Features several multiplayer-friendly customizations.

from CvPythonExtensions import *
import math
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
	return 9
	
def getCustomMapOptionName(argsList):
	[iOption] = argsList
	if iOption == 0:
		return "World Wrap"
	elif iOption == 1:
		return "Number of Continents"
	elif iOption == 2:
		return "Continent Shoreline"
	elif iOption == 3:
		return "Continent Shape"
	elif iOption == 4:
		return "Teamer Resource Balancing"
	elif iOption == 5:
		return "Land Food Across Map"
	elif iOption == 6:
		return "Land Food on Starts"
	elif iOption == 7:
		return "Reduce Coastal Peaks"
	elif iOption == 8:
		return "Debug Signs"
	return ""
	
def getNumCustomMapOptionValues(argsList):
	[iOption] = argsList
	if iOption == 0: return 3
	elif iOption == 1: return 2
	elif iOption == 2: return 3
	elif iOption == 3: return 2
	elif iOption == 4: return 2
	elif iOption == 5: return 4
	elif iOption == 6: return 4
	elif iOption == 7: return 3
	elif iOption == 8: return 2
	return 0
	
def getCustomMapOptionDescAt(argsList):
	[iOption, iSelection] = argsList
	if iOption == 0:
		if iSelection == 0: return "Flat"
		elif iSelection == 1: return "Cylindrical"
		return "Toroidal"
	elif iOption == 1:
		if iSelection == 0: return "2"
		return "3"
	elif iOption == 2:
		if iSelection == 0: return "Pressed"
		elif iSelection == 1: return "Natural"
		return "Fjord"
	elif iOption == 3:
		if iSelection == 0: return "Fractal"
		return "Solid"
	elif iOption == 4:
		if iSelection == 0: return "Disabled"
		return "Enabled"
	elif iOption == 5:
		if iSelection == 0: return "Disabled"
		elif iSelection == 1: return "1 per 4x4 tiles"
		elif iSelection == 2: return "1 per 5x5 tiles"
		return "1 per 6x6 tiles"
	elif iOption == 6:
		if iSelection == 0: return "Disabled"
		elif iSelection == 1: return "At least 1"
		elif iSelection == 2: return "At least 2"
		return "At least 3"
	elif iOption == 7:
		if iSelection == 0: return "Disabled"
		elif iSelection == 1: return "Reduce 50%"
		return "Reduce 100%"
	elif iOption == 8:
		if iSelection == 0: return "Disabled"
		return "Enabled"
	return ""

def getCustomMapOptionDefault(argsList):
	[iOption] = argsList
	if iOption == 0: return 1
	elif iOption == 1: return 0
	elif iOption == 2: return 0
	elif iOption == 3: return 1
	elif iOption == 4: return 1
	elif iOption == 5: return 2
	elif iOption == 6: return 1
	elif iOption == 7: return 0
	elif iOption == 8: return 0
	return 0

def getWrapX():
	map = CyMap()
	return (map.getCustomMapOption(0) == 1 or map.getCustomMapOption(0) == 2)

def getWrapY():
	map = CyMap()
	return (map.getCustomMapOption(0) == 2)

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
	bDebugSignsEnabled = (map.getCustomMapOption(8) == 1)

	activeTeams = []
	for iPlayer in range(gc.getMAX_CIV_PLAYERS()):
		pPlayer = gc.getPlayer(iPlayer)
		if pPlayer.isEverAlive():
			iTeam = pPlayer.getTeam()
			if iTeam not in activeTeams:
				activeTeams.append(iTeam)

	activeTeams.sort()
	iNumTeams = len(activeTeams)
	iRegionCount = 2 + map.getCustomMapOption(1)

	if iNumTeams == 2:
		bTeamPlacement = True
		teamRegionMap[activeTeams[0]] = "ColumnL"
		teamRegionMap[activeTeams[1]] = "ColumnR"
	elif iNumTeams == 3 and iRegionCount == 3:
		bTeamPlacement = True
		teamRegionMap[activeTeams[0]] = "ColumnL"
		teamRegionMap[activeTeams[1]] = "ColumnR"
		teamRegionMap[activeTeams[2]] = "ColumnC"

	if bTeamPlacement:
		print "THem team placement enabled:", teamRegionMap

class GeometricMultiFractal(CvMapGeneratorUtil.MultilayeredFractal):
	"""
	Fractal generator supporting geometric masking and rotation.
	Shapes: RECT, ELLIPSE, ISOTRI.
	"""
	def getReducedEdgeWaterThreshold(self, r_type, water_prc, iWaterThreshold, iWaterThresholds,
	rx, ry, invRxSq, invRySq, radius_x, radius_y,
	height_tiles, b_dist, v_dist, max_rx):
		fCenterInner = 0.45
		fCenterOuter = 0.65
		fCenterMultiplier = 2.0
		fEdgeInner = 0.80
		fEdgeOuter = 1.00
		fEdgeMultiplier = 1.0
		fIsotriEdgeBand = 0.20
		edgeStrength = 0.0
		centerStrength = 0.0
		shape_fill = 0.0
		if r_type == "ELLIPSE":
			shape_fill = math.sqrt((rx*rx * invRxSq) + (ry*ry * invRySq))
		elif r_type == "ISOTRI":
			edgeBand = min(radius_x, height_tiles) * fIsotriEdgeBand
			edgeMargin = min(ry + b_dist, v_dist - ry, max_rx - abs(rx))
			if edgeBand <= 0:
				shape_fill = 1.0
			else:
				shape_fill = 1.0 - (edgeMargin / edgeBand)
		else:
			if radius_x > 0: shape_fill = abs(rx) / radius_x
			if radius_y > 0:
				y_fill = abs(ry) / radius_y
				if y_fill > shape_fill: shape_fill = y_fill
		if shape_fill < fCenterInner:
			centerStrength = 1.0 * fCenterMultiplier
		elif shape_fill < fCenterOuter:
			if fCenterOuter > fCenterInner:
				centerStrength = ((fCenterOuter - shape_fill) / (fCenterOuter - fCenterInner)) * fCenterMultiplier
		if shape_fill > fEdgeInner:
			if fEdgeOuter > fEdgeInner:
				edgeStrength = ((shape_fill - fEdgeInner) / (fEdgeOuter - fEdgeInner)) * fEdgeMultiplier
		if edgeStrength > 1.0: edgeStrength = 1.0
		if centerStrength > 1.0: centerStrength = 1.0
		if edgeStrength > 0.0:
			iLocalWaterPercent = water_prc + int((100 - water_prc) * edgeStrength)
			if iLocalWaterPercent > 100: iLocalWaterPercent = 100
			return iWaterThresholds[iLocalWaterPercent]
		elif centerStrength > 0.0:
			iLocalWaterPercent = int(water_prc * (1.0 - centerStrength))
			if iLocalWaterPercent < 0: iLocalWaterPercent = 0
			return iWaterThresholds[iLocalWaterPercent]

		return iWaterThreshold

	def generatePlotsByRegion(self, region_data):
		sea = 0 
		
		# Define Terrain Profiles: (HillDensity%, PeakDensity%_of_Hills)
		terrain_profiles = {
			"flat":         (15, 1),
			"default":      (30, 20),
			"plateau":      (50, 30),
			"highland":     (75, 40),
			"alpine":       (95, 60),
		}
		
		gc = CyGlobalContext()
		m = CyMap()
		iRocky = gc.getInfoTypeForString("CLIMATE_ROCKY")
		if m.getClimate() == iRocky:
			for key in terrain_profiles.keys():
				h_dens, p_dens = terrain_profiles[key]
				new_h = int(h_dens * 1.2)
				new_p = int(p_dens * 1.1)
				if new_h > 100: new_h = 100
				if new_p > 100: new_p = 100
				terrain_profiles[key] = (new_h, new_p)

		for data in region_data:
			name, r_type_raw, cx, cy, d1, d2, d3, terrain, grain, h_grain, water_prc, bReduceEdges = data
			r_type = r_type_raw.upper()
			
			# 1. Coordinate Math
			center_x = cx * self.iW
			center_y = cy * self.iH
			radius_x = (d1 / 2.0) * self.iW
			radius_y = (d2 / 2.0) * self.iH
			height_tiles = d2 * self.iH

			# Rotation/Geometry Math
			rad = -math.radians(d3)
			cosA, sinA = math.cos(rad), math.sin(rad)
			v_dist, b_dist = (2.0 / 3.0) * height_tiles, (1.0 / 3.0) * height_tiles
			invRxSq, invRySq = 0.0, 0.0
			if radius_x > 0: invRxSq = 1.0 / (radius_x * radius_x)
			if radius_y > 0: invRySq = 1.0 / (radius_y * radius_y)

			if r_type == "ELLIPSE":
				x_extent = math.sqrt((radius_x * cosA) * (radius_x * cosA) + (radius_y * sinA) * (radius_y * sinA))
				y_extent = math.sqrt((radius_x * sinA) * (radius_x * sinA) + (radius_y * cosA) * (radius_y * cosA))
				min_x = -x_extent
				max_x = x_extent
				min_y = -y_extent
				max_y = y_extent
			elif r_type == "ISOTRI":
				points = [(-radius_x, -b_dist), (radius_x, -b_dist), (0.0, v_dist)]
				min_x = 0.0
				max_x = 0.0
				min_y = 0.0
				max_y = 0.0
				for iPoint in range(len(points)):
					local_x, local_y = points[iPoint]
					world_dx = local_x * cosA + local_y * sinA
					world_dy = -local_x * sinA + local_y * cosA
					if iPoint == 0 or world_dx < min_x: min_x = world_dx
					if iPoint == 0 or world_dx > max_x: max_x = world_dx
					if iPoint == 0 or world_dy < min_y: min_y = world_dy
					if iPoint == 0 or world_dy > max_y: max_y = world_dy
			else:
				x_extent = abs(radius_x * cosA) + abs(radius_y * sinA)
				y_extent = abs(radius_x * sinA) + abs(radius_y * cosA)
				min_x = -x_extent
				max_x = x_extent
				min_y = -y_extent
				max_y = y_extent
			
			iWest = max(0, int(center_x + min_x))
			iEast = min(self.iW - 1, int(center_x + max_x))
			iSouth = max(0, int(center_y + min_y))
			iNorth = min(self.iH - 1, int(center_y + max_y))
			
			reg_w, reg_h = iEast - iWest + 1, iNorth - iSouth + 1
			if reg_w <= 0 or reg_h <= 0: continue

			# 2. Fractal Initialization
			NiTextOut("Generating %s (Geometric Fractal) ..." % name)
			
			# This fractal is now shared by BOTH Land and Water regions
			regionContFrac = CyFractal()
			regionContFrac.fracInit(reg_w, reg_h, grain, self.dice, self.iFlags, -1, -1)
			
			# Calculate threshold for the "Active" part of the fractal
			if water_prc <= 0:
				iWaterThreshold = -1
			elif water_prc >= 100:
				iWaterThreshold = 255
			else:
				iWaterThreshold = regionContFrac.getHeightFromPercent(water_prc + sea)

			is_subtractive = (terrain == "water")
			iWaterThresholds = []
			if bReduceEdges and not is_subtractive and water_prc > 0 and water_prc < 100:
				for iPercent in range(101):
					iWaterThresholds.append(regionContFrac.getHeightFromPercent(iPercent))

			# Only Land regions need Hill/Peak fractals
			if not is_subtractive:
				regionHillsFrac = CyFractal()
				regionPeaksFrac = CyFractal()
				regionHillsFrac.fracInit(reg_w, reg_h, h_grain, self.dice, 0, -1, -1)
				regionPeaksFrac.fracInit(reg_w, reg_h, h_grain+1, self.dice, 0, -1, -1)

				h_dens, p_dens = terrain_profiles.get(terrain, terrain_profiles["default"])
				iHillThreshold = regionHillsFrac.getHeightFromPercent(100 - h_dens)
				iPeakThreshold = regionPeaksFrac.getHeightFromPercent(100 - p_dens)

			# 3. Iterate over the grid
			for x in range(reg_w):
				world_x = x + iWest
				# Add 0.5 to world_x to get the center of the tile
				dx = (float(world_x) + 0.5) - center_x
				for y in range(reg_h):
					world_y = y + iSouth
					# Add 0.5 to world_y to get the center of the tile
					dy = (float(world_y) + 0.5) - center_y

					# Now, tiles on either side of an even-numbered split will have 
					# identical distance values (e.g., -0.5 and 0.5).
					# Geometry Check
					rx = dx * cosA - dy * sinA
					ry = dx * sinA + dy * cosA
					is_inside = False
					max_rx = 0.0
					if r_type == "ELLIPSE":
						if (rx*rx * invRxSq) + (ry*ry * invRySq) <= 1.0: is_inside = True
					elif r_type == "ISOTRI":
						if ry >= -b_dist and ry <= v_dist:
							max_rx = radius_x * (v_dist - ry) / height_tiles
							if abs(rx) <= max_rx: is_inside = True
					else: # RECT
						if abs(rx) <= radius_x and abs(ry) <= radius_y: is_inside = True

					if not is_inside: continue
						
					# Decide plot type
					world_i = world_y * self.iW + world_x
					val = regionContFrac.getHeight(x, y)
					# Edge reduction
					iLocalWaterThreshold = iWaterThreshold
					if bReduceEdges and not is_subtractive and water_prc > 0 and water_prc < 100:
						iLocalWaterThreshold = self.getReducedEdgeWaterThreshold(
							r_type, water_prc, iWaterThreshold, iWaterThresholds,
							rx, ry, invRxSq, invRySq, radius_x, radius_y,
							height_tiles, b_dist, v_dist, max_rx)
					
					if is_subtractive:
						# WATER REGION: If fractal roll is within the water percent, punch a hole.
						# Setting water_prc=100 will now correctly turn every tile to ocean.
						if val <= iLocalWaterThreshold:
							self.wholeworldPlotTypes[world_i] = PlotTypes.PLOT_OCEAN
					else:
						# LAND REGION: Skip tiles within the water percent threshold (remains ocean).
						if val <= iLocalWaterThreshold: 
							continue
						
						# Process Hills and Peaks for land
						if regionHillsFrac.getHeight(x, y) >= iHillThreshold:
							if regionPeaksFrac.getHeight(x, y) >= iPeakThreshold:
								self.wholeworldPlotTypes[world_i] = PlotTypes.PLOT_PEAK
							else:
								self.wholeworldPlotTypes[world_i] = PlotTypes.PLOT_HILLS
						else:
							self.wholeworldPlotTypes[world_i] = PlotTypes.PLOT_LAND
							
		return self.wholeworldPlotTypes

class THem_RegionMaskManager:
	def makeRegionMask(self, centerX, centerY, width, height, angle, iW, iH):
		center_x = centerX * iW
		center_y = centerY * iH
		radius_x = (width / 2.0) * iW
		radius_y = (height / 2.0) * iH
		rad = -math.radians(angle)
		cosA = math.cos(rad)
		sinA = math.sin(rad)
		x_extent = abs(radius_x * cosA) + abs(radius_y * sinA)
		y_extent = abs(radius_x * sinA) + abs(radius_y * cosA)

		iWestX = int(center_x - x_extent)
		iEastX = int(center_x + x_extent)
		iSouthY = int(center_y - y_extent)
		iNorthY = int(center_y + y_extent)

		if iWestX < 0: iWestX = 0
		if iEastX > iW - 1: iEastX = iW - 1
		if iSouthY < 0: iSouthY = 0
		if iNorthY > iH - 1: iNorthY = iH - 1

		iWidth = iEastX - iWestX + 1
		iHeight = iNorthY - iSouthY + 1
		if iWidth < 1: iWidth = 1
		if iHeight < 1: iHeight = 1

		return (centerX, centerY, width, height, angle, iWestX, iSouthY, iWidth, iHeight)

	def getRegionMaskBounds(self, regionMask, iW, iH):
		if len(regionMask) == 4:
			return regionMask
		return (regionMask[5], regionMask[6], regionMask[7], regionMask[8])

	def plotInRegionMask(self, regionMask, x, y, iW, iH):
		if len(regionMask) == 4:
			iWestX, iSouthY, iWidth, iHeight = regionMask
			if x < iWestX or x >= iWestX + iWidth: return False
			if y < iSouthY or y >= iSouthY + iHeight: return False
			return True

		centerX, centerY, width, height, angle, iWestX, iSouthY, iWidth, iHeight = regionMask
		center_x = centerX * iW
		center_y = centerY * iH
		radius_x = (width / 2.0) * iW
		radius_y = (height / 2.0) * iH
		rad = -math.radians(angle)
		cosA = math.cos(rad)
		sinA = math.sin(rad)
		dx = (float(x) + 0.5) - center_x
		dy = (float(y) + 0.5) - center_y
		rx = dx * cosA - dy * sinA
		ry = dx * sinA + dy * cosA
		if abs(rx) > radius_x: return False
		if abs(ry) > radius_y: return False
		return True

	def plotInRegionMasks(self, regionMasks, x, y, iW, iH):
		if len(regionMasks) == 0:
			return True
		for regionMask in regionMasks:
			if self.plotInRegionMask(regionMask, x, y, iW, iH):
				return True
		return False

regionMaskManager = THem_RegionMaskManager()

class THem_ContinentBalancer:
	def countRegionLand(self, plotTypes, regionRects, iW, iH):
		counts = {}
		for label in regionRects.keys():
			iCount = 0
			regionMasks = regionRects[label]
			for regionMask in regionMasks:
				iWestX, iSouthY, iWidth, iHeight = regionMaskManager.getRegionMaskBounds(regionMask, iW, iH)
				for x in range(iWestX, iWestX + iWidth):
					for y in range(iSouthY, iSouthY + iHeight):
						if not regionMaskManager.plotInRegionMask(regionMask, x, y, iW, iH): continue
						i = y * iW + x
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

def _remove_one_tile_lakes(plotTypes, iW, iH):
	if plotTypes is None:
		return None

	lakePlots = []
	directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
	bWrapX = getWrapX()
	bWrapY = getWrapY()

	for x in range(iW):
		for y in range(iH):
			i = y * iW + x
			if plotTypes[i] != PlotTypes.PLOT_OCEAN: continue

			bAdjacentWater = False
			for dx, dy in directions:
				adjX = x + dx
				adjY = y + dy
				if bWrapX:
					if adjX < 0: adjX = iW - 1
					elif adjX >= iW: adjX = 0
				if bWrapY:
					if adjY < 0: adjY = iH - 1
					elif adjY >= iH: adjY = 0
				if adjX < 0 or adjX >= iW: continue
				if adjY < 0 or adjY >= iH: continue
				if plotTypes[adjY * iW + adjX] == PlotTypes.PLOT_OCEAN:
					bAdjacentWater = True
					break

			if not bAdjacentWater:
				lakePlots.append(i)

	for i in lakePlots:
		plotTypes[i] = PlotTypes.PLOT_LAND

	if len(lakePlots) > 0:
		print "THem converted %d one-tile lakes to flatland" % len(lakePlots)

	return plotTypes

def _is_coastal_peak_plot(plotTypes, x, y, iW, iH):
	i = y * iW + x
	if plotTypes[i] != PlotTypes.PLOT_PEAK:
		return False

	for dx in range(-1, 2):
		for dy in range(-1, 2):
			if dx == 0 and dy == 0: continue
			adjX = x + dx
			adjY = y + dy
			if adjX < 0 or adjX >= iW: continue
			if adjY < 0 or adjY >= iH: continue
			if plotTypes[adjY * iW + adjX] == PlotTypes.PLOT_OCEAN:
				return True

	return False

def _reduce_coastal_peaks(plotTypes, iW, iH, iReductionOption, dice):
	if plotTypes is None:
		return None
	if iReductionOption <= 0:
		return plotTypes

	reducedPlots = []
	for x in range(iW):
		for y in range(iH):
			if not _is_coastal_peak_plot(plotTypes, x, y, iW, iH): continue
			bReduce = False
			if iReductionOption == 1:
				if dice.get(100, "THem Reduce Coastal Peak") < 50:
					bReduce = True
			else:
				bReduce = True

			if bReduce:
				reducedPlots.append(y * iW + x)

	for i in reducedPlots:
		plotTypes[i] = PlotTypes.PLOT_HILLS

	if len(reducedPlots) > 0:
		print "THem reduced %d coastal peaks to hills" % len(reducedPlots)

	return plotTypes

def generatePlotTypes():
	global _THEM_REGION_RECTS
	global _START_PLOT_MAP
	global plotgen

	print "THem GMF generatePlotTypes entered"
	NiTextOut("Setting Plot Types (Python Geometric Continents) ...")
	_START_PLOT_MAP = None
	
	gc = CyGlobalContext()
	map = CyMap()
	iW = map.getGridWidth()
	iH = map.getGridHeight()
	continent_grain = map.getCustomMapOption(2)
	continent_count = map.getCustomMapOption(1)
	bPeripheralReduce = (map.getCustomMapOption(3) == 1)
	iReduceCoastalPeaks = map.getCustomMapOption(7)
	iContinentAngle = gc.getGame().getMapRand().get(51, "THem Continent Angle") - 25
	print "THem continent angle:", iContinentAngle

	sizekey = map.getWorldSize()
	sizevalues = {
		WorldSizeTypes.WORLDSIZE_DUEL:      (3,2,1),
		WorldSizeTypes.WORLDSIZE_TINY:      (3,2,1),
		WorldSizeTypes.WORLDSIZE_SMALL:     (4,2,1),
		WorldSizeTypes.WORLDSIZE_STANDARD:  (4,2,1),
		WorldSizeTypes.WORLDSIZE_LARGE:     (4,2,1),
		WorldSizeTypes.WORLDSIZE_HUGE:      (5,2,1)
	}
	(ScatterGrain, BalanceGrain, GatherGrain) = sizevalues[sizekey]
	if continent_grain == 0:
		PeripheralGrain = 1
	else:
		PeripheralGrain = continent_grain + 2
	CoreGrain = continent_grain + 1
	
	iRawSeaLevelChange = gc.getSeaLevelInfo(map.getSeaLevel()).getSeaLevelChange()
	fPeripheralSizeChange = 0.0
	iWaterPercentChange = 0
	if iRawSeaLevelChange > 0: # High
		fPeripheralSizeChange = -0.06
		iWaterPercentChange = 10
	elif iRawSeaLevelChange < 0: # Low
		fPeripheralSizeChange = +0.06
	
	regions =[]
	additional_regions = []
	
	if continent_count == 0:
		regions = [
			# Required: Name, Type, Center X, Center Y, Width, Height, Angle, Terrain, Grain, Hills Grain, Water Percent, bReduceEdges
			("PeripheralL", "Rect", 0.250, 0.45, 0.30+fPeripheralSizeChange, 0.70+fPeripheralSizeChange, iContinentAngle, "plateau", PeripheralGrain, ScatterGrain+1, 50+iWaterPercentChange, bPeripheralReduce),
			("PeripheralR", "Rect", 0.750, 0.55, 0.30+fPeripheralSizeChange, 0.70+fPeripheralSizeChange, iContinentAngle, "plateau", PeripheralGrain, ScatterGrain+1, 50+iWaterPercentChange, bPeripheralReduce),
			("IslandsR", "Rect", 0.750, 0.18, 0.3, 0.2, 0, "default", ScatterGrain, ScatterGrain, 85, False),
			("IslandsL", "Rect", 0.250, 0.82, 0.3, 0.2, 0, "default", ScatterGrain, ScatterGrain, 85, False),
		]
		region_data = [
			("ColumnL", 0.250, 0.450, 0.30+fPeripheralSizeChange, 0.70+fPeripheralSizeChange, iContinentAngle),
			("ColumnR", 0.750, 0.550, 0.30+fPeripheralSizeChange, 0.70+fPeripheralSizeChange, iContinentAngle),
		]
		if continent_grain == 0:
			additional_regions =[
				("CoreL", "Ellipse", 0.250, 0.45, 0.15, 0.5, iContinentAngle, "default", CoreGrain, ScatterGrain, 25, True),
				("CoreR", "Ellipse", 0.750, 0.55, 0.150, 0.5, iContinentAngle, "default", CoreGrain, ScatterGrain, 25, True),
			]
		else: # smaller core for higher grain continents
			additional_regions =[
				("CoreL", "Ellipse", 0.250, 0.45, 0.07, 0.25, iContinentAngle, "flat", CoreGrain, ScatterGrain, 25, True),
				("CoreR", "Ellipse", 0.750, 0.55, 0.07, 0.25, iContinentAngle, "flat", CoreGrain, ScatterGrain, 25, True),
			]
	else: # 3 continents
		regions = [
			("PeripheralL", "Rect", 0.167, 0.450, 0.2+fPeripheralSizeChange, 0.7+fPeripheralSizeChange, iContinentAngle, "plateau", PeripheralGrain, ScatterGrain, 40+iWaterPercentChange, bPeripheralReduce),
			("PeripheralR", "Rect", 0.833, 0.550, 0.2+fPeripheralSizeChange, 0.7+fPeripheralSizeChange, iContinentAngle, "plateau", PeripheralGrain, ScatterGrain, 40+iWaterPercentChange, bPeripheralReduce),
			("PeripheralC", "Rect", 0.500, 0.500, 0.2+fPeripheralSizeChange, 0.7+fPeripheralSizeChange, iContinentAngle, "plateau", PeripheralGrain, ScatterGrain, 40+iWaterPercentChange, bPeripheralReduce),
			
			("IslandsR", "Rect", 0.833, 0.22, 0.10, 0.150, 0, "default", ScatterGrain, ScatterGrain, 85, False),
			("IslandsL", "Rect", 0.167, 0.78, 0.10, 0.150, 0, "default", ScatterGrain, ScatterGrain, 85, False),
			("IslandsC_Top", "Rect", 0.500, 0.10, 0.10, 0.075, 0, "default", ScatterGrain, ScatterGrain, 80, False),
			("IslandsC_Bot", "Rect", 0.500, 0.90, 0.10, 0.075, 0, "default", ScatterGrain, ScatterGrain, 80, False),
		]
		if continent_grain == 0:
			additional_regions =[
				("CoreL", "Ellipse", 0.167, 0.450, 0.12, 0.55, iContinentAngle, "default", GatherGrain, ScatterGrain, 25, True),
				("CoreR", "Ellipse", 0.833, 0.550, 0.12, 0.55, iContinentAngle, "default", GatherGrain, ScatterGrain, 25, True),
				("CoreC", "Ellipse", 0.500, 0.500, 0.12, 0.55, iContinentAngle, "default", GatherGrain, ScatterGrain, 25, True),
			]
		else: # smaller core for higher grain continents
			additional_regions =[
				("CoreL", "Ellipse", 0.167, 0.450, 0.050, 0.23, iContinentAngle, "default", GatherGrain, ScatterGrain, 25, True),
				("CoreR", "Ellipse", 0.833, 0.550, 0.050, 0.23, iContinentAngle, "default", GatherGrain, ScatterGrain, 25, True),
				("CoreC", "Ellipse", 0.500, 0.500, 0.050, 0.23, iContinentAngle, "default", GatherGrain, ScatterGrain, 25, True),
			]
		region_data = [
			("ColumnL", 0.167, 0.450, 0.2+fPeripheralSizeChange, 0.7+fPeripheralSizeChange, iContinentAngle),
			("ColumnR", 0.833, 0.550, 0.2+fPeripheralSizeChange, 0.7+fPeripheralSizeChange, iContinentAngle),
			("ColumnC", 0.500, 0.500, 0.2+fPeripheralSizeChange, 0.7+fPeripheralSizeChange, iContinentAngle),
		]

	regions.extend(additional_regions)

	regionRects = {}
	for data in region_data:
		label, centerX, centerY, width, height, angle = data
		regionRects[label] = [regionMaskManager.makeRegionMask(centerX, centerY, width, height, angle, iW, iH)]

	iMaxAttempts = 20
	bestPlotTypes = None
	bestRects = None
	iBestScore = -1
	continentBalancer = THem_ContinentBalancer()

	for iAttempt in range(1, iMaxAttempts + 1):
		plotgen = GeometricMultiFractal()
		plotTypes = plotgen.generatePlotsByRegion(regions)
		plotTypes = _reduce_coastal_peaks(plotTypes, iW, iH, iReduceCoastalPeaks, gc.getGame().getMapRand())
		# if continent_grain < 2: # Less than Fjord
			# plotTypes = _remove_one_tile_lakes(plotTypes, iW, iH)
		counts = continentBalancer.countRegionLand(plotTypes, regionRects, iW, iH)
		bAccepted = continentBalancer.isLandBalanceAcceptable(counts)
		continentBalancer.printLandBalance(iAttempt, counts, bAccepted)
		if bAccepted:
			_THEM_REGION_RECTS = regionRects
			return plotTypes

		iScore = continentBalancer.getLandBalanceScore(counts)
		if iBestScore == -1 or iScore < iBestScore:
			iBestScore = iScore
			bestPlotTypes = plotTypes
			bestRects = regionRects

	if bestRects != None:
		_THEM_REGION_RECTS = bestRects
	print "THem land balance fallback after %d attempts" % (iMaxAttempts)
	return bestPlotTypes

def _get_dominant_area_for_region(label, usedAreas):
	global _THEM_REGION_RECTS

	map = CyMap()
	iW = map.getGridWidth()
	iH = map.getGridHeight()
	areaCounts = {}
	regionMasks = _THEM_REGION_RECTS.get(label, [])
	for regionMask in regionMasks:
		iWestX, iSouthY, iWidth, iHeight = regionMaskManager.getRegionMaskBounds(regionMask, iW, iH)
		for x in range(iWestX, iWestX + iWidth):
			for y in range(iSouthY, iSouthY + iHeight):
				if not regionMaskManager.plotInRegionMask(regionMask, x, y, iW, iH): continue
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

	regionMasks = _THEM_REGION_RECTS.get(label, [])
	if len(regionMasks) == 0:
		return (0, iW - 1, 0, iH - 1)

	xMin = iW - 1
	xMax = 0
	yMin = iH - 1
	yMax = 0

	for regionMask in regionMasks:
		iWestX, iSouthY, iWidth, iHeight = regionMaskManager.getRegionMaskBounds(regionMask, iW, iH)
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

class THem_StartPlotManager:
	def countAdjacentWaterTiles(self, map, x, y, iW, iH):
		iWaterCount = 0
		for dx in range(-1, 2):
			for dy in range(-1, 2):
				if dx == 0 and dy == 0: continue
				adjX = x + dx
				adjY = y + dy
				if getWrapX():
					if adjX < 0: adjX = iW - 1
					elif adjX >= iW: adjX = 0
				if getWrapY():
					if adjY < 0: adjY = iH - 1
					elif adjY >= iH: adjY = 0
				if adjX < 0 or adjX >= iW: continue
				if adjY < 0 or adjY >= iH: continue
				if map.plot(adjX, adjY).isWater():
					iWaterCount += 1
		return iWaterCount

	def isStartTooCoastal(self, map, x, y, iW, iH, playerID, context):
		iWaterCount = self.countAdjacentWaterTiles(map, x, y, iW, iH)
		if iWaterCount >= 3:
			print "THem rejected %s start for player %d at (%d, %d): %d adjacent water tiles" % (context, playerID, x, y, iWaterCount)
			return True
		return False

	def isStartLandmassTooSmall(self, map, pPlot, playerID, context):
		iArea = pPlot.getArea()
		if iArea == -1:
			print "THem rejected %s start for player %d at (%d, %d): no land area" % (context, playerID, pPlot.getX(), pPlot.getY())
			return True

		pArea = map.getArea(iArea)
		if pArea.isNone():
			print "THem rejected %s start for player %d at (%d, %d): no land area" % (context, playerID, pPlot.getX(), pPlot.getY())
			return True

		iAreaTiles = pArea.getNumTiles()
		if iAreaTiles < 20:
			print "THem rejected %s start for player %d at (%d, %d): landmass has %d tiles" % (context, playerID, pPlot.getX(), pPlot.getY(), iAreaTiles)
			return True

		return False

	def isValidStartPlot(self, map, pPlot, playerID, context):
		if pPlot.isWater() or pPlot.isPeak(): return False
		if self.isStartTooCoastal(map, pPlot.getX(), pPlot.getY(), map.getGridWidth(), map.getGridHeight(), playerID, context): return False
		if self.isStartLandmassTooSmall(map, pPlot, playerID, context): return False
		return True

def _is_valid_default_start_plot(playerID, x, y):
	map = CyMap()
	pPlot = map.plot(x, y)
	startManager = THem_StartPlotManager()
	return startManager.isValidStartPlot(map, pPlot, playerID, "default")

def _is_prohibited_start_bonus(pPlot, gc):
	ProhibitedStartBonusIDs = ['BONUS_WHEAT', 'BONUS_RICE', 'BONUS_CORN', 'BONUS_COW', 'BONUS_SHEEP', 'BONUS_PIG', 'BONUS_DEER']

	iBonus = pPlot.getBonusType(-1)
	if iBonus == -1:
		return False
	for bonusName in ProhibitedStartBonusIDs:
		iProhibited = gc.getInfoTypeForString(bonusName)
		if iProhibited != -1 and iBonus == iProhibited:
			return True
	return False

def _assign_all_starting_plots():
	global bTeamPlacement
	global teamRegionMap
	global teamAreaMap

	gc = CyGlobalContext()
	map = CyMap()
	mapRand = gc.getGame().getMapRand()
	startManager = THem_StartPlotManager()
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
		teamMasks = _THEM_REGION_RECTS.get(label, [])
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
							if not regionMaskManager.plotInRegionMasks(teamMasks, x, y, iW, iH): continue
							pPlot = map.plot(x, y)
							if not startManager.isValidStartPlot(map, pPlot, playerID, "team candidate"): continue
							if pPlot.getArea() != iTargetArea: continue
							if _is_prohibited_start_bonus(pPlot, gc): continue

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
						if not regionMaskManager.plotInRegionMasks(teamMasks, x, y, iW, iH): continue
						pPlot = map.plot(x, y)
						if not startManager.isValidStartPlot(map, pPlot, playerID, "team fallback"): continue
						if pPlot.getArea() != iTargetArea: continue
						if _is_prohibited_start_bonus(pPlot, gc): continue
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
		return CvMapGeneratorUtil.findStartingPlot(playerID, _is_valid_default_start_plot)

	if _START_PLOT_MAP is None:
		_START_PLOT_MAP = _assign_all_starting_plots()
		if _START_PLOT_MAP is None:
			return CvMapGeneratorUtil.findStartingPlot(playerID, _is_valid_default_start_plot)

	iPlot = _START_PLOT_MAP.get(playerID, -1)
	if iPlot == -1:
		return CvMapGeneratorUtil.findStartingPlot(playerID, _is_valid_default_start_plot)

	map = CyMap()
	pPlot = map.plotByIndex(iPlot)
	startManager = THem_StartPlotManager()
	if not startManager.isValidStartPlot(map, pPlot, playerID, "final"):
		return CvMapGeneratorUtil.findStartingPlot(playerID, _is_valid_default_start_plot)

	return iPlot

def normalizeStartingPlotLocations():
	global bTeamPlacement

	if bTeamPlacement:
		return None

	CyPythonMgr().allowDefaultImpl()
	return None

def getTHemLatitude(iX, iY):
	map = CyMap()
	iH = map.getGridHeight()

	if iH <= 1: iH = 2

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

class PathNavigator:
	def __init__(self, map_obj, dice):
		self.map = map_obj
		self.dice = dice
		self.iW = map_obj.getGridWidth()
		self.iH = map_obj.getGridHeight()
		self.noise = CyFractal()
		self.noise.fracInit(self.iW, self.iH, 2, self.dice, 0, -1, -1)

	def is_any_water(self, x, y):
		if x < 0 or x >= self.iW or y < 0 or y >= self.iH: return False
		return self.map.plot(x, y).isWater()

	def get_best_move(self, cx, cy, tx, ty, visited, meander):
		best_score = 999999.0
		best_move = None
		moves = [(1,0), (-1,0), (0,1), (0,-1), (1,1), (1,-1), (-1,1), (-1,-1)]

		for move in moves:
			nx = cx + move[0]
			ny = cy + move[1]
			if nx < 0 or nx >= self.iW or ny < 0 or ny >= self.iH: continue

			bVisited = False
			for v in visited:
				if nx == v[0] and ny == v[1]:
					bVisited = True
					break
			if bVisited: continue

			dist = math.sqrt((nx - tx)**2 + (ny - ty)**2)
			n_val = (self.noise.getHeight(nx, ny) / 100.0) - 0.5
			score = dist * (1.0 + (n_val * meander))

			if score < best_score:
				best_score = score
				best_move = (nx, ny, move[0], move[1])

		return best_move

	def generate_path(self, start, end, meander):
		curr_x, curr_y = start
		path = [(curr_x, curr_y)]
		visited = [(curr_x, curr_y)]

		max_steps = (abs(curr_x - end[0]) + abs(curr_y - end[1])) * 4
		for i in range(max_steps):
			if curr_x == end[0] and curr_y == end[1]: break
			move = self.get_best_move(curr_x, curr_y, end[0], end[1], visited, meander)
			if not move: break
			curr_x = move[0]
			curr_y = move[1]
			path.append((curr_x, curr_y))
			visited.append((curr_x, curr_y))

			if i > 0:
				if self.is_any_water(curr_x, curr_y):
					break

		return path

class StandardRiverMaker:
	def __init__(self, navigator):
		self.nav = navigator
		self.map = navigator.map

	def build(self, checkpoints, meander):
		riverID = self.map.getNextRiverID()
		self.map.incrementNextRiverID()
		for i in range(len(checkpoints) - 1):
			start = (int(self.nav.iW * checkpoints[i][0]), int(self.nav.iH * checkpoints[i][1]))
			end = (int(self.nav.iW * checkpoints[i+1][0]), int(self.nav.iH * checkpoints[i+1][1]))
			path = self.nav.generate_path(start, end, meander)
			if not path: break

			for j in range(len(path)-1):
				curr = path[j]
				nextPlot = path[j+1]
				dx = nextPlot[0] - curr[0]
				dy = nextPlot[1] - curr[1]
				bStop = self._apply_river_flags(curr[0], curr[1], dx, dy, riverID)
				if bStop: return

	def _apply_river_flags(self, x, y, dx, dy, rID):
		N = CardinalDirectionTypes.CARDINALDIRECTION_NORTH
		S = CardinalDirectionTypes.CARDINALDIRECTION_SOUTH
		E = CardinalDirectionTypes.CARDINALDIRECTION_EAST
		W = CardinalDirectionTypes.CARDINALDIRECTION_WEST
		bStop = False

		if dx != 0:
			if dx == 1:
				tx = x
				flow = E
				look_x = tx + 1
			else:
				tx = x - 1
				flow = W
				look_x = tx - 1

			if self.nav.is_any_water(look_x, y) or self.nav.is_any_water(look_x, y-1):
				bStop = True

			p = self.map.plot(tx, y)
			if p:
				if not self.nav.is_any_water(tx, y):
					if not self.nav.is_any_water(tx, y-1):
						if self._check_merge(tx, y, False, flow):
							bStop = True
						p.setNOfRiver(True, flow)
						p.setRiverID(rID)
			if bStop: return True

		if dy != 0:
			tx = x + dx - 1
			if dy == 1:
				ty = y
				flow = N
				look_y = ty + 1
			else:
				ty = y - 1
				flow = S
				look_y = ty - 1

			if self.nav.is_any_water(tx, look_y) or self.nav.is_any_water(tx+1, look_y):
				bStop = True

			p = self.map.plot(tx, ty)
			if p:
				if not self.nav.is_any_water(tx, ty):
					if not self.nav.is_any_water(tx+1, ty):
						if self._check_merge(tx, ty, True, flow):
							bStop = True
						p.setWOfRiver(True, flow)
						p.setRiverID(rID)

		return bStop

	def _check_merge(self, x, y, is_vertical, flow):
		N = CardinalDirectionTypes.CARDINALDIRECTION_NORTH
		S = CardinalDirectionTypes.CARDINALDIRECTION_SOUTH
		E = CardinalDirectionTypes.CARDINALDIRECTION_EAST
		W = CardinalDirectionTypes.CARDINALDIRECTION_WEST
		if is_vertical:
			if flow == N:
				p = self.map.plot(x, y+1)
				if p and ((p.isWOfRiver() and p.getRiverNSDirection() == N) or (p.isNOfRiver() and p.getRiverWEDirection() == W)): return True
				p = self.map.plot(x+1, y+1)
				if p and (p.isNOfRiver() and p.getRiverWEDirection() == E): return True
			else:
				p = self.map.plot(x, y)
				if p and (p.isNOfRiver() and p.getRiverWEDirection() == W): return True
				p = self.map.plot(x, y-1)
				if p and (p.isWOfRiver() and p.getRiverNSDirection() == S): return True
				p = self.map.plot(x+1, y)
				if p and (p.isNOfRiver() and p.getRiverWEDirection() == E): return True
		else:
			if flow == E:
				p = self.map.plot(x, y)
				if p and (p.isWOfRiver() and p.getRiverNSDirection() == N): return True
				p = self.map.plot(x, y-1)
				if p and (p.isWOfRiver() and p.getRiverNSDirection() == S): return True
				p = self.map.plot(x+1, y)
				if p and (p.isNOfRiver() and p.getRiverWEDirection() == E): return True
			else:
				p = self.map.plot(x-1, y)
				if p and ((p.isNOfRiver() and p.getRiverWEDirection() == W) or (p.isWOfRiver() and p.getRiverNSDirection() == N)): return True
				p = self.map.plot(x-1, y-1)
				if p and (p.isWOfRiver() and p.getRiverNSDirection() == S): return True
		return False

class THem_ExtraRivers:
	def __init__(self, map_obj, gc, dice):
		self.map = map_obj
		self.gc = gc
		self.dice = dice
		self.engine = CyEngine()
		self.iW = map_obj.getGridWidth()
		self.iH = map_obj.getGridHeight()

	def addRiverDebugSign(self, pPlot, msg):
		global bDebugSignsEnabled

		if not bDebugSignsEnabled: return
		if pPlot is None: return
		if pPlot.isNone(): return
		self.engine.addSign(pPlot, -1, msg)

	def getExtraRiverEndpoint(self, startX, startY, xMin, xMax, yMin, yMax):
		iWestDist = startX - xMin
		iEastDist = xMax - startX
		iSouthDist = startY - yMin
		iNorthDist = yMax - startY
		iBest = iWestDist
		sSide = "W"

		if iEastDist < iBest:
			iBest = iEastDist
			sSide = "E"
		if iSouthDist < iBest:
			iBest = iSouthDist
			sSide = "S"
		if iNorthDist < iBest:
			iBest = iNorthDist
			sSide = "N"

		endX = startX
		endY = startY
		if sSide == "W":
			endX = xMin - 2
		elif sSide == "E":
			endX = xMax + 2
		elif sSide == "S":
			endY = yMin - 2
		else:
			endY = yMax + 2

		if endX < 0: endX = 0
		if endX >= self.iW: endX = self.iW - 1
		if endY < 0: endY = 0
		if endY >= self.iH: endY = self.iH - 1

		return (endX, endY)

	def getExtraRiverCount(self):
		sizekey = self.map.getWorldSize()
		sizevalues = {
			WorldSizeTypes.WORLDSIZE_DUEL: 1,
			WorldSizeTypes.WORLDSIZE_TINY: 2,
			WorldSizeTypes.WORLDSIZE_SMALL: 3,
			WorldSizeTypes.WORLDSIZE_STANDARD: 4,
			WorldSizeTypes.WORLDSIZE_LARGE: 5,
			WorldSizeTypes.WORLDSIZE_HUGE: 6
		}
		return sizevalues.get(sizekey, 4)

	def isAwayFromCoast(self, pPlot, iMinDistance):
		startX = pPlot.getX()
		startY = pPlot.getY()

		for dx in range(-iMinDistance, iMinDistance + 1):
			for dy in range(-iMinDistance, iMinDistance + 1):
				x = startX + dx
				y = startY + dy
				if x < 0 or x >= self.iW: continue
				if y < 0 or y >= self.iH: continue
				if plotDistance(startX, startY, x, y) > iMinDistance: continue
				if self.map.plot(x, y).isWater():
					return False

		return True

	def removeNearbyRiverStarts(self, candidates, pStart, iMinDistance):
		filtered = []
		startX = pStart.getX()
		startY = pStart.getY()

		for pPlot in candidates:
			if plotDistance(startX, startY, pPlot.getX(), pPlot.getY()) >= iMinDistance:
				filtered.append(pPlot)

		return filtered

	def hasAdjacentRiver(self, pPlot):
		startX = pPlot.getX()
		startY = pPlot.getY()

		for dx in range(-1, 2):
			for dy in range(-1, 2):
				x = startX + dx
				y = startY + dy
				if x < 0 or x >= self.iW: continue
				if y < 0 or y >= self.iH: continue
				pAdj = self.map.plot(x, y)
				if pAdj.isNOfRiver() or pAdj.isWOfRiver():
					return True

		return False

	def removeAdjacentRiverStarts(self, candidates):
		filtered = []

		for pPlot in candidates:
			if not self.hasAdjacentRiver(pPlot):
				filtered.append(pPlot)

		return filtered

	def addExtraRivers(self):
		global bTeamPlacement
		global teamRegionMap
		global teamAreaMap
		global _THEM_REGION_RECTS

		if not bTeamPlacement:
			print "THem extra rivers skipped: team placement inactive"
			return

		self.map.recalculateAreas()

		if len(teamAreaMap) == 0:
			if not _resolve_team_areas():
				print "THem extra rivers skipped: could not resolve team areas"
				return

		nav = PathNavigator(self.map, self.dice)
		rivers = StandardRiverMaker(nav)
		iExtraRivers = self.getExtraRiverCount()
		sortedTeams = teamRegionMap.keys()
		sortedTeams.sort()

		for iTeam in sortedTeams:
			label = teamRegionMap[iTeam]
			regionMasks = _THEM_REGION_RECTS.get(label, [])
			if len(regionMasks) == 0:
				print "THem extra river skipped team %d: no region masks" % iTeam
				continue

			iArea = -1
			if teamAreaMap.has_key(iTeam):
				iArea = teamAreaMap[iTeam]

			candidates = []
			for regionMask in regionMasks:
				iWestX, iSouthY, iWidth, iHeight = regionMaskManager.getRegionMaskBounds(regionMask, self.iW, self.iH)
				for x in range(iWestX, iWestX + iWidth):
					for y in range(iSouthY, iSouthY + iHeight):
						if x < 0 or x >= self.iW: continue
						if y < 0 or y >= self.iH: continue
						if not regionMaskManager.plotInRegionMask(regionMask, x, y, self.iW, self.iH): continue
						pPlot = self.map.plot(x, y)
						if pPlot.isNone(): continue
						if pPlot.isWater(): continue
						if not pPlot.isHills() and not pPlot.isPeak(): continue
						if not self.isAwayFromCoast(pPlot, 4): continue
						if self.hasAdjacentRiver(pPlot): continue
						if iArea != -1:
							if pPlot.getArea() != iArea: continue
						candidates.append(pPlot)

			if len(candidates) == 0:
				print "THem extra river skipped team %d region %s: no valid start" % (iTeam, label)
				continue

			xMin, xMax, yMin, yMax = _get_team_region_bounds(label, self.iW, self.iH)
			for iRiver in range(iExtraRivers):
				if len(candidates) == 0:
					print "THem extra river skipped team %d region %s: candidates exhausted" % (iTeam, label)
					break

				iChoice = self.dice.get(len(candidates), "THem Extra River Start")
				pStart = candidates[iChoice]
				candidates = self.removeNearbyRiverStarts(candidates, pStart, 3)
				startX = pStart.getX()
				startY = pStart.getY()
				endX, endY = self.getExtraRiverEndpoint(startX, startY, xMin, xMax, yMin, yMax)

				startRelX = float(startX) / float(self.iW)
				startRelY = float(startY) / float(self.iH)
				endRelX = float(endX) / float(self.iW)
				endRelY = float(endY) / float(self.iH)
				rivers.build([(startRelX, startRelY), (endRelX, endRelY)], meander=0.2)
				candidates = self.removeAdjacentRiverStarts(candidates)
				self.addRiverDebugSign(pStart, "THem river %d start T%d" % (iRiver + 1, iTeam))
				print "THem extra river %d team %d from (%d, %d) toward (%d, %d)" % (iRiver + 1, iTeam, startX, startY, endX, endY)

def THemAddExtraRivers():
	map = CyMap()
	gc = CyGlobalContext()
	dice = gc.getGame().getMapRand()
	extraRivers = THem_ExtraRivers(map, gc, dice)
	extraRivers.addExtraRivers()

def addRivers():
	THemAddExtraRivers()
	CyPythonMgr().allowDefaultImpl()

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
		regionMasks = _THEM_REGION_RECTS.get(label, [])
		iArea = -1
		if teamAreaMap.has_key(iTeam):
			iArea = teamAreaMap[iTeam]

		for regionMask in regionMasks:
			iWestX, iSouthY, iWidth, iHeight = regionMaskManager.getRegionMaskBounds(regionMask, self.iW, self.iH)
			for x in range(iWestX, iWestX + iWidth):
				for y in range(iSouthY, iSouthY + iHeight):
					if x < 0 or x >= self.iW: continue
					if y < 0 or y >= self.iH: continue
					if not regionMaskManager.plotInRegionMask(regionMask, x, y, self.iW, self.iH): continue
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
					players.append((player.getID(), pStart.getX(), pStart.getY(), pStart.getArea()))

		for (pid, sx, sy, iStartArea) in players:
			present = {}

			for dx in range(-radius, radius + 1):
				for dy in range(-radius, radius + 1):
					nx = sx + dx
					ny = sy + dy
					if nx >= 0 and nx < self.iW and ny >= 0 and ny < self.iH:
						if plotDistance(sx, sy, nx, ny) <= radius:
							pPlot = self.map.plot(nx, ny)
							if pPlot.getArea() != iStartArea: continue
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
									if pPlot.getArea() != iStartArea: continue
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
										if pPlot.getArea() != iStartArea: continue
										if not pPlot.isWater() and not pPlot.isPeak() and not self._is_player_start_plot(pPlot, startLookup):
											if pPlot.getBonusType(-1) == -1:
												if pPlot.getFeatureType() != -1: continue
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

	def ensure_bonus_per_grid(self, bonusNames, iGridSize):
		if iGridSize <= 0:
			return

		bonusIDs = self._bonus_ids_from_names(bonusNames)
		bonusLookup = {}
		for iBonus in bonusIDs:
			bonusLookup[iBonus] = 1

		startLookup = self._start_plot_lookup()
		iBlocksChecked = 0
		iBlocksSatisfied = 0
		iPlaced = 0
		iBlocked = 0

		for xMin in range(0, self.iW, iGridSize):
			for yMin in range(0, self.iH, iGridSize):
				iBlocksChecked += 1
				xMax = xMin + iGridSize
				yMax = yMin + iGridSize
				if xMax > self.iW: xMax = self.iW
				if yMax > self.iH: yMax = self.iH

				iExisting = 0
				plots = []
				for x in range(xMin, xMax):
					for y in range(yMin, yMax):
						pPlot = self.map.plot(x, y)
						if bonusLookup.has_key(pPlot.getBonusType(-1)):
							iExisting += 1
						plots.append(pPlot)

				if iExisting > 0:
					iBlocksSatisfied += 1
					continue

				plots = self._shuffle_list(plots, "THem Map Food Plot Shuffle")
				shuffledBonusIDs = self._shuffle_list(bonusIDs, "THem Map Food Bonus Shuffle")
				bPlaced = False
				for pPlot in plots:
					if pPlot.getBonusType(-1) != -1: continue
					if pPlot.isWater() or pPlot.isPeak(): continue
					if self._is_player_start_plot(pPlot, startLookup): continue
					for iBonus in shuffledBonusIDs:
						if pPlot.canHaveBonus(iBonus, True):
							pPlot.setBonusType(iBonus)
							self._debug_sign(pPlot, "THem map food " + self._bonus_name_from_id(iBonus))
							iPlaced += 1
							bPlaced = True
							break
					if bPlaced:
						break

				if not bPlaced:
					iBlocked += 1

		print "THem map food scan: checked %d blocks, satisfied %d, placed %d, blocked %d" % (iBlocksChecked, iBlocksSatisfied, iPlaced, iBlocked)

	def _is_bfc_offset(self, dx, dy):
		if dx == 0 and dy == 0: return False
		if abs(dx) > 2 or abs(dy) > 2: return False
		if abs(dx) == 2 and abs(dy) == 2: return False
		return True

	def place_bonus_in_BFC(self, bonusNames, iTargetCount, bCheckExisting):
		if iTargetCount <= 0:
			return

		bonusIDs = self._bonus_ids_from_names(bonusNames)
		iPlains = self.gc.getInfoTypeForString("TERRAIN_PLAINS")
		iFloodplains = self.gc.getInfoTypeForString("FEATURE_FLOOD_PLAINS")

		bfcOffsets = []
		for dx in range(-2, 3):
			for dy in range(-2, 3):
				if not self._is_bfc_offset(dx, dy): continue
				bfcOffsets.append((dx, dy))

		for iPlayer in range(self.gc.getMAX_CIV_PLAYERS()):
			pPlayer = self.gc.getPlayer(iPlayer)
			if not pPlayer.isEverAlive(): continue
			pStart = pPlayer.getStartingPlot()
			if pStart is None: continue
			if pStart.isNone(): continue
			iStartArea = pStart.getArea()

			iExisting = 0
			if bCheckExisting:
				for dx, dy in bfcOffsets:
					x = pStart.getX() + dx
					y = pStart.getY() + dy
					if x < 0 or x >= self.iW: continue
					if y < 0 or y >= self.iH: continue
					pPlot = self.map.plot(x, y)
					if pPlot.getArea() != iStartArea: continue
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
						if pPlot.getArea() != iStartArea: continue
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
						if pPlot.getArea() != iStartArea: continue
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

	iTeamerBalancingOption = map.getCustomMapOption(4)
	iMapFoodOption = map.getCustomMapOption(5)
	iStartFoodOption = map.getCustomMapOption(6)
	bCustomBalancing = False
	LandFoodBonus = ["BONUS_WHEAT", "BONUS_RICE", "BONUS_CORN", "BONUS_COW", "BONUS_SHEEP", "BONUS_PIG", "BONUS_DEER", "BONUS_BANANA"]
	StartLandFoodBonus = ["BONUS_WHEAT", "BONUS_RICE", "BONUS_CORN", "BONUS_COW", "BONUS_SHEEP", "BONUS_PIG"]
	Strategics = ["BONUS_IRON", "BONUS_COPPER", "BONUS_HORSE","BONUS_COAL", "BONUS_URANIUM", "BONUS_ALUMINUM", "BONUS_OIL"]
	SemiStrategics = ["BONUS_IVORY", "BONUS_STONE", "BONUS_MARBLE"]
	PreciousMetals = ["BONUS_GOLD", "BONUS_SILVER", "BONUS_GEMS"]
	EarlyHappiness = ["BONUS_FUR", "BONUS_WINE"]
	CalendarBonus = ["BONUS_SPICES", "BONUS_SUGAR", "BONUS_DYE", "BONUS_INCENSE", "BONUS_SILK"]
	WaterBonus = ["BONUS_FISH", "BONUS_CRAB", "BONUS_CRAB", "BONUS_WHALE"]

	if bTeamPlacement and iTeamerBalancingOption == 1:
		if _resolve_team_areas():
			bCustomBalancing = True

	if bCustomBalancing:
		print "PY: Teamer balancing regional resource groups..."
		rm.swap_resources("BONUS_IVORY", None)
		rm.place_bonus_in_radius(Strategics, 7, 1, 5)

		sortedTeams = teamRegionMap.keys()
		sortedTeams.sort()
		for iTeam in sortedTeams:
			iPlayerCount = rm._get_player_count_for_team(iTeam)
			iRoundedDown = int(0.5 * iPlayerCount)
			iRoundedUp = int(0.5 * iPlayerCount + 1)
			if iRoundedDown < 1: iRoundedDown = 1

			rm.place_balanced_team_resource(iTeam, CalendarBonus, 4, iRoundedUp)
			rm.place_balanced_team_resource(iTeam, PreciousMetals, 3, iRoundedUp)
			rm.place_balanced_team_resource(iTeam, EarlyHappiness, 2, iPlayerCount)
			rm.place_balanced_team_resource(iTeam, SemiStrategics, 3, iRoundedDown, True, 4)
	else: # Default placer
		CyPythonMgr().allowDefaultImpl()
	if iMapFoodOption != 0:
		print "PY: Teamer ensuring mapwide land food bonuses..."
		rm.ensure_bonus_per_grid(LandFoodBonus, iMapFoodOption+3)
	if iStartFoodOption > 0:
		print "PY: Teamer adding starting plot food bonuses..."
		rm.place_bonus_in_BFC(StartLandFoodBonus, iStartFoodOption, True)
