#!/bin/sh
cd /app

# Устанавливаем зависимости если не установлены (fallback если образ собрался без них)
pip install --no-cache-dir --timeout 60 \
  -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
  -r requirements.txt || \
pip install --no-cache-dir --timeout 60 \
  -i https://mirrors.aliyun.com/pypi/simple/ \
  -r requirements.txt || \
echo "⚠️ pip install failed, continuing with existing packages"

echo "🖥 ЗАПУСК ДАШБОРДА (В ФОНЕ)..."
# Запускаем сайт в фоновом режиме (& в конце), логи сайта нам не особо важны сейчас
python3 -m streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0 > /dev/null 2>&1 &

echo "🤖 ЗАПУСК БОТА (В ГЛАВНОМ ПОТОКЕ)..."
# Запускаем бота БЕЗ перенаправления вывода. Теперь все ошибки будут видны в Docker logs.
# Если бот упадет, контейнер перезагрузится (если настроен restart policy).
python3 -u main.py