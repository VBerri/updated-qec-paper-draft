from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class ToyFiLMDecoder(nn.Module):
    def __init__(self, syndrome_dim: int, calib_dim: int, hidden: int = 64):
        super().__init__()
        self.syndrome_encoder = nn.Sequential(
            nn.Linear(syndrome_dim, hidden),
            nn.ReLU(),
        )
        self.film = nn.Linear(calib_dim, hidden * 2)
        self.head = nn.Linear(hidden, 1)

    def forward(self, syndrome: torch.Tensor, calibration: torch.Tensor) -> torch.Tensor:
        h = self.syndrome_encoder(syndrome)
        gamma_beta = self.film(calibration)
        gamma, beta = torch.chunk(gamma_beta, chunks=2, dim=-1)
        modulated = (1.0 + gamma) * h + beta
        return self.head(torch.relu(modulated))


def train_and_predict_toy_film_decoder(
    syndrome: np.ndarray,
    labels: np.ndarray,
    calibration_vector: np.ndarray,
    epochs: int = 6,
    batch_size: int = 256,
    lr: float = 1e-3,
    seed: int = 12345,
) -> np.ndarray:
    torch.manual_seed(seed)
    np.random.seed(seed)

    x = syndrome.astype(np.float32)
    y = labels.astype(np.float32).reshape(-1, 1)
    c = np.repeat(calibration_vector.astype(np.float32)[None, :], repeats=x.shape[0], axis=0)

    ds = TensorDataset(torch.from_numpy(x), torch.from_numpy(c), torch.from_numpy(y))
    dl = DataLoader(ds, batch_size=batch_size, shuffle=True)

    model = ToyFiLMDecoder(syndrome_dim=x.shape[1], calib_dim=c.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    model.train()
    for _ in range(epochs):
        for xb, cb, yb in dl:
            opt.zero_grad()
            logits = model(xb, cb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        logits = model(torch.from_numpy(x), torch.from_numpy(c))
        preds = (torch.sigmoid(logits).numpy() > 0.5).astype(np.uint8)
    return preds
