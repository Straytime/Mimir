FROM e2bdev/code-interpreter:latest

RUN apt-get update \
    && apt-get install -y --no-install-recommends fontconfig \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/local/share/fonts/noto-cjk

COPY assets/fonts/NotoSansCJKsc-Regular.otf /usr/local/share/fonts/noto-cjk/NotoSansCJKsc-Regular.otf

RUN fc-cache -f -v
