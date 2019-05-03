import numpy as np
from simplemodel import *
import torch.optim as optim
import pickle
import os
import itertools
import librosa
from specgrams_helper import *

sampleRate = 22050
helper = SpecgramsHelper(2*sampleRate, tuple([192, 512]), 0.75, sampleRate, 1)

def writeWav(spectogram, filename = "trial.wav"):
                global helper, sampleRate
                outtrue = helper.melspecgrams_to_waves(spectogram)
                with tf.Session() as sess:
                                outtrue = outtrue.eval()
                librosa.output.write_wav(filename, outtrue[0], sampleRate)


bigbasepath = "../../VEGAS/VEGAS/data"
trainEpoch = int(2e5)
height = 48
width = int(8 * height / 3)
gpu = "cuda:1"

weight = 0.0003
dropLr = 15
dropBy = 2
numIter = 512
bs = 64


index=0


# mmean = mmean.detach().cpu().numpy()
# mstd = mstd.detach().cpu().numpy()

SIZE = 128
model = torch.load("model2.pth")#AudioVAE(gpu=gpu, specShape = (height, width), genChannels = 2*SIZE, encChannels = 2*SIZE, latentDim = SIZE)
model = model.to(gpu)

LR = {
                'Encoder' : 3e-4,
                'Generator' : 3e-4,
   }

Optimizer = {
                                'Encoder':optim.Adam(model.encoder.parameters(), lr=LR['Encoder']),
                                'Generator':optim.Adam(model.decoder.parameters(), lr=LR['Generator'])
                }

for i in range(trainEpoch):
        for alpha,beta in itertools.product(range(4), range(10)):
                Path = os.path.join(bigbasepath, 'subdata' + str(alpha+1), 'wav', str(beta)+'.pkl')
                data = pickle.load(open(Path, 'rb'))
                data = np.transpose(data, [0, 3, 1, 2])[:,:,::4,::4]
                data = torch.Tensor(data)##[:256]
                numIter = data.shape[0] // bs

                mstd = [0 for _ in range(data.shape[0])]
                mmean = [0 for _ in range(data.shape[0])]
                for iij in range(data.shape[0]):
                                mmean[iij] = data[iij].mean().detach().cpu().numpy()
                                mstd[iij] = data[iij].std().detach().cpu().numpy()
                                data[iij] = (data[iij] - data[iij].mean()) / data[iij].std()

                print_losses = [0, 0, 0]
                for j in range(numIter):
                                #print(i, j, alpha, beta)

                                currentData = data[j*bs:(j + 1)*bs].to(gpu)
                                # print("hererere----------------------------")
                                #print(currentData.shape)
                                temp = model(currentData[:,:1,:,:])
                                mean = temp[0]
                                sigma = temp[1]
                                reconstructedMean = temp[2]
                                reconstructedSigma = temp[3]

                                losses = vae_loss(mean, sigma, reconstructedMean, reconstructedSigma, currentData[:,:1,:,:], index, weight)
                                loss = sum(list(losses))
                                loss.backward()

                                if i%25 == 24:
                                                # temp3 = reconstructedMean[0]
                                                # temp3 = temp3.detach().cpu().numpy()
                                                # temp3 = temp3.transpose(1,2,0)*mstd[j]+mmean[j]
                                                print(reconstructedMean[0].shape)

                                                temp2 = np.zeros(tuple([ reconstructedMean[0].shape[1], reconstructedMean[0].shape[2], 2]))
                                                # temp2 = temp2.detach().cpu().numpy()
                                                temp2[:,:,0] = reconstructedMean[0,0,:,:].detach().cpu().numpy()
                                                temp2 = temp2*mstd[j]+mmean[j]
                                                temp2[:,:,1] = currentData[0,1,:,:]
                                                reconstructed = np.zeros(tuple([192,512,2]))
                                                for iii in range(temp2.shape[0]):
                                                                for jjj in range(temp2.shape[1]):
                                                                                for ii in range(4):
                                                                                                for jj in range(4):
                                                                                                                reconstructed[4*iii+ii, 4*jjj+jj, :] = temp2[iii, jjj, :]

                                                reconstructed = reconstructed.reshape((1, data.shape[2]*4, data.shape[3]*4, data.shape[1]))
                                                writeWav(reconstructed.astype(np.float32), filename = "wavdumps/temp_re"+str(j)+".wav")

                                #print(currentData.shape, reconstructedMean.shape)
                                print_losses[0] += losses[0].item()
                                print_losses[1] += losses[1].item()
                                print_losses[2] += ((currentData - reconstructedMean)**2).mean().item()

                                for _,myoptim in Optimizer.items():
                                                myoptim.step()
                                                myoptim.zero_grad()

                print(i, print_losses[0]/numIter / (weight), "\t", print_losses[1]/numIter, "\t", print_losses[2] / numIter)

        if i %dropLr == dropLr - 1:
                        LR['Encoder']/= dropBy
                        LR['Generator']/= dropBy
        if i%10:
                        torch.save(model, 'model2.pth')



