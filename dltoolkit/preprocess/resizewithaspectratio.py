"""Resize an image while maintaining its aspect ratio, cropping the image if/when required

Code is based on the excellent book "Deep Learning for Computer Vision" by PyImageSearch available on:
https://www.pyimagesearch.com/deep-learning-computer-vision-python-book/
"""
import cv2
import imutils


class ResizeWithAspectRatioPreprocessor:
    def __init__(self, width, height, inter=cv2.INTER_AREA):
        """
        Initialise the class
        :param width: desired image width
        :param height: desired image height
        :param inter: desired interpolation method
        """
        self.width = width
        self.height = height
        self.inter = inter

    def preprocess(self, image):
        """
        Perform the resize operation
        :param image: image data
        :return: resized image data
        """
        (height, width) = image.shape[:2]
        crop_width = 0
        crop_height = 0

        # Determine whether to crop the height or width
        if width < height:
            image = imutils.resize(image, width=self.width, inter=self.inter)
            crop_height = int((image.shape[0] - self.height)/2.0)
        else:
            image = imutils.resize(image, height=self.height, inter=self.inter)
            crop_width = int((image.shape[1] - self.width)/2.0)

        # Crop the image
        (height, width) = image.shape[:2]
        image = image[crop_height:height - crop_height, crop_width:width - crop_width]

        # Finally resize
        return cv2.resize(image, (self.width, self.height), interpolation=self.inter)
