import wx
from wx import glcanvas

from Cameras3D import *
from sys import exit, argv
import numpy as np
import scipy.io as sio
from scipy.io import wavfile
import scipy.spatial as spatial
import scipy.linalg
from pylab import cm
import os
import math
import time

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.arrays import vbo

from CoverSong import *

import pygame

DEFAULT_SIZE = wx.Size(1200, 800)
DEFAULT_POS = wx.Point(10, 10)

class LoopDittyCanvas(glcanvas.GLCanvas):
	def __init__(self, parent):
		attribs = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24)
		glcanvas.GLCanvas.__init__(self, parent, -1, attribList = attribs)	
		self.context = glcanvas.GLContext(self)
		
		self.parent = parent
		#Camera state variables
		self.size = self.GetClientSize()
		self.camera = MousePolarCamera(self.size.width, self.size.height)
		self.Fs = 22050
		
		#Main state variables
		self.MousePos = [0, 0]
		self.initiallyResized = False
		
		self.bbox = np.array([ [1, 1, 1], [-1, -1, -1] ])
		
		#Cover song info
		self.coverSong1 = None
		self.coverSong2 = None
		self.selectedCover = None
		
		#Point cloud and playing information
		self.DrawEdges = True
		
		self.GLinitialized = False
		#GL-related events
		wx.EVT_ERASE_BACKGROUND(self, self.processEraseBackgroundEvent)
		wx.EVT_SIZE(self, self.processSizeEvent)
		wx.EVT_PAINT(self, self.processPaintEvent)
		#Mouse Events
		wx.EVT_LEFT_DOWN(self, self.MouseDown)
		wx.EVT_LEFT_UP(self, self.MouseUp)
		wx.EVT_RIGHT_DOWN(self, self.MouseDown)
		wx.EVT_RIGHT_UP(self, self.MouseUp)
		wx.EVT_MIDDLE_DOWN(self, self.MouseDown)
		wx.EVT_MIDDLE_UP(self, self.MouseUp)
		wx.EVT_MOTION(self, self.MouseMotion)		
		#self.initGL()
	
	
	def processEraseBackgroundEvent(self, event): pass #avoid flashing on MSW.

	def processSizeEvent(self, event):
		self.size = self.GetClientSize()
		self.SetCurrent(self.context)
		glViewport(0, 0, self.size.width, self.size.height)
		if not self.initiallyResized:
			#The canvas gets resized once on initialization so the camera needs
			#to be updated accordingly at that point
			self.camera = MousePolarCamera(self.size.width, self.size.height)
			self.camera.centerOnBBox(self.bbox, math.pi/2, math.pi/2)
			self.initiallyResized = True

	def processPaintEvent(self, event):
		dc = wx.PaintDC(self)
		self.SetCurrent(self.context)
		if not self.GLinitialized:
			self.initGL()
			self.GLinitialized = True
		self.repaint()

	def repaint(self):
		#Set up projection matrix
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		farDist = 3*np.sqrt(np.sum( (self.camera.eye - np.mean(self.bbox, 0))**2 ))
		nearDist = farDist/50.0
		gluPerspective(180.0*self.camera.yfov/np.pi, float(self.size.x)/self.size.y, nearDist, farDist)
		
		#Set up modelview matrix
		self.camera.gotoCameraFrame()	
		glClearColor(0.0, 0.0, 0.0, 0.0)
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		
		if self.selectedCover:
			glDisable(GL_LIGHTING)
			glColor3f(1, 0, 0)
			glPointSize(3)
			currBeat = self.selectedCover.currBeat
			StartPoint = self.selectedCover.BeatStartIdx[currBeat]
			#Find endpoint based on how long sound has been playing
			startTime = self.selectedCover.SampleDelays[currBeat][0] 
			EndTime = startTime + float(pygame.mixer.music.get_pos()) / 1000.0
			EndPoint = StartPoint
			i = 0
			while self.selectedCover.SampleDelays[currBeat][i] < EndTime:
				i = i+1
				EndPoint = EndPoint + 1
				if i >= len(self.selectedCover.SampleDelays[currBeat]) - 1:
					pygame.mixer.music.stop()
					break
			
			#print "startTime = %g, EndTime = %g, StartPoint = %i, EndPoint = %i"%(startTime, EndTime, StartPoint, EndPoint)
			
			self.selectedCover.YVBO.bind()
			glEnableClientState(GL_VERTEX_ARRAY)
			glVertexPointerf( self.selectedCover.YVBO )
			
			self.selectedCover.YColorsVBO.bind()
			glEnableClientState(GL_COLOR_ARRAY)
			glColorPointer(3, GL_FLOAT, 0, self.selectedCover.YColorsVBO)
			
			if self.DrawEdges:
				glDrawArrays(GL_LINES, StartPoint, EndPoint - StartPoint)
				glDrawArrays(GL_LINES, StartPoint+1, EndPoint - StartPoint)
			glDrawArrays(GL_POINTS, StartPoint, EndPoint - StartPoint + 1)
			self.selectedCover.YVBO.unbind()
			self.selectedCover.YColorsVBO.unbind()
			glDisableClientState(GL_VERTEX_ARRAY)
			glDisableClientState(GL_COLOR_ARRAY)
		self.SwapBuffers()
		self.Refresh()
	
	def initGL(self):		
		glutInit('')
		glEnable(GL_NORMALIZE)
		glEnable(GL_DEPTH_TEST)

	def handleMouseStuff(self, x, y):
		#Invert y from what the window manager says
		y = self.size.height - y
		self.MousePos = [x, y]

	def MouseDown(self, evt):
		x, y = evt.GetPosition()
		self.CaptureMouse()
		self.handleMouseStuff(x, y)
		self.Refresh()
	
	def MouseUp(self, evt):
		x, y = evt.GetPosition()
		self.handleMouseStuff(x, y)
		self.ReleaseMouse()
		self.Refresh()

	def MouseMotion(self, evt):
		x, y = evt.GetPosition()
		[lastX, lastY] = self.MousePos
		self.handleMouseStuff(x, y)
		dX = self.MousePos[0] - lastX
		dY = self.MousePos[1] - lastY
		if evt.Dragging():
			if evt.MiddleIsDown():
				self.camera.translate(dX, dY)
			elif evt.RightIsDown():
				self.camera.zoom(-dY)#Want to zoom in as the mouse goes up
			elif evt.LeftIsDown():
				self.camera.orbitLeftRight(dX)
				self.camera.orbitUpDown(dY)
		self.Refresh()


class CoverSongsFrame(wx.Frame):
	(ID_LOADCOVERSONG1, ID_LOADCOVERSONG2, ID_SAVESCREENSHOT) = (1, 2, 3)

	def __init__(self, parent, id, title, pos=DEFAULT_POS, size=DEFAULT_SIZE, style=wx.DEFAULT_FRAME_STYLE, name = 'GLWindow'):
		style = style | wx.NO_FULL_REPAINT_ON_RESIZE
		super(CoverSongsFrame, self).__init__(parent, id, title, pos, size, style, name)
		#Initialize the menu
		self.CreateStatusBar()
		
		#Sound variables
		self.soundSamples = np.array([])
		self.Fs = 22050
		self.Playing = True
		
		self.size = size
		self.pos = pos
		
		filemenu = wx.Menu()
		menuLoadCoverSong1 = filemenu.Append(CoverSongsFrame.ID_LOADCOVERSONG1, "&Load Cover Song 1","Load Cover Song 1")
		self.Bind(wx.EVT_MENU, self.OnLoadCoverSong1, menuLoadCoverSong1)
		menuLoadCoverSong2 = filemenu.Append(CoverSongsFrame.ID_LOADCOVERSONG2, "&Load Cover Song 2","Load Cover Song 2")
		self.Bind(wx.EVT_MENU, self.OnLoadCoverSong2, menuLoadCoverSong2)
		menuSaveScreenshot = filemenu.Append(CoverSongsFrame.ID_SAVESCREENSHOT, "&Save Screenshot", "Save a screenshot of the GL Canvas")		
		
		# Creating the menubar.
		menuBar = wx.MenuBar()
		menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
		self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
		
		#Vertical Buttons at top
		chooseBeatButtons = wx.BoxSizer(wx.HORIZONTAL)
		backButton = wx.Button(self, label = '<== BACK')
		playButton = wx.Button(self, label = 'PLAY')
		nextButton = wx.Button(self, label = 'NEXT ==>')
		chooseBeatButtons.Add(backButton)
		chooseBeatButtons.Add(playButton)
		chooseBeatButtons.Add(nextButton)
		backButton.Bind(wx.EVT_BUTTON, self.OnBackButton)
		playButton.Bind(wx.EVT_BUTTON, self.OnPlayButton)
		nextButton.Bind(wx.EVT_BUTTON, self.OnNextButton)
		
		#GLCanvas and beat plots stuff
		BeatPlotsRow = wx.BoxSizer(wx.HORIZONTAL)
		self.glcanvas = LoopDittyCanvas(self)
		BeatPlotsRow.Add(self.glcanvas, 1, wx.LEFT | wx.TOP | wx.GROW)
		#self.beatPlotsFrame = wx.Frame(self, title='Beat Plots')
		self.beatPlots = CoverSongBeatPlots(self)
		BeatPlotsRow.Add(self.beatPlots, 0, wx.RIGHT)
		
		#Waveform Plots
		self.waveform1 = CoverSongWaveformPlots(self)
		self.waveform2 = CoverSongWaveformPlots(self)
		
		#Add everything to a vertical box sizer	
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(chooseBeatButtons, 0, wx.EXPAND)
		self.sizer.Add(BeatPlotsRow, 0, wx.EXPAND)
		self.sizer.Add(self.waveform1, 0, wx.EXPAND)
		self.sizer.Add(self.waveform2, 0, wx.EXPAND)
		
		self.SetSizer(self.sizer)
		self.Layout()
		self.Show()

	def OnLoadCoverSong1(self, evt):
		dlg = CoverSongFilesDialog(self)
		dlg.ShowModal()
		dlg.Destroy()
		if dlg.matfilename and dlg.soundfilename:
			self.glcanvas.coverSong1 = CoverSong(dlg.matfilename, dlg.soundfilename)
			#self.waveform1.updateCoverSong(self.glcanvas.coverSong1)
			self.glcanvas.selectedCover = self.glcanvas.coverSong1
			self.beatPlots.updateCoverSong(self.glcanvas.selectedCover)
			pygame.mixer.init(frequency=self.glcanvas.selectedCover.Fs)
			pygame.mixer.music.load(self.glcanvas.selectedCover.soundfilename)

	def OnLoadCoverSong2(self, evt):
		dlg = CoverSongFilesDialog(self)
		dlg.ShowModal()
		dlg.Destroy()
		if dlg.matfilename and dlg.soundfilename:
			self.glcanvas.coverSong2 = CoverSong(dlg.matfilename, dlg.soundfilename)
			#self.waveform2.updateCoverSong(self.glcanvas.coverSong2)
			self.glcanvas.selectedCover = self.glcanvas.coverSong2
			self.beatPlots.updateCoverSong(self.glcanvas.selectedCover)
			pygame.mixer.init(frequency=self.glcanvas.selectedCover.Fs)
			pygame.mixer.music.load(self.glcanvas.selectedCover.soundfilename)
	
	def OnBackButton(self, evt):
		if self.glcanvas.selectedCover:
			self.glcanvas.selectedCover.changeBeat(-1)
			self.beatPlots.draw() #Update the beat plots
			self.glcanvas.startTime = self.glcanvas.selectedCover.SampleStartTimes[self.glcanvas.selectedCover.currBeat]
			pygame.mixer.music.play(0, self.glcanvas.startTime)
			self.glcanvas.Refresh()

	def OnPlayButton(self, evt):
		if self.glcanvas.selectedCover:
			self.glcanvas.startTime = self.glcanvas.selectedCover.SampleStartTimes[self.glcanvas.selectedCover.currBeat]
			pygame.mixer.music.play(0, self.glcanvas.startTime)
			self.glcanvas.Refresh()

	def OnNextButton(self, evt):
		if self.glcanvas.selectedCover:
			self.glcanvas.selectedCover.changeBeat(1)
			self.beatPlots.draw() #Update the beat plots
			self.glcanvas.startTime = self.glcanvas.selectedCover.SampleStartTimes[self.glcanvas.selectedCover.currBeat]
			pygame.mixer.music.play(0, self.glcanvas.startTime)
			self.glcanvas.Refresh()

if __name__ == "__main__":
	pygame.init()
	app = wx.App()
	frame = CoverSongsFrame(None, -1, 'Cover Songs GUI')
	frame.Show(True)
	app.MainLoop()
	app.Destroy()
