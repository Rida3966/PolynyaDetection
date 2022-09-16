# -*- coding: utf-8 -*-
"""PD_Main_2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1fr6EHuTH-MjEHGL5WbXPGw1C1bhkolFu

##**MULTIRES-UNET ARCHITECTURE**

**IMPORTING LIBRARIES**
"""

# Commented out IPython magic to ensure Python compatibility.
# Required Packages

# %tensorflow_version 2.1.0
!pip install segmentation-models==1.0.1

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

# Import Custom files
import unet_func_block
from unet_func_block import drop_out, conv_block, encoder_block, decoder_block_unet, build_unet, build_autoencoder, build_encoder, build_decoder

import pd_functions
from pd_functions import load_data, load_test_data, visualize, visualize_generated, preprocessing, preprocess_customUnet, data_split
from pd_functions import augment, augment32, model_IOU, iou_acc, evaluation, performance, testing, compare_evaluation_2, compare_evaluation_3
from pd_functions import compare_performance

import multiresunet_func_block
from multiresunet_func_block import conv_block, multires_block, res_path, encoder_block, decoder_block, build_multiresunet

sm.set_framework('tf.keras')
sm.framework()

"""#### ***COMPARISON OF MULTIRES-UNET WITH ORIGINAL UNET ARCHITECTURE***


*   MultiRes-Unet Architecture
*   Unet vs MultiRes Unet


"""

### DIRECTORY

drive_path = '/content/drive/MyDrive/Colab Notebooks/'
saved_models = '/content/drive/MyDrive/Colab Notebooks/saved_models/'
Train_path = "/data/Train_folder/OriginalTrain"
Mask_path =  "/data/Train_folder/AnnotationsTrain"
test_path = "/testdata/Testers"

### HYPER-PARAMETERS

# (Data Dynamics)
size = 256
IMG_CHANNELS = 3
input_shape = (size, size, IMG_CHANNELS)

# (Model Parameters)
iou = sm.metrics.iou_score
jaccard_loss = sm.losses.bce_jaccard_loss
binary_loss = 'binary_crossentropy'
optimizer = 'Adam'

# (Batch Sizes)
BS16 = 16                            
BS32 = 32

# Loading Image Directory

zip_ref = zipfile.ZipFile(f'{drive_path}Train_folder.zip', 'r')
zip_ref.extractall('/data')
zip_ref.close()

# Loading Test Directory

zip_ref = zipfile.ZipFile(f'{drive_path}Testers.zip', 'r')
zip_ref.extractall('/testdata')
zip_ref.close()

# Loading Data
train_images, mask_images = load_data(Train_path, Mask_path, size)

print(train_images.shape)
print(mask_images.shape)

# Visualization before preprocessing

img_num = random.randint(0, len(train_images)-1)
V = visualize(train_images, mask_images, img_num)
V

# Preprocessing

X, Y = preprocess_customUnet(train_images,mask_images)

print(X.shape)
print(Y.shape)

# Visualizing Preprocessed images

img_num = random.randint(0, len(X)-1)
VP = visualize(X,Y, img_num)
VP

# Data Split

x_train, y_train, x_val, y_val = data_split(X, Y, split_size = 0.2, random_state = 42)

print("Train Data Dynamics:" , x_train.shape, y_train.shape)
print("Test Data Dynamics:" , x_val.shape, y_val.shape)

"""**MultiRes Unet using Original Data Set (Batch Size= 16)**"""

# Building MultiRes UNET model

multires = build_multiresunet(input_shape)
multires.compile(optimizer='adam', loss= binary_loss, metrics=[iou])

history_mr_orig = multires.fit(x=x_train, y= y_train, batch_size= BS16, 
                                    epochs= 100, verbose=1, validation_data= (x_val, y_val))

# Saving model and history
multires.save(f'{saved_models}multires_original.h5')

# Saving history
np.save(f'{saved_models}multires_orig_history.npy', history_mr_orig.history)

# Accuracy
accuracy = model_IOU(multires, x_val, y_val, 0.5)
print('IOU score of model "multires unet model" is', f'{accuracy:.0%}')

# Evaluation

EV = evaluation(history_mr_orig)

# Performance

img_num = random.randint(0, len(x_val)-1)
perf = performance(x_val, y_val, model = multires, threshold=0.8, test_img_number=img_num)

"""**COMPARISON OF UNET VS MULTIRES**"""

unet_original_history = np.load(f'{saved_models}custom_unet_original_history.npy',allow_pickle='TRUE').item()
multires_original_history = np.load(f'{saved_models}multires_orig_history.npy',allow_pickle='TRUE').item()

def compare_evaluation_2(history1, history2, model1, model2):

    val_acc1 = history1['val_iou_score']
    val_acc2 = history2['val_iou_score']
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

C1 = compare_evaluation_2(unet_original_history, multires_original_history, "unet", "multires_unet")

"""**COMPARISON OF PERFORMANCE**"""

# Load Models

unet_original = load_model(f'{saved_models}custom_unet_original.h5', compile=False)
multires_original = load_model(f'{saved_models}multires_original.h5', compile=False)

CP = compare_performance(x_val, y_val, unet_original, multires_original, 0.8)

"""#### ***EXPERIMENTING DATA AUGMENTATION***"""

# Data Augmentation

train_generator, val_generator, trainImage_generated, trainMask_generated = augment32(X, Y, 0.2)

# Visualize generated images

VG = visualize_generated(trainImage_generated,trainMask_generated)

#Building multires unet model with augmented data

multires_aug = build_multiresunet(input_shape)
multires_aug.compile(optimizer='adam', loss= jaccard_loss, metrics=[iou])
#multires.summary()

history_mr_aug = multires_aug.fit_generator(train_generator, validation_data= val_generator,
                                             steps_per_epoch= 20, validation_steps= 20, epochs= 100)

# Accuracy
accuracy2 = model_IOU(multires_aug, x_val, y_val, 0.5)
print('IOU score of model "multires unet augmented model" is', f'{accuracy2:.0%}')

# saving model
multires_aug.save(f'{saved_models}multires_augmented.h5')

# saving history
np.save(f'{saved_models}multires_aug_history.npy', history_mr_aug.history)

# Evaluation

EV2 = evaluation(history_mr_aug)

"""**Comparison of Unet and MultiRes Unet with augmented data**"""

# Loading history of unet
hist_unet = np.load(f'{saved_models}custom_unet_augmented_history.npy', allow_pickle='TRUE').item()
hist_multires = np.load(f'{saved_models}multires_aug_history.npy', allow_pickle='TRUE').item()

# Compare History Evaluation

C1 = compare_evaluation_2(hist_unet, hist_multires, "unet_augmented", "multires_augmented")

"""**TESTING ON UNSEEN DATA**"""

# Testing on Unseen Data 

tester_img = load_test_data(test_path, size)
print(tester_img.shape)

# Performance of Multires-unet Model trained on Original Dataset

img_num = random.randint(0, len(tester_img)-1)
T2 = testing(tester_img, multires_original, 0.8, img_num)

# Performance of Unet Model trained on Original Dataset

img_num = random.randint(0, len(tester_img)-1)
T2 = testing(tester_img, unet_original, 0.8, img_num)

"""#### ***CONSIDERED MODELS***


*   MultiRes-Unet and Unet with original dataset
*   Cross validation results on MultiRes-Unet
*   Cross validation results on Unet





"""

### DIRECTORY

drive_path = '/content/drive/MyDrive/Colab Notebooks/'
saved_models = '/content/drive/MyDrive/Colab Notebooks/saved_models/'
Train_path = "/data/Train_folder/OriginalTrain"
Mask_path =  "/data/Train_folder/AnnotationsTrain"
test_path = "/testdata/Testers"

### HYPER-PARAMETERS

# (Data Dynamics)
size = 256
IMG_CHANNELS = 3
input_shape = (size, size, IMG_CHANNELS)

# (Model Parameters)
iou = sm.metrics.iou_score
jaccard_loss = sm.losses.bce_jaccard_loss
binary_loss = 'binary_crossentropy'
optimizer = 'Adam'

# (Batch Sizes)
BS16 = 16                            
BS32 = 32

# Loading Image Directory

zip_ref = zipfile.ZipFile(f'{drive_path}Train_folder.zip', 'r')
zip_ref.extractall('/data')
zip_ref.close()

# Loading Test Directory

zip_ref = zipfile.ZipFile(f'{drive_path}Testers.zip', 'r')
zip_ref.extractall('/testdata')
zip_ref.close()

# Loading Data
train_images, mask_images = load_data(Train_path, Mask_path, size)

print(train_images.shape)
print(mask_images.shape)

# Visualization before preprocessing

img_num = random.randint(0, len(train_images)-1)
V = visualize(train_images, mask_images, img_num)
V

# Preprocessing

X, Y = preprocess_customUnet(train_images,mask_images)

print(X.shape)
print(Y.shape)

# Visualizing Preprocessed images

img_num = random.randint(0, len(X)-1)
VP = visualize(X,Y, img_num)
VP

# Data Split

x_train, y_train, x_val, y_val = data_split(X, Y, split_size = 0.2, random_state = 42)

print("Train Data Dynamics:" , x_train.shape, y_train.shape)
print("Test Data Dynamics:" , x_val.shape, y_val.shape)

"""**Training MultiRes-Unet over 150 Epochs**"""

# Building MultiRes UNET model

multires_selected = build_multiresunet(input_shape)
multires_selected.compile(optimizer='adam', loss= binary_loss, metrics=[iou])

history_mr_selected = multires_selected.fit(x=x_train, y= y_train, batch_size= BS16, 
                                    epochs= 150, verbose=1, validation_data= (x_val, y_val))

# Saving model and history
multires.save(f'{saved_models}multires.h5')

# Accuracy
accuracy = model_IOU(multires_selected, x_val, y_val, 0.8)
print('IOU score of model "multires unet model over 150 epochs" is', f'{accuracy:.0%}')

# Evaluation

EV = evaluation(history_mr_selected)

# Performance

img_num = random.randint(0, len(x_val)-1)
perf = performance(x_val, y_val, model = multires_original, threshold=0.8, test_img_number=img_num)

"""**MultiRes Unet model trained with cross validation**"""

# Building Model

multires = build_multiresunet(input_shape)
multires.compile(optimizer='adam', loss= binary_loss, metrics=[iou])

# Producing Cross Validation Data Splits

kfold = KFold(n_splits=5, shuffle=True, random_state=42)
cvscores1 = []
Fold = 1
for train, val in kfold.split(X, Y):
    
    print ('Fold: ',Fold)

    x_train = X[train]
    x_val = X[val]
    y_train = Y[train]
    y_val = Y[val]

    history1 = multires.fit(x=x_train, y= y_train, batch_size= BS16, 
                                    epochs= 100, verbose=1, validation_data= (x_val, y_val))
    

    # evaluate model for each validation set
    scores = multires.evaluate(x_val, y_val, verbose=0)
    print("%s: %.2f%%" % (multires.metrics_names[1], scores[1]))
    cvscores1.append(scores[1])

    Fold = Fold +1

cvscores1

# Accuracy
accuracy1 = model_IOU(multires, x_val, y_val, 0.8)
print('IOU score of model "multires unet model with cross validation" is', f'{accuracy1:.0%}')

# Performance on Validation dataset

img_num = random.randint(0, len(x_val)-1)
perf = performance(x_val, y_val, model = multires, threshold=0.8, test_img_number=img_num)

# Testing on Unseen Data 

tester_img = load_test_data(test_path, size)
print(tester_img.shape)

# Performance on unseen data

img_num = random.randint(0, len(tester_img)-1)
T = testing(tester_img, multires, 0.8, img_num)

"""**Unet model trained with cross validation**"""

# Building Model

unet = build_unet(input_shape)
unet.compile(optimizer='adam', loss= binary_loss, metrics=[iou])

# Producing Cross Validation Data Splits

kfold = KFold(n_splits=5, shuffle=True, random_state=42)
cvscores2 = []
Fold = 1
for train, val in kfold.split(X, Y):
    
    print ('Fold: ',Fold)

    x_train = X[train]
    x_val = X[val]
    y_train = Y[train]
    y_val = Y[val]

    history2 = unet.fit(x=x_train, y= y_train, batch_size= BS32, 
                                    epochs= 100, verbose=1, validation_data= (x_val, y_val))
    

    # evaluate model for each validation set
    scores = unet.evaluate(x_val, y_val, verbose=0)
    print("%s: %.2f%%" % (unet.metrics_names[1], scores[1]))
    cvscores2.append(scores[1])

    Fold = Fold +1

cvscores2

# Accuracy
accuracy2 = model_IOU(unet, x_val, y_val, 0.8)
print('IOU score of model "multires unet model with cross validation" is', f'{accuracy2:.0%}')

# Saving model and history
unet.save(f'{saved_models}unet.h5')