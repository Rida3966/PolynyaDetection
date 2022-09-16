# -*- coding: utf-8 -*-
"""PD_functions.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1AjnIBJFJBcthQeHI6KoNjnvut0RakhTf
"""

# LIBRARIES
# DATA LOADING AND READING
# DATA VISUALIZATION
# PREPROCESSING
# TRAIN TEST SPLIT
# DATA AUGMENTATION
# EVALUATION
# PERFORMANCE ON UNSEEN DATA

"""**IMPORTING LIBRARIES**"""

# Commented out IPython magic to ensure Python compatibility.
# Required Packages

# %tensorflow_version 2.1.0
#!pip install segmentation-models==1.0.1

# Commented out IPython magic to ensure Python compatibility.
# Data Handling
import numpy as np
import os
import glob
import cv2
import random
import zipfile
from skimage import io
import imutils

# Visualization
from matplotlib import pyplot as plt
# %matplotlib inline

# Data Split
from sklearn.model_selection import train_test_split
from sklearn.model_selection import KFold

# Deep Learning Libraries
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.utils import get_file
from keras_applications import imagenet_utils
from tensorflow.keras.models import load_model
from tensorflow.keras.metrics import MeanIoU
from keras.preprocessing.image import ImageDataGenerator
import segmentation_models as sm
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Conv2D, MaxPooling2D, Concatenate, Conv2DTranspose, BatchNormalization, Dropout, Activation

# Import files
import unet_func_block
from unet_func_block import drop_out, conv_block, encoder_block, decoder_block_unet, build_unet, build_autoencoder, build_encoder, build_decoder

print(keras.__version__)
sm.set_framework('tf.keras')
sm.framework()

"""**LOADING DATA**"""

# Loading Data from Drive

def load_data(Train_path, Mask_path, size):
    train_images = []
    mask_images = []

    # Loading Train Images in an array
    for directory_path in glob.glob(Train_path):
      for img_path in sorted(glob.glob(os.path.join(directory_path, "*.png"))):
        img = cv2.imread(img_path, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (size, size))               # Resizing image dimensions to obtain same size
        train_images.append(img)
    train_images = np.array(train_images)                  # Filling images in array for CNN

    # Corresponding Image Masks/ Annotations
    for directory_path in glob.glob(Mask_path):
      for mask_path in sorted(glob.glob(os.path.join(directory_path, "*.png"))):
        mask = cv2.imread(mask_path, 0)
        mask = cv2.resize(mask, (size, size))             # Resizing image dimensions to obtain same size
        mask = np.where(mask>0, 1, mask)                  # Converting masked images to binary pixel images
        if (np.count_nonzero(mask==1) > 10000):           # Fixing Data to adjust abnormalities
            mask = np.where(mask>=0, 0, mask)

        mask_images.append(mask)
    mask_images = np.array(mask_images)                   # Filling images in array for CNN

    return (train_images, mask_images)                    # Returning array of data

# Load Test Data from temporary directory on colab

def load_test_data(test_path, size):

    tester_img = []                                        # Loading Test Data in array

    for directory_path in glob.glob(test_path):
      for img_path in sorted(glob.glob(os.path.join(directory_path, "*.png"))):
        img = cv2.imread(img_path, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (size, size))               # Resize
        img = (img.astype('float32')) / 255.              # Scaling pixel values in each image
        tester_img.append(img)
    tester_img = np.array(tester_img)                     # Constructing an array

    return tester_img

# Loading Data from Local Directory

"""**VISUALIZATION**"""

def visualize(train_images, mask_images, img_num):

    # Displaying Image and its corresponding mask
    
    tester_img = train_images[img_num]
    tester_mask = mask_images[img_num]

    #PLotting
    plt.subplot(1,2,1)
    plt.imshow(tester_img)
    plt.title('Image')
    plt.subplot(1,2,2)
    plt.imshow(np.reshape(tester_mask,(256,256)), cmap='gray')
    plt.title('Mask')
    plt.show()
    
    labels,count = np.unique(tester_mask, return_counts=True)
    print("Labels are:", labels, "and label count is:", count)
    print("Image Number=", img_num)

def visualize_generated(x,y):
    # Data Checks for Generated Images

    x = x.next()
    y = y.next()

    for i in range(0,1):
      img = x[i]
      mask = y[i]
      plt.subplot(1,2,1)
      plt.imshow(img)
      plt.subplot(1,2,2)
      plt.imshow(mask[:,:,0], cmap='gray')
      plt.show()

      print("Labels", np.unique(mask))

"""**PREPROCESSING**"""

def preprocessing(train_images,mask_images, backbone):
  
    X = (train_images.astype('float32')) / 255                 # Scaling images
    Y = mask_images.astype('float32') 
    
    preprocess_input = sm.get_preprocessing(backbone)        # Preprocessing with CNN backbone
    X = preprocess_input(X)
    Y = np.expand_dims(Y, 3)                                 # Expanding axis of binary masks to match originial images

    return (X, Y)

def preprocess_customUnet(train_images,mask_images):       # Involves no preprocessing by Transfer learning

    X = (train_images.astype('float32')) / 255                 # Scaling images    
    Y = mask_images.astype('float32')
    Y = np.expand_dims(Y, 3)                                 # Expanding axis of binary masks to match originial images

    return (X,Y)

"""**DATA SPLIT**"""

def data_split(X, Y, split_size, random_state):

    x_train, x_val, y_train, y_val = train_test_split(X, Y, test_size= split_size, random_state= random_state)

    return (x_train, y_train, x_val, y_val)

"""**DATA AUGMENTATION**"""

# Data Agmentation with default batch size = 32

def augment(x, y, split_size):
    seed = 24
    x_train, y_train, x_val, y_val = data_split(x, y, split_size, random_state=seed)

    # Augmentation features
    image_datagen_args = dict(rotation_range = 45,
                                width_shift_range=0.2, height_shift_range= 0.2,
                                shear_range=0.2, zoom_range=0.1,
                                horizontal_flip=True, vertical_flip=False,
                                fill_mode= 'nearest')
    mask_datagen_args = dict(rotation_range = 45,
                                width_shift_range=0.2, height_shift_range= 0.2,
                                shear_range=0.2, zoom_range=0.1,
                                horizontal_flip=True, vertical_flip=False,
                                fill_mode= 'nearest',
                                preprocessing_function = lambda x: np.where(x>0, 1, 0).astype(x.dtype))

    # Data Generator
    image_datagenerator = ImageDataGenerator (**image_datagen_args)
    image_datagenerator.fit(x_train , augment=True , seed = seed)

    # Generated training and validation images
    trainImage_generated = image_datagenerator.flow(x_train, seed=seed)
    valImage_generated = image_datagenerator.flow(x_val, seed=seed)

    mask_datagenerator = ImageDataGenerator (**mask_datagen_args)
    mask_datagenerator.fit(y_train , augment=True , seed = seed)

    # Generated training and validation masks
    trainMask_generated = mask_datagenerator.flow(y_train, seed=seed)
    valMask_generated = mask_datagenerator.flow(y_val, seed=seed)

    # For simplification
    def img_mask_gen(image_gen , mask_gen):
        training_generator = zip(image_gen, mask_gen)
        for(img, mask) in training_generator:
            yield(img, mask)

    # For input into model.fit
    train_generator = img_mask_gen(trainImage_generated, trainMask_generated)
    val_generator = img_mask_gen(valImage_generated, valMask_generated)

    return (train_generator, val_generator, trainImage_generated, trainMask_generated)


# Data Augmentation with Batch Size = 16 (Used for multiRes Unet architecture)

def augment32(x, y, split_size):
    seed = 24
    x_train, y_train, x_val, y_val = data_split(x, y, split_size, random_state=seed)

    # Augmentation features
    image_datagen_args = dict(rotation_range = 45,
                                width_shift_range=0.2, height_shift_range= 0.2,
                                shear_range=0.2, zoom_range=0.1,
                                horizontal_flip=True, vertical_flip=False,
                                fill_mode= 'nearest')
    mask_datagen_args = dict(rotation_range = 45,
                                width_shift_range=0.2, height_shift_range= 0.2,
                                shear_range=0.2, zoom_range=0.1,
                                horizontal_flip=True, vertical_flip=False,
                                fill_mode= 'nearest',
                                preprocessing_function = lambda x: np.where(x>0, 1, 0).astype(x.dtype))

    batch_size = 16
    # Data Generator
    image_datagenerator = ImageDataGenerator (**image_datagen_args)
    image_datagenerator.fit(x_train , augment=True , seed = seed)

    # Generated training and validation images
    trainImage_generated = image_datagenerator.flow(x_train, seed=seed, batch_size=batch_size)
    valImage_generated = image_datagenerator.flow(x_val, seed=seed,batch_size=batch_size)

    mask_datagenerator = ImageDataGenerator (**mask_datagen_args)
    mask_datagenerator.fit(y_train , augment=True , seed = seed)

    # Generated training and validation masks
    trainMask_generated = mask_datagenerator.flow(y_train, seed=seed, batch_size=batch_size)
    valMask_generated = mask_datagenerator.flow(y_val, seed=seed, batch_size=batch_size)

    # For simplification
    def img_mask_gen(image_gen , mask_gen):
        training_generator = zip(image_gen, mask_gen)
        for(img, mask) in training_generator:
            yield(img, mask)

    # For input into model.fit
    train_generator = img_mask_gen(trainImage_generated, trainMask_generated)
    val_generator = img_mask_gen(valImage_generated, valMask_generated)

    return (train_generator, val_generator, trainImage_generated, trainMask_generated)

"""**HISTORY EVALUATION AND PERFORMANCE**"""

# IOU Score for segmentation

def model_IOU(model, x_val, y_val, thresh):
    y_pred = model.predict(x_val)
    y_pred_thresholded = y_pred > thresh 

    intersection = np.logical_and(y_val, y_pred_thresholded)
    union = np.logical_or(y_val, y_pred_thresholded)
    iou_score = np.sum(intersection)/ np.sum(union)

    return iou_score
   
#print("IOU score of model is" , f"{iou_score:.0%}")

# IOU for single image

def iou_acc(ground_truth, prediction):

    IOU_keras = MeanIoU(num_classes=2)  
    IOU_keras.update_state(ground_truth[:,:,0], prediction)
    iou_score = IOU_keras.result().numpy()
       
    return iou_score

def evaluation(history):

    loss = history.history['loss']
    val_loss = history.history['val_loss']
    epochs = range(1, len(loss) +1)
    plt.plot(epochs, loss, 'y', label= 'Training loss')
    plt.plot(epochs, val_loss, 'r', label='Validation loss')
    plt.ylim(0,50)
    plt.title('Training and validation loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.show()

    acc = history.history['iou_score']
    val_acc = history.history['val_iou_score']
    plt.plot(epochs, acc, 'y', label= 'Training IOU')
    plt.plot(epochs, val_acc, 'r', label='Validation IOU')
    plt.title('Training and validation IOU')
    plt.xlabel('Epochs')
    plt.ylabel('IOU')
    plt.legend()
    plt.show()

# Performance Evaluation

#test_img_number = random.randint(0, len(x_val)-1)           # Random image number

def performance(x_val, y_val, model, threshold, test_img_number):

    # PREDICTION
    
    test_img = x_val[test_img_number]                           # Original image
    ground_truth = y_val[test_img_number]                       # Labelled mask

    test_img_input = np.expand_dims(test_img, 0)                
    prediction = model.predict(test_img_input)
    prediction = prediction > threshold
    prediction = prediction[0, :,:,0]                           # Predicted mask


    # IOU SCORE
    IOU_score = iou_acc(ground_truth, prediction)
    print("Image Number=", test_img_number)

    # EXTRACTING CONTOURS 
    actual = ground_truth.astype(np.uint8)
    predicted = prediction.astype(np.uint8)
    contours1, hierarchy1 = cv2.findContours(image=actual, mode=cv2.RETR_TREE, method=cv2.CHAIN_APPROX_NONE)
    contours2, hierarchy2 = cv2.findContours(image=predicted, mode=cv2.RETR_TREE, method=cv2.CHAIN_APPROX_NONE)
    contoured = test_img.copy()
    contoured = (contoured * 255).astype(np.uint8)
    cv2.drawContours(image=contoured, contours=contours1, contourIdx=-1, color=(255, 0, 0), thickness=1, lineType=cv2.LINE_AA)
    cv2.drawContours(image=contoured, contours=contours2, contourIdx=-1, color=(255, 165, 0), thickness=1, lineType=cv2.LINE_AA)

    # PLOTTING
    plt.figure(figsize=(16, 8))
    plt.subplot(231)
    plt.title("Testing image")
    plt.imshow(test_img)
    plt.subplot(232)
    plt.title("Ground Truth")
    plt.imshow(ground_truth[:,:,0], cmap='gray')
    plt.subplot(233)
    plt.title(f"Predicted Mask ({IOU_score:.0%} accuracy)")
    plt.imshow(prediction, cmap='gray')
    plt.subplot(234) 
    plt.title("Comparison of Actual and Predicted mask")
    plt.imshow(contoured)
    plt.show()

"""**TESTING ON UNSEEN DATA**"""

def testing(test_data, model, thresh, img_num):

    # PREDICTION
    test_input = test_data[img_num]                                 # Input image
    prediction_on_test = np.expand_dims(test_input, 0)
    prediction_on_test = model.predict(prediction_on_test)
    prediction_on_test = prediction_on_test > thresh
    predicted_img = prediction_on_test[0,:,:,0]                     # Predicted Mask

    # EXTRACTING CONTOURS
   
    predicted = predicted_img.astype(np.uint8)
    cnts = cv2.findContours(image=predicted, mode=cv2.RETR_TREE, method=cv2.CHAIN_APPROX_NONE)
    #cnts = cv2.findContours(image=predicted, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)
    contours = imutils.grab_contours(cnts)
    contoured = test_input.copy()
    contoured = (contoured * 255).astype(np.uint8)
    cv2.drawContours(image=contoured, contours=contours, contourIdx=-1, color=(255, 0, 0), thickness=1, lineType=cv2.LINE_AA)

     # Circumference of detected Mask

    if contours :
        print("Polynya Detected")
        for i in range(len(contours)):
            circum = cv2.arcLength(contours[i], True)
            print(f"Circumference of Polynya : {round(circum,2)} px")
    else:
        print("No Polynya Detected")


    # PLOTTING
    plt.figure(figsize=(8,8))
    plt.subplot(121)
    plt.imshow(test_input)
    plt.title('Image')
    plt.subplot(122)
    plt.imshow(contoured)
    #plt.imshow((contoured*255).astype(np.uint8))
    plt.title('POLYNYA PREDICTION')
    plt.show()

    print("Image number:", img_num)

"""**COMPARISON OF MODELS**"""

# Comparing History

def compare_evaluation_2(history1, history2, model1, model2):

    val_acc1 = history1.history['val_iou_score']
    val_acc2 = history2.history['val_iou_score']
    epochs = range(1, len(val_acc1) +1)

    plt.figure(figsize=(8, 6))
    plt.plot(epochs, val_acc1, label= f'{model1}', color = 'xkcd:blue')
    plt.plot(epochs, val_acc2, label=f'{model2}', color='xkcd:orange')
    plt.title('Comparison of Validation accuracy from two models')
    plt.xlabel('Epochs')
    plt.ylabel('IOU')
    plt.legend(loc='upper left')
    plt.grid()
    plt.show()

def compare_evaluation_3(history1, history2, history3, model1, model2, model3):

    val_acc1 = history1.history['val_iou_score']
    val_acc2 = history2.history['val_iou_score']
    val_acc3 = history3.history['val_iou_score']
    epochs = range(1, len(val_acc1) +1)

    plt.figure(figsize=(12, 8))
    plt.plot(epochs, val_acc1,'xkcd:blue', label= f'{model1}')
    plt.plot(epochs, val_acc2, 'xkcd:orange', label=f'{model2}')
    plt.plot(epochs, val_acc3, 'xkcd:green', label=f'{model3}')
    plt.title('Comparison of Validation accuracy from three models')
    plt.xlabel('Epochs')
    plt.ylabel('IOU')
    plt.legend(loc='upper left')
    plt.grid()
    plt.show()

def compare_evaluation_4(history1, history2, history3,history4, model1, model2, model3, model4):

    val_acc1 = history1.history['val_iou_score']
    val_acc2 = history2.history['val_iou_score']
    val_acc3 = history3.history['val_iou_score']
    val_acc4 = history4.history['val_iou_score']

    epochs = range(1, len(val_acc1) +1)

    plt.figure(figsize=(12, 8))
    plt.plot(epochs, val_acc1,'xkcd:blue', label= f'{model1}')
    plt.plot(epochs, val_acc2, 'xkcd:orange', label=f'{model2}')
    plt.plot(epochs, val_acc3, 'xkcd:green', label=f'{model3}')
    plt.plot(epochs, val_acc3, 'xkcd:magenta', label=f'{model4}')
    plt.title('Comparison of Validation accuracy from three models')
    plt.xlabel('Epochs')
    plt.ylabel('IOU')
    plt.legend(loc='upper left')
    plt.grid()
    plt.show()

def compare_performance(x_val, y_val, model1, model2, thresh):

    test_img_number = random.randint(0, x_val.shape[0]-1)                     # Random image from Data

    # PREDICTIONS
    test_img = x_val[test_img_number]
    ground_truth = y_val[test_img_number]

    test_img_input = np.expand_dims(test_img, 0)
    prediction1 = (model1.predict(test_img_input)[0,:,:,0] > thresh)
    prediction2 = (model2.predict(test_img_input)[0,:,:,0] > thresh)

    #CALCULATING SCORE

    IOU1 = iou_acc(ground_truth, prediction1)
    IOU2 = iou_acc(ground_truth, prediction2)

    # EXTRACTING CONTOURS 
    M1 = prediction1.astype(np.uint8)
    M2 = prediction2.astype(np.uint8)
    contours1, hierarchy1 = cv2.findContours(image=M1, mode=cv2.RETR_TREE, method=cv2.CHAIN_APPROX_NONE)
    contours2, hierarchy2 = cv2.findContours(image=M2, mode=cv2.RETR_TREE, method=cv2.CHAIN_APPROX_NONE)
    contoured = test_img.copy()
    contoured = (contoured * 255).astype(np.uint8)
    cv2.drawContours(image=contoured, contours=contours1, contourIdx=-1, color=(255, 0, 0), thickness=1, lineType=cv2.LINE_AA)
    cv2.drawContours(image=contoured, contours=contours2, contourIdx=-1, color=(255, 255, 255), thickness=1, lineType=cv2.LINE_AA)

    # PLOTTING
    plt.figure(figsize=(16, 8))
    plt.subplot(231)
    plt.title('Testing Image')
    plt.imshow(test_img)
    plt.subplot(232)
    plt.title('Ground_truth')
    plt.imshow(ground_truth[:,:,0], cmap='gray')
    plt.subplot(233)
    plt.title(f'Predicted Mask Model1({IOU1:.0%} acc)')
    plt.imshow(prediction1, cmap='gray')
    plt.subplot(234)
    plt.title(f'Predicted mask Model2({IOU2:.0%} acc)')
    plt.imshow(prediction2, cmap='gray')
    plt.subplot(235)
    plt.title('Comparison')
    plt.imshow(contoured)
  
    plt.show()