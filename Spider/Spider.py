import sys
import urllib.request
import logging
import re
import os
from functools import reduce
from PIL import Image

class Spider:
	"""Base Spider"""
	imageTotal = 0	
	def __init__(self):
		self.articles = []
	def ReadRule(self, rule):
		if rule == None \
		or not isinstance(rule, dict) \
		or not 'rule' in rule \
		or not 'name' in rule \
		or not 'url' in rule['rule'] \
		or not 'reAbstract' in rule['rule'] \
		or not 'reArticle' in rule['rule'] \
		or not 'reImage' in rule['rule'] \
		or not 'regionId' in rule['rule'] \
		or not 'spiderName' in rule['rule']:
			return False
		self.sourceName = rule['name']
		self.url = rule['rule']['url']
		self.reAbstract = rule['rule']['reAbstract']
		self.reArticle = rule['rule']['reArticle']
		self.reImage = rule['rule']['reImage']
		self.regionId = int(rule['rule']['regionId'])
		self.spiderName = rule['rule']['spiderName']
		self.sourceId = (0 if not 'sourceId' in rule else int(rule['sourceId']) )
		self.temp = sys.path[0] + '\\temp\\'
		self.headers = [('User-Agent','Chrome/23.0.1271'),
						# ('Accept','text/html;q=0.9,*/*;q=0.8'),
						# ('Accept-Charset','ISO-8859-1,utf-8;q=0.7,*;q=0.3'),
						# ('Accept-Encoding','gzip'),
						# ('Referer', 'None'),
						('Connection','close')]
		opener = urllib.request.build_opener()
		opener.addheaders = self.headers
		urllib.request.install_opener(opener)
		self.reCss = r'class=".+?"'
		self.reHerf = r'<[aA][^<>]+?href="(.+?)"[^<>]*?>(.+?)</[aA]>'
		self.reBlank = r'&ensp;|&emsp;|&nbsp;|\n|\t;'
		self.reStyle = r'style="[^"]*?"'
		return True
	def CatchArticles(self):
		return []
	def DownLoadHtml(self, url, logFormat, encoding = 'utf-8'):
		html = ''
		try:
			html = urllib.request.urlopen(url).read().decode(encoding).strip()
			# logging.debug(html)
		except Exception as e:
			logging.warn(logFormat.format(url, str(e)))
			return None
		return html
	def DownLoadImage(self, url, logFormat):
		image = dict(imageUrl = url)
		fileName = url[url.rfind('/') + 1 :]
		iDot = fileName.rfind('.')
		imageFormat = fileName[iDot:] if iDot > 0 else '.jpg'
		imageLocal = self.temp + str(Spider.imageTotal) + imageFormat
		try:
			urllib.request.urlretrieve(url, imageLocal)
		except Exception as e:
			logging.warn(logFormat.format(url, str(e)))
			return None
		image['imageLocal'] = imageLocal
		Spider.imageTotal += 1
		ConvertImageToJpg(image)
		return image
	def ReplaceArticleImages(self):
		if not self.articles \
		or len(self.articles) == 0:
			return False
		recImage = re.compile(self.reImage, re.DOTALL)
		images = list(map(lambda article: article['images'], self.articles))
		# logging.debug(images)
		global imagesCache
		imagesCache = list(reduce(
							lambda images0, images1: images0 + images1,
							images));
		# logging.debug(imagesCache)
		for article in self.articles:
			if not 'content' in article:
				continue
			article['content'] = recImage.sub(ReplaceImage, article['content'])
		#ExtraReplace
		self.ClearArticles()
		return True
	def CacheArticle(self, article, content, images, logFormat):
		article['content'] = content
		article['images'] = images
		article['regionId'] = self.regionId
		article['author'] = self.spiderName
		article['sourceName'] = self.sourceName
		article['sourceId'] = self.sourceId
		logging.info(logFormat.format(article['url']))
		self.articles.append(article)
	def ClearArticles(self):
		if not self.articles \
		or len(self.articles) == 0:
			return False
		recCss = re.compile(self.reCss, re.DOTALL)
		recHerf = re.compile(self.reHerf, re.DOTALL)
		recBlank = re.compile(self.reBlank, re.DOTALL)
		recStyle = re.compile(self.reStyle, re.DOTALL)
		for article in self.articles:
			if not 'content' in article:
				continue
			article['content'] = recCss.sub(ClearExternalCss, article['content'])
			article['content'] = recHerf.sub(ClearExternalHerf, article['content'])
			article['content'] = recBlank.sub(ClearExternalBlank, article['content'])
			article['content'] = recStyle.sub(ClearExternalStyle, article['content'])
		return True
	def ClearTempImages(self):
		for root, dirs, files in os.walk(self.temp, topdown = True):
			for name in files:
				os.remove(os.path.join(root, name))
		Spider.imageTotal = 0

imagesCache = []
"""Image Infos Cache"""

def ReplaceImage(matchobj):
	"""Replace Remote Images With Dumpped Images"""
	dumpImage = r'<img src="{0}"/>'
	remoteImage = matchobj.group(1)
	global imagesCache
	imageInfo = list(filter(
		lambda info: 'imageUrl' in info \
			and 'imageDumpUrl' in info \
			and info['imageUrl'].endswith(remoteImage[remoteImage.find('/') + 1:]),
		imagesCache
	))
	# logging.debug(imageInfo)
	if len(imageInfo) > 0:
		return dumpImage.format(imageInfo[0]['imageDumpUrl'])
	else:
		return dumpImage.format(matchobj.group(1))

def ClearExternalCss(matchobj):
	"""Clear External Css In Article Content"""
	return ''

def ClearExternalHerf(matchobj):
	"""Clear External Herf In Article Content"""
	herfText = matchobj.group(2)
	# logging.debug(herfText)
	return herfText

def ClearExternalBlank(matchobj):
	"""Clear External Blank Character In Article Content"""
	return ''

def ClearExternalStyle(matchobj):
	"""Clear External Style In Article Content"""
	return ''

def ComposeUrl(currentUrl, relativeUrl):
	"""Assemble  Relative Url And Current Url Into Absolute Url"""
	head = relativeUrl[0]
	localSecs = currentUrl.split('/')
	absoluteUrl = relativeUrl
	if head == '/':
		absoluteUrl = '/'.join(localSecs[0:3]) + relativeUrl
	elif head == '.':
		index = relativeUrl.find('/')
		if len(list(filter(lambda c : c == '.', relativeUrl[0:index]))) == index:
			absoluteUrl = '/'.join(localSecs[0:len(localSecs) - index]) + relativeUrl[index:]
	elif not relativeUrl.startswith('http://'):
		absoluteUrl = '/'.join(localSecs[0:len(localSecs) - 1]) + '/' + relativeUrl
	# logging.debug(absoluteUrl)
	return absoluteUrl

def ConvertImageToJpg(image):
	"""Convert PNG Or BMP Format Image To JPG Format Image"""
	if not image \
	or not isinstance(image, dict) \
	or not 'imageLocal' in image:
		return False
	dotIndex = image['imageLocal'].rfind('.')
	if dotIndex < 0 \
	or dotIndex >= len(image['imageLocal']):
		return False
	imageFormat = image['imageLocal'][dotIndex + 1:].lower()
	if imageFormat in ['jpg', 'jpeg']:
		return True
	elif imageFormat in ['png', 'bmp']:
		im = Image.open(image['imageLocal'])			
		try:
			imageNew = image['imageLocal'][0:dotIndex + 1] + 'jpg'
			if im.mode != 'RGB':
				im = im.convert('RGB')
			im.save(imageNew)
			image['imageLocal'] = imageNew
			return True
		except Exception as e:
			logging.warn('图片{0}，格式转化失败，异常为{1}'.format(image['imageLocal'], str(e)))
			return False
	else:
		return False