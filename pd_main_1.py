# -*- coding: utf-8 -*-
"""PD_Main_1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1wLHN3g_pfKHMvRXLsx6Ev3uJQUk4lIyu

##**UNET ARCHITECTURE**

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
from pd_functions import augment, model_IOU, iou_acc, evaluation, performance, testing, compare_evaluation_2, compare_evaluation_3
from pd_functions import compare_performance, load_model

sm.set_framework('tf.keras')
sm.framework()

"""#### ***01 - COMPARISON OF LOSS FUNCTIONS***


*   Binary Cross Entropy
*   Jackard loss 
*   Dice Focal loss


"""

### DIRECTORY

drive_path = '/content/drive/MyDrive/Colab Notebooks/'
saved_models = '/content/drive/MyDrive/Colab Notebooks/saved_models/'
Train_path = "/data/Train_folder/OriginalTrain"
Mask_path =  "/data/Train_folder/AnnotationsTrain"
test_path = "/content/Testers"

### HYPER-PARAMETERS

# (Data Dynamics)
size = 256
IMG_CHANNELS = 3
input_shape = (size, size, IMG_CHANNELS)

# (Model Parameters)
iou = sm.metrics.iou_score
acc = 'accuracy'
jaccard_loss = sm.losses.bce_jaccard_loss
binary_loss = 'binary_crossentropy'
focal_dice_loss = sm.losses.binary_focal_dice_loss
optimizer = 'Adam'
backbone = 'resnet34'

# (Batch Sizes)
BS16 = 16                            
BS32 = 32

# Loading Image Directory

zip_ref = zipfile.ZipFile(f'{drive_path}Train_folder.zip', 'r')
zip_ref.extractall('/data')
zip_ref.close()

# Loading Data
train_images, mask_images = load_data(Train_path, Mask_path, size)

print(train_images.shape)
print(mask_images.shape)

# Visualization before preprocessing

img_num = random.randint(0, len(train_images)-1)
V = visualize(train_images, mask_images, img_num)
V

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

# First Model Using Binary Cross Entropy Loss 

cross_entropy = build_unet(input_shape)
cross_entropy.compile(optimizer=optimizer, loss= binary_loss, metrics=[iou])
history1 = cross_entropy.fit(x=x_train, y= y_train, batch_size= BS32, epochs= 100, verbose=1, validation_data= (x_val, y_val))

# Second Model Using Jaccard Loss 

jaccard_score = build_unet(input_shape)
jaccard_score.compile(optimizer=optimizer, loss= jaccard_loss, metrics=[iou])
history2 = jaccard_score.fit(x=x_train, y= y_train, batch_size= BS32, epochs= 100, verbose=1, validation_data= (x_val, y_val))

# Third Model Using Dice Focal Loss

dice_focal = build_unet(input_shape)
dice_focal.compile(optimizer=optimizer, loss= focal_dice_loss, metrics=[iou])
history3 = dice_focal.fit(x=x_train, y= y_train, batch_size= BS32, epochs= 100, verbose=1, validation_data= (x_val, y_val))

accuracy1 = model_IOU(cross_entropy, x_val, y_val, 0.5)
accuracy2 = model_IOU(jaccard_score, x_val, y_val, 0.5)
accuracy3 = model_IOU(dice_focal, x_val, y_val, 0.5)

print('IOU score with loss function "Binary Cross Entropy Loss" is', f'{accuracy1:.0%}')
print('IOU score with loss function "Jaccard Loss" is', f'{accuracy2:.0%}')
print('IOU score with loss function "Focal Dice Loss" is', f'{accuracy3:.0%}')

# Compare performance history of 3 loss functions

LF = compare_evaluation_3(history1, history2, history3, model1 = 'wt binary cross entropy loss', 
                          model2 = 'wt Jaccard Loss',
                          model3 = 'wt Focal Dice loss')
LF

"""**Performance on Test Images**"""

# Binary Cross ENtropy vs Jaccard Loss

CP2 = compare_performance(x_val, y_val, cross_entropy, jaccard_score, 0.5)

# Binary Cross Entropy vs Dice Focal Loss

CP3 = compare_performance(x_val, y_val, cross_entropy, dice_focal, 0.5)

# Saving Models

cross_entropy.save('/content/drive/MyDrive/Colab Notebooks/saved_models/cross_entropy_loss_model.h5')
jaccard_score.save('/content/drive/MyDrive/Colab Notebooks/saved_models/jaccard_loss_model.h5')
dice_focal.save('/content/drive/MyDrive/Colab Notebooks/saved_models/dice_focal_loss_model.h5')

"""####***02 - AFFECTS OF PRETRAINED WEIGHTS IN TRANSFER LEARNING***



*   Model 1 : UNET with pretrained 'imagenet' weights  
*   Model 2 : UNET with random encoder weights
*   Model 3 : UNET with pre-trained Auto-encoder weights







"""

### DIRECTORY

drive_path = '/content/drive/MyDrive/Colab Notebooks/'
saved_models = '/content/drive/MyDrive/Colab Notebooks/saved_models/'
Train_path = "/data/Train_folder/OriginalTrain"
Mask_path =  "/data/Train_folder/AnnotationsTrain"
test_path = "/content/Testers"

### HYPER-PARAMETERS

# (Data Dynamics)
size = 256
IMG_CHANNELS = 3
input_shape = (size, size, IMG_CHANNELS)

# (Model Parameters)
iou = sm.metrics.iou_score                    # Evaluation Metrics
acc = 'accuracy'                              # Metric used for evaluating Autoencoders
jaccard_loss = sm.losses.bce_jaccard_loss
binary_loss = 'binary_crossentropy'           
mse = 'mean_squared_error'                    # Used for training AUtoencoders
optimizer = 'Adam'   
backbone = 'resnet34'                         # Used For Built-in Unet framework from Segmentation Models library

# (Pretrained weights)
pretrained_EW = 'imagenet'                

# (Batch Sizes)
BS16 = 16                            
BS32 = 32

# Loading Image Directory

zip_ref = zipfile.ZipFile(f'{drive_path}Train_folder.zip', 'r')
zip_ref.extractall('/data')
zip_ref.close()

# Loading Data
train_images, mask_images = load_data(Train_path, Mask_path, size)

print(train_images.shape)
print(mask_images.shape)

# Visualization before preprocessing

img_num = random.randint(0, len(train_images)-1)
V = visualize(train_images, mask_images, img_num)
V

# Preprocessing for built-in Unet

X, Y = preprocessing(train_images,mask_images, backbone)

print(X.shape)
print(Y.shape)

# Preprocessing for custom built Unet

X1, Y1 = preprocess_customUnet(train_images,mask_images)

print(X1.shape)
print(Y1.shape)

# Visualizing Preprocessed images

img_num = random.randint(0, len(X)-1)
VP = visualize(X,Y, img_num)
VP

img_num = random.randint(0, len(X)-1)
VP1 = visualize(X1,Y1, img_num)
VP1

# Data Split

x_train, y_train, x_val, y_val = data_split(X, Y, split_size = 0.2, random_state = 42)

print("Train Data Dynamics:" , x_train.shape, y_train.shape)
print("Test Data Dynamics:" , x_val.shape, y_val.shape)

# Data Split

x_train1, y_train1, x_val1, y_val1 = data_split(X1, Y1, split_size = 0.2, random_state = 42)

print("Train Data Dynamics:" , x_train1.shape, y_train1.shape)
print("Test Data Dynamics:" , x_val1.shape, y_val1.shape)

"""**BUILDING AUTOENCODER MODEL AND SAVING WEIGHTS FOR UNET**"""

# Build Autoencoder model and save weights to be added in unet training

autoencoder = build_autoencoder(input_shape)
autoencoder.compile(optimizer='adam', loss=mse, metrics=[acc])
AE = autoencoder.fit(X1, X1, epochs=30, verbose=1)

# Visualize performance of autoencoder model

num = random.randint(0, len(train_images)-1)         # Random image number 

test_img = np.expand_dims(X1[num], axis=0)           # Input image      
pred = autoencoder.predict(test_img)                 # Prediction

plt.subplot(1,2,1)
plt.imshow(test_img[0])
plt.title('Original')
plt.subplot(1,2,2)
plt.imshow(pred[0].reshape(256,256,3))
plt.title('Reconstructed')
plt.show()

# Building Unet with encoder layers replaced with that of autoencoders

unet_model_weights = build_unet(input_shape)

#Set weights to encoder part of the U-net (first 35 layers taken from autoencoders)
for l1, l2 in zip(unet_model_weights.layers[:35], autoencoder.layers[0:35]):
    l1.set_weights(l2.get_weights())
unet_model_weights.compile(optimizer=optimizer, loss=binary_loss, metrics=[iou])
unet_model_weights.save(f'{saved_models}unet_model_weights.h5')

"""**TRAINING 3 MODELS**"""

# Built-in UNET architecture from keras segmentation models. Transfer Learning using pre-trained encoder weights trained on 'imagenet'
# Batch size = 32 , Epochs = 100 

TransferLearning_wt_imagenet = sm.Unet(backbone, encoder_weights= 'imagenet')
TransferLearning_wt_imagenet.compile(optimizer=optimizer, loss= binary_loss, metrics=[iou])
history_TL1 = TransferLearning_wt_imagenet.fit(x=x_train, y= y_train, batch_size= BS32, epochs= 100, verbose=1, validation_data= (x_val, y_val))

# Saving Model and History

TransferLearning_wt_imagenet.save(f'{saved_models}TransferLearning_wt_imagenet.h5')
np.save(f'{saved_models}TransferLearning_wt_imagenet_history.npy', history_TL1.history)

# Built-in UNet architecture from keras segmentation models. Trained with random encoder weights
# Batch size = 32 , Epochs = 100

transfered_unet_wt_randomweights = sm.Unet(backbone, encoder_weights= None)
transfered_unet_wt_randomweights.compile(optimizer=optimizer, loss= binary_loss, metrics=[iou])
history_TL2 = transfered_unet_wt_randomweights.fit(x=x_train, y= y_train, batch_size= BS32, epochs= 100, verbose=1, validation_data= (x_val, y_val))

# Saving Model and History

transfered_unet_wt_randomweights.save(f'{saved_models}TransferLearning_wt_randomweights.h5')
np.save(f'{saved_models}TransferLearning_wt_randomweights_history.npy', history_TL2.history)

# Designed UNET architecture with pretrained encoder weights using autoencoders.
# Batch size = 32 , Epochs = 100 

unet_wt_autoencoder_weights = build_unet(input_shape)
unet_wt_autoencoder_weights.load_weights(f'{saved_models}unet_model_weights.h5')

unet_wt_autoencoder_weights.compile(optimizer=optimizer, loss=binary_loss, metrics=[iou])
history_AE = unet_wt_autoencoder_weights.fit(x=x_train1, y= y_train1, batch_size= BS32, epochs= 100, verbose=1, validation_data= (x_val1, y_val1))

# Saving model and History

unet_wt_autoencoder_weights.save(f'{saved_models}unet_wt_autoencoder_weights_model.h5')
np.save(f'{saved_models}unet_wt_autoencoder_history.npy', history_AE.history)

# Loading Saved Models

TransferLearning_wt_imagenet = load_model(f'{saved_models}TransferLearning_wt_imagenet.h5', compile=False)
transfered_unet_wt_randomweights = load_model(f'{saved_models}TransferLearning_wt_randomweights.h5', compile=False)

# Loading Saved History

history_TL1 = np.load(f'{saved_models}TransferLearning_wt_imagenet_history.npy', allow_pickle='TRUE').item()
history_TL2 = np.load(f'{saved_models}TransferLearning_wt_randomweights_history.npy', allow_pickle='TRUE').item()
history_TL3 = np.load(f'{saved_models}unet_wt_autoencoder_history.npy', allow_pickle='TRUE').item()

# Comparing Mean Accuracy of 3 Models

accuracy1 = model_IOU(TransferLearning_wt_imagenet, x_val, y_val, 0.5)
accuracy2 = model_IOU(transfered_unet_wt_randomweights, x_val, y_val, 0.5)
accuracy3 = model_IOU(unet_wt_autoencoder_weights, x_val, y_val, 0.5)

print('IOU score of model "TransferLearning_wt_imagenet" is', f'{accuracy1:.0%}')
print('IOU score of model "TransferLearning_wt_randomweights" is', f'{accuracy2:.0%}')
print('IOU score of model "TransferLearning_wt_autoencoder_weights" is', f'{accuracy3:.0%}')

"""**Comparison of IOU Accuracy over 100 Epochs**"""

def compare_evaluation(history1, history2, history3, model1, model2, model3):

    val_acc1 = history1['val_iou_score']
    val_acc2 = history2['val_iou_score']
    val_acc3 = history3['val_iou_score']
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

# Compare history of 3 models

CE = compare_evaluation(history_TL1, history_TL2, history_TL3, model1 = 'TransferLearning_wt_imagenet', 
                          model2 = 'TransferLearning_wt_randomweights',
                          model3 = 'TransferLearning_wt_autoencoder_weights')
CE

"""**PERFORMANCE ON TEST IMAGES**"""

# Comparison of Transfer Learning with imagenet weights vs Autoencoder weights

testing = compare_performance(x_val1, y_val1, TransferLearning_wt_imagenet , unet_wt_autoencoder_weights, 0.5)

"""#### ***03 - COMPARISON OF ORIGINAL AND AUGMENTED DATA***


*   Original Data
*   Augmented Data
*   Original and Augmented Data Using Autoencoders
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
backbone = 'resnet34'

# (Pretrained weights)
pretrained_EW = 'imagenet'

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

# Preprocessing for transferred/built-in Unet

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

"""**ORIGINAL DATA**"""

# Building custom built Unet architecture for training original dataset (without using pretrained autencoder weights)

original_unet = build_unet(input_shape)                                   # Designed Unet function
original_unet.compile('Adam', loss= binary_loss, metrics= [iou]) 

history_orig = original_unet.fit(x=x_train, y= y_train, batch_size= 32, epochs= 100, verbose=1, validation_data= (x_val, y_val))

# Accuracy
accuracy1 = model_IOU(original_unet, x_val, y_val, 0.5)
print('IOU score of model "original_unet" is', f'{accuracy1:.0%}')

# Saving model and history
original_unet.save(f'{saved_models}custom_unet_original.h5')

# Saving history
np.save(f'{saved_models}custom_unet_original_history.npy', history_orig.history)

# Evaluation of Training and Validation Loss and Accuracy

EV1 = evaluation(history_orig)

"""**AUGMENTED DATA**"""

# Data Augmentation (using designed Augment Fnction)

train_generator, val_generator, trainImage_generated, trainMask_generated = augment(X, Y, 0.2)

# Visualize generated images

VG = visualize_generated(trainImage_generated,trainMask_generated)

# Building custom Unet architecture for training augmented dataset (without pretrained autoencoder weights)

augmented_unet = build_unet(input_shape)                                   
augmented_unet.compile(optimizer= optimizer, loss= binary_loss, metrics= [iou]) 

history_aug = augmented_unet.fit_generator(train_generator, validation_data= val_generator, steps_per_epoch= 50, validation_steps= 50, epochs= 100)

# Mean Accuracy
accuracy2 = model_IOU(augmented_unet, x_val, y_val, 0.5)
print('IOU score of model "augmented_unet" is', f'{accuracy2:.0%}')

# Saving model and history
augmented_unet.save(f'{saved_models}custom_unet_augmented.h5')
np.save(f'{saved_models}custom_unet_augmented_history.npy', history_aug.history)

# Evaluation of Training and Validation Loss and Accuracy
EV2 = evaluation(history_aug)

"""**Comparison of original vs augmented data history**"""

CE2 = compare_evaluation_2(history_orig, history_aug, model1 = 'custom_unet_unaugmented', 
                          model2 = 'custom_unet_augmented')

"""**PERFORMANCE OF TWO MODELS ON TEST DATA**"""

original_unet = load_model(f'{saved_models}custom_unet_original.h5', compile=False)
augmented_unet = load_model(f'{saved_models}custom_unet_augmented.h5', compile=False)

# Comparison of Transfer Learning with imagenet weights vs Autoencoder weights

testing = compare_performance(x_val, y_val, original_unet , augmented_unet, 0.5)

"""**USING AUGMENTATION WITH PRETRAINED AUTOENCODER WEIGHTS**"""

# Building designed Unet architecture for training augmented dataset using pretrained autoencoders weights

augmented_unet = build_unet(input_shape)                                   # Custom built Unet function
augmented_unet.load_weights(f'{saved_models}unet_model_weights.h5')        # Loading pretrained weights

augmented_unet.compile('Adam', loss= binary_loss, metrics= [iou]) 

history_aug_pretrained = augmented_unet.fit_generator(train_generator, validation_data= val_generator, steps_per_epoch= 50, validation_steps= 50, epochs= 100)

# Mean Accuracy

accuracy3 = model_IOU(augmented_unet, x_val, y_val, 0.5)
print('IOU score of model "augmented_unet_pretrained" is', f'{accuracy3:.0%}')

# Saving model and history

augmented_unet.save(f'{saved_models}augmented_unet_pretrained.h5')
np.save(f'{saved_models}augmented_unet_pretrained_history.npy', history_aug_pretrained.history)

"""**Comparison of Augmented Unet with and without pretrained weights**"""

# Loading previosuly experimented augmented Unet history

history_aug = np.load(f'{saved_models}custom_unet_augmented_history.npy', allow_pickle='TRUE').item()

val_acc1 = history_aug['val_iou_score']
val_acc2 = history_aug_pretrained.history['val_iou_score']

epochs = range(1, len(val_acc1) +1)

plt.figure(figsize=(12, 8))
plt.plot(epochs, val_acc1,'xkcd:blue', label= f'augmented_unet')
plt.plot(epochs, val_acc2, 'xkcd:orange', label=f'augmented_unet_pretrained')
plt.title('Comparison of Validation accuracy from two models')
plt.xlabel('Epochs')
plt.ylabel('IOU')
plt.legend(loc='upper left')
plt.grid()
plt.show()

"""**Comparison of Performance (Augmented Unet with and without pretrained Autoencoder Weights)**"""

# Loading Saved models

custom_unet_augmented = load_model(f'{saved_models}custom_unet_augmented.h5', compile=False)
augmented_unet_pretrained = load_model(f'{saved_models}augmented_unet_pretrained.h5', compile=False)

# Comparison of Augmented Unet model with and without Pretrained Autoencoder weights

testing = compare_performance(x_val, y_val, custom_unet_augmented , augmented_unet_pretrained, 0.8)

"""**TESTING ON UNSEEN DATA**"""

augmented_unet_pretrained = load_model(f'{saved_models}augmented_unet_pretrained.h5', compile=False)
original_unet = load_model(f'{saved_models}custom_unet_original.h5', compile=False)
original_unet_pretrained = load_model(f'{saved_models}unet_wt_autoencoder_weights_model.h5', compile=False)

# Testing on Unseen Data 

tester_img = load_test_data(test_path, size)
print(tester_img.shape)

# Model Unet trained on original dataset without pretrained weights

img_num = random.randint(0, len(tester_img)-1)
T2 = testing(tester_img, original_unet, 0.8, img_num=31)