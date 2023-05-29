# -*- coding: utf-8 -*-
"""Untitled0.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1JFYMFVP1vtdwqaNa9QHmKhYeRWQywNk7
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import matplotlib.pyplot as plt
from torchvision import datasets, transforms,models
from torch.utils.data import DataLoader
from torchvision.utils import save_image
import torchvision.models.resnet as resnet
from tqdm import tqdm
from torch.optim.lr_scheduler import StepLR

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Hyper-parameters
latent_size = 100
batch_size = 512
epochs = 50
lr = 0.0005

transform = transforms.Compose([
    transforms.Resize(28),
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])

train_dataset = datasets.EMNIST('data', train=True,split='balanced', download=True, transform=transform)
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,drop_last=True)

class Generator(nn.Module):
    def __init__(self):
        super(Generator, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(latent_size, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 7 * 7 * 128),
            nn.BatchNorm1d(7 * 7 * 128),
            nn.ReLU()
        )
        self.conv = nn.Sequential(
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.ConvTranspose2d(64, 1, kernel_size=4, stride=2, padding=1),
            nn.Tanh()
        )
    def forward(self, x):
        x = self.fc(x)
        # print(x.shape)
        x = x.view(-1,128 , 7, 7)
        x = self.conv(x)
        # x = x.repeat(1,3,1,1)
        # print(x.shape)
        return x

class ResNet56(nn.Module):
    def __init__(self):
        super(ResNet56, self).__init__()
        self.resnet50 = models.resnet50(pretrained=False)
        self.resnet50.fc = nn.Linear(256, 1)
        self.sigmoid = nn.Sigmoid()
        self.resnet50.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        
    def forward(self, x):
        # print(x.shape)
        x = self.resnet50.conv1(x)
        x = self.resnet50.bn1(x)
        x = self.resnet50.relu(x)
        x = self.resnet50.maxpool(x)

        x = self.resnet50.layer1(x)
        # print(x.shape)
        # x = self.resnet50.layer2(x)
        # x = self.resnet50.layer3(x)
        # x = self.resnet50.layer4(x)

        x = self.resnet50.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.resnet50.fc(x)
        x = self.sigmoid(x)

        return x

generator = Generator().to(device)
discriminator = ResNet56().to(device)

total_params = sum(p.numel() for p in discriminator.parameters())
print(total_params)

# for i, param in enumerate(discriminator.parameters()):
#     print(i)
#     if i < 140:
#         param.requires_grad = False

criterion = nn.BCELoss()
g_optimizer = optim.Adam(generator.parameters(), lr=0.0002)
d_optimizer = optim.Adam(discriminator.parameters(), lr=0.0002)

total_steps = len(train_loader)
d_losslist=[]
g_losslist=[]
for epoch in range(epochs):
    generator.train()
    discriminator.train()
    d_losses=0
    g_losses=0
    for i, (images, _) in tqdm(enumerate(train_loader)):
        # Configure real and fake labels for discriminator loss
        real_labels = torch.ones(images.size(0), 1).to(device)
        fake_labels = torch.zeros(images.size(0), 1).to(device)
        # Train discriminator with real images
        real_images = images.to(device)
        d_optimizer.zero_grad()
        real_outputs = discriminator(real_images)
        d_loss_real = criterion(real_outputs, torch.ones_like(real_outputs))
        # Train discriminator with fake images
        noise = torch.randn(images.size(0), latent_size).to(device)
        fake_images = generator(noise)
        fake_outputs = discriminator(fake_images.detach())
        d_loss_fake = criterion(fake_outputs,  torch.zeros_like(real_outputs))
        
        # Update discriminator parameters
        d_loss = (d_loss_real + d_loss_fake)
        d_loss.backward()
        if i%10==0:
         d_losslist.append(d_loss/batch_size)
        d_optimizer.step()
        # scaler.update()
        d_losses+=d_loss
        # Train generator
        g_optimizer.zero_grad()
        noise1 = torch.randn(images.size(0), latent_size).to(device)
        fake_images1 = generator(noise1)

        fake_outputs1 = discriminator(fake_images1)
        
        g_loss = criterion(fake_outputs1, torch.ones_like(fake_outputs1))
        g_loss.backward()
        g_losses+=g_loss
        if i%10==0:
         g_losslist.append(g_loss/batch_size)
        # Update generator parameters
        g_optimizer.step()
    if epoch%2 == 0:
      with torch.no_grad():
        generator.eval()
        noise=torch.randn(20, 100).to(device)
        generated_images = generator(noise)
        generated_images = (generated_images + 1) / 2  # Denormalize the generated images
        generated_images = torchvision.utils.make_grid(generated_images, nrow=5).cpu()
        plt.imshow(generated_images.permute(1, 2, 0))
        plt.axis('off')
        plt.title(f'Generated images after epoch {epoch + 1}')
        plt.show()
    
    print(epoch , d_losses/len(train_loader),g_losses/len(train_loader))

g_l=[]
d_l=[]
for i,j in zip(d_losslist,g_losslist):
  i=i.cpu()
  j=j.cpu()
  i=i.detach().numpy()
  j=j.detach().numpy()
  g_l.append(j)
  d_l.append(i)

import matplotlib.pyplot as plt
plt.title("Generator loss")
plt.plot(g_l)
plt.xlabel('Iteration')
plt.ylabel('Loss')

plt.title("Discriminator loss")
plt.plot(d_l)
plt.xlabel('Iteration')
plt.ylabel('Loss')

