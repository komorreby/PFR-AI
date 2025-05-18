import asyncio
from typing import Any, List, Optional

# Необходимо установить: pip install sentence-transformers torch einops 'numpy<2'
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError("Необходимо установить sentence-transformers: pip install sentence-transformers")

from llama_index.core.base.embeddings.base import BaseEmbedding, Embedding
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.callbacks.base import CallbackManager
from llama_index.core.constants import DEFAULT_EMBED_BATCH_SIZE

# Модель по умолчанию
DEFAULT_JINA_V3_MODEL = "jinaai/jina-embeddings-v3"

class JinaV3Embedding(BaseEmbedding):
    """
    Класс-обертка для использования модели jinaai/jina-embeddings-v3
    с LlamaIndex, поддерживающий специфичные для задачи эмбеддинги (Task LoRA).

    Требует установки sentence-transformers, torch, einops.
    """
    model_name: str = Field(
        default=DEFAULT_JINA_V3_MODEL, description="Имя модели Hugging Face."
    )
    
    _model: SentenceTransformer = PrivateAttr()
    _device: Optional[str] = PrivateAttr()

    def __init__(
        self,
        model_name: str = DEFAULT_JINA_V3_MODEL,
        embed_batch_size: Optional[int] = None, # Используем None, чтобы потом взять дефолт LlamaIndex
        callback_manager: Optional[CallbackManager] = None,
        device: Optional[str] = None, # Например, 'cuda' или 'cpu'
        trust_remote_code: bool = True, # Необходимо для jina-v3
        **kwargs: Any,
    ) -> None:
        # Получаем размер батча по умолчанию из настроек LlamaIndex, если не задан
        effective_batch_size = embed_batch_size or DEFAULT_EMBED_BATCH_SIZE
        
        super().__init__(
            model_name=model_name, 
            embed_batch_size=effective_batch_size, 
            callback_manager=callback_manager,
            **kwargs
        )

        try:
            self._model = SentenceTransformer(
                model_name, 
                device=device,
                trust_remote_code=trust_remote_code
            )
            # Сохраняем устройство, которое фактически используется моделью
            self._device = str(self._model.device) 
            print(f"JinaV3Embedding: Модель '{model_name}' загружена на устройство '{self._device}'.")
        except Exception as e:
            print(f"Ошибка при загрузке модели {model_name}: {e}")
            raise

    @classmethod
    def class_name(cls) -> str:
        return "JinaV3Embedding"

    # --- Синхронные методы ---

    def _get_query_embedding(self, query: str) -> Embedding:
        """Получает эмбеддинг для запроса (query)."""
        if not self._model:
            raise ValueError("Модель эмбеддингов не инициализирована.")
        
        embedding_dim = self._model.get_sentence_embedding_dimension()
        if not embedding_dim:
            print("Ошибка: Не удалось определить размерность эмбеддингов.")
            return []

        embeddings = self._model.encode(
            [query], 
            task="retrieval.query", # Используем LoRA для запросов
            batch_size=1, # Для одного запроса батч = 1
            normalize_embeddings=True # Jina рекомендует нормализацию
        )
        # Проверка типа и формы перед возвратом
        if embeddings is not None and embeddings.ndim == 2 and embeddings.shape[0] == 1:
            return embeddings[0].tolist() # Возвращаем как список float
        else:
             # Логирование или обработка ошибки, если эмбеддинг не получен
             print(f"Предупреждение: Не удалось получить корректный эмбеддинг для запроса: {query}. Возвращен нулевой вектор.")
             return [0.0] * embedding_dim


    def _get_text_embedding(self, text: str) -> Embedding:
        """Получает эмбеддинг для документа (passage)."""
        if not self._model:
            raise ValueError("Модель эмбеддингов не инициализирована.")
        
        embedding_dim = self._model.get_sentence_embedding_dimension()
        if not embedding_dim:
            print("Ошибка: Не удалось определить размерность эмбеддингов.")
            return []
            
        embeddings = self._model.encode(
            [text], 
            task="retrieval.passage", # Используем LoRA для документов
            batch_size=1,
            normalize_embeddings=True
        )
        if embeddings is not None and embeddings.ndim == 2 and embeddings.shape[0] == 1:
            return embeddings[0].tolist()
        else:
             print(f"Предупреждение: Не удалось получить корректный эмбеддинг для текста: {text[:100]}... Возвращен нулевой вектор.")
             return [0.0] * embedding_dim

    def _get_text_embeddings(self, texts: List[str]) -> List[Embedding]:
        """Получает эмбеддинги для списка документов (passages)."""
        if not self._model:
            raise ValueError("Модель эмбеддингов не инициализирована.")

        embedding_dim = self._model.get_sentence_embedding_dimension()
        if not embedding_dim:
            print("Ошибка: Не удалось определить размерность эмбеддингов.")
            # Возвращаем список пустых списков, если не можем определить размерность для нулевых векторов
            return [[] for _ in texts] 

        # Убираем пустые строки или нестроковые элементы, сохраняя индексы для восстановления
        valid_texts_with_indices = []
        for i, t in enumerate(texts):
            if isinstance(t, str) and len(t.strip()) > 0:
                valid_texts_with_indices.append((t, i))
        
        valid_texts = [item[0] for item in valid_texts_with_indices]
        original_indices = [item[1] for item in valid_texts_with_indices]

        # Инициализируем список результатов нулевыми векторами (или пустыми, если размерность неизвестна)
        # Это гарантирует, что список будет той же длины, что и входной `texts`
        default_embedding = [0.0] * embedding_dim if embedding_dim else []
        result_embeddings: List[Embedding] = [default_embedding[:] for _ in texts] # Используем [:] для копирования

        if not valid_texts:
            print("Предупреждение: В батче нет валидных текстов для эмбеддинга. Возвращены нулевые векторы.")
            return result_embeddings 
        
        try:    
            encoded_embeddings = self._model.encode(
                valid_texts, 
                task="retrieval.passage", 
                batch_size=self.embed_batch_size, # Используем размер батча из настроек
                normalize_embeddings=True,
                show_progress_bar=False # Можно включить при необходимости
            )
            
            # Заполняем result_embeddings полученными эмбеддингами на их оригинальные позиции
            for i, emb_array in enumerate(encoded_embeddings):
                original_idx = original_indices[i]
                if emb_array is not None:
                    result_embeddings[original_idx] = emb_array.tolist()
                # else: оставляем default_embedding, если по какой-то причине encode вернул None для валидного текста
                     
            return result_embeddings
            
        except Exception as e:
            print(f"Ошибка при кодировании батча текстов: {e}. Возвращены нулевые векторы для всего батча.")
            # В случае общей ошибки, все равно возвращаем список нулевых векторов нужной длины
            return [default_embedding[:] for _ in texts]


    # --- Асинхронные методы (используем to_thread) ---

    async def _aget_query_embedding(self, query: str) -> Embedding:
        """Асинхронно получает эмбеддинг для запроса."""
        return await asyncio.to_thread(self._get_query_embedding, query)

    async def _aget_text_embedding(self, text: str) -> Embedding:
        """Асинхронно получает эмбеддинг для документа."""
        return await asyncio.to_thread(self._get_text_embedding, text)

    async def _aget_text_embeddings(self, texts: List[str]) -> List[Embedding]:
        """Асинхронно получает эмбеддинги для списка документов."""
        return await asyncio.to_thread(self._get_text_embeddings, texts) 