"""Common image handling and conversion methods"""
from dltoolkit.io import HDF5Reader, HDF5Writer
from dltoolkit.utils.image import normalise, standardise
from dltoolkit.utils.generic import list_images

import numpy as np
import cv2
import time, os, progressbar
import matplotlib.pyplot as plt


# Note - OpenCV expects pixel intensities:
#
# 0.0 - 1.0 if dtype is uint8
# 0 - 255 if dtype is float32
#
# otherwise it will not show images properly.


def convert_to_hdf5(img_path, img_shape, img_exts, key, ext, is_mask=False):
    """
    Convert images present in `img_path` to HDF5 format. The HDF5 file is one sub folder up from where the
    images are located. Masks are binary tresholded to be 0 for background pixels and 255 for blood vessels.
    :param img_path: path to the folder containing images
    :param img_shape: shape of each image (width, height, # of channels)
    :return: full path to the generated HDF5 file
    """
    output_path = os.path.join(os.path.dirname(img_path), os.path.basename(img_path)) + ext
    imgs_list = sorted(list(list_images(basePath=img_path, validExts=img_exts)))

    # Prepare the HDF5 writer, which expects a label vector. Because this is a segmentation problem just pass None
    hdf5_writer = HDF5Writer((len(imgs_list), img_shape[0], img_shape[1], img_shape[2]), output_path,
                             feat_key=key,
                             label_key=None,
                             del_existing=True,
                             buf_size=len(imgs_list),
                             dtype_feat="f" if not is_mask else "i8"
                             )

    # Loop through all images
    widgets = ["Creating HDF5 database ", progressbar.Percentage(), " ", progressbar.Bar(), " ", progressbar.ETA()]
    pbar = progressbar.ProgressBar(maxval=len(imgs_list), widgets=widgets).start()
    for i, img in enumerate(imgs_list):
        image = cv2.imread(img, cv2.IMREAD_GRAYSCALE)

        # Apply binary thresholding to ground truth masks
        if is_mask:
            _, image = cv2.threshold(image, settings.MASK_BINARY_THRESHOLD, settings.MASK_BLOODVESSEL, cv2.THRESH_BINARY)

        # Reshape from (height, width) to (height, width, 1)
        image = image.reshape((img_shape[0],
                               img_shape[1],
                               img_shape[2]))

        hdf5_writer.add([image], None)
        pbar.update(i)

    pbar.finish()
    hdf5_writer.close()

    return output_path


def convert_img_to_pred_4D(ground_truths, settings, verbose=False):
    """
    Convert an array of grayscale images with shape (-1, height, width, 1) to an array of the same length with
    shape (-1, height, width, num_classes).
    :param ground_truths: array of grayscale images, pixel values are integers 0 (background) or 255 (blood vessels)
    :param settings:
    :param verbose: True if additional information is to be printed to the console during training
    :return: one-hot encoded version of the image
    """
    start_time = time.time()

    img_height = ground_truths.shape[1]
    img_width = ground_truths.shape[2]

    new_masks = np.empty((ground_truths.shape[0], img_height, img_width, settings.NUM_CLASSES), dtype=np.uint8 )
    print("new_masks type = {}".format(new_masks.dtype))

    for image in range(ground_truths.shape[0]):
        if image != 0 and verbose and image % 1000 == 0:
            print("Processed {}/{}".format(image, ground_truths.shape[0]))

        for pix_h in range(img_height):
            for pix_w in range(img_width):
                if ground_truths[image, pix_h, pix_w] == settings.MASK_BACKGROUND:
                    new_masks[image, pix_h, pix_w, settings.ONEHOT_BACKGROUND] = 1
                    new_masks[image, pix_h, pix_w, settings.ONEHOT_BLOODVESSEL] = 0
                else:
                    new_masks[image, pix_h, pix_w, settings.ONEHOT_BACKGROUND] = 0
                    new_masks[image, pix_h, pix_w, settings.ONEHOT_BLOODVESSEL] = 1

    if verbose:
        print("Elapsed time: {}".format(time.time() - start_time))

    return new_masks


def convert_img_to_pred_3D(ground_truths, settings, verbose=False):
    # from (-1, height, width, 1) to (-1, height * width, num_classes)
    # last axis: 0 = background, 1 = blood vessel
    start_time = time.time()

    img_height = ground_truths.shape[1]
    img_width = ground_truths.shape[2]

    print("gt from: {}".format(ground_truths.shape))
    ground_truths = np.reshape(ground_truths, (ground_truths.shape[0], img_height * img_width))
    print("  gt to: {} ".format(ground_truths.shape))

    new_masks = np.empty((ground_truths.shape[0], img_height * img_width, settings.NUM_CLASSES), dtype=np.uint8)

    for image in range(ground_truths.shape[0]):
        if verbose and image % 1000 == 0:
            print("{}/{}".format(image, ground_truths.shape[0]))

        for pix in range(img_height*img_width):
            if ground_truths[image, pix] == settings.MASK_BACKGROUND:      # TODO: update for num_model_channels > 2
                new_masks[image, pix, settings.ONEHOT_BACKGROUND] = 1
                new_masks[image, pix, settings.ONEHOT_BLOODVESSEL] = 0
            else:
                new_masks[image, pix, settings.ONEHOT_BACKGROUND] = 0
                new_masks[image, pix, settings.ONEHOT_BLOODVESSEL] = 1

    if verbose:
        print("Elapsed time: {}".format(time.time() - start_time))

    return new_masks


def convert_pred_to_img_4D(pred, settings, threshold=0.5, verbose=False):
    # from (-1, height, width, num_classes) to (-1, height, width, 1)
    start_time = time.time()

    pred_images = np.empty((pred.shape[0], pred.shape[1], pred.shape[2]), dtype=np.uint8)
    # pred = np.reshape(pred, newshape=(pred.shape[0], pred.shape[1] * pred.shape[2]))

    for i in range(pred.shape[0]):
        for pix in range(pred.shape[1]):
            for pix_w in range(pred.shape[2]):
                if pred[i, pix, pix_w, settings.ONEHOT_BLOODVESSEL] > threshold:        # TODO for multiple classes > 2 use argmax
                    # print("from {} to {}".format(pred[i, pix, 1], 1))
                    pred_images[i, pix, pix_w] = settings.MASK_BLOODVESSEL
                else:
                    # print("from {} to {}".format(pred[i, pix, 1], 0))
                    pred_images[i, pix, pix_w] = settings.MASK_BACKGROUND

    pred_images = np.reshape(pred_images, (pred.shape[0], settings.IMG_HEIGHT, settings.IMG_WIDTH, 1))

    if verbose:
        print("Elapsed time: {}".format(time.time() - start_time))

    return pred_images


def convert_pred_to_img_3D(pred, settings, threshold=0.5, verbose=False):
    # from (-1, height * width, num_classes) to (-1, height, width, 1)
    start_time = time.time()

    pred_images = np.empty((pred.shape[0], pred.shape[1]), dtype=np.uint8)
    # pred = np.reshape(pred, newshape=(pred.shape[0], pred.shape[1] * pred.shape[2]))

    for i in range(pred.shape[0]):
        for pix in range(pred.shape[1]):
            if pred[i, pix, settings.ONEHOT_BLOODVESSEL] > threshold:        # TODO for multiple classes > 2 use argmax
                # print("from {} to {}".format(pred[i, pix, 1], 1))
                pred_images[i, pix] = settings.MASK_BLOODVESSEL
            else:
                # print("from {} to {}".format(pred[i, pix, 1], 0))
                pred_images[i, pix] = settings.MASK_BACKGROUND

    pred_images = np.reshape(pred_images, (pred.shape[0], settings.IMG_HEIGHT, settings.IMG_WIDTH, 1))

    if verbose:
        print("Elapsed time: {}".format(time.time() - start_time))

    return pred_images


def perform_image_preprocessing(image_path, key):
    """Perform image pre-processing, resulting pixel values are between 0.0 and 1.0"""
    imgs = HDF5Reader().load_hdf5(image_path, key)
    print("Loading image HDF5: {} with dtype = {}\n".format(image_path, imgs.dtype))

    # Standardise
    imgs = standardise(imgs)
    print("Image dtype after preprocessing = {}\n".format(imgs.dtype))

    return imgs


def perform_groundtruth_preprocessing(ground_truth_path, key):
    """Perform ground truth image pre-processing, resulting pixel values are between 0 and 255"""
    imgs = HDF5Reader().load_hdf5(ground_truth_path, key).astype("uint8")
    print("Loading ground truth HDF5: {} with dtype = {}\n".format(ground_truth_path, imgs.dtype))

    return imgs



def gallery(array, ncols=3):
    nindex, height, width, intensity = array.shape
    nrows = nindex//ncols
    assert nindex == nrows*ncols
    # want result.shape = (height*nrows, width*ncols, intensity)
    result = (array.reshape(nrows, ncols, height, width, intensity)
              .swapaxes(1,2)
              .reshape(height*nrows, width*ncols, intensity))
    return result


def group_images(imgs, num_per_row, empty_color=255, show=False, save_path=None):
    """
    Combines an array of images into a single image using a grid with num_per_row columns, the number of rows is
    calculated using the number of images in the array and the number of requested columns. Grid cells without an
    image are replaced with an empty image using
    :param imgs: numpy array of images , shape: (-1, height, width, channels)
    :param num_per_row: number of images shown in each row
    :param empty_color: color to use for empty grid cells, e.g. 255 for white (grayscale images)
    :param show: True if the resulting image should be displayed on screen, False otherwise
    :param save_path: full path for the image, None otherwise
    :return: resulting grid image
    """
    all_rows= []
    img_height = imgs.shape[1]
    img_width = imgs.shape[2]
    img_channels = imgs.shape[3]

    num_rows = (imgs.shape[0] // num_per_row) + (1 if imgs.shape[0] % num_per_row else 0)
    for i in range(num_rows):
        # Add the first image to the current row
        row = imgs[i * num_per_row]

        if i == (num_rows-1):
            # Ensure the last row does not use more images than available in the array
            remaining = num_rows * num_per_row - len(imgs)
            rng = range(i * num_per_row + 1, i * num_per_row + num_per_row - remaining)
        else:
            rng = range(i * num_per_row + 1, i * num_per_row + num_per_row)

        # Concatenate the remaining images to the current row
        for k in rng:
            row = np.concatenate((row, imgs[k]), axis=1)

        if i == (num_rows-1):
            # For the last row use white images for any empty cells
            row = np.concatenate((row,
                                  np.full((img_height, remaining*img_width, img_channels),
                                          empty_color,
                                          dtype=imgs[0].dtype)),
                                 axis=1)

        all_rows.append(row)

    # Create the grid image by concatenating all rows
    final_image = all_rows[0]
    for i in range(1, len(all_rows)):
        final_image = np.concatenate((final_image, all_rows[i]),axis=0)

    # Plot the image
    plt.figure(figsize=(20.48, 15.36))
    plt.axis('off')
    plt.imshow(final_image[:,:,0], cmap="gray")

    # Save the plot to a file if desired
    if save_path is not None:
        save_path = save_path + ".png"
        plt.savefig(save_path, dpi=100)

    # Show the plot if desired
    if show:
        plt.show()

    plt.close()

    return final_image
