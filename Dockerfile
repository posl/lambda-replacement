# ==================================================
# Builder stage
# ==================================================
FROM ubuntu:24.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive
ARG SRCML_VERSION=1.1.0
ARG GUMTREE_VERSION=4.0.0-beta3

ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

RUN apt update && apt install -y --no-install-recommends \
    build-essential \
    cmake \
    git curl wget \
    openjdk-17-jdk \
    ocaml libnum-ocaml-dev \
    libxml2-dev libxslt1-dev \
    libarchive-dev \
    libcurl4-openssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# --------------------------
# build srcML
# --------------------------
RUN curl -L https://github.com/srcML/srcML/archive/refs/tags/v${SRCML_VERSION}.tar.gz \
    | tar xz && \
    mv srcML-${SRCML_VERSION} srcML && \
    cmake -S srcML -B srcML/build && \
    cmake --build srcML/build -j$(nproc) && \
    cmake --install srcML/build --prefix=/opt/srcML

# --------------------------
# build GumTree
# --------------------------
RUN curl -L https://github.com/GumTreeDiff/gumtree/archive/refs/tags/v${GUMTREE_VERSION}.tar.gz \
    | tar xz && \
    mv gumtree-${GUMTREE_VERSION} gumtree && \
    JAVA_TOOL_OPTIONS="-Dfile.encoding=UTF-8" \
    gumtree/gradlew -p gumtree build

# ==================================================
# Runtime stage (FINAL IMAGE)
# ==================================================
FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG TZ=Asia/Tokyo

ARG UID=1000
ARG GID=1000

RUN groupadd -g $GID exp && \
    useradd -m -u $UID -g $GID exp

ENV TZ=${TZ}
ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    JAVA_TOOL_OPTIONS=-Dfile.encoding=UTF-8 \
    PATH="/root/.local/bin:${PATH}"

# ---- runtime dependencies only ----
RUN apt update && apt install -y --no-install-recommends \
    openjdk-17-jre \
    python3 python3-pip python3-dev \
    nodejs npm \
    curl ca-certificates tzdata \
    libxml2 libxslt1.1 \
    libarchive13 \
    libcurl4 \
    git maven openssh-client\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/local/bin

# --------------------------
# copy built binaries
# --------------------------
# ----- srcML -----
COPY --from=builder /opt/srcML /opt/srcml
ENV PATH="/opt/srcml/bin:${PATH}"

RUN echo "/opt/srcml/lib" > /etc/ld.so.conf.d/srcml.conf && ldconfig

# ----- GumTree -----
COPY --from=builder \
    /opt/gumtree/dist/build/install/gumtree \
    /opt/gumtree

ENV PATH="/opt/gumtree/bin:${PATH}"

# ==================================================
# Python environment (uv)
# ==================================================
USER exp
WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN uv python install 3.12 && \
    uv sync


RUN git config --global --add safe.directory '*'

CMD ["/bin/bash"]
