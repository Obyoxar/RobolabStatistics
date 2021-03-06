from robolib.networks.erianet import Erianet, ConvolutionalConfig, ClassicConfig
import matplotlib.pyplot as plt
import numpy as np

insets = (0, 0, 0, 0)
net = Erianet(None, input_image_size=(96, 128), input_to_output_stride=1, config=ClassicConfig)
size = (int(96), int(128))
x, y = net.get_train_data(50, "convlfw", None)

for (a, b), l in zip(x, y):
    plt.figure(1)
    a = np.reshape(a, size)
    b = np.reshape(b, size)
    img = np.concatenate((a, b))
    plt.imshow(img.T, cmap='Greys_r', )
    plt.text(0, -5, str(l))
    plt.show()
