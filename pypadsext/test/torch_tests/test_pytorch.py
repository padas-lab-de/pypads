import os

from pypads.test.base_test import BaseTest
from pypads.test.sklearn.mappings.mapping_sklearn_test import _get_mapping

torch_padre = _get_mapping(os.path.join(os.path.dirname(__file__), "torch_1_4_0.json"))


# https://github.com/jcjohnson/pytorch-examples/blob/master/nn/two_layer_net_nn.py
def torch_simple_example():
    from torch.nn import Sequential, Conv2d, Linear, ReLU, MaxPool2d, Dropout2d, Softmax, CrossEntropyLoss
    from torch.optim import Adam
    import torch
    from torchvision import datasets
    from torchvision.transforms import transforms

    log_interval = 100

    class Flatten(torch.nn.Module):
        __constants__ = ['start_dim', 'end_dim']

        def __init__(self, start_dim=1, end_dim=-1):
            super(Flatten, self).__init__()
            self.start_dim = start_dim
            self.end_dim = end_dim

        def forward(self, input: torch.Tensor):
            return input.flatten(self.start_dim, self.end_dim)

    def train(model, device, train_loader, optimizer, epoch):
        model.train()
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(device), target.to(device)
            optimizer.zero_grad()
            output = model(data)
            loss = loss_fn(output, target)
            loss.backward()
            optimizer.step()
            if batch_idx % log_interval == 0:
                print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                    epoch, batch_idx * len(data), len(train_loader.dataset),
                           100. * batch_idx / len(train_loader), loss.item()))

    def test(model, device, test_loader):
        model.eval()
        test_loss = 0
        correct = 0
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(device), target.to(device)
                output = model(data)
                test_loss += loss_fn(output, target).item()  # sum up batch loss
                pred = output.argmax(dim=1, keepdim=True)  # get the index of the max log-probability
                correct += pred.eq(target.view_as(pred)).sum().item()

    # Set the random seed
    torch.manual_seed(0)
    device = torch.device('cpu')

    # Load Mnist Dataset
    train_mnist = datasets.MNIST('data', train=True, download=False, transform=transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ]))
    test_mnist = datasets.MNIST('data', train=False, download=False, transform=transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ]))

    # N is batch size;
    N, epochs = 100, 1

    # Training Loader
    train_loader = torch.utils.data.DataLoader(train_mnist, batch_size=N)

    # Testing Loader
    test_loader = torch.utils.data.DataLoader(test_mnist, batch_size=N)

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
        Softmax(dim=1)
    ).to(device)

    # Define loss function
    loss_fn = CrossEntropyLoss().to(device)

    # define the optimize
    optimizer = Adam(model.parameters(), lr=1e-4)

    # Training loop
    for epoch in range(1, epochs + 1):
        train(model=model, device=device, train_loader=train_loader, optimizer=optimizer, epoch=epoch)
        test(model=model, device=device, test_loader=test_loader)


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
