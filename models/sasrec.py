import torch
import torch.nn as nn
import numpy as np
from typing import List, Tuple

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_seq_length: int):
        super().__init__()
        position = torch.arange(max_seq_length).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-np.log(10000.0) / d_model))
        pe = torch.zeros(max_seq_length, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:x.size(0)]

class SasRec(nn.Module):
    def __init__(
        self,
        num_items: int,
        max_seq_length: int,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dropout: float = 0.1
    ):
        super().__init__()
        self.num_items = num_items
        self.max_seq_length = max_seq_length
        self.d_model = d_model

        # Item Embedding
        self.item_embeddings = nn.Embedding(num_items + 1, d_model, padding_idx=0)
        
        # Position Embedding
        self.pos_embedding = PositionalEncoding(d_model, max_seq_length)
        
        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Layer Normalization
        self.layer_norm = nn.LayerNorm(d_model)
        
        # Output Layer
        self.output_layer = nn.Linear(d_model, num_items + 1)

    def forward(self, input_seq: torch.Tensor, attention_mask: torch.Tensor = None) -> torch.Tensor:
        # input_seq shape: (batch_size, seq_length)
        batch_size = input_seq.size(0)
        
        # Item Embedding
        x = self.item_embeddings(input_seq)  # (batch_size, seq_length, d_model)
        
        # Position Embedding
        x = self.pos_embedding(x)
        
        # Create attention mask if not provided
        if attention_mask is None:
            attention_mask = (input_seq == 0).transpose(0, 1)  # (seq_length, batch_size)
        
        # Transformer Encoder
        x = self.transformer_encoder(x, src_key_padding_mask=attention_mask)
        
        # Layer Normalization
        x = self.layer_norm(x)
        
        # Output Layer
        output = self.output_layer(x)  # (batch_size, seq_length, num_items + 1)
        
        return output

    def predict(self, input_seq: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        예측을 수행하는 메서드
        Returns:
            Tuple[torch.Tensor, torch.Tensor]: (예측 점수, 예측된 아이템 인덱스)
        """
        self.eval()
        with torch.no_grad():
            output = self(input_seq)
            scores = output[:, -1, :]  # 마지막 시퀀스의 예측만 사용
            _, predicted = torch.max(scores, dim=1)
            return scores, predicted

class SasRecRecommender:
    def __init__(
        self,
        num_items: int,
        max_seq_length: int = 50,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dropout: float = 0.1,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    ):
        self.device = device
        self.model = SasRec(
            num_items=num_items,
            max_seq_length=max_seq_length,
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers,
            dropout=dropout
        ).to(device)
        
    def prepare_sequence(self, sequence: List[int], max_length: int) -> torch.Tensor:
        """
        시퀀스를 모델 입력 형식으로 변환
        """
        if len(sequence) > max_length:
            sequence = sequence[-max_length:]
        else:
            sequence = [0] * (max_length - len(sequence)) + sequence
        return torch.tensor(sequence, dtype=torch.long).unsqueeze(0).to(self.device)
    
    def recommend(self, sequence: List[int], top_k: int = 5) -> List[Tuple[int, float]]:
        """
        주어진 시퀀스에 대해 top-k 추천을 수행
        """
        input_seq = self.prepare_sequence(sequence, self.model.max_seq_length)
        scores, _ = self.model.predict(input_seq)
        scores = scores.squeeze().cpu().numpy()
        
        # 이미 시퀀스에 있는 아이템은 제외
        scores[sequence] = -np.inf
        
        # top-k 아이템 선택
        top_items = np.argsort(scores)[-top_k:][::-1]
        top_scores = scores[top_items]
        
        return list(zip(top_items.tolist(), top_scores.tolist())) 