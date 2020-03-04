import os

from pypads.test.base_test import BaseTest
from pypads.test.sklearn.mappings.mapping_sklearn_test import _get_mapping

torch_padre = _get_mapping(os.path.join(os.path.dirname(__file__), "torch_1_4_0.json"))


# https://github.com/jcjohnson/pytorch-examples/blob/master/nn/two_layer_net_nn.py
def torch_simple_example():
    from torch.nn import Sequential, Conv2d, Linear, ReLU, MaxPool2d, MSELoss, LogSoftmax, Dropout2d
    from torch.optim import SGD
    import torch
    from torchvision import datasets
    from torchvision.transforms import transforms

    class Flatten(torch.nn.Module):
        __constants__ = ['start_dim', 'end_dim']

        def __init__(self, start_dim=1, end_dim=-1):
            super(Flatten, self).__init__()
            self.start_dim = start_dim
            self.end_dim = end_dim

        def forward(self, input: torch.Tensor):
            return input.flatten(self.start_dim, self.end_dim)

    # Set the random seed
    torch.manual_seed(0)
    device = torch.device('cpu')

    # Load Mnist Dataset
    mnist = datasets.MNIST('data', train=True, download=False, transform=transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ]))

    # N is batch size;
    N, epochs = 64, 50

    # Training Loader
    loader = torch.utils.data.DataLoader(mnist, batch_size=N)

    # Create random Tensors to hold inputs and outputs
    # x = torch.randn(N, D_in, device=device)
    # y = torch.randn(N, D_out, device=device)

    # Use the nn package to define our model as a sequence of layers
    model = Sequential(
        Conv2d(1, 32, 3, 1),
        ReLU(),
        Conv2d(32, 64, 3, 1),
        MaxPool2d(2),
        Dropout2d(0.25),
        Flatten(),
        Linear(9216, 128),
        ReLU(),
        Dropout2d(0.5),
        Linear(128, 10),
        LogSoftmax(dim=1)
    ).to(device)

    # define the loss function
    loss_fn = MSELoss(reduction='sum')

    # define the optimize
    optimizer = SGD(model.parameters(), lr=1e-4, momentum=0.9)

    # Training loop
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        # Forward pass: Compute predicted y by passing x to the model
        y_pred = model(x)

        # Compute and print loss
        loss = loss_fn(y_pred, y)
        print(loss.item())

        # Zero gradients, perform a backward pass, and update the weights.
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    # for t in range(epochs):
    #     # Forward pass: Compute predicted y by passing x to the model
    #     y_pred = model(x)
    #
    #     # Compute and print loss
    #     loss = loss_fn(y_pred, y)
    #     print(t, loss.item())
    #
    #     # Zero gradients, perform a backward pass, and update the weights.
    #     optimizer.zero_grad()
    #     loss.backward()
    #     optimizer.step()


# noinspection PyMethodMayBeStatic
class PyPadsTorchTest(BaseTest):
    def test_torch_Sequential_class(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        PyPadrePads(mapping=torch_padre)

        import timeit
        t = timeit.Timer(torch_simple_example)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------
