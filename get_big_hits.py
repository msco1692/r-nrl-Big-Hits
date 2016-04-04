import os
import cPickle
import re
from datetime import datetime
from PIL import Image

import praw
import requests
from selenium import webdriver

from config_bot import *

# Downloads file from imgur at imageUrl and saves it locally at imageName.
# May work with other image hosting websites, would need to test.
def downloadImgurImage(imageUrl, imageName):
	response = requests.get(imageUrl)
	with open(imageName, 'wb') as fo:
	    for chunk in response.iter_content(4096):
	        fo.write(chunk)

# Takes a screenshot of given element and saves it locally at imageName.
# Elements are obtained using selenium.webdriver functions 
def screenCapElement(element, imageName, offset = 350):

	bottom = None
	if type(element) is list:
		bottom = element[-1].location['y']
		element = element[0]

	# Find location of element
	location = element.location
	size = element.size
	
	# Generate bounding box around element
	left = location['x']
	top = location['y']
	# Reddit elements of interest go to the far right of screen, and are overlaid with ads. Offset of 325 required, but can probably be increased for comments. Titles often take up the full space.
	right = location['x'] + size['width'] - offset 

	if bottom is None:
		bottom = location['y'] + size['height']


	# Take, crop and save screenshot.
	fox.save_screenshot(imageName)
	im = Image.open(imageName)
	im = im.crop((left, top, right, bottom))
	im.save(imageName)
	
# Generates a list of parent comments from the provided message. The number of comments included can be capped at maxPostCount.
def getParentCommentList(msg, maxPostCount = 3):
	post_list = [msg]
	for _ in range(maxPostCount):
		post = r.get_info(thing_id = post_list[-1].parent_id)
		# If a top level-comment has been reached the parent will be a Submission not a Comment
		if isinstance(post, praw.objects.Comment):
			post_list.append(post)
	return post_list

# Returns element corresponding to comment with ID given by msgID
def getCommentElement(msgID):
	element = fox.find_element_by_id(msgID)
	return element

# Returns element corresponding to title and thumbnail in reddit post.
def getTitleElement():
	# There is surely a better way to access this element, but so far this seems to be the easiest way.
	element = fox.find_element_by_class_name("sitetable")
	return element

# Specifies current NRL Round
ROUND_NUM 		= 5
# Set TESTING_FLAG to stop messages from being marked as read and to store images in local Testing folder.
TESTING_FLAG 	= False

NO_FLY_LIST = []
MIN_USER_AGE = 0
if __name__ == '__main__':

	# Login as nrl_big_hits_bot
	user_agent = ("r/NRL Big Hit Tracker 1.01: made by u/stua8992")
	r = praw.Reddit(user_agent = user_agent)
	r.login(REDDIT_USERNAME, REDDIT_PASS, disable_warning = True)

	# Move to directory to save images
	if TESTING_FLAG == False:
		if not os.path.isdir('Round ' + str(ROUND_NUM)):
			os.mkdir('Round ' + str(ROUND_NUM))		
		os.chdir('Round ' + str(ROUND_NUM))
	else:
		if not os.path.isdir('Testing'):
			os.mkdir('Testing')		
		os.chdir('Testing')

	# Create firefox instance
	fox = webdriver.Firefox()

	# Loop through all messages sent to nrl_big_hits_bot
	for msg in r.get_unread(limit = None):
		if msg.was_comment:		

			# Basic stuff to stop abuse
			user = msg.author
			if user in NO_FLY_LIST:
				msg.mark_as_read()
				continue

			user_age = (datetime.now() - datetime.fromtimestamp(user.created_utc)).days
			if user_age < 0:
				msg.mark_as_read()
				continue

			# Open context of message (msg.context only contains the suffix of the url)
			fox.get("http://www.reddit.com" + msg.context)

			parent_list = getParentCommentList(msg)

			# Screencap naming convention: 
				# title: submissionTime
				# submission image: submissionTime_0
				# posts: submissionTime_parentTime
				# images from posts: submissionTime_parentTime_imageNumber
			# When sorting screencap folder all images will be organised by thread in alphabetical order, with title, submission image, and posts interlaced with relevant images

			submissionTime = str(int(msg.submission.created_utc))
			commentTime = str(int(parent_list[1].created_utc))
			# Get title screencap if this hasn't been done before
			if not os.path.isfile(submissionTime + ".png"):
				titleName = submissionTime + ".png"
				screenCapElement(element = getTitleElement(), imageName = titleName, offset = 325)

			# Get submission image if this hasn't been done before and it exists
			if not os.path.isfile(submissionTime + "_0.png"):
				if 'imgur' in msg.submission.domain:
					imageName = submissionTime + "_0.png"
					downloadImgurImage(imageUrl = msg.submission.url, imageName = imageName)

			# Screencap parent comments
			commentName = submissionTime + "_" + commentTime + ".png"
			screenCapElement(element = [getCommentElement("thing_t1_" + parent_list[-1].id), getCommentElement("thing_t1_" + parent_list[0].id)], imageName = commentName)

			# Extract images linked within the posts
			for post in parent_list[::-1]:
				imageNumber = 1
				imgurRefs = re.findall(r"<a href=.*?imgur.*?>", post.body_html)
				for imgurRef in imgurRefs:
					url = re.findall(r'"(.*?)"', imgurRef)[0]
					imageName = submissionTime + "_" + str(int(post.created_utc)) + "_" + str(imageNumber) + ".png"
					imageNumber += 1
					downloadImgurImage(imageUrl = url, imageName = imageName)				

		if TESTING_FLAG == False:
			msg.mark_as_read()

	# Close firefox instance
	fox.quit()
