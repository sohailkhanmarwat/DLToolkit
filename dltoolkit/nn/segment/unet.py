"""Implementation of U-Net using Keras"""
from keras.layers import Input, Conv2D, MaxPooling2D, concatenate, UpSampling2D, Cropping2D,\
    Dropout, Activation, Reshape, Conv2DTranspose, BatchNormalization
from keras.models import Model
from keras.initializers import RandomNormal
from keras import backend as K
from dltoolkit.nn.base_nn import BaseNN

import math

class UNet_NN(BaseNN):
    _title = "UNet"

    def __init__(self, img_height, img_width, img_channels, num_classes, dropout_rate=0.0):
        self._img_width = img_width
        self._img_height = img_height
        self._img_channels = img_channels
        self._dropout_rate = dropout_rate
        self._num_classes = num_classes

    def build_model_DRIVE(self):
        """Build the U-Net architecture used for the DRIVE retinal fundus images data set"""
        self._title = "UNet_DRIVE"

        # Set the input shape
        if K.image_data_format() == "channels_first":
            input_shape = (self._img_channels, self._img_width, self._img_height)
        else:
            input_shape = (self._img_height, self._img_width, self._img_channels)
            print("CHANNELS LAST")

        inputs = Input(input_shape)

        # Contracting path
        conv_contr1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(inputs)
        conv_contr1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(conv_contr1)
        pool_contr1 = MaxPooling2D(pool_size=(2, 2))(conv_contr1)

        conv_contr2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(pool_contr1)
        conv_contr2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(conv_contr2)
        pool_contr2 = MaxPooling2D(pool_size=(2, 2))(conv_contr2)

        # "Bottom" layer
        conv_bottom = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(pool_contr2)
        conv_bottom = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(conv_bottom)

        # Crop outputs of each contracting path "layer" for use in their corresponding expansive path "layer"
        crop_up1 = conv_contr1  # no cropping required
        crop_up2 = conv_contr2  # no cropping required

        # Expansive path
        conv_scale_up2 = Conv2DTranspose(filters=64, kernel_size=(2, 2), strides=2, activation="relu", padding="same",
                             kernel_initializer="he_normal")(conv_bottom)
        merge_up2 = concatenate([conv_scale_up2, crop_up2], axis=3)
        conv_up2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(merge_up2)
        conv_up2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(conv_up2)

        conv_scale_up1 = Conv2DTranspose(filters=32, kernel_size=(2, 2), strides=2, activation="relu", padding="same",
                             kernel_initializer="he_normal")(conv_up2)
        merge_up1 = concatenate([conv_scale_up1, crop_up1], axis=3)
        conv_up1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(merge_up1)
        conv_up1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(conv_up1)

        # Final 1x1 conv layer
        conv_final = Conv2D(self._num_classes, (1, 1), activation="relu", padding="same",
                             kernel_initializer="he_normal")(conv_up1)
        conv_final = Reshape((self._img_height * self._img_width, self._num_classes))(conv_final)
        conv_final = Activation("softmax")(conv_final)

        self._model = Model(inputs=[inputs], outputs=[conv_final])

        return self._model

    def build_model_BRAIN_1layer(self, use_bn=False, use_dropout=False):
        """
        Build a 1 layer version of the U-Net architecture as defined by Ronneberger et al
        """
        self._title = "UNet_brain_1layer"
        self._title+= "_BN" if use_bn else ""
        self._title+= "_DO" if use_dropout else ""

        # Set the input shape
        input_shape = (self._img_height, self._img_width, self._img_channels)
        inputs = Input(input_shape)

        # Contracting path - Layer 1
        conv_contr1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(inputs)
        conv_contr1 = BatchNormalization()(conv_contr1) if use_bn else conv_contr1
        conv_contr1 = Dropout(self._dropout_rate)(conv_contr1) if use_dropout else conv_contr1
        conv_contr1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 32))))(conv_contr1)
        conv_contr1 = BatchNormalization()(conv_contr1) if use_bn else conv_contr1
        pool_contr1 = MaxPooling2D(pool_size=(2, 2))(conv_contr1)

        # Crop outputs of each contracting path "layer" for use in their corresponding expansive path "layer"
        crop_up1 = conv_contr1  # no cropping required

        # Layer 1
        conv_scale_up1 = Conv2DTranspose(filters=32, kernel_size=(2, 2), strides=2, activation="relu", padding="same",
                                         kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 64))))(pool_contr1)
        merge_up1 = concatenate([conv_scale_up1, crop_up1], axis=3)
        conv_up1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 64))))(merge_up1)
        conv_up1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 32))))(conv_up1)

        # Final 1x1 conv layer
        conv_final = Conv2D(self._num_classes, (1, 1), activation="relu", padding="same",
                            kernel_initializer="he_normal")(conv_up1)
        conv_final = Activation("softmax")(conv_final)

        self._model = Model(inputs=[inputs], outputs=[conv_final])

        return self._model

    def build_model_BRAIN_2layer(self, use_bn=False, use_dropout=False):
        """
        Build a 2 layer version of the U-Net architecture as defined by Ronneberger et al
        """
        self._title = "UNet_brain_2layer"
        self._title+= "_BN" if use_bn else ""
        self._title+= "_DO" if use_dropout else ""

        # Set the input shape
        input_shape = (self._img_height, self._img_width, self._img_channels)
        inputs = Input(input_shape)

        # Contracting path - Layer 1
        conv_contr1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(inputs)
        conv_contr1 = BatchNormalization()(conv_contr1) if use_bn else conv_contr1
        conv_contr1 = Dropout(self._dropout_rate)(conv_contr1) if use_dropout else conv_contr1
        conv_contr1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 32))))(conv_contr1)
        conv_contr1 = BatchNormalization()(conv_contr1) if use_bn else conv_contr1
        pool_contr1 = MaxPooling2D(pool_size=(2, 2))(conv_contr1)

        # "Bottom" Layer 2
        conv_bottom = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 32))))(pool_contr1)
        conv_bottom = BatchNormalization()(conv_bottom) if use_bn else conv_bottom
        conv_bottom = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 64))))(conv_bottom)
        conv_bottom = BatchNormalization()(conv_bottom) if use_bn else conv_bottom

        # Crop outputs of each contracting path "layer" for use in their corresponding expansive path "layer"
        crop_up1 = conv_contr1  # no cropping required

        # Layer 1
        conv_scale_up1 = Conv2DTranspose(filters=32, kernel_size=(2, 2), strides=2, activation="relu", padding="same",
                                         kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 64))))(conv_bottom)
        merge_up1 = concatenate([conv_scale_up1, crop_up1], axis=3)
        conv_up1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 64))))(merge_up1)
        conv_up1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 32))))(conv_up1)

        # Final 1x1 conv layer
        conv_final = Conv2D(self._num_classes, (1, 1), activation="relu", padding="same",
                            kernel_initializer="he_normal")(conv_up1)
        conv_final = Activation("softmax")(conv_final)

        self._model = Model(inputs=[inputs], outputs=[conv_final])

        return self._model

    def build_model_BRAIN_3layer(self, use_bn=False, use_dropout=False):
        """
        Build a 3 layer version of the U-Net architecture as defined by Ronneberger et al
        """
        self._title = "UNet_brain_3layer"
        self._title+= "_BN" if use_bn else ""
        self._title+= "_DO" if use_dropout else ""

        # Set the input shape
        input_shape = (self._img_height, self._img_width, self._img_channels)
        inputs = Input(input_shape)

        # Contracting path - Layer 1
        conv_contr1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(inputs)
        conv_contr1 = BatchNormalization()(conv_contr1) if use_bn else conv_contr1
        conv_contr1 = Dropout(self._dropout_rate)(conv_contr1) if use_dropout else conv_contr1
        conv_contr1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 32))))(conv_contr1)
        conv_contr1 = BatchNormalization()(conv_contr1) if use_bn else conv_contr1
        pool_contr1 = MaxPooling2D(pool_size=(2, 2))(conv_contr1)

        # Layer 2
        conv_contr2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 32))))(pool_contr1)
        conv_contr2 = BatchNormalization()(conv_contr2) if use_bn else conv_contr2
        conv_contr2 = Dropout(self._dropout_rate)(conv_contr2) if use_dropout else conv_contr2
        conv_contr2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 64))))(conv_contr2)
        conv_contr2 = BatchNormalization()(conv_contr2) if use_bn else conv_contr2
        pool_contr2 = MaxPooling2D(pool_size=(2, 2))(conv_contr2)

        # "Bottom" Layer 3
        conv_bottom = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 64))))(pool_contr2)
        conv_bottom = BatchNormalization()(conv_bottom) if use_bn else conv_bottom
        conv_bottom = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 128))))(conv_bottom)
        conv_bottom = BatchNormalization()(conv_bottom) if use_bn else conv_bottom

        # Crop outputs of each contracting path "layer" for use in their corresponding expansive path "layer"
        crop_up1 = conv_contr1  # no cropping required
        crop_up2 = conv_contr2  # no cropping required

        # Expansive path - Layer 2
        conv_scale_up2 = Conv2DTranspose(filters=64, kernel_size=(2, 2), strides=2, activation="relu", padding="same",
                                         kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 128))))(conv_bottom)
        merge_up2 = concatenate([conv_scale_up2, crop_up2], axis=3)
        conv_up2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 128))))(merge_up2)
        conv_up2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 64))))(conv_up2)

        # Layer 1
        conv_scale_up1 = Conv2DTranspose(filters=32, kernel_size=(2, 2), strides=2, activation="relu", padding="same",
                                         kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 64))))(conv_up2)
        merge_up1 = concatenate([conv_scale_up1, crop_up1], axis=3)
        conv_up1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 64))))(merge_up1)
        conv_up1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer = RandomNormal(stddev=math.sqrt(2 / (3**2 * 32))))(conv_up1)

        # Final 1x1 conv layer
        conv_final = Conv2D(self._num_classes, (1, 1), activation="relu", padding="same",
                            kernel_initializer="he_normal")(conv_up1)
        conv_final = Activation("softmax")(conv_final)

        self._model = Model(inputs=[inputs], outputs=[conv_final])

        return self._model

    def build_model_BRAIN_4layer(self, use_bn=False, use_dropout=False):
        """
        Build a 4 layer version of the U-Net architecture as defined by Ronneberger et al
        """
        self._title = "UNet_brain_4layer"
        self._title += "_BN" if use_bn else ""
        self._title += "_DO" if use_dropout else ""

        # Set the input shape
        input_shape = (self._img_height, self._img_width, self._img_channels)
        inputs = Input(input_shape)

        # Contracting path - Layer 1
        conv_contr1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer="he_normal")(inputs)
        conv_contr1 = BatchNormalization()(conv_contr1) if use_bn else conv_contr1
        conv_contr1 = Dropout(self._dropout_rate)(conv_contr1) if use_dropout else conv_contr1
        conv_contr1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 32))))(conv_contr1)
        conv_contr1 = BatchNormalization()(conv_contr1) if use_bn else conv_contr1
        pool_contr1 = MaxPooling2D(pool_size=(2, 2))(conv_contr1)

        # Layer 2
        conv_contr2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 32))))(pool_contr1)
        conv_contr2 = BatchNormalization()(conv_contr2) if use_bn else conv_contr2
        conv_contr2 = Dropout(self._dropout_rate)(conv_contr2) if use_dropout else conv_contr2
        conv_contr2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 64))))(conv_contr2)
        conv_contr2 = BatchNormalization()(conv_contr2) if use_bn else conv_contr2
        pool_contr2 = MaxPooling2D(pool_size=(2, 2))(conv_contr2)

        # Layer 3
        conv_contr3 = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 64))))(pool_contr2)
        conv_contr3 = BatchNormalization()(conv_contr3) if use_bn else conv_contr3
        conv_contr3 = Dropout(self._dropout_rate)(conv_contr3) if use_dropout else conv_contr3
        conv_contr3 = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 128))))(conv_contr3)
        conv_contr3 = BatchNormalization()(conv_contr3) if use_bn else conv_contr3
        pool_contr3 = MaxPooling2D(pool_size=(2, 2))(conv_contr3)

        # "Bottom" Layer 4
        conv_bottom = Conv2D(filters=256, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 128))))(pool_contr3)
        conv_bottom = BatchNormalization()(conv_bottom) if use_bn else conv_bottom
        conv_bottom = Conv2D(filters=256, kernel_size=(3, 3), activation="relu", padding="same",
                             kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 256))))(conv_bottom)
        conv_bottom = BatchNormalization()(conv_bottom) if use_bn else conv_bottom

        # Crop outputs of each contracting path "layer" for use in their corresponding expansive path "layer"
        crop_up1 = conv_contr1  # no cropping required
        crop_up2 = conv_contr2  # no cropping required
        crop_up3 = conv_contr3  # no cropping required

        # Expansive path - Layer 3
        conv_scale_up3 = Conv2DTranspose(filters=128, kernel_size=(2, 2), strides=2, activation="relu",
                                         padding="same",
                                         kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 256))))(conv_bottom)
        merge_up3 = concatenate([conv_scale_up3, crop_up3], axis=3)
        conv_up3 = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 256))))(merge_up3)
        conv_up3 = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 128))))(conv_up3)

        # Expansive path - Layer 2
        conv_scale_up2 = Conv2DTranspose(filters=64, kernel_size=(2, 2), strides=2, activation="relu",
                                         padding="same",
                                         kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 128))))(conv_up3)
        merge_up2 = concatenate([conv_scale_up2, crop_up2], axis=3)
        conv_up2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 128))))(merge_up2)
        conv_up2 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 64))))(conv_up2)

        # Layer 1
        conv_scale_up1 = Conv2DTranspose(filters=32, kernel_size=(2, 2), strides=2, activation="relu",
                                         padding="same",
                                         kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 64))))(conv_up2)
        merge_up1 = concatenate([conv_scale_up1, crop_up1], axis=3)
        conv_up1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 64))))(merge_up1)
        conv_up1 = Conv2D(filters=32, kernel_size=(3, 3), activation="relu", padding="same",
                          kernel_initializer=RandomNormal(stddev=math.sqrt(2 / (3 ** 2 * 32))))(conv_up1)

        # Final 1x1 conv layer
        conv_final = Conv2D(self._num_classes, (1, 1), activation="relu", padding="same",
                            kernel_initializer="he_normal")(conv_up1)
        conv_final = Activation("softmax")(conv_final)

        self._model = Model(inputs=[inputs], outputs=[conv_final])

        return self._model

    def build_model(self):
        """
        Build the original 5 layer/4 skip connections U-Net architecture as defined by Ronneberger et al:
        https://lmb.informatik.uni-freiburg.de/people/ronneber/u-net/

        Uses an input shape of 572x572. Instantiate the model using:

            UNet_NN(img_height=572,
                    img_width=572,
                    img_channels=1,
                    num_classes=2).build_model()

        Todo:
        - add Dropout layers at the end of the contracting path
        - add kernel initialisers: kernel_initializer=RandomNormal(stddev=sqrt(2 / (prev. kernel**2 * filters)))
        """
        self._title = "UNet_paper"

        # Set the input shape
        if K.image_data_format() == "channels_first":
            input_shape = (self._img_channels, self._img_width, self._img_height)
        else:
            input_shape = (self._img_height, self._img_width, self._img_channels)

        inputs = Input(input_shape)

        # Contracting path, from the paper:
        # The contracting path follows the typical architecture of a convolutional network. It consists of the
        # repeated application of two 3x3 convolutions (unpadded convolutions), each followed by a rectified linear
        # unit (ReLU) and a 2x2 max pooling operation with stride 2 for downsampling. At each downsampling step we
        # double the number of feature channels.
        # Layer 1
        conv_contr1 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="valid")(inputs)
        conv_contr1 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="valid")(conv_contr1)
        pool_contr1 = MaxPooling2D(pool_size=(2, 2))(conv_contr1)

        # Layer 2
        conv_contr2 = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="valid")(pool_contr1)
        conv_contr2 = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="valid")(conv_contr2)
        pool_contr2 = MaxPooling2D(pool_size=(2, 2))(conv_contr2)

        # Layer 3
        conv_contr3 = Conv2D(filters=256, kernel_size=(3, 3), activation="relu", padding="valid")(pool_contr2)
        conv_contr3 = Conv2D(filters=256, kernel_size=(3, 3), activation="relu", padding="valid")(conv_contr3)
        pool_contr3 = MaxPooling2D(pool_size=(2, 2))(conv_contr3)

        # Layer 4
        conv_contr4 = Conv2D(filters=512, kernel_size=(3, 3), activation="relu", padding="valid")(pool_contr3)
        conv_contr4 = Conv2D(filters=512, kernel_size=(3, 3), activation="relu", padding="valid")(conv_contr4)
        pool_contr4 = MaxPooling2D(pool_size=(2, 2))(conv_contr4)

        # "Bottom" Layer 5
        conv_bottom = Conv2D(filters=1024, kernel_size=(3, 3), activation="relu", padding="valid")(pool_contr4)
        conv_bottom = Conv2D(filters=1024, kernel_size=(3, 3), activation="relu", padding="valid")(conv_bottom)

        # Crop outputs of each contracting path "layer" for use in their corresponding expansive path "layer"
        crop_up1 = Cropping2D(cropping=((88, 88), (88, 88)))(conv_contr1)
        crop_up2 = Cropping2D(cropping=((40, 40), (40, 40)))(conv_contr2)
        crop_up3 = Cropping2D(cropping=((16, 16), (16, 16)))(conv_contr3)
        crop_up4 = Cropping2D(cropping=((4, 4), (4, 4)))(conv_contr4)

        # crop_up1 = conv_contr1
        # crop_up2 = conv_contr2
        # crop_up3 = conv_contr3
        # crop_up4 = conv_contr4

        # Expansive path, from the paper:
        # Every step in the expansive path consists of an upsampling of the feature map followed by a 2x2 convolution
        # (“up-convolution”) that halves the number of feature channels, a concatenation with the correspondingly
        # cropped feature map from the contracting path, and two 3x3 convolutions, each followed by a ReLU
        # Layer 4
        scale_up4 = UpSampling2D(size=(2, 2))(conv_bottom)
        conv_scale_up4 = Conv2D(filters=512, kernel_size=(2, 2), activation="relu", padding="same")(scale_up4)
        merge_up4 =  concatenate([conv_scale_up4, crop_up4], axis=3)
        conv_up4 = Conv2D(filters=512, kernel_size=(3, 3), activation="relu", padding="valid")(merge_up4)
        conv_up4 = Conv2D(filters=512, kernel_size=(3, 3), activation="relu", padding="valid")(conv_up4)

        # Layer 3
        scale_up3 = UpSampling2D(size=(2, 2))(conv_up4)
        conv_scale_up3 = Conv2D(filters=256, kernel_size=(2, 2), activation="relu", padding="same")(scale_up3)
        merge_up3 =  concatenate([conv_scale_up3, crop_up3], axis=3)
        conv_up3 = Conv2D(filters=256, kernel_size=(3, 3), activation="relu", padding="valid")(merge_up3)
        conv_up3 = Conv2D(filters=256, kernel_size=(3, 3), activation="relu", padding="valid")(conv_up3)

        # Layer 2
        scale_up2 = UpSampling2D(size=(2, 2))(conv_up3)
        conv_scale_up2 = Conv2D(filters=128, kernel_size=(2, 2), activation="relu", padding="same")(scale_up2)
        merge_up2 =  concatenate([conv_scale_up2, crop_up2], axis=3)
        conv_up2 = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="valid")(merge_up2)
        conv_up2 = Conv2D(filters=128, kernel_size=(3, 3), activation="relu", padding="valid")(conv_up2)

        # Layer 1
        scale_up1 = UpSampling2D(size=(2, 2))(conv_up2)
        conv_scale_up1 = Conv2D(filters=64, kernel_size=(2, 2), activation="relu", padding="same")(scale_up1)
        merge_up1 =  concatenate([conv_scale_up1, crop_up1], axis=3)
        conv_up1 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="valid")(merge_up1)
        conv_up1 = Conv2D(filters=64, kernel_size=(3, 3), activation="relu", padding="valid")(conv_up1)

        # Final 1x1 conv layer
        conv_final = Conv2D(filters=2, kernel_size=(1, 1), activation="sigmoid")(conv_up1)

        self._model = Model(inputs=inputs, outputs=conv_final)

        return self._model
