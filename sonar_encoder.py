# Codificador SONAR (Meta) para textos en español.
#
# El paquete oficial `sonar-space` depende de fairseq2, que no corre en Windows.
# Usamos el port a HuggingFace de los mismos pesos (cointegrated/SONAR_200_text_encoder),
# que produce los mismos embeddings de 1024 dimensiones con mean-pooling.

import numpy as np
import torch
from transformers import AutoTokenizer
from transformers.models.m2m_100.modeling_m2m_100 import M2M100Encoder

DEFAULT_MODEL = 'cointegrated/SONAR_200_text_encoder'


class SonarEncoder:
    def __init__(self, model_name: str = DEFAULT_MODEL, lang: str = 'spa_Latn',
                 device: str = None, fp16: bool = True):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.tokenizer.src_lang = lang
        self.model = M2M100Encoder.from_pretrained(model_name).to(self.device).eval()
        if fp16 and self.device == 'cuda':
            self.model = self.model.half()
        self.dim = self.model.config.d_model

    @torch.inference_mode()
    def encode(self, texts, batch_size: int = 32, max_length: int = 512,
               show_progress: bool = False) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        # Ordenar por longitud reduce el padding.
        order = np.argsort([-len(t) for t in texts])
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        it = range(0, len(texts), batch_size)
        if show_progress:
            from tqdm import tqdm
            it = tqdm(it, desc='SONAR', unit='batch')
        for start in it:
            idx = order[start:start + batch_size]
            batch = self.tokenizer([texts[i] for i in idx], return_tensors='pt',
                                   padding=True, truncation=True,
                                   max_length=max_length).to(self.device)
            hidden = self.model(**batch).last_hidden_state.float()
            mask = batch['attention_mask'].unsqueeze(-1).float()
            emb = (hidden * mask).sum(1) / mask.sum(1)
            out[idx] = emb.cpu().numpy()
        return out
