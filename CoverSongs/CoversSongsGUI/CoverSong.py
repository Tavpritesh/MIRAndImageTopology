#Holds all of the saved info about the cover song:
#'LEigs', 'IsRips', 'IsMorse', 'Dists', 'bts', 'SampleDelays', 'Fs', 'TimeLoopHists', 'MFCCs', 'PointClouds'

#Holds a flattened version of PointClouds in a vertex buffer with
#pointers from times within beats to locations within the vertex buffer

#Provides classes to select and draw information about each beat
#in the cover song

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.arrays import vbo

import matplotlib
matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure
import wx

import wx
from wx import glcanvas
import numpy as np
import scipy.io as sio
from pylab import cm

import subprocess

#Constants
DGM1EXTENT = 2.0
RANGE0DPERS = 10

def doCenteringAndPCA(X, ncomponents = 3):
	#TODO: Add code to do centering
	X = X - np.tile(np.mean(X, 0), (X.shape[0], 1))
	X[np.isinf(X)] = 0
	X[np.isnan(X)] = 0
	D = (X.T).dot(X)
	(lam, eigvecs) = np.linalg.eig(D)
	lam = np.abs(lam)
	varExplained = np.sum(lam[0:ncomponents])/np.sum(lam)
	#print "2D Var Explained: %g"%(np.sum(lam[0:2])/np.sum(lam))
	eigvecs = eigvecs[:, 0:ncomponents]
	Y = X.dot(eigvecs)
	return (Y, varExplained)

#Stores vertex buffers and other information for a cover song
class CoverSong(object):
	def __init__(self, matfilename, soundfilename):
		self.matfilename = matfilename
		self.soundfilename = soundfilename
		
		#Step 1: Load in precomputed beat information
		self.title = matfilename.split('.mat')[0]
		X = sio.loadmat(matfilename)
		self.Fs = float(X['Fs'].flatten()[0])
		self.TimeLoopHists = X['TimeLoopHists'].flatten() #Cell Array
		self.bts = X['bts'].flatten() #1D Matrix
		self.LEigs = X['LEigs'].flatten() #Cell Array
		self.LEigs = X['LEigs'].flatten() #2D Matrix
		self.SampleDelays = X['SampleDelays'].flatten()/self.Fs #Cell array
		self.IsRips = X['IsRips'].flatten() #Cell Array
		self.IsMorse = X['IsMorse'].flatten() #Cell Array
		self.MFCCs = X['MFCCs'] #2D Matrix
		self.PointClouds = X['PointClouds'].flatten()
		self.Dists = X['Dists']
		self.SampleStartTimes = np.zeros(self.SampleDelays.shape[0])
		self.BeatStartIdx = np.zeros(self.SampleDelays.shape[0], dtype='int32')
		
		for i in range(self.SampleDelays.shape[0]):
			self.SampleDelays[i] = self.SampleDelays[i].flatten()
			self.SampleStartTimes[i] = self.SampleDelays[i][0]
		
		#Sort the DGMs0 by persistence since the birth time doesn't
		#really matter
		IsMorse = []
		for i in range(self.IsMorse.shape[0]):
			P = self.IsMorse[1, :] - self.IsMorse[0, :]
			P = np.sort(P)
			P = P[::-1]
			IsMorse.append(P)
		
		#Step 2: Setup a vertex buffer for this song
		N = self.PointClouds.shape[0]
		if N == 0:
			return
		cmConvert = cm.get_cmap('jet')
		print "Doing PCA on all windows..."
		(self.Y, varExplained) = doCenteringAndPCA(self.PointClouds[0])
		self.YColors = cmConvert(np.linspace(0, 1, self.Y.shape[0]))[:, 0:3]
		
		for i in range(1, self.PointClouds.shape[0]):
			(Yi, varExplained) = doCenteringAndPCA(self.PointClouds[i])
			self.Y = np.concatenate((self.Y, Yi), 0)
			Colorsi = cmConvert(np.linspace(0, 1, self.PointClouds[i].shape[0]))[:, 0:3]
			self.YColors = np.concatenate((self.YColors, Colorsi), 0)
			self.BeatStartIdx[i] = self.BeatStartIdx[i-1] + Colorsi.shape[0]
		print "Finished PCA"
		
		self.YVBO = vbo.VBO(np.array(self.Y, dtype='float32'))
		self.YColorsVBO = vbo.VBO(np.array(self.YColors, dtype='float32'))
		#TODO: Free vertex buffers when this is no longer used?
		
		#Step 3: Load in the song waveform
		name, ext = os.path.splitext(soundfilename)
		#TODO: Replace this ugly subprocess call with some Python
		#library that understand other files
		if ext.upper() != ".WAV":
			if "temp.wav" in set(os.listdir('.')):
				os.remove("temp.wav")
			subprocess.call(["avconv", "-i", soundfilename, "temp.wav"])
			self.Fs, self.waveform = wavfile.read("temp.wav")
		else:
			self.Fs, self.waveform = wavfile.read(soundfilename)
		

class CoverSongFilesDialog(wx.Dialog):
	def __init__(self, *args, **kw):
		super(CoverSongFilesDialog, self).__init__(*args, **kw)
		#Remember parameters from last time
		self.matfilename = None
		self.soundfilename = None
		self.InitUI()
		self.SetSize((250, 200))
		self.SetTitle("Load Cover Song Data")

	def InitUI(self):
		vbox = wx.BoxSizer(wx.VERTICAL)
		
		hbox1 = wx.BoxSizer(wx.HORIZONTAL)
		matfileButton = wx.Button(self, label="Choose Mat File")
		self.matfileTxt = wx.TextCtrl(self)
		hbox1.Add(matfileButton)
		hbox1.Add(self.matfileTxt, flag=wx.RIGHT, border=5)

		hbox2 = wx.BoxSizer(wx.HORIZONTAL)
		soundfileButton = wx.Button(self, label='Choose Sound File')
		self.soundfileTxt = wx.TextCtrl(self)
		hbox2.Add(soundfileButton)
		hbox2.Add(self.soundfileTxt, flag=wx.RIGHT, border=5)

		hboxexit = wx.BoxSizer(wx.HORIZONTAL)
		okButton = wx.Button(self, label='Ok')
		closeButton = wx.Button(self, label='Close')
		hboxexit.Add(okButton)
		hboxexit.Add(closeButton, flag=wx.LEFT, border=5)

		vbox.Add(hbox1, 
		flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
		vbox.Add(hbox2, 
		flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
		vbox.Add(hboxexit, 
		flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)

		self.SetSizer(vbox)

		okButton.Bind(wx.EVT_BUTTON, self.OnClose)
		closeButton.Bind(wx.EVT_BUTTON, self.OnClose)
		matfileButton.Bind(wx.EVT_BUTTON, self.OnChooseMatfile)
		soundfileButton.Bind(wx.EVT_BUTTON, self.OnChooseSoundfile)
		

	def OnChooseMatfile(self, evt):
		dlg = wx.FileDialog(self, "Choose a file", ".", "", "*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetFilename()
			dirname = dlg.GetDirectory()
			filepath = os.path.join(dirname, filename)
			self.matfilename = filepath
			self.matfileTxt.SetValue(filepath)
		dlg.Destroy()
		return

	def OnChooseSoundfile(self, evt):
		dlg = wx.FileDialog(self, "Choose a file", ".", "", "*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetFilename()
			dirname = dlg.GetDirectory()
			filepath = os.path.join(dirname, filename)
			self.soundfilename = filepath
			self.soundfileTxt.SetValue(filepath)
		dlg.Destroy()
		return

	def OnClose(self, e):
		self.Destroy()

class CoverSongBeatPlots(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent)
		self.figure = Figure()
		
		self.FigDists = self.figure.add_subplot(222)
		self.DGM1 = self.figure.add_subplot(223)
		self.DGM0 = self.figure.add_subplot(224)
		
		self.canvas = FigureCanvas(self, -1, self.figure)
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP)
		self.SetSizer(self.sizer)
		self.Fit()
		self.coverSong = None
		self.currBeat = 0
		self.draw()

	def updateCoverSong(self, newCoverSong):
		self.coverSong = newCoverSong
		self.draw()
	
	def updateBeat(self, newBeat):
		self.currBeat = newBeat
		self.draw()

	def draw(self):
		if self.coverSong:
			if self.currBeat >= len(self.bts):
				return
			I1 = self.coverSong.IsRips[self.currBeat]
			I0 = self.coverSong.IsMorse[self.currBeat]
			D = self.coverSong.Dists[self.currBeat, :]
			#Bar plot distances
			self.FigDists.bar([0, 1], D, color='r')
			self.FigDists.xticks([0.5, 1.5], ('Euc', 'Geo'))
			self.FigDists.ylim([0, RANGE0DPERS])
			#TODO: Also plot letter here
			self.FigDists.title('Distances')
			
			#Plot DGM1
			if I1.shape[0] > 0:
				self.DGM1.plot(I1[:, 0], I1[:, 1], 'b.')
				self.DGM1.hold(True)
				maxVal = max(np.max(I1) + 0.2, DGM1EXTENT)
				self.DGM1.plot([0, maxVal], [0, maxVal], 'r')
			else:
				self.DGM1.plot([0, DGM1EXTENT], [0, DGM1EXTENT], 'r')
			self.DGM1.title('DGM1')
			#Plot DGM0
			if len(I0) > 0:
				self.DGM0.plot(I0)
				self.DGM0.xlim([0, 60])
				self.DGM0.ylim([0, 1])
				self.DGM0.hold(True)
			self.DGM0.title('DGM0')

class CoverSongWaveformPlots(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent)
		self.figure = Figure()
		self.axes = self.figure.add_subplot(111)
		self.canvas = FigureCanvas(self, -1, self.figure)
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
		self.SetSizer(self.sizer)
		self.Fit()
		self.coverSong = None
		self.currPos = 0 #Current position in seconds
		self.draw()

	def updateCoverSong(self, newCoverSong):
		self.coverSong = newCoverSong
		if self.coverSong:
			self.y0 = np.min(self.coverSong.waveform)
			self.y1 = np.max(self.coverSong.waveform)
			self.t = np.arange(0, self.coverSong.waveform.shape[0])	
			self.draw()

	def updatePos(self, newPos):
		self.currPos = newPos
		self.draw()

	def draw(self):
		if self.coverSong:
			if self.currBeat >= len(self.bts):
				return
			#Plot waveform
			self.axes.plot(t, coverSong.waveform, 'b')
			self.axes.hold(True)
			#Plot current marker in song
			self.axes.plot(np.array([self.currPos, self.currPos]), np.array([self.y0, self.y1]), 'g')		

if __name__ == '__main__':
	c = CoverSong('CaliforniaLove_2.mat', 'CaliforniaLove.mp3')
